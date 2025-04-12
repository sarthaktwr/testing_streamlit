# import streamlit as st
# from geopy.distance import geodesic
# import math
# import time
# import pandas as pd
# import pydeck as pdk
# import gspread
# from datetime import datetime
# from shapely.geometry import Point, mapping
# import geopandas as gpd
# from google.oauth2.service_account import Credentials
# import json

# # Constants
# PROXIMITY_THRESHOLD = 4500  # in meters
# # Simulated user roles and credentials
# USER_ROLES = {
#     'command_center': {'username': 'command', 'password': 'center123'},
#     'ground_unit': {'username': 'ground', 'password': 'unit123'},
#     'aircraft': {'username': 'aircraft', 'password': 'flight123'}
# }
# scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
# google_credentials = json.loads(st.secrets['google_credentials']['value'])
# creds = Credentials.from_service_account_info(google_credentials, scopes = scope)
# client = gspread.authorize(creds)

# # Initialize session state
# if 'user_role' not in st.session_state:
#     st.session_state['user_role'] = None
# if 'alert_sent' not in st.session_state:
#     st.session_state['alert_sent'] = False

# def send_alert_to_unit(unit_type):
#     """
#     Sends an alert to a specific unit type.
#     Args:
#         unit_type (str): The type of unit to send the alert to.
#     Returns:
#         None
#     """
#     st.session_state['alerts'][unit_type] = True
#     st.write(f"Alert sent to {unit_type}!")

# def calculate_3d_distance(loc1, loc2):
#     """
#     Calculates the 3D distance between two locations.
#     Args:
#         loc1 (tuple): The 3D coordinates of the first location.
#         loc2 (tuple): The 3D coordinates of the second location.
#     Returns:
#         float: The 3D distance between the two locations in meters.
#     """
#     surface_distance = geodesic((loc1[0], loc1[1]), (loc2[0], loc2[1])).meters
#     elevation_difference = abs(loc1[2] - loc2[2])
#     distance_3d = math.sqrt(surface_distance**2 + elevation_difference**2)
#     return distance_3d

# def check_aircraft_proximity(ground_unit_location, aircraft_location):
#     """
#     Checks if an aircraft is within a certain proximity to a ground unit.
#     Args:
#         ground_unit_location (tuple): The 3D coordinates of the ground unit.
#         aircraft_location (tuple): The 3D coordinates of the aircraft.
#     Returns:
#         bool: True if the aircraft is within the proximity threshold, False otherwise.
#     """
#     distance_to_aircraft = calculate_3d_distance(ground_unit_location, aircraft_location)
#     if distance_to_aircraft <= PROXIMITY_THRESHOLD:
#         return True
#     else:
#         return False

# # Function to animate the aircraft path

# def animate_path(df, view_state):

#     """
#     Animate the path of the aircraft on the map.
#     Parameters:
#     - df: DataFrame containing the aircraft path data
#     - view_state: pydeck View State object for the map view settings
#     """
#     # Placeholder for the map
#     map_placeholder = st.empty()
#     # Loop through the DataFrame and incrementally add points to the path

#     for i in range(1, len(df) + 1):
#         # Create a path layer for the current segment of the flight path
#         path_layer = pdk.Layer(
#             "PathLayer",
#             data=pd.DataFrame({'path': [df[['longitude_wgs84(deg)', 'latitude_wgs84(deg)']].values.tolist()[:i]]}),
#             pickable=True,
#             get_color=[255, 0, 0, 150],  # Red color for the path
#             width_scale=20,
#             width_min_pixels=2,
#             get_path="path",
#             get_width=5,
#         )
#         # Create the deck.gl map for the current segment
#         r = pdk.Deck(
#             layers=[path_layer],
#             initial_view_state=view_state,
#             map_style="mapbox://styles/mapbox/light-v9",
#         )
#         # Update the map in the placeholder
#         map_placeholder.pydeck_chart(r)
#         # Pause for animation effect
#         time.sleep(0.3)

# def create_alerts_sheet():
#     """
#     Creates a Google Sheet to store alerts.
#     Returns:
#         gspread.Spreadsheet: The created Google Sheet.
#     """
#     sheet = client.create('Aircraft Proximity Alert System')

#     sheet.share('aksh30990@gmail.com', perm_type='user', role='writer')

#     worksheet = sheet.sheet1

#     worksheet.append_row(['Time', 'Alert', 'Unit Type'])
# def send_alert_to_unit(unit_type, sheet):
#     """
#     Sends an alert to a specific unit type.
#     Args:
#         unit_type (str): The type of unit to send the alert to.
#     Returns:
#         None
#     """
#     current_time = datetime.utcnow().isoformat()
#     sheet.append_row([current_time, 'True', unit_type])
#     st.session_state['alert_sent'] = True
#     st.write(f"Alert sent to {unit_type}!")

