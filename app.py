import streamlit as st
import time

# User Credentials
USER_CREDENTIALS = {
    "command": {"username": "command", "password": "123"},
    "ground": {"username": "ground", "password": "123"},
    "aircraft": {"username": "aircraft", "password": "123"},
}

# Global Constants
PROXIMITY_THRESHOLD = 500  # Example threshold (distance in meters)

# Login
def login():
    st.title("🔐 Secure Login")
    role = st.selectbox("Login As", ["Command Center", "Ground Unit", "Aircraft"])
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        role_key_map = {
            "Command Center": "command",
            "Ground Unit": "ground",
            "Aircraft": "aircraft"
        }
        role_key = role_key_map.get(role, None)
        
        # Check credentials
        cred = USER_CREDENTIALS.get(role_key)
        if cred and username == cred["username"] and password == cred["password"]:
            st.session_state.logged_in = True
            st.session_state.role = role_key
            st.session_state.alert_sent = False  # Reset alert flag on login
            st.success(f"Logged in as {role}")
            st.experimental_rerun()  # Trigger a rerun to load the correct dashboard
        else:
            st.error("Invalid credentials. Please check your username and password.")

# Handle messages and alerts
def handle_alert(distance):
    if distance <= PROXIMITY_THRESHOLD and not st.session_state.alert_sent:
        st.warning("⚠️ Aircraft in PRIORITY range")
        st.session_state.alert_sent = True  # Set the flag to prevent further alerts

# Main dashboard
def main_dashboard():
    # Simulate some kind of input that would trigger alerts
    st.title("Main Dashboard")
    
    # Use the session state to keep track of previously entered messages
    if 'alert_sent' not in st.session_state:
        st.session_state.alert_sent = False
    
    # Simulate ground and aircraft positions (example data)
    ground_position = [28.6139, 77.2090, 0.0]  # Lat, Lon, Elevation
    aircraft_position = [28.6239, 77.2190, 500.0]  # Lat, Lon, Elevation
    
    # Calculate distance (simple 2D for now, you can expand to 3D if needed)
    distance = ((aircraft_position[0] - ground_position[0])**2 + (aircraft_position[1] - ground_position[1])**2) ** 0.5
    st.write(f"Distance: {distance:.2f} meters")
    
    handle_alert(distance)  # Check for alert condition
    
    # Allow the user to manually reset the alert if necessary
    if st.button("Reset Alert"):
        st.session_state.alert_sent = False
        st.success("Alert has been reset.")
    
# Main
def main():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'role' not in st.session_state:
        st.session_state.role = None

    # If not logged in, show the login screen
    if not st.session_state.logged_in:
        login()
    else:
        role = st.session_state.role
        st.sidebar.success(f"Logged in as {role.upper()}")
        
        # Handle dashboard depending on role
        if role == "command":
            main_dashboard()
        elif role == "ground":
            st.title("Ground Unit Dashboard")
            st.write("Welcome to the Ground Unit dashboard!")
        elif role == "aircraft":
            st.title("Aircraft Dashboard")
            st.write("Welcome to the Aircraft dashboard!")

        if st.sidebar.button("Logout"):
            # Reset session state variables when logging out
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.experimental_rerun()  # Rerun the app to reset to login screen

if __name__ == "__main__":
    main()
