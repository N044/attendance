import streamlit as st
import pandas as pd
import bcrypt
import datetime
import pytz
import time
from streamlit_js_eval import get_geolocation
from lib import attendance

# 🔐 Ensure admin always exists
attendance.ensure_admin_exists()

# ================= LOCATION =================
ALLOWED_LOCATION = (3.5882070813256024, 98.69050121230667)

def is_within_allowed_location(user_location, allowed_location, threshold=0.0005):
    lat_diff = abs(user_location[0] - allowed_location[0])
    lon_diff = abs(user_location[1] - allowed_location[1])
    return lat_diff <= threshold and lon_diff <= threshold


# ================= SESSION =================
if "is_logged_in" not in st.session_state:
    st.session_state.is_logged_in = False
    st.session_state.username = ""
    st.session_state.is_admin = False

if "login_attempt" not in st.session_state:
    st.session_state.login_attempt = 0

if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "login"


# ================= LOGIN =================
if not st.session_state.is_logged_in:

    st.divider()
    st.title("Mikroskil - Monitoring System Attendance (MMSA)")
    st.caption("Copyright © 2026 Student Affairs Office (N044)")
    st.divider()

    # ===== LOGIN MODE =====
    if st.session_state.auth_mode == "login":

        username = st.text_input("Username").strip()
        password = st.text_input("Password", type="password")
        otp_input = st.text_input("OTP (One Time Password)", type="password")

        if st.button("Login", use_container_width=True):

            user = attendance.get_user(username)

            if not user:
                st.session_state.login_attempt += 1
                st.error(f"Username tidak ditemukan ({st.session_state.login_attempt}/3)")
                if st.session_state.login_attempt >= 3:
                    st.session_state.auth_mode = "reset"
                    st.rerun()
                st.stop()

            stored_hash = str(user.get("PasswordHash", "")).strip()

            if not stored_hash:
                st.error("Password belum diset")
                st.stop()

            if not stored_hash.startswith("$2b$"):
                st.error("Format hash tidak valid")
                st.stop()

            try:
                if not bcrypt.checkpw(password.encode(), stored_hash.encode()):
                    st.session_state.login_attempt += 1
                    st.error(f"Password salah ({st.session_state.login_attempt}/3)")
                    if st.session_state.login_attempt >= 3:
                        st.session_state.auth_mode = "reset"
                        st.rerun()
                    st.stop()
            except ValueError:
                st.error("Hash password invalid")
                st.stop()

            # OTP (non admin)
            if not user.get("IsAdmin"):
                if not otp_input:
                    st.error("OTP wajib diisi")
                    st.stop()

                if not attendance.validate_otp(username, otp_input):
                    st.session_state.login_attempt += 1
                    st.error(f"OTP salah ({st.session_state.login_attempt}/3)")
                    if st.session_state.login_attempt >= 3:
                        st.session_state.auth_mode = "reset"
                        st.rerun()
                    st.stop()

            # SUCCESS
            st.session_state.login_attempt = 0
            st.session_state.is_logged_in = True
            st.session_state.username = username
            st.session_state.is_admin = user.get("IsAdmin", False)

            st.success("Login berhasil!")
            st.rerun()

    # ===== RESET MODE =====
    else:
        st.warning("🔐 Reset Password Required")

        reset_username = st.text_input("Username")
        reset_otp = st.text_input("OTP", type="password")
        new_password = st.text_input("Password Baru", type="password")
        confirm_password = st.text_input("Konfirmasi Password", type="password")

        col1, col2 = st.columns(2)

        with col1:
            if st.button(" ✅ Reset Password", use_container_width=True):

                if not reset_username or not reset_otp or not new_password:
                    st.error("Semua field wajib diisi", icon="⚠️")
                    st.stop()

                if new_password != confirm_password:
                    st.error("Password tidak cocok")
                    st.stop()

                if len(new_password) < 6:
                    st.error("Password minimal 6 karakter")
                    st.stop()

                success, msg = attendance.reset_password_with_otp(
                    reset_username,
                    reset_otp,
                    new_password
                )

                if success:
                    st.success("Password berhasil direset")
                    st.session_state.login_attempt = 0
                    st.session_state.auth_mode = "login"
                    st.rerun()
                else:
                    st.error(msg)

        with col2:
            if st.button("Kembali ke Login", use_container_width=True):
                st.session_state.auth_mode = "login"
                st.session_state.login_attempt = 0
                st.rerun()