# def check_for_alerts():
#     """
#     Checks if there are any alerts in the Google Sheet.
#     Returns:
#         bool: True if there are alerts, False otherwise.
#     """
#     sheet = client.open('Aircraft Proximity Alert System').sheet1
#     alerts = sheet.get_all_records()
#     if alerts:
#         latest_alert = alerts[-1]
#         # latest_alert['Unit Type'] = 'Ground Unit'
#         if latest_alert['Alert'] == 'True':
#                 return latest_alert

# def login_user(username, password):
#     """
#     Logs in a user with the given username and password.
    
#     Args:
#         username (str): The username of the user to log in.
#         password (str): The password of the user to log in.
    
#     Returns:
#         None
#     """
#     for role, credentials in USER_ROLES.items():
#         if credentials['username'] == username and credentials['password'] == password:
#             st.session_state['user_role'] = role
#             st.success(f'Logged in as {role}')
#             return
#     st.error('Incorrect username or password')

# # Login form
# if st.session_state['user_role'] is None:
#     st.subheader('Login')
#     username = st.text_input('Username')
#     password = st.text_input('Password', type='password')
#     if st.button('Login'):
#         login_user(username, password)
#     # Logout button
#     if st.session_state['user_role'] is not None:
#         if st.button('Logout'):
#             st.session_state['user_role'] = None
#             st.session_state['alert_sent'] = False
#             st.write("You have been logged out.")

# # App functionality based on user role

# else:
#     if st.session_state['user_role'] == 'command_center':
#         # Command center interface
#         st.title('Command Center Dashboard')
#         st.title('Aircraft Proximity Alert System')
#         try:
#             sheet = client.open('Aircraft Proximity Alert System').sheet1
#         except gspread.SpreadsheetNotFound:
#             create_alerts_sheet()
#             sheet = create_alerts_sheet()
#         # Input fields for the ground unit location
#         st.subheader('Ground Unit Location')
#         ground_lat = st.number_input('Latitude (deg)', value=0.0, format='%f')
#         ground_lon = st.number_input('Longitude (deg)', value=0.0, format='%f')
#         ground_elev = st.number_input('Elevation (meters)', value=0.0, format='%f')
#         ground_unit_location = (ground_lat, ground_lon, ground_elev)

#         # File uploader for the aircraft location CSV
#         st.subheader('Upload Aircraft Location CSV')
#         csv_file = st.file_uploader("Choose a CSV file", type="csv")

#         if csv_file is not None:
#             # Read the CSV file into a DataFrame
#             df = pd.read_csv(csv_file)

#             # Ensure the required columns are present
#             required_columns = ['latitude_wgs84(deg)', 'longitude_wgs84(deg)', 'elevation_wgs84(m)']
#             if all(col in df.columns for col in required_columns):
#                 # Create a new column for the path to match PyDeck's input format
#                 df['path'] = df[['longitude_wgs84(deg)', 'latitude_wgs84(deg)']].values.tolist()

#                 # Define the initial view state of the map
#                 view_state = pdk.ViewState(
#                     latitude=df['latitude_wgs84(deg)'].mean(),
#                     longitude=df['longitude_wgs84(deg)'].mean(),
#                     zoom=11,
#                     pitch=50,
#                 )

#                 # Initialize an empty list to accumulate paths for animation
#                 animated_path = []

#                 # Create a placeholder for the map
#                 map_placeholder = st.empty()

#                 # Create a DataFrame for the ground unit
#                 ground_unit_df = pd.DataFrame({
#                     'latitude': [ground_unit_location[0]],
#                     'longitude': [ground_unit_location[1]],
#                     'elevation': [ground_unit_location[2]],
#                 })

#                 # Icon layer for the square point
#                 icon_data = pd.DataFrame({
#                     'coordinates': [[ground_unit_location[1], ground_unit_location[0]]],
#                 })

#                 # Initialize placeholders for alerts and buttons
#                 button_placeholder = st.empty()
#                 alert_placeholder = st.empty()

#                 # Initialize an empty list to store alerts
#                 ground_unit_alerts = []
#                 aircraft_alerts = []

#                 # Loop through the rows of the DataFrame to animate the flight path
#                 for index, row in df.iterrows():
#                     # Append the current point to the animated path
#                     animated_path.append(row['path'])

