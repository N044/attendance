import streamlit as st
import pandas as pd
import bcrypt
import datetime
import os
import time
from streamlit_js_eval import get_geolocation  # Import for GPS-based location
from lib import attendance

# Simulasi pengguna dengan password yang sudah di-hash
users = {
    "user1": {"password": bcrypt.hashpw(b"password123", bcrypt.gensalt()), "isAdmin": False},
    "user2": {"password": bcrypt.hashpw(b"anotherpassword", bcrypt.gensalt()), "isAdmin": False},
    "admin": {"password": bcrypt.hashpw(b"admin123", bcrypt.gensalt()), "isAdmin": True}
}

# Define allowed location (Latitude, Longitude)
ALLOWED_LOCATION = (3.584020034856336, 98.64739611799341)  # Rumah
# ALLOWED_LOCATION = (3.5882070813256024, 98.69050121230667) # Universitas Mikroskil - Gedung C

# Function to check if the user's location is within an acceptable range
def is_within_allowed_location(user_location, allowed_location, threshold=0.0005):
    lat_diff = abs(user_location[0] - allowed_location[0])
    lon_diff = abs(user_location[1] - allowed_location[1])
    return lat_diff <= threshold and lon_diff <= threshold

# Inisialisasi session state jika belum ada
if "is_logged_in" not in st.session_state:
    st.session_state.is_logged_in = False
    st.session_state.username = ""  # Initialize username if not set
    st.session_state.is_admin = False

# Halaman Login
if not st.session_state.is_logged_in:
    st.title("Universitas Mikroskil - Live Attendance System (LAS)")
    st.caption("By Student Affairs Office")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login", use_container_width=True):
        if username in users:
            if bcrypt.checkpw(password.encode('utf-8'), users[username]["password"]):
                st.session_state.is_logged_in = True
                st.session_state.username = username
                st.session_state.is_admin = users[username]["isAdmin"]
                st.success("Login berhasil!")
                st.rerun()
            else:
                st.error("Password salah")
        else:
            st.error("Username tidak ditemukan")

else:
    # Admin or User Attendance Interface
    st.title("Universitas Mikroskil")
    st.caption("Live Attendance System (LAS) by Student Affairs Office")

    if st.session_state.is_admin:
        # Admin View: Show all attendance logs
        st.subheader("📜 Attendance Logs")
        file_path = 'data/absensi.csv'
        if os.path.exists(file_path):
            df_absensi = pd.read_csv(file_path)
            if not df_absensi.empty:
                # Edit Attendance Data
                edited_df = st.data_editor(df_absensi, key="editable_table", width=700)

        # Save changes button
        if st.button("Save Changes", use_container_width=True):
            edited_df.to_csv('data/absensi.csv', index=False)
            st.success("Changes saved successfully!")
            st.rerun()

        # Delete all data button
        if st.button("Delete All Data", use_container_width=True):
            if os.path.exists('data/absensi.csv'):
                os.remove('data/absensi.csv')
                st.success("All attendance data has been deleted!")
            else:
                st.error("No data found to delete.")

        # Sidebar for admin: Display only logout option
        with st.sidebar:
            st.title(f"Welcome, {st.session_state.username}")
        
            if st.button("Logout", use_container_width=True):
                st.session_state.is_logged_in = False
                st.session_state.username = ""
                st.session_state.is_admin = False
                st.rerun()

    else:
        # Sidebar for regular users
        with st.sidebar:
            st.title(f"Welcome, {st.session_state.username}")
            if not st.session_state.is_admin:  # Hanya tampilkan riwayat absensi untuk pengguna biasa
                st.header("📝 Attendance log ")
                username = st.session_state.username
                df_user = attendance.show_attendance_history(username)
                if not df_user.empty:
                    st.dataframe(df_user, width=322, height=107)
                else:
                    st.info("Belum ada riwayat absensi.")
        
            if st.button("Logout", use_container_width=True):
                st.session_state.is_logged_in = False
                st.session_state.username = ""
                st.session_state.is_admin = False
                st.rerun()

        # Get current location using GPS (HTML5 Geolocation API)
        location = get_geolocation()

        if location:
            current_location = (location["coords"]["latitude"], location["coords"]["longitude"])
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # **Fixing Spacing**: Place "Hari" and "Keterangan" in a row
            col1, col2 = st.columns(2)
            with col1:
                hari = st.selectbox("Pilih Hari", ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu'])
            with col2:
                jadwal = st.selectbox("Keterangan", ['Hadir', 'Sakit', 'Izin'])

            # Optional message field for Sakit or Izin
            message = ""
            if jadwal in ['Sakit', 'Izin']:
                message = st.text_area("Message (Optional)")
            
            # **Fixing Spacing**: Display location **next to** the dropdowns
            with st.container():
                st.write(f"📍 **Your Location:** {current_location}")
                st.write(f"🕒 **Waktu Absensi:** {current_time}")

            if jadwal == "Hadir":
                if is_within_allowed_location(current_location, ALLOWED_LOCATION):
                    st.success("✅ Anda berada di lokasi yang diizinkan. Silakan absen.")
                    
                    # Add 5-second press-and-hold functionality
                    with st.empty():  # Keeps the button active while it's being pressed
                        button_pressed = st.button("Clock In / Out", use_container_width=True)
                        if button_pressed:
                            start_time = time.time()  # Record the start time of button press
                            # Loop until the button is held for 5 seconds
                            while time.time() - start_time < 5:
                                time_left = 5 - int(time.time() - start_time)
                                st.warning(f"Hold for {time_left} seconds", icon="⏳")
                                time.sleep(1)  # Sleep for 1 second to prevent excessive CPU usage
                            
                            # After 5 seconds, process attendance
                            attendance.save_attendance(st.session_state.username, hari, jadwal, current_time, current_location, message)
                            st.success("✅ Data absensi berhasil disimpan!")
                            st.rerun()
                else:
                    st.error("❌ Anda tidak berada di lokasi yang diizinkan. Absensi ditolak.")
            else:
                # For Sakit or Izin, no location check, but also handle 5-second press
                with st.empty():  # Keeps the button active while it's being pressed
                    button_pressed = st.button("Clock In / Out", use_container_width=True)
                    if button_pressed:
                        start_time = time.time()  # Record the start time of button press
                        # Loop until the button is held for 5 seconds
                        while time.time() - start_time < 5:
                            time_left = 5 - int(time.time() - start_time)
                            st.warning(f"Hold for {time_left} seconds", icon="⏳")
                            time.sleep(1)  # Sleep for 1 second to prevent excessive CPU usage
                        
                        # After 5 seconds, process attendance
                        attendance.save_attendance(st.session_state.username, hari, jadwal, current_time, current_location, message)
                        st.success("✅ Data absensi berhasil disimpan!")
                        st.rerun()
        else:
            st.warning("⚠ Tidak dapat mendeteksi lokasi Anda. Silakan izinkan akses lokasi di browser.")