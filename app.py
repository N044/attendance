import streamlit as st
import pandas as pd
import bcrypt
import datetime
import pytz
import time
from lib.attendance import get_analytics_from_df
from streamlit_js_eval import get_geolocation
from lib import attendance

@st.cache_resource
def init_admin():
    attendance.ensure_admin_exists()

init_admin()

@st.cache_data
def init_otp(today):
    attendance.sync_otp_once_per_day()

today = datetime.datetime.now().strftime("%Y-%m-%d")
init_otp(today)

def format_duration(d):
    if pd.isna(d):
        return "-"

    try:
        d = float(d)
    except:
        return "-"

    total_seconds = int(d * 3600)

    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60

    return f"{h} Jam {m} Menit"

# ================= HYBRID+ DATA LAYER =================

today = datetime.datetime.now().strftime("%Y-%m-%d")

# ===== INIT BASE (DATA LAMA - 1x SAJA) =====
if "df_base" not in st.session_state:
    st.session_state.df_base = attendance.fetch_all()

# ===== FETCH HARI INI SAJA =====
df_today = attendance.fetch_today_only()

# ===== AMANKAN BASE =====
df_base = st.session_state.df_base.copy()

if not df_base.empty and "Waktu" in df_base.columns:
    df_base["Waktu_dt"] = pd.to_datetime(df_base["Waktu"], errors="coerce")

    today_date = pd.to_datetime(today).date()

    df_base = df_base[
        df_base["Waktu_dt"].dt.date != today_date
    ]

    # 🔥 CLEANUP KOLOM SEMENTARA
    df_base = df_base.drop(columns=["Waktu_dt"], errors="ignore")

# ===== MERGE (FINAL DATA) =====
if df_today.empty:
    df_all = df_base
elif df_base.empty:
    df_all = df_today
else:
    df_all = pd.concat([df_today, df_base], ignore_index=True)

# 🔥 ANTI DUPLICATE (OPTIONAL)
if not df_all.empty:
    df_all = df_all.drop_duplicates(subset=["Username", "Waktu", "Type"])

# 🔥 FIX TIMEZONE DISPLAY (WAJIB)
if not df_all.empty and "Waktu" in df_all.columns:
    df_all["Waktu"] = pd.to_datetime(df_all["Waktu"], errors="coerce", utc=True) \
        .dt.tz_convert("Asia/Jakarta") \
        .dt.strftime("%Y-%m-%d %H:%M:%S")

# ===== USERS =====
if "df_users" not in st.session_state:
    st.session_state.df_users = attendance.fetch_users()

df_users = st.session_state.df_users

