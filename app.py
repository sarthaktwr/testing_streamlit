import streamlit as st
import pandas as pd
import time
import pydeck as pdk
from datetime import datetime
from typing import List, Tuple

# Constants
PROXIMITY_THRESHOLD = 500  # meters
ANIMATION_DELAY = 0.1  # seconds

# GIF URLs
AIRPLANE_GIF_URL = "https://media.giphy.com/media/WFZvB7VIXBgiz3oDXE/giphy.gif"
BOMBING_GIF_URL = "https://media.giphy.com/media/3o7btPCcdNniyf0ArS/giphy.gif"

# Session state initialization
if 'alerts' not in st.session_state:
    st.session_state.alerts = {}
if 'alert_sent' not in st.session_state:
    st.session_state.alert_sent = False

# Utility functions
def calculate_3d_distance(p1: Tuple[float, float, float], p2: Tuple[float, float, float]) -> float:
    return ((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2 + (p1[2] - p2[2])**2) ** 0.5

def create_layers(ground_loc: Tuple[float, float, float], path: List[List[float]]) -> List[pdk.Layer]:
    return [pdk.Layer(
        'PathLayer',
        [{'coordinates': path}],
        get_path='coordinates',
        get_width=5,
        get_color=[255, 0, 0],
        width_scale=20
    )]

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
            gif_display = st.empty()
            progress = st.progress(0)

            for i, row in df.iterrows():
                aircraft_pos = (
                    row['latitude_wgs84(deg)'],
                    row['longitude_wgs84(deg)'],
                    row['elevation_wgs84(m)']
                )
                distance = calculate_3d_distance(ground, aircraft_pos)
                path.append([aircraft_pos[1], aircraft_pos[0]])  # lon, lat

                # Map view
                view_state = pdk.ViewState(
                    latitude=aircraft_pos[0],
                    longitude=aircraft_pos[1],
                    zoom=10,
                    pitch=45
                )
                chart.pydeck_chart(pdk.Deck(
                    layers=create_layers(ground, path),
                    initial_view_state=view_state,
                    map_style='mapbox://styles/mapbox/satellite-streets-v11'
                ))

                # Distance status
                status.metric("Distance (m)", f"{distance:.2f}")
                progress.progress((i + 1) / len(df))

                # Display airplane gif
                gif_display.image(AIRPLANE_GIF_URL, width=100)

                # Bombing gif if within range
                if distance <= PROXIMITY_THRESHOLD and not st.session_state.alert_sent:
                    st.warning(f"🚨 Aircraft within {distance:.2f}m! Engage?")
                    st.image(BOMBING_GIF_URL, width=150)
                    if st.button("🚀 ALERT GROUND UNIT"):
                        send_alert("ground_unit")
                        st.success("Alert sent to Ground Unit!")
                    if st.button("✈️ ALERT AIRCRAFT"):
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