# ================= MAIN =================
else:
    st.divider()
    st.title("Mikroskil - Monitoring System Attendance (MMSA)")
    st.caption("Copyright © 2026 Student Affairs Office (N044)")
    st.divider()

    # ================= ADMIN =================
    if st.session_state.is_admin:

        st.subheader("📜 Attendance Logs")
        df = attendance.fetch_all()

        if not df.empty:
            st.dataframe(df)
        else:
            st.info("Belum ada data absensi")

        with st.sidebar:
            st.title(f"Welcome, {st.session_state.username} 👋🏼")

            st.subheader("🔐 OTP Management")
            df_users = attendance.fetch_users()

            if not df_users.empty:
                display_cols = ["Username", "OTP", "OTP_Date"]
                for col in display_cols:
                    if col not in df_users.columns:
                        df_users[col] = "-"
                st.dataframe(df_users[display_cols])

            with st.expander("👤 User Management"):
                new_username = st.text_input("Username Baru")
                new_password = st.text_input("Password", type="password")
                confirm_password = st.text_input("Konfirmasi Password", type="password")
                is_admin = st.checkbox("Jadikan Admin")

                if st.button("Create User", use_container_width=True):
                    if new_password != confirm_password:
                        st.error("Password tidak cocok")
                        st.stop()

                    success = attendance.create_user_airtable(
                        new_username,
                        new_password,
                        is_admin
                    )

                    if success:
                        st.success("User berhasil dibuat")
                        st.rerun()

            if st.button("Logout", use_container_width=True):
                st.session_state.clear()
                st.rerun()

    # ================= ANALYTICS =================
        st.divider()
        st.subheader("📊 Analytics Dashboard")

        summary, status, trend = attendance.get_analytics()

        if summary is None:
            st.info("Belum ada data analytics")
        else:

            # ===== SUMMARY =====
            st.markdown("### 👤 Summary Per User")
            st.dataframe(summary, use_container_width=True)

            # ===== STATUS =====
            st.markdown("### 📌 Status Distribution")
            pivot_status = status.pivot(
                index="Username",
                columns="Keterangan",
                values="Jumlah"
            ).fillna(0)

            st.dataframe(pivot_status, use_container_width=True)

            # ===== TREND =====
            st.markdown("### 📈 Daily Working Hours")

            trend_chart = trend.pivot(
                index="Tanggal",
                columns="Username",
                values="Jam"
            ).fillna(0)

            st.line_chart(trend_chart)

    # ================= USER =================
    else:

        with st.sidebar:
            st.title(f"Welcome, {st.session_state.username}")

            history = attendance.show_attendance_history(st.session_state.username)
            if not history.empty:
                st.subheader("📜 Riwayat Absensi")
                st.dataframe(history, use_container_width=True)
            else:
                st.info("Belum ada riwayat absensi.")

            if st.button("Logout", use_container_width=True):
                st.session_state.clear()
                st.rerun()

        location = get_geolocation()

        if not location or "coords" not in location:
            st.warning("Aktifkan lokasi browser")
            st.stop()

        lat = location["coords"].get("latitude")
        lon = location["coords"].get("longitude")

        current_location = (lat, lon)

        tz = pytz.timezone('Asia/Jakarta')
        now = datetime.datetime.now(tz)
        current_time = now.strftime("%Y-%m-%d %H:%M:%S")

        hari = now.strftime("%A")

        df_today = attendance.get_today_attendance(st.session_state.username)

        if df_today.empty:
            st.info("ℹ️ Belum ada aktivitas hari ini")
        else:
            last = df_today.iloc[0]

            if last.get("Type") == "IN":
                st.warning(f"🟡 Sudah Clock In sejak {last.get('Waktu')}")
            elif last.get("Type") == "OUT":
                st.success("✅ Sudah Clock Out")
                st.info(f"Durasi: {last.get('Duration', '-')}")

        # ===== RESULT =====
        result = st.session_state.get("last_result")
        if result:
            st.divider()

            if result == "clock_in":
                st.success("✅ Clock In berhasil!")
            elif result == "clock_out":
                st.success("✅ Clock Out berhasil!")
            elif result == "already_clocked_out":
                st.warning("⚠ Sudah Clock Out")
            elif result == "already_clocked_in":
                st.warning("⚠ Sudah Clock In")
            elif result == "no_clock_out_needed":
                st.info("ℹ Tidak perlu Clock Out")

            st.session_state.last_result = None

        jadwal = st.selectbox("Keterangan", ["Hadir", "Sakit", "Izin"])
        message = st.text_input("Alasan") if jadwal == "Izin" else ""

        if st.button("Clock In / Out"):
            with st.spinner("Memproses..."):
                st.session_state.last_result = attendance.save_attendance(
                    st.session_state.username,
                    hari,
                    jadwal,
                    current_time,
                    current_location,
                    message
                )
            st.rerun()