# ================= LOCATION =================
ALLOWED_LOCATION = (3.5882070813256024, 98.69050121230667) # Lokasi Kantor Pusat Mikroskil

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

        if st.button("Login", width="stretch"):

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
            if st.button(" ✅ Reset Password", width="stretch"):

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
            if st.button("Kembali ke Login", width="stretch"):
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
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader("📜 Attendance Logs")
            # ===== OPTIONAL: TAMPILKAN LAST REFRESH =====
            if "last_refresh" not in st.session_state:
                st.session_state.last_refresh = "-"
            if "last_refresh" in st.session_state:
                st.caption(f"Last sync: {st.session_state.last_refresh}")

        with col2:
            st.caption("‎ ")
            if st.button("🔄 Refresh Data", width="stretch"):
                st.caption("Klik 🔄 untuk sinkronisasi data")
                st.session_state.df_base = attendance.fetch_all()  # refresh data lama
                attendance.fetch_today_only.clear()  # clear cache hari ini
                st.session_state.last_refresh = datetime.datetime.now().strftime("%d %b %Y • %H:%M")
                st.success("Data berhasil disinkronisasi")
                st.rerun()

        df = df_all.copy()

        if not df.empty and "Duration" in df.columns:
            
            df["Duration"] = pd.to_numeric(
            df["Duration"].astype(str)
                .str.replace(" Jam", "")
                .str.replace(" Menit", ""),
            errors="coerce"
        )

        df["Duration"] = df["Duration"].apply(format_duration)

        if not df.empty:
            st.dataframe(df, width="stretch")
        else:
            st.info("Belum ada data absensi")

        with st.sidebar:
            st.title(f"Welcome, {st.session_state.username} 👋🏼")

            st.subheader("🔐 OTP Management")

            if not df_users.empty:
                display_df = df_users.copy()

                display_cols = ["Username", "OTP", "OTP_Date"]
                for col in display_cols:
                    if col not in display_df.columns:
                        display_df[col] = "-"
                st.dataframe(display_df[display_cols])

            with st.expander("👤 User Management"):
                new_username = st.text_input("Username Baru")
                new_password = st.text_input("Password", type="password")
                confirm_password = st.text_input("Konfirmasi Password", type="password")
                is_admin = st.checkbox("Jadikan Admin")

                if st.button("Create User", width="stretch"):
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
                        st.session_state.df_users = attendance.fetch_users()  # refresh users
                        st.rerun()

            if st.button("Logout", width="stretch"):
                st.session_state.clear()
                st.rerun()

    # ================= ANALYTICS =================
        st.divider()
        st.subheader("📊 Analytics Dashboard")

        summary, status, trend = get_analytics_from_df(df_all)

        if summary is None:
            st.info("Belum ada data analytics")
        else:

            # ===== SUMMARY =====
            st.markdown("### 👤 Summary Per User")
            st.dataframe(summary, width="stretch")

            # ===== STATUS =====
            st.markdown("### 📌 Status Distribution")
            pivot_status = status.pivot(
                index="Username",
                columns="Keterangan",
                values="Jumlah"
            ).fillna(0)

            st.dataframe(pivot_status, width="stretch")

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
            st.title(f"Welcome, {st.session_state.username} 👋🏼")

            df_user = df_all[df_all["Username"] == st.session_state.username]

            history = df_user[df_user["Type"] != "INIT"].sort_values("Waktu", ascending=False)
            history = history.copy()

            if not history.empty and "Duration" in history.columns:
                history["Duration"] = pd.to_numeric(
                    history["Duration"].astype(str)
                        .str.replace(" Jam", "")
                        .str.replace(" Menit", ""),
                    errors="coerce"
                )
                history["Duration"] = history["Duration"].apply(format_duration)

            if not history.empty:
                st.subheader("📜 Riwayat Absensi")
                st.dataframe(history, width="stretch")
            else:
                st.info("Belum ada riwayat absensi.")

            if st.button("Logout", width="stretch"):
                st.session_state.clear()
                st.rerun()

        #================== GEOLOCATION ===================

        location = get_geolocation()

        if not location or "coords" not in location:
            st.warning("Aktifkan lokasi browser")
            st.stop()

        lat = location["coords"].get("latitude")
        lon = location["coords"].get("longitude")

        current_location = (lat, lon)

        #======== TIME & DATE ========

        tz = pytz.timezone('Asia/Jakarta')
        now = datetime.datetime.now(tz)
        current_time = now.isoformat()

        hari_map = {
            "Monday": "Senin",
            "Tuesday": "Selasa",
            "Wednesday": "Rabu",
            "Thursday": "Kamis",
            "Friday": "Jumat",
            "Saturday": "Sabtu",
            "Sunday": "Minggu"
        }

        hari = hari_map.get(now.strftime("%A"))

        #======== STATUS CHECK ========

        today = datetime.datetime.now().strftime("%Y-%m-%d")
        df_today = df_user[
            df_user["Waktu"].astype(str).str.startswith(today)
        ]

        if df_today.empty:
            st.info("ℹ️ Belum ada aktivitas hari ini")
        else:
            last = df_today.iloc[0]

            if last.get("Type") == "IN":
                st.warning(f"🟡 Sudah Clock In sejak {last.get('Waktu')}")
            elif last.get("Type") == "OUT":
                duration = last.get("Duration")

                duration = pd.to_numeric(
                    str(duration).replace(" Jam", "").replace(" Menit", ""),
                    errors="coerce"
                )
                duration = format_duration(duration)

                st.info(f"🕰️ Total Durasi: {duration}")

        # ===== RESULT =====
        result = st.session_state.get("last_result")
        if result:

            if result == "clock_in":
                st.success("✅ Clock In berhasil!")
            elif result == "clock_out":
                st.success("✅ Clock Out berhasil!")
            elif result == "already_clocked_out":
                st.warning(f"❗️Hari Ini (**{last.get('Hari', '-')}**), Sudah Clock Out")
            elif result == "already_clocked_in":
                st.warning("⚠ Sudah Clock In")
            elif result == "no_clock_out_needed":
                st.info("ℹ Sakit / Izin, tidak perlu Clock Out.")

            st.session_state.last_result = None

        # ======== FORM ========
        

        col1, col2 = st.columns(2)
        with col1:
            st.text_input("📅 Hari", value=hari, disabled=True)
        
        with col2:
            jadwal = st.selectbox("Keterangan", ["Hadir", "Sakit", "Izin"])

        message = ""
        if jadwal in ["Izin"]:
            message = st.text_area("Alasan Izin (wajib)")

        if st.button("Clock In / Out", width="stretch"):

            # 🔒 HARDENING: pastikan lokasi ada
            if lat is None or lon is None:
                st.error("❌ Lokasi belum terdeteksi.")
                st.stop()

            # 🔒 VALIDASI LOKASI (WAJIB)
            if not is_within_allowed_location(current_location, ALLOWED_LOCATION):
                st.error("❌ Anda tidak berada di lokasi yang diizinkan.")
                st.stop()

            with st.spinner("Memproses Absensi..."):
                time.sleep(1)  # Simulate processing time
                st.session_state.last_result = attendance.save_attendance(
                    st.session_state.username,
                    hari,
                    jadwal,
                    current_time,
                    current_location,
                    message,
                    df_all
                )
            # update hari ini saja (tanpa fetch_all)
            st.session_state.df_base = st.session_state.df_base  # keep lama
            attendance.fetch_today_only.clear()
            st.rerun()