#                     # Create the path layer for the animated path
#                     path_layer = pdk.Layer(
#                         "PathLayer",
#                         data=pd.DataFrame({'path': [animated_path]}),  # Wrap in a DataFrame
#                         pickable=True,
#                         get_color=[255, 0, 0, 150],  # Red color for the path
#                         width_scale=20,
#                         width_min_pixels=2,
#                         get_path="path",
#                         get_width=5,
#                     )

#                     # Create the scatterplot layer for the ground unit's circle
#                     scatter_layer = pdk.Layer(
#                         "ScatterplotLayer",
#                         data=ground_unit_df,
#                         get_position=["longitude", "latitude"],
#                         get_fill_color=[0, 0, 255, 50],  # Light blue color for the circle
#                         get_radius=2500,  # 2.5km radius
#                         pickable=True,
#                     )

#                     # Create the icon layer for the ground unit's square point
#                     icon_layer = pdk.Layer(
#                         "IconLayer",
#                         data=icon_data,
#                         get_icon={
#                             "url": "https://img.icons8.com/windows/32/000000/square-full.png",  # URL for a square icon
#                             "width": 128,
#                             "height": 128,
#                             "anchorY": 128,
#                         },
#                         get_position="coordinates",
#                         get_size=10,  # Size of the square
#                         size_scale=10,
#                         pickable=True,
#                     )

#                     # Create the deck.gl map with all layers
#                     r = pdk.Deck(
#                         layers=[path_layer, scatter_layer, icon_layer],
#                         initial_view_state=view_state,
#                         map_style="mapbox://styles/mapbox/light-v9",
#                     )

#                     # Render the updated map in the same placeholder
#                     map_placeholder.pydeck_chart(r)

#                     # Calculate proximity for the current aircraft position
#                     aircraft_location = (
#                         row['latitude_wgs84(deg)'],
#                         row['longitude_wgs84(deg)'],
#                         row['elevation_wgs84(m)']
#                     )
#                     aircraft_location = (row['latitude_wgs84(deg)'], row['longitude_wgs84(deg)'], row['elevation_wgs84(m)'])
#                     alert = check_aircraft_proximity(ground_unit_location, aircraft_location)
#                     distance_to_ground = calculate_3d_distance(ground_unit_location, aircraft_location)

#                     # Add an alert if the aircraft is within 4.5 km
#                     if distance_to_ground <= 4500:
#                         ground_unit_alerts.append(
#                             f"Aircraft is within firing range of the ground unit. Distance: {distance_to_ground:.2f} meters at timestamp:{datetime.utcnow().isoformat()}"
#                         )
#                         aircraft_alerts.append(
#                             f"Aircraft at index {index} is near the ground unit. Distance: {distance_to_ground:.2f} meters."
#                         )

#                         # Display buttons dynamically
#                         with button_placeholder.container():
#                             col1, col2 = st.columns(2)

#                             with col1:
#                                 if st.button("Priority to Ground Unit", key=f"ground_unit_{index}"):
#                                     with alert_placeholder.container():
#                                         unit_type = 'ground_unit'
#                                         send_alert_to_unit(unit_type, sheet)
#                                         st.write('Alert Sent to Ground Unit')
#                                         # st.write("### Ground Unit Alerts")
#                                         # for alert in ground_unit_alerts:
#                                         #     st.write(alert)

#                             with col2:
#                                 if st.button("Priority to Aircraft", key=f"aircraft_{index}"):
#                                     with alert_placeholder.container():
#                                         unit_type = 'aircraft'
#                                         send_alert_to_unit(unit_type, sheet)
#                                         st.write('Alert Sent to Aircraft')                                                                            
#                                         # st.write("### Aircraft Alerts")
#                                         # for alert in aircraft_alerts:
#                                         #     st.write(alert)

#                     # Add a delay to create the animation effect
#                     time.sleep(0.1)

#             else:
#                 st.error('CSV file must contain latitude, longitude, and elevation columns.')

#     elif st.session_state['user_role'] == 'ground_unit':
#         # Ground unit interface
#         st.title('Ground Unit Dashboard')
#         system_alerts = check_for_alerts()
#         if system_alerts != None:
#             if system_alerts['Unit Type'] == 'ground_unit':
#                 st.error('Keep Firing.')
#             else:
#                 st.error('Friendly aircraft approaching. Stop Firing !')
#         @st.cache(ttl = 30, allow_output_mutation = True, suppress_st_warning = True)
#         def rerun_in_seconds(seconds):
#             time.sleep(seconds)
#             return
        
#         # if rerun_in_seconds(30):
#         #     st.experimental_rerun()

