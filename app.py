import streamlit as st
from geopy.distance import geodesic
import math
import pandas as pd
import pydeck as pdk
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
import json

# Constants
PROXIMITY_THRESHOLD = 4500  # in meters
# User Credentials
USER_CREDENTIALS = {
    "command": {"username": "command", "password": "center123"},
    "ground": {"username": "ground", "password": "unit123"},
    "aircraft": {"username": "aircraft", "password": "flight123"},
}

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
google_credentials = json.loads(st.secrets['google_credentials']['value'])
creds = Credentials.from_service_account_info(google_credentials, scopes=scope)
client = gspread.authorize(creds)

# Initialize all session state variables
def init_session_state():
    required_states = {
        'logged_in': False,
        'role': None,
        'alert_sent_ground': False,
        'alert_sent_aircraft': False,
        'ground_position': (28.6139, 77.2090, 0.0),
        'alert_log': [],
        'unit_logs': {"ground": [], "aircraft": []}  # Separate logs for each unit
    }

    for key, value in required_states.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Helper Functions
def calculate_3d_distance(loc1, loc2):
    """
    Calculates the 3D distance between two locations.
    Args:
    loc1 (tuple): The 3D coordinates of the first location.
    loc2 (tuple): The 3D coordinates of the second location.
    Returns:
    float: The 3D distance between the two locations in meters.
    """
    surface_distance = geodesic((loc1[0], loc1[1]), (loc2[0], loc2[1])).meters
    elevation_difference = abs(loc1[2] - loc2[2])
    distance_3d = math.sqrt(surface_distance**2 + elevation_difference**2)
    return distance_3d

def send_alert_to_unit(unit_type, sheet):
    """
    Sends an alert to a specific unit type.
    Args:
    unit_type (str): The type of unit to send the alert to.
    Returns:
    None
    """
    current_time = datetime.utcnow().isoformat()
    sheet.append_row([current_time, 'True', unit_type])
    st.session_state['alert_sent'] = True
    st.write(f"Alert sent to {unit_type}!")

def create_alerts_sheet():
    """
    Creates a Google Sheet to store alerts.
    Returns:
    gspread.Spreadsheet: The created Google Sheet.
    """
    sheet = client.create('Aircraft Proximity Alert System')
    sheet.share('aksh30990@gmail.com', perm_type='user', role='writer')
    worksheet = sheet.sheet1
    worksheet.append_row(['Time', 'Alert', 'Unit Type'])

def check_for_alerts():
    """
    Checks if there are any alerts in the Google Sheet.
    Returns:
    bool: True if there are alerts, False otherwise.
    """
    sheet = client.open('Aircraft Proximity Alert System').sheet1
    alerts = sheet.get_all_records()
    if alerts:
        latest_alert = alerts[-1]
        if latest_alert['Alert'] == 'True':
            return latest_alert

def login_user(username, password):
    """
    Logs in a user with the given username and password.
    Args:
    username (str): The username of the user to log in.
    password (str): The password of the user to log in.
    Returns:
    None
    """
    for role, credentials in USER_CREDENTIALS.items():
        if credentials['username'] == username and credentials['password'] == password:
            st.session_state['role'] = role
            st.session_state['logged_in'] = True
            st.success(f'Logged in as {role}')
            st.rerun()  # Rerun the app to reflect the new user role
            return
    st.error('Incorrect username or password')

