import streamlit as st
import pandas as pd
import bcrypt
import datetime
import os

from qr_code import generate_daily_qr_code, scan_qr_code 
from attendance import save_attendance, show_attendance_history
from utils import logout

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
            secret_key = "my_secret_key"
            qr_buffer, qr_code_data = generate_daily_qr_code(secret_key)
            st.subheader("Today QR")
            st.image(qr_buffer, caption="(Berubah Setiap Hari)")
            st.write("QR Code ID :", qr_code_data)
            st.info("Share this QR Code in place.", )
            if st.button("Logout"):
                logout()

        # Admin dapat melihat data absensi
        st.info("Admin can view, edit, download attendance data. ")
        st.info("!! WARNING !! All change you made effect to user data.")

        # Menampilkan seluruh data absensi untuk admin
        file_path = 'data/absensi.csv'  # Pastikan path sesuai
        if os.path.exists(file_path):
            df_absensi = pd.read_csv(file_path)
            if not df_absensi.empty:
                # st.dataframe(df_absensi)

                # Edit Attendance Data
                edited_df = st.data_editor(df_absensi, key="editable_table", width=700)

                # Save Changes Button
                if st.button("Save Changes"):
                    edited_df.to_csv(file_path, index=False)
                    st.success("Perubahan telah disimpan!")
                    st.rerun()  # Refresh halaman setelah menyimpan
            else:
                st.info("Belum ada data absensi.")
        else:
            st.info("File absensi.csv tidak ditemukan.")

        # Tombol untuk menghapus seluruh data absensi
        if st.button("Delete All"):
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
                df_user = show_attendance_history(username)
                if not df_user.empty:
                    st.dataframe (df_user, width=322, height=107)
                else:
                    st.info("Belum ada riwayat absensi.")
            if st.button("Logout"):
                logout()

        # Jadwal Absensi hanya untuk pengguna biasa
        hari = st.selectbox("Pilih Hari", ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu'])
        jadwal = st.selectbox("Keterangan", ['Hadir', 'Sakit', 'Izin'])

        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.write("Waktu Absensi:", current_time)

        # Jika keterangan Sakit atau Izin, tampilkan tombol simpan data
        if jadwal in ['Sakit', 'Izin']:
            if st.button("Save"):
                save_attendance(username, hari, jadwal, current_time, "Tidak ada QR Code")
                st.success("Data absensi berhasil disimpan!")
                st.rerun()  # Memaksa halaman untuk me-refresh
        else:
            # Jika keterangan Hadir, tampilkan opsi untuk scan QR Code
            st.subheader("Scan QR Code")
            if st.button("Mulai Scan QR Code"):
                qr_code_data = scan_qr_code()

                if qr_code_data:
                    secret_key = "my_secret_key"
                    _, expected_qr_code = generate_daily_qr_code(secret_key)
                    if qr_code_data == expected_qr_code:
                        save_attendance(username, hari, jadwal, current_time, qr_code_data)
                        st.success("Data absensi berhasil disimpan!")
                        st.rerun()  # Memaksa halaman untuk me-refresh
                    else:
                        st.error("QR Code tidak valid!")