import streamlit as st
import pandas as pd
import time
import pydeck as pdk
from datetime import datetime
from typing import List, Tuple

# Constants
COLORS = {"status_background": "#f0f0f5", "button_background": "#ff6347"}
PROXIMITY_THRESHOLD = 500  # meters (example threshold for alert)
ANIMATION_DELAY = 0.1  # delay for animation speed

# Function to calculate zoom level based on latitude and longitude bounds
def calculate_zoom(min_lat, max_lat, min_lon, max_lon) -> int:
    lat_diff = max_lat - min_lat
    lon_diff = max_lon - min_lon
    zoom = 10  # Default zoom
    if lat_diff > 2 or lon_diff > 2:
        zoom = 5  # Less zoom for larger area
    return zoom

# Function to calculate 3D distance between ground position and aircraft position
def calculate_3d_distance(ground_loc: Tuple[float, float, float], aircraft: Tuple[float, float, float]) -> float:
    lat1, lon1, elev1 = ground_loc
    lat2, lon2, elev2 = aircraft
    # Simple Euclidean distance calculation (can be replaced with Haversine for accurate lat-lon distances)
    distance = ((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2 + (elev2 - elev1) ** 2) ** 0.5
    return distance

# Function to create layers for pydeck map
def create_layers(ground_loc: Tuple[float, float, float], path: List[List[float]]) -> List[pdk.Layer]:
    path_layer = pdk.Layer(
        'PathLayer',
        path,
        get_path='coordinates',
        get_width=5,
        get_color=[255, 0, 0, 140],
        width_scale=20,
    )
    return [path_layer]

# Function to simulate sending alert (you can modify this to integrate actual alerting system)
def send_alert(unit: str):
    alert_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.alerts[unit] = f"ALERT SENT to {unit} at {alert_time}"

# Command Center Function (sending alerts to Ground Unit or Aircraft)
def command_center() -> None:
    """Render command center dashboard."""
    st.title('🛡️ COMMAND CENTER DASHBOARD')

    with st.expander("CONFIGURATION", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader('GROUND POSITION')
            ground = (
                st.number_input('LATITUDE', value=28.6139, format='%f', key='lat'),
                st.number_input('LONGITUDE', value=77.2090, format='%f', key='lon'),
                st.number_input('ELEVATION (m)', value=0.0, format='%f', key='elev')
            )

        with col2:
            st.subheader('AIRCRAFT PATH')
            csv = st.file_uploader("UPLOAD CSV", type="csv", help="CSV with columns: latitude_wgs84(deg), longitude_wgs84(deg), elevation_wgs84(m)")

    if csv:
        try:
            df = pd.read_csv(csv)
            req_cols = ['latitude_wgs84(deg)', 'longitude_wgs84(deg)', 'elevation_wgs84(m)']
            
            if not all(col in df.columns for col in req_cols):
                st.error(f'MISSING COLUMNS: {", ".join(req_cols)}')
                return

            df['path'] = df[['longitude_wgs84(deg)', 'latitude_wgs84(deg)']].values.tolist()

            # Calculate view bounds
            min_lat, max_lat = df['latitude_wgs84(deg)'].min(), df['latitude_wgs84(deg)'].max()
            min_lon, max_lon = df['longitude_wgs84(deg)'].min(), df['longitude_wgs84(deg)'].max()
            min_lat, max_lat = min(min_lat, ground[0]), max(max_lat, ground[0])
            min_lon, max_lon = min(min_lon, ground[1]), max(max_lon, ground[1])

            view = pdk.ViewState(
                latitude=(min_lat + max_lat) / 2, 
                longitude=(min_lon + max_lon) / 2, 
                zoom=calculate_zoom(min_lat, max_lat, min_lon, max_lon), 
                pitch=50
            )

            path = []
            map_area = st.empty()
            status_box = st.empty()
            alert_sent = False

            progress_bar = st.progress(0)
            total_frames = len(df)

            for idx, row in df.iterrows():
                progress_bar.progress((idx + 1) / total_frames)
                path.append(row['path'])
                aircraft = (
                    row['latitude_wgs84(deg)'], 
                    row['longitude_wgs84(deg)'], 
                    row['elevation_wgs84(m)']
                )
                distance = calculate_3d_distance(ground, aircraft)

                # Update view to follow aircraft
                view.latitude = aircraft[0]
                view.longitude = aircraft[1]

                # Update map
                map_area.pydeck_chart(pdk.Deck(
                    layers=create_layers(ground, path),
                    initial_view_state=view,
                    map_style='mapbox://styles/mapbox/satellite-streets-v11'
                ))

                # Update status
                status_text = f"""
                <div style="padding:10px;border-radius:5px;background-color:{COLORS['status_background']};">
                    <h4>STATUS</h4>
                    <p>Aircraft Frame: {idx+1}/{len(df)}</p>
                    <p>Distance: {distance:.2f}m</p>
                    <p>Status: {'⚠️ ENGAGEMENT RANGE' if distance <= PROXIMITY_THRESHOLD else '✅ CLEAR'}</p>
                </div>
                """
                status_box.markdown(status_text, unsafe_allow_html=True)

                if distance <= PROXIMITY_THRESHOLD and not alert_sent:
                    st.warning(f"⚠️ AIRCRAFT IN RANGE ({distance:.2f}m)")
                    alert_cols = st.columns(2)
                    with alert_cols[0]:
                        if st.button("🚀 ALERT GROUND UNIT", key=f"g{idx}"):
                            send_alert('ground_unit')
                            alert_sent = True
                            st.session_state.alert_sent = True  # Store alert status in session

                    with alert_cols[1]:
                        if st.button("✈️ ALERT AIRCRAFT", key=f"a{idx}"):
                            send_alert('aircraft')
                            alert_sent = True
                            st.session_state.alert_sent = True  # Store alert status in session

                time.sleep(ANIMATION_DELAY)

            progress_bar.empty()
            st.success("Aircraft path simulation completed")

        except Exception as e:
            st.error(f"PROCESSING ERROR: {str(e)}")
            st.exception(e)

# Unit Interface Function (Ground Unit or Aircraft)
def unit_interface(unit: str) -> None:
    """Render interface for ground unit or aircraft."""
    name = unit.replace("_", " ").upper()
    st.title(f"🎯 {name} DASHBOARD")
    st.markdown("---")

    # Check if there is a pending alert
    if hasattr(st.session_state, 'alert_sent') and st.session_state.alert_sent:
        st.warning("⚠️ ALERT PENDING ACKNOWLEDGEMENT")
        if st.button("✅ ACKNOWLEDGE ALERT"):
            st.session_state.alert_sent = False  # Reset alert status
            st.session_state.alerts[unit] = []  # Clear any previous alerts for this unit
            st.success("Alert Acknowledged. Ready for next alert.")
            st.session_state.last_refresh = datetime.now()
            st.rerun()
    else:
        st.success("✅ NO ACTIVE ALERTS")

# Main Function
def main():
    # Initialize session state if it doesn't exist
    if 'alerts' not in st.session_state:
        st.session_state.alerts = {}
    if 'alert_sent' not in st.session_state:
        st.session_state.alert_sent = False
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = datetime.now()

    page = st.sidebar.radio("Select Page", ['Command Center', 'Ground Unit', 'Aircraft'])

    if page == 'Command Center':
        command_center()
    elif page == 'Ground Unit':
        unit_interface('ground_unit')
    elif page == 'Aircraft':
        unit_interface('aircraft')

if __name__ == "__main__":
    main()