#     elif st.session_state['user_role'] == 'aircraft':
#         # Aircraft interface
#         st.title('Aircraft Dashboard')
#         system_alerts = check_for_alerts()
#         if system_alerts != None:
#             if system_alerts['Unit Type'] == 'ground_unit':
#                 st.error('Ground Unit Firing. Reroute the current path.')
#             else:
#                 st.error('Clearance to fly.')
#         @st.cache(ttl = 30, allow_output_mutation = True, suppress_st_warning = True)
#         def rerun_in_seconds(seconds):
#             time.sleep(seconds)
#             return
        
#         # if rerun_in_seconds(30):
#         #     st.experimental_rerun()



# Tactical Aircraft Threat Detection Dashboard (Indian Defence)

import streamlit as st
from geopy.distance import geodesic
import math
import time
import pandas as pd
import pydeck as pdk
from datetime import datetime

# Constants
PROXIMITY_THRESHOLD = 4500  # in meters
REFRESH_INTERVAL = 30       # seconds for dashboard refresh
ANIMATION_DELAY = 10       # seconds between animation frames

# Military color scheme
COLORS = {
    "dark_green": "#0a5c36",
    "army_green": "#4b5320",
    "sand": "#c2b280",
    "red_alert": "#ff0000",
    "yellow_warning": "#ffff00",
    "white": "#ffffff"
}

USER_ROLES = {
    'command_center': {'username': 'command', 'password': 'center123'},
    'ground_unit': {'username': 'ground', 'password': 'unit123'},
    'aircraft': {'username': 'aircraft', 'password': 'flight123'}
}

def set_military_theme():
    st.markdown(f"""
        <style>
            .stApp {{ background-color: {COLORS["dark_green"]}; color: {COLORS["white"]}; }}
            .stTextInput>div>div>input, .stNumberInput>div>div>input {{
                background-color: {COLORS["sand"]};
                color: {COLORS["army_green"]};
            }}
            .stButton>button {{
                background-color: {COLORS["army_green"]};
                color: {COLORS["white"]};
                border: 2px solid {COLORS["sand"]};
                border-radius: 6px;
                font-weight: bold;
            }}
            .stButton>button:hover {{
                background-color: {COLORS["sand"]};
                color: {COLORS["army_green"]};
            }}
            h1, h2, h3 {{
                color: {COLORS["sand"]};
                text-shadow: 1px 1px 2px black;
            }}
        </style>
    """, unsafe_allow_html=True)

def init_session():
    if 'user_role' not in st.session_state:
        st.session_state.user_role = None
    if 'alerts' not in st.session_state:
        st.session_state.alerts = {'ground_unit': False, 'aircraft': False}
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

def login(username, password):
    for role, creds in USER_ROLES.items():
        if creds['username'] == username and creds['password'] == password:
            st.session_state.user_role = role
            st.session_state.logged_in = True
            st.session_state.login_message = f"ACCESS GRANTED: {role.replace('_', ' ').upper()} TERMINAL"
            return True
    st.error('ACCESS DENIED: INVALID CREDENTIALS', icon="🔒")
    return False

def calculate_3d_distance(loc1, loc2):
    surface = geodesic(loc1[:2], loc2[:2]).meters
    elev_diff = abs(loc1[2] - loc2[2])
    return math.sqrt(surface ** 2 + elev_diff ** 2)

def check_aircraft_proximity(g, a):
    return calculate_3d_distance(g, a) <= PROXIMITY_THRESHOLD

def send_alert(unit):
    st.session_state.alerts[unit] = True
    st.success(f"ALERT SENT TO {unit.replace('_', ' ').upper()}", icon="⚠️")

def get_active_alert():
    for unit, status in st.session_state.alerts.items():
        if status:
            st.session_state.alerts[unit] = False
            return unit
    return None

def create_layers(ground_loc, path):
    ground_df = pd.DataFrame({
        'latitude': [ground_loc[0]],
        'longitude': [ground_loc[1]],
        'elevation': [ground_loc[2]]
    })
    icon_df = pd.DataFrame({
        'coordinates': [[ground_loc[1], ground_loc[0]]],
    })
    return [
        pdk.Layer("PathLayer", pd.DataFrame({'path': [path]}), get_color=[255, 0, 0, 200], get_path="path", width_scale=20, get_width=5),
        pdk.Layer("ScatterplotLayer", ground_df, get_position=["longitude", "latitude"], get_fill_color=[0, 100, 0, 150], get_radius=PROXIMITY_THRESHOLD),
        pdk.Layer("IconLayer", icon_df, get_icon={"url": "https://img.icons8.com/ios-filled/50/000000/military-base.png", "width": 128, "height": 128, "anchorY": 128}, get_position="coordinates", size_scale=15)
    ]

