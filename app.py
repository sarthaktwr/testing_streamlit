import streamlit as st
import pandas as pd
import time
import pydeck as pdk
from datetime import datetime
from typing import List, Tuple

# Constants
PROXIMITY_THRESHOLD = 500  # meters
ANIMATION_DELAY = 0.1  # seconds

# Icon URLs
AIRPLANE_ICON_URL = "https://cdn-icons-png.flaticon.com/512/808/808484.png"
BOMB_ICON_URL = "https://cdn-icons-png.flaticon.com/512/3460/3460388.png"

# Session state initialization
if 'alerts' not in st.session_state:
    st.session_state.alerts = {}
if 'alert_sent' not in st.session_state:
    st.session_state.alert_sent = False

# Utility functions
def calculate_3d_distance(p1: Tuple[float, float, float], p2: Tuple[float, float, float]) -> float:
    return ((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2 + (p1[2] - p2[2])**2) ** 0.5

def create_layers(ground_loc: Tuple[float, float, float], path: List[List[float]], aircraft_pos: Tuple[float, float], show_bomb: bool) -> List[pdk.Layer]:
    layers = []

    # Path Layer
    layers.append(pdk.Layer(
        'PathLayer',
        [{'coordinates': path}],
        get_path='coordinates',
        get_width=5,
        get_color=[255, 0, 0],
        width_scale=20
    ))

    # Aircraft Icon
    layers.append(pdk.Layer(
        'IconLayer',
        data=[{
            'position': [aircraft_pos[1], aircraft_pos[0]],
            'icon_data': {
                'url': AIRPLANE_ICON_URL,
                'width': 128,
                'height': 128,
                'anchorY': 128,
            },
        }],
        get_icon='icon_data',
        get_size=4,
        size_scale=10,
        get_position='position',
        pickable=False
    ))

    # Bomb Icon on Ground (if aircraft is in range)
    if show_bomb:
        layers.append(pdk.Layer(
            'IconLayer',
            data=[{
                'position': [ground_loc[1], ground_loc[0]],
                'icon_data': {
                    'url': BOMB_ICON_URL,
                    'width': 128,
                    'height': 128,
                    'anchorY': 128,
                },
            }],
            get_icon='icon_data',
            get_size=4,
            size_scale=10,
            get_position='position',
            pickable=False
        ))

    return layers

def send_alert(unit: str):
    st.session_state.alerts[unit] = f"ALERT SENT to {unit} at {datetime.now().strftime('%H:%M:%S')}"
    st.session_state.alert_sent = True

# Command center page
def command_center():
    st.title("🛡️ Command Center")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Ground Location")
        ground = (
            st.number_input("Latitude", value=28.6139),
            st.number_input("Longitude", value=77.2090),
            st.number_input("Elevation (m)", value=0.0),
        )

    with col2:
        st.subheader("Upload Aircraft Path CSV")
        uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            req_cols = ['latitude_wgs84(deg)', 'longitude_wgs84(deg)', 'elevation_wgs84(m)']
            if not all(col in df.columns for col in req_cols):
                st.error("CSV missing required columns.")
                return

            path = []
            chart = st.empty()
            status = st.empty()
            progress = st.progress(0)

            for i, row in df.iterrows():
                aircraft_pos = (
                    row['latitude_wgs84(deg)'],
                    row['longitude_wgs84(deg)'],
                    row['elevation_wgs84(m)']
                )
                distance = calculate_3d_distance(ground, aircraft_pos)
                path.append([aircraft_pos[1], aircraft_pos[0]])  # lon, lat

                view_state = pdk.ViewState(
                    latitude=aircraft_pos[0],
                    longitude=aircraft_pos[1],
                    zoom=10,
                    pitch=45
                )

                show_bomb = distance <= PROXIMITY_THRESHOLD
                layers = create_layers(ground, path, aircraft_pos, show_bomb)

                chart.pydeck_chart(pdk.Deck(
                    layers=layers,
                    initial_view_state=view_state,
                    map_style='mapbox://styles/mapbox/satellite-streets-v11'
                ))

                status.metric("Distance (m)", f"{distance:.2f}")
                progress.progress((i + 1) / len(df))

                if show_bomb and not st.session_state.alert_sent:
                    st.warning(f"🚨 Aircraft within {distance:.2f}m! Engage?")
                    col_a, col_b = st.columns(2)
                    if col_a.button("🚀 ALERT GROUND UNIT", key=f"g{row.name}"):
                        send_alert("ground_unit")
                        st.success("Alert sent to Ground Unit!")
                    if col_b.button("✈️ ALERT AIRCRAFT", key=f"a{row.name}"):
                        send_alert("aircraft")
                        st.success("Alert sent to Aircraft!")

                time.sleep(ANIMATION_DELAY)

            st.success("✔️ Simulation complete.")
        except Exception as e:
            st.error("Failed to process the CSV.")
            st.exception(e)

# Ground Unit or Aircraft Page
def unit_dashboard(unit_name: str):
    st.title(f"🎯 {unit_name.replace('_', ' ').upper()} Dashboard")

    if st.session_state.alerts.get(unit_name):
        st.warning(st.session_state.alerts[unit_name])
        if st.button("✅ Acknowledge Alert"):
            st.session_state.alerts[unit_name] = ""
            st.session_state.alert_sent = False
            st.success("Alert acknowledged.")
    else:
        st.success("✅ No alerts.")

# Main app
def main():
    page = st.sidebar.radio("Select Role", ["Command Center", "Ground Unit", "Aircraft"])
    if page == "Command Center":
        command_center()
    elif page == "Ground Unit":
        unit_dashboard("ground_unit")
    else:
        unit_dashboard("aircraft")

if __name__ == "__main__":
    main()
