import streamlit as st
import pandas as pd
import time
import pydeck as pdk
from datetime import datetime
from typing import List, Tuple

# Constants
COLORS = {"status_background": "#f0f0f5", "button_background": "#ff6347"}
PROXIMITY_THRESHOLD = 500  # meters
ANIMATION_DELAY = 0.1

# Icons
AIRCRAFT_ICON_URL = "https://cdn-icons-png.flaticon.com/512/287/287221.png"
BOMB_ICON_URL = "https://cdn-icons-png.flaticon.com/512/4389/4389779.png"

def calculate_zoom(min_lat, max_lat, min_lon, max_lon) -> int:
    lat_diff = max_lat - min_lat
    lon_diff = max_lon - min_lon
    zoom = 10
    if lat_diff > 2 or lon_diff > 2:
        zoom = 5
    return zoom

def calculate_3d_distance(ground_loc: Tuple[float, float, float], aircraft: Tuple[float, float, float]) -> float:
    lat1, lon1, elev1 = ground_loc
    lat2, lon2, elev2 = aircraft
    distance = ((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2 + (elev2 - elev1) ** 2) ** 0.5
    return distance

def create_layers(ground_loc: Tuple[float, float, float], path: List[List[float]], current_aircraft_pos: List[float]) -> List[pdk.Layer]:
    layers = [
        pdk.Layer(
            'PathLayer',
            data=[{"coordinates": path}],
            get_path='coordinates',
            get_width=5,
            get_color=[255, 0, 0],
            width_scale=20,
        ),
        pdk.Layer(
            'ScatterplotLayer',
            data=[{"position": [ground_loc[1], ground_loc[0]]}],
            get_position='position',
            get_color=[0, 128, 0],
            get_radius=100,
            pickable=True
        ),
        pdk.Layer(
            "IconLayer",
            data=[
                {
                    "position": current_aircraft_pos,
                    "icon": {"url": AIRCRAFT_ICON_URL, "width": 128, "height": 128, "anchorY": 128}
                },
                {
                    "position": [ground_loc[1], ground_loc[0]],
                    "icon": {"url": BOMB_ICON_URL, "width": 128, "height": 128, "anchorY": 128}
                }
            ],
            get_icon="icon",
            get_size=4,
            size_scale=15,
            get_position="position"
        )
    ]
    return layers

def send_priority(unit: str, message: str):
    st.session_state.fwg_messages[unit] = message
    st.toast(f"FWG message sent to {unit}: {message}")

def command_center():
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
            csv = st.file_uploader("UPLOAD CSV", type="csv", help="CSV with latitude, longitude, elevation")

    if csv:
        try:
            df = pd.read_csv(csv)
            req_cols = ['latitude_wgs84(deg)', 'longitude_wgs84(deg)', 'elevation_wgs84(m)']
            if not all(col in df.columns for col in req_cols):
                st.error(f'MISSING COLUMNS: {", ".join(req_cols)}')
                return

            df['path'] = df[['longitude_wgs84(deg)', 'latitude_wgs84(deg)']].values.tolist()
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
            progress_bar = st.progress(0)

            for idx, row in df.iterrows():
                progress_bar.progress((idx + 1) / len(df))
                path.append(row['path'])
                aircraft = (row['latitude_wgs84(deg)'], row['longitude_wgs84(deg)'], row['elevation_wgs84(m)'])
                aircraft_pos = [row['longitude_wgs84(deg)'], row['latitude_wgs84(deg)']]
                distance = calculate_3d_distance(ground, aircraft)

                view.latitude, view.longitude = aircraft[0], aircraft[1]
                layers = create_layers(ground, path, aircraft_pos)

                map_area.pydeck_chart(pdk.Deck(
                    layers=layers,
                    initial_view_state=view,
                    map_style='mapbox://styles/mapbox/satellite-streets-v11'
                ))

                status_box.markdown(f"""
                <div style="padding:10px;background-color:{COLORS['status_background']};border-radius:5px;">
                    <h4>STATUS</h4>
                    <p>Aircraft Frame: {idx+1}/{len(df)}</p>
                    <p>Distance: {distance:.2f}m</p>
                    <p>Status: {'⚠️ PRIORITY RANGE' if distance <= PROXIMITY_THRESHOLD else '✅ CLEAR'}</p>
                </div>
                """, unsafe_allow_html=True)

                if distance <= PROXIMITY_THRESHOLD and not st.session_state.priority_sent:
                    st.warning(f"⚠️ AIRCRAFT IN RANGE ({distance:.2f}m)")
                    priority_to = st.radio("Send Priority To:", ["Aircraft", "Gun"], key=f"priority_{idx}")
                    if st.button("🚨 SEND PRIORITY", key=f"send_priority_{idx}"):
                        if priority_to == "Aircraft":
                            send_priority("gun", "Stop Firing")
                            send_priority("aircraft", "Clearance to continue flight")
                        else:
                            send_priority("gun", "Continue Firing")
                            send_priority("aircraft", "Danger Area Reroute immediately")
                        st.session_state.priority_sent = True

                time.sleep(ANIMATION_DELAY)

            progress_bar.empty()
            st.success("✅ Simulation complete")

        except Exception as e:
            st.error(f"Error: {str(e)}")

def unit_interface(unit: str):
    name = unit.replace("_", " ").upper()
    st.title(f"🎯 {name} DASHBOARD")
    st.markdown("---")

    if st.session_state.fwg_messages.get(unit):
        st.warning(f"📨 FWG Message: {st.session_state.fwg_messages[unit]}")
        if st.button("✅ Acknowledge"):
            st.session_state.fwg_messages[unit] = ""
            st.session_state.priority_sent = False
            st.success("Acknowledged. Awaiting further instruction.")
            st.rerun()
    else:
        st.success("✅ NO ACTIVE MESSAGES")

def main():
    if 'fwg_messages' not in st.session_state:
        st.session_state.fwg_messages = {}
    if 'priority_sent' not in st.session_state:
        st.session_state.priority_sent = False

    page = st.sidebar.radio("Select Page", ['Command Center', 'Ground Unit', 'Aircraft'])

    if page == 'Command Center':
        command_center()
    elif page == 'Ground Unit':
        unit_interface('gun')
    elif page == 'Aircraft':
        unit_interface('aircraft')

if __name__ == "__main__":
    main()