def calculate_zoom(min_lat, max_lat, min_lon, max_lon):
    diff = max(abs(max_lat - min_lat), abs(max_lon - min_lon))
    for threshold, zoom in [(20, 4), (10, 5), (5, 6), (2, 7), (1, 8), (0.5, 9), (0.2, 10), (0.1, 11)]:
        if diff > threshold: return zoom
    return 12

def command_center():
    st.title('🛡️ COMMAND CENTER DASHBOARD')
    col1, col2 = st.columns(2)

    with col1:
        st.subheader('GROUND POSITION')
        ground = (
            st.number_input('LATITUDE', value=0.0, format='%f', key='lat'),
            st.number_input('LONGITUDE', value=0.0, format='%f', key='lon'),
            st.number_input('ELEVATION (m)', value=0.0, format='%f', key='elev')
        )

    with col2:
        st.subheader('AIRCRAFT PATH')
        csv = st.file_uploader("UPLOAD CSV", type="csv")

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

            view = pdk.ViewState(latitude=(min_lat + max_lat) / 2, longitude=(min_lon + max_lon) / 2, zoom=calculate_zoom(min_lat, max_lat, min_lon, max_lon), pitch=50)

            path = []
            map_area = st.empty()
            status_box = st.empty()

            for idx, row in df.iterrows():
                path.append(row['path'])
                aircraft = (row['latitude_wgs84(deg)'], row['longitude_wgs84(deg)'], row['elevation_wgs84(m)'])
                distance = calculate_3d_distance(ground, aircraft)

                view.latitude = aircraft[0]
                view.longitude = aircraft[1]

                map_area.pydeck_chart(pdk.Deck(layers=create_layers(ground, path), initial_view_state=view, map_style='mapbox://styles/mapbox/satellite-v9'))

                with status_box.container():
                    st.markdown(f"""
                        <div style="background-color:{COLORS['army_green']};padding:10px;border-radius:5px;">
                            <h4 style="color:{COLORS['sand']};">STATUS</h4>
                            <p>Aircraft Frame: {idx+1}/{len(df)}</p>
                            <p>Distance: {distance:.2f}m</p>
                            <p>Status: {'⚠️ ENGAGEMENT RANGE' if distance <= PROXIMITY_THRESHOLD else '✅ CLEAR'}</p>
                        </div>
                    """, unsafe_allow_html=True)

                if distance <= PROXIMITY_THRESHOLD:
                    st.warning(f"⚠️ AIRCRAFT IN RANGE ({distance:.2f}m)")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("🚀 ALERT GROUND UNIT", key=f"g{idx}"):
                            send_alert('ground_unit')
                    with c2:
                        if st.button("✈️ ALERT AIRCRAFT", key=f"a{idx}"):
                            send_alert('aircraft')
                time.sleep(ANIMATION_DELAY)

        except Exception as e:
            st.error(f"PROCESSING ERROR: {str(e)}")

def unit_interface(unit):
    name = unit.replace("_", " ").upper()
    st.title(f"🎯 {name} DASHBOARD")
    st.markdown("---")

    alert = get_active_alert()

    if alert == unit:
        st.error("""
        ⚠️ HIGH ALERT
        **ORDERS:** ACTION REQUIRED
        """)
    elif alert:
        st.success("""
        ✅ NO THREAT
        **ORDERS:** MAINTAIN POSITION
        """)

    st.markdown(f"""
        <div style="background-color:{COLORS['army_green']};padding:10px;border-radius:5px;margin-top:20px;">
            <h4 style="color:{COLORS['sand']};">SYSTEM STATUS</h4>
            <p>Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <p>Status: {'ALERT' if alert else 'NORMAL'}</p>
        </div>
    """, unsafe_allow_html=True)
    time.sleep(REFRESH_INTERVAL)
    st.rerun()

def main():
    set_military_theme()
    init_session()

    if not st.session_state.logged_in:
        st.title("🔐 TACTICAL LOGIN")
        with st.form("auth"):
            username = st.text_input("OPERATOR ID")
            password = st.text_input("ACCESS CODE", type="password")
            if st.form_submit_button("LOGIN"):
                if login(username, password):
                    st.rerun()
    else:
        if hasattr(st.session_state, 'login_message'):
            st.success(st.session_state.login_message)
            del st.session_state.login_message

        if st.session_state.user_role == 'command_center':
            command_center()
        else:
            unit_interface(st.session_state.user_role)

        if st.button("🔒 LOGOUT"):
            st.session_state.clear()
            st.success("LOGOUT SUCCESSFUL")
            time.sleep(1)
            st.rerun()

if __name__ == '__main__':
    main()
