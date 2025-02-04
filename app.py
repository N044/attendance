import streamlit as st
import pandas as pd
import bcrypt
import datetime
import os
import geocoder

from lib import attendance

# Simulasi pengguna dengan password yang sudah di-hash
users = {
    "user1": {"password": bcrypt.hashpw(b"password123", bcrypt.gensalt()), "isAdmin": False},
    "user2": {"password": bcrypt.hashpw(b"anotherpassword", bcrypt.gensalt()), "isAdmin": False},
    "admin": {"password": bcrypt.hashpw(b"admin123", bcrypt.gensalt()), "isAdmin": True}
}

# Fungsi untuk memeriksa password
def check_password(password_hash, user_password):
    return bcrypt.checkpw(user_password.encode('utf-8'), password_hash)

# Inisialisasi session state
if "is_logged_in" not in st.session_state:
    st.session_state.is_logged_in = False
    st.session_state.username = ""
    st.session_state.is_admin = False

# Fungsi Logout
def logout():
    st.session_state.is_logged_in = False
    st.session_state.username = ""
    st.session_state.is_admin = False
    st.rerun()  # Refresh halaman setelah logout

# Define the allowed location (latitude, longitude)
ALLOWED_LOCATION = (3.5833, 98.6667)  # Example: coordinates of a specific location
ALLOWED_LOCATION = (45.5946, -121.1787)  # Example: coordinates of a specific location

# Function to get the user's current location
def get_user_location():
    g = geocoder.ip('me')  # Get geolocation using IP address
    return (g.latlng[0], g.latlng[1]) if g.latlng else None

# Function to check if the user's location is within an acceptable range
def is_within_allowed_location(user_location, allowed_location, threshold=0.01):
    lat_diff = abs(user_location[0] - allowed_location[0])
    lon_diff = abs(user_location[1] - allowed_location[1])
    return lat_diff <= threshold and lon_diff <= threshold

# Halaman Login
if not st.session_state.is_logged_in:
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in users:
            if check_password(users[username]["password"], password):
                st.session_state.is_logged_in = True
                st.session_state.username = username
                st.session_state.is_admin = users[username]["isAdmin"]
                st.success("Login berhasil!")
                st.rerun()  # Refresh halaman setelah login
            else:
                st.error("Password salah")
        else:
            st.error("Username tidak ditemukan")
else:
    # Halaman Utama
    if st.session_state.is_admin:
        # Halaman Admin
        st.title(f"Universitas Mikroskil")
        st.subheader("Student Affairs Office - Attendance System")

        # Sidebar
        with st.sidebar:
            st.title(f"Welcome, {st.session_state.username}")

            # Add a logout button
            if st.button("Logout", use_container_width=True):
                logout()

        # Menampilkan data absensi untuk admin
        file_path = 'data/absensi.csv'
        if os.path.exists(file_path):
            df_absensi = pd.read_csv(file_path)
            if not df_absensi.empty:
                # Edit Attendance Data
                edited_df = st.data_editor(df_absensi, key="editable_table", width=700)

                # Save Changes Button
                if st.button("Save Changes", use_container_width=True):
                    edited_df.to_csv(file_path, index=False)
                    st.success("Perubahan telah disimpan!")
                    st.rerun()  # Refresh halaman setelah menyimpan
            else:
                st.info("Belum ada data absensi.")
        else:
            st.info("File absensi.csv tidak ditemukan.")

        # Tombol untuk menghapus seluruh data absensi
        if st.button("Delete All", use_container_width=True):
            if os.path.exists(file_path):
                os.remove(file_path)  # Menghapus file absensi.csv
                st.success("Semua data absensi berhasil dihapus!")
                st.rerun()  # Memaksa halaman untuk me-refresh
            else:
                st.error("File absensi.csv tidak ditemukan.")
    else:
        # Halaman Pengguna
        st.title(f"Universitas Mikroskil")
        st.subheader("Student Affairs Office - Attendance System")
        
        # Sidebar
        with st.sidebar:
            st.title(f"Welcome, {st.session_state.username}")
            if not st.session_state.is_admin:  # Hanya tampilkan riwayat absensi untuk pengguna biasa
                st.header("Riwayat Absensi")
                username = st.session_state.username
                df_user = attendance.show_attendance_history(username)
                if not df_user.empty:
                    st.dataframe(df_user, width=322, height=107)
                else:
                    st.info("Belum ada riwayat absensi.")
            if st.button("Logout", use_container_width=True):
                logout()

        # Jadwal Absensi hanya untuk pengguna biasa
        hari = st.selectbox("Pilih Hari", ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu'])
        jadwal = st.selectbox("Keterangan", ['Hadir', 'Sakit', 'Izin'])

        # Get current location for all choices
        current_location = get_user_location()
        
        # Display Waktu Absensi and current location for all choices
        if current_location:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.write("Waktu Absensi:", current_time)
            st.write(f"Your current location is: {current_location}")
        
        # Handle "Hadir" case with location check only when user clicks the save button
        if jadwal == "Hadir":
            if current_location:
                if is_within_allowed_location(current_location, ALLOWED_LOCATION):
                    st.info("You are in the allowed location. Proceed with attendance.")
                    
                    # Show Save Attendance button
                    if st.button("Save Attendance", use_container_width=True):
                        attendance.save_attendance(st.session_state.username, hari, jadwal, current_time, current_location)
                        st.success("Data absensi berhasil disimpan!")
                        st.rerun()  # Refresh the page to reflect the changes
                else:
                    st.error("You are not in the allowed location. Attendance cannot be recorded.")
            else:
                st.error("Unable to detect your location.")
        
        # For "Sakit" and "Izin", just save the attendance with no location check
        else:
            if st.button("Save Attendance", use_container_width=True):
                attendance.save_attendance(st.session_state.username, hari, jadwal, current_time, current_location)
                st.success("Data absensi berhasil disimpan!")
                st.rerun()