# Login form
def login():
    st.title("🔐 Secure Login")
    role = st.selectbox("Login As", ["Command Center", "Ground Unit", "Aircraft"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        login_user(username, password)

# Command Center Dashboard
def command_center_dashboard():
    st.title('Command Center Dashboard')
    st.title('Aircraft Proximity Alert System')
    try:
        sheet = client.open('Aircraft Proximity Alert System').sheet1
    except gspread.SpreadsheetNotFound:
        create_alerts_sheet()
        sheet = create_alerts_sheet()

    # Input fields for the ground unit location
    st.subheader('Ground Unit Location')
    ground_lat = st.number_input('Latitude (deg)', value=0.0, format='%f')
    ground_lon = st.number_input('Longitude (deg)', value=0.0, format='%f')
    ground_elev = st.number_input('Elevation (meters)', value=0.0, format='%f')
    ground_unit_location = (ground_lat, ground_lon, ground_elev)

    # File uploader for the aircraft location CSV
    st.subheader('Upload Aircraft Location CSV')
    csv_file = st.file_uploader("Choose a CSV file", type="csv")

    if csv_file is not None:
        # Reset alert states when a new CSV file is uploaded
        st.session_state['alert_sent_ground'] = False
        st.session_state['alert_sent_aircraft'] = False

        # Read the CSV file into a DataFrame
        df = pd.read_csv(csv_file)

        # Ensure the required columns are present
        required_columns = ['latitude_wgs84(deg)', 'longitude_wgs84(deg)', 'elevation_wgs84(m)']
        if all(col in df.columns for col in required_columns):
            # Create a new column for the path to match PyDeck's input format
            df['path'] = df[['longitude_wgs84(deg)', 'latitude_wgs84(deg)']].values.tolist()

            # Define the initial view state of the map
            view_state = pdk.ViewState(
                latitude=df['latitude_wgs84(deg)'].mean(),
                longitude=df['longitude_wgs84(deg)'].mean(),
                zoom=11,
                pitch=50,
            )

            # Create a placeholder for the map
            map_placeholder = st.empty()

            # Create a DataFrame for the ground unit
            ground_unit_df = pd.DataFrame({
                'latitude': [ground_unit_location[0]],
                'longitude': [ground_unit_location[1]],
                'elevation': [ground_unit_location[2]],
            })

            # Icon layer for the square point
            icon_data = pd.DataFrame({
                'coordinates': [[ground_unit_location[1], ground_unit_location[0]]],
            })

            # Create the path layer for the aircraft's movement
            path_layer = pdk.Layer(
                "PathLayer",
                data=df,
                get_path="path",
                get_color=[255, 0, 0, 150],  # Red color for the path
                width_scale=20,
                width_min_pixels=2,
                get_width=5,
            )

            # Create the scatterplot layer for the ground unit's circle
            scatter_layer = pdk.Layer(
                "ScatterplotLayer",
                data=ground_unit_df,
                get_position=["longitude", "latitude"],
                get_fill_color=[0, 0, 255, 50],  # Light blue color for the circle
                get_radius=2500,  # 2.5km radius
                pickable=True,
            )

            # Create the icon layer for the ground unit's square point
            icon_layer = pdk.Layer(
                "IconLayer",
                data=icon_data,
                get_icon={
                    "url": "https://img.icons8.com/windows/32/000000/square-full.png",  # URL for a square icon
                    "width": 128,
                    "height": 128,
                    "anchorY": 128,
                },
                get_position="coordinates",
                get_size=10,  # Size of the square
                size_scale=10,
                pickable=True,
            )

            # Create the deck.gl map with all layers
            r = pdk.Deck(
                layers=[path_layer, scatter_layer, icon_layer],
                initial_view_state=view_state,
                map_style="mapbox://styles/mapbox/light-v9",
            )

            # Render the updated map in the same placeholder
            map_placeholder.pydeck_chart(r)

            # Display buttons dynamically
            for index, row in df.iterrows():
                aircraft_location = (
                    row['latitude_wgs84(deg)'],
                    row['longitude_wgs84(deg)'],
                    row['elevation_wgs84(m)']
                )

                # Display buttons dynamically
                col1, col2 = st.columns(2)

                with col1:
                    if st.button("Priority to Ground Unit", key=f"ground_unit_{index}"):
                        distance_to_ground = calculate_3d_distance(ground_unit_location, aircraft_location)
                        if distance_to_ground <= PROXIMITY_THRESHOLD:
                            send_alert_to_unit('ground_unit', sheet)
                        else:
                            st.warning("Aircraft is out of range for ground unit.")

                with col2:
                    if st.button("Priority to Aircraft", key=f"aircraft_{index}"):
                        distance_to_ground = calculate_3d_distance(ground_unit_location, aircraft_location)
                        if distance_to_ground <= PROXIMITY_THRESHOLD:
                            send_alert_to_unit('aircraft', sheet)
                        else:
                            st.warning("Aircraft is out of range for aircraft alert.")

        else:
            st.error('CSV file must contain latitude, longitude, and elevation columns.')

    elif st.session_state['role'] == 'ground':
        # Ground unit interface
        st.title('Ground Unit Dashboard')
        system_alerts = check_for_alerts()
        if system_alerts is not None:
            if system_alerts['Unit Type'] == 'ground_unit':
                st.error('Keep Firing.')
            else:
                st.error('Friendly aircraft approaching. Stop Firing!')

    elif st.session_state['role'] == 'aircraft':
        # Aircraft interface
        st.title('Aircraft Dashboard')
        system_alerts = check_for_alerts()
        if system_alerts is not None:
            if system_alerts['Unit Type'] == 'ground_unit':
                st.error('Ground Unit Firing. Reroute the current path.')
            else:
                st.error('Clearance to fly.')

# Main
def main():
    init_session_state()

    if not st.session_state.logged_in:
        login()
    else:
        role = st.session_state.role
        st.sidebar.success(f"Logged in as {role.upper()}")
        if st.sidebar.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        if role == "command":
            command_center_dashboard()
        elif role == "ground":
            unit_dashboard("ground")
        elif role == "aircraft":
            unit_dashboard("aircraft")

if __name__ == "__main__":
    main()
