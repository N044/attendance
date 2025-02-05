import streamlit as st
import pandas as pd
import bcrypt
import datetime
import pytz
import os
import time
import random
from streamlit_js_eval import get_geolocation  # Import for GPS-based location
from lib import attendance

# Simulasi pengguna dengan password yang sudah di-hash
users = {
    "user1": {"password": bcrypt.hashpw(b"password123", bcrypt.gensalt()), "isAdmin": False},
    "user2": {"password": bcrypt.hashpw(b"anotherpassword", bcrypt.gensalt()), "isAdmin": False},
    "admin": {"password": bcrypt.hashpw(b"admin123", bcrypt.gensalt()), "isAdmin": True},
    "Noah": {"password": bcrypt.hashpw(b"admin123", bcrypt.gensalt()), "isAdmin": True},
    "Evelyn": {"password": bcrypt.hashpw(b"admin123", bcrypt.gensalt()), "isAdmin": True},
    "Tommy": {"password": bcrypt.hashpw(b"admin123", bcrypt.gensalt()), "isAdmin": True}
}

# Define allowed location (Latitude, Longitude)
ALLOWED_LOCATION = (3.5882070813256024, 98.69050121230667)  # Universitas Mikroskil - Gedung C

# Function to check if the user's location is within an acceptable range
def is_within_allowed_location(user_location, allowed_location, threshold=0.0005):
    lat_diff = abs(user_location[0] - allowed_location[0])
    lon_diff = abs(user_location[1] - allowed_location[1])
    return lat_diff <= threshold and lon_diff <= threshold

# Path for storing OTP keys
OTP_DB = 'data/otp_db.csv'

# Function to generate and store OTP for all users
def generate_daily_otp_for_all_users():
    if not os.path.exists(OTP_DB):
        df = pd.DataFrame(columns=['Username', 'OTP_Key', 'Last_Generated'])
        df.to_csv(OTP_DB, index=False)

    df = pd.read_csv(OTP_DB)
    today = datetime.date.today().strftime("%Y-%m-%d")
    
    for username in users:
        if username not in df['Username'].values:
            otp_key = str(random.randint(1000, 9999))  # 4-digit numeric OTP
            new_entry = pd.DataFrame({'Username': [username], 'OTP_Key': [otp_key], 'Last_Generated': [today]})
            df = pd.concat([df, new_entry], ignore_index=True)
        else:
            user_data = df[df['Username'] == username].iloc[0]
            if user_data['Last_Generated'] != today:
                otp_key = str(random.randint(1000, 9999))  # 4-digit numeric OTP
                df.loc[df['Username'] == username, ['OTP_Key', 'Last_Generated']] = [otp_key, today]
    
    df.to_csv(OTP_DB, index=False)

# Call the function to generate OTP for all users daily
generate_daily_otp_for_all_users()

# Function to validate OTP with debugging
def validate_otp(username, otp):
    df = pd.read_csv(OTP_DB)
    today = datetime.date.today().strftime("%Y-%m-%d")
    
    print(f"Validating OTP for {username} with OTP: {otp}")
    
    if username in df['Username'].values:
        user_data = df[df['Username'] == username].iloc[0]
        stored_otp = str(user_data['OTP_Key']).strip()  # Ensure the OTP is a string and remove any spaces
        input_otp = str(otp).strip()  # Ensure input OTP is also a string and remove any spaces
        
        print(f"Stored OTP for {username}: {stored_otp}")
        print(f"Last Generated Date: {user_data['Last_Generated']}")
        
        # Check if the OTP is valid and not expired
        if user_data['Last_Generated'] == today:
            if stored_otp == input_otp:
                return True
            else:
                print(f"Invalid OTP for {username}")
                return False
        else:
            print(f"OTP expired for {username}")
            return False
    return False

# Inisialisasi session state jika belum ada
if "is_logged_in" not in st.session_state:
    st.session_state.is_logged_in = False
    st.session_state.username = ""
    st.session_state.is_admin = False

# Halaman Login
if not st.session_state.is_logged_in:
    st.title("Universitas Mikroskil - Live Attendance System (LAS)")
    st.caption("By Student Affairs Office")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    otp = st.text_input("OTP (One Time Password)", type="password")
    
    if st.button("Login", use_container_width=True):
        if username in users:
            if bcrypt.checkpw(password.encode('utf-8'), users[username]["password"]):
                if users[username]["isAdmin"]:
                    # Skip OTP for admins
                    st.session_state.is_logged_in = True
                    st.session_state.username = username
                    st.session_state.is_admin = True
                    st.success("Login berhasil sebagai Admin!")
                    st.rerun()
                else:
                    # Validate OTP for regular users
                    if validate_otp(username, otp):
                        st.session_state.is_logged_in = True
                        st.session_state.username = username
                        st.session_state.is_admin = False
                        st.success("Login berhasil!")
                        st.rerun()
                    else:
                        st.error("OTP salah atau kadaluarsa.")
            else:
                st.error("Password salah")
        else:
            st.error("Username tidak ditemukan")
else:
    st.title("Universitas Mikroskil - Live Attendance System (LAS)")
    st.caption("By Student Affairs Office")

    if st.session_state.is_admin:
        st.subheader("📜 Attendance Logs")
        file_path = 'data/absensi.csv'
        if os.path.exists(file_path):
            df_absensi = pd.read_csv(file_path)
            if not df_absensi.empty:
                edited_df = st.data_editor(df_absensi, key="editable_table", width=700)
        else:
            st.info("Belum ada riwayat absensi.")

        if st.button("Save Changes", use_container_width=True):
            edited_df.to_csv('data/absensi.csv', index=False)
            st.success("Changes saved successfully!")
            st.rerun()

        if st.button("Delete All Data", use_container_width=True):
            if os.path.exists('data/absensi.csv'):
                os.remove('data/absensi.csv')
                st.success("All attendance data has been deleted!")
                st.rerun()
            else:
                st.error("No data found to delete.")
        
        # Show OTP for each user to Admin
        with st.sidebar:
            st.title(f"Welcome, {st.session_state.username}")
            st.subheader("🔑 Daily OTP Codes")
            df_otp = pd.read_csv(OTP_DB)

             # Ensure OTP values are displayed as strings
            df_otp['OTP_Key'] = df_otp['OTP_Key'].astype(str)

            st.dataframe(df_otp[['Username', 'OTP_Key']], use_container_width=True)

            if st.button("Logout", use_container_width=True):
                st.session_state.is_logged_in = False
                st.session_state.username = ""
                st.session_state.is_admin = False
                st.rerun()
    else:
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
            jakarta_tz = pytz.timezone('Asia/Jakarta')
            current_time = datetime.datetime.now(jakarta_tz).strftime("%Y-%m-%d %H:%M:%S")

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
                with st.empty():
                    button_pressed = st.button("Clock In / Out", use_container_width=True)
                    if button_pressed:
                        start_time = time.time()
                        while time.time() - start_time < 5:
                            time_left = 5 - int(time.time() - start_time)
                            st.warning(f"Hold for {time_left} seconds", icon="⏳")
                            time.sleep(1)
                            
                        attendance.save_attendance(st.session_state.username, hari, jadwal, current_time, current_location, message)
                        st.success("✅ Data absensi berhasil disimpan!")
                        st.rerun()
        else:
            st.warning("⚠ Tidak dapat mendeteksi lokasi Anda. Silakan izinkan akses lokasi di browser.")