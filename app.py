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

# ================= HYBRID+ DATA LAYER =================

today = datetime.datetime.now().strftime("%Y-%m-%d")

# ===== INIT BASE (DATA LAMA - 1x SAJA) =====
if "df_base" not in st.session_state:
    st.session_state.df_base = attendance.fetch_all()

# ===== FETCH HARI INI SAJA =====
df_today = attendance.fetch_today_only()

# ===== AMANKAN BASE =====
df_base = st.session_state.df_base.copy()

if not df_base.empty and "waktu" in df_base.columns:
    df_base["waktu_dt"] = pd.to_datetime(df_base["waktu"], errors="coerce")

    today_date = pd.to_datetime(today).date()

    df_base = df_base[
        df_base["waktu_dt"].dt.date != today_date
    ]

    # 🔥 CLEANUP KOLOM SEMENTARA
    df_base = df_base.drop(columns=["waktu_dt"], errors="ignore")

# ===== MERGE (FINAL DATA) =====
if df_today.empty:
    df_all = df_base
elif df_base.empty:
    df_all = df_today
else:
    df_all = pd.concat([df_today, df_base], ignore_index=True)

# 🔥 ANTI DUPLICATE (OPTIONAL)
if not df_all.empty:
    df_all = df_all.drop_duplicates(subset=["username", "waktu", "type"])

# 🔥 FIX TIMEZONE DISPLAY (WAJIB)
if not df_all.empty and "waktu" in df_all.columns:
    df_all["waktu"] = pd.to_datetime(df_all["waktu"], errors="coerce", utc=True) \
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

if "attendance_cooldown" not in st.session_state:
    st.session_state.attendance_cooldown = False

if "last_attendance_time" not in st.session_state:
    st.session_state.last_attendance_time = 0


# ================= LOGIN =================
if not st.session_state.is_logged_in:

    st.title("Mikroskil - Monitoring System Attendance (MMSA)")
    st.caption("Copyright © 2026 Student Affairs Office (N044)")
    st.divider()

    # ===== LOGIN MODE =====
    if st.session_state.auth_mode == "login":

        # =========================
        # USERNAME & PASSWORD
        # =========================
        col1, col2 = st.columns(2)

        with col1:
            username = st.text_input(
                "Username",
                placeholder="Enter username"
            ).strip()

        with col2:
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter password"
            )

        # =========================
        # CHECK USER
        # =========================
        user = attendance.get_user(username) if username else None

        is_admin_user = False

        if user:
            is_admin_user = user.get("isadmin", False)

        # =========================
        # OTP (NON ADMIN ONLY)
        # =========================
        if not is_admin_user:

            otp_input = st.text_input(
                "OTP Verification Code",
                placeholder="Enter OTP code"
            )

        else:
            otp_input = ""

        # =========================
        # REMEMBER ME + NEW USER
        # =========================
        col3, col4 = st.columns([1, 1])

        with col3:

            remember_me = st.checkbox(
                "Remember Me",
                key="remember_me_login"
            )

        with col4:

            st.markdown(
                """
        <style>
        .new-user-link {
            text-align: right;
            margin-top: 6px;
        }

        @media (max-width: 768px) {
            .new-user-link {
                margin-top: -50px;
            }
        }
        </style>

        <div class="new-user-link">
            <a
                href="mailto:sa.officemikroskil@gmail.com?cc=noah.napitupulu@mikroskil.ac.id&subject=Permohonan%20Pembuatan%20Akun%20MMSA%20-%20[Your%20Name]&body=Dear%20Bapak/Ibu%20%0AStudent%20Affairs%20Office,%0A%0APerkenalkan,%20melalui%20email%20ini%20saya%20ingin%20mengajukan%20pembuatan%20akun%20untuk%20mengakses%20Mikroskil%20Monitoring%20Attendance%20System%20(MMSA).%0A%0ABerikut%20data%20diri%20saya:%0A-%20Nama%20Lengkap:%0A-%20NIM:%0A-%20Email%20Students:%0A%0AData%20yang%20saya%20berikan%20di%20atas%20telah%20sesuai%20dan%20email%20ini%20saya%20kirimkan%20menggunakan%20email%20student%20saya.%20Mohon%20bantuannya%20agar%20permohonan%20ini%20dapat%20diproses.%0A%0ATerima%20kasih.%0A%0ABest%20Regards,%0A[Your%20Name]"
                style="
                    text-decoration:none;
                    font-size:15px;
                    color:#2563eb;
                    font-weight:500;
                "
            >
                Create an account?
            </a>
        </div>
                """,
                unsafe_allow_html=True
            )


        # =========================
        # LOGIN BUTTON
        # =========================
        if st.button("Login", width="stretch"):

            # ===== USER CHECK =====
            if not user:
                st.session_state.login_attempt += 1

                st.error(
                    f"Username tidak ditemukan "
                    f"({st.session_state.login_attempt}/3)"
                )

                if st.session_state.login_attempt >= 3:
                    st.session_state.auth_mode = "reset"
                    st.rerun()

                st.stop()

            # ===== PASSWORD CHECK =====
            stored_hash = str(
                user.get("passwordhash", "")
            ).strip()

            if not stored_hash:
                st.error("Password belum diset")
                st.stop()

            if not stored_hash.startswith("$2b$"):
                st.error("Format hash tidak valid")
                st.stop()

            try:

                if not bcrypt.checkpw(
                    password.encode(),
                    stored_hash.encode()
                ):

                    st.session_state.login_attempt += 1

                    st.error(
                        f"Password salah "
                        f"({st.session_state.login_attempt}/3)"
                    )

                    if st.session_state.login_attempt >= 3:
                        st.session_state.auth_mode = "reset"
                        st.rerun()

                    st.stop()

            except ValueError:
                st.error("Hash password invalid")
                st.stop()

            # ===== OTP CHECK =====
            if not is_admin_user:

                if not otp_input.strip():
                    st.error("OTP wajib diisi")
                    st.stop()

                if not attendance.validate_otp(
                    username,
                    otp_input
                ):

                    st.session_state.login_attempt += 1

                    st.error(
                        f"OTP salah "
                        f"({st.session_state.login_attempt}/3)"
                    )

                    if st.session_state.login_attempt >= 3:
                        st.session_state.auth_mode = "reset"
                        st.rerun()

                    st.stop()

            # ===== LOGIN SUCCESS =====
            st.session_state.login_attempt = 0

            st.session_state.is_logged_in = True
            st.session_state.username = username
            st.session_state.is_admin = is_admin_user

            if remember_me:
                st.session_state.remember_me = True

            st.success("✅ Login berhasil!")

            time.sleep(1)

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
                    st.error("Password tidak cocok", width="stretch")
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
                st.session_state.df_base = attendance.fetch_all()  # refresh data lama
                attendance.fetch_today_only.clear()  # clear cache hari ini
                jakarta_tz = pytz.timezone("Asia/Jakarta")

                st.session_state.last_refresh = datetime.datetime.now(
                    jakarta_tz
                ).strftime(f"%d %b %Y • %H:%M WIB")
                st.success("Data berhasil disinkronisasi")
                st.rerun()

            df = df_all.copy()

            # ===== DISPLAY ONLY =====
            df_display = df.copy()
        if not df_display.empty:

            df_display = df_display.drop(
                columns=[
                    "id",
                    "created_at",
                    "duration_hours",
                ],
                errors="ignore"
            )

        if not df.empty:
            df_display = df_display.drop(
                columns=["id", "created_at"],
                errors="ignore"
            )
            st.dataframe(df_display, width="stretch")
        else:
            st.info("Belum ada data absensi")

        with st.sidebar:
            st.title(f"Welcome, {st.session_state.username} 👋🏼")
            hari_map = {
                "Monday": "Monday",
                "Tuesday": "Tuesday",
                "Wednesday": "Wednesday",
                "Thursday": "Thursday",
                "Friday": "Friday",
                "Saturday": "Saturday",
                "Sunday": "Sunday"
            }

            now = datetime.datetime.now()

            hari = hari_map[now.strftime("%A")]

            today_display = now.strftime("%d %b %Y")

            st.caption(f"Today's: {hari}, {today_display}")

            st.subheader("🔐 OTP Management")

            if not df_users.empty:

                display_df = df_users[
                    df_users["isadmin"] != True
                ].copy()

                display_df = display_df[
                    ["username", "otp"]
                ]

                display_df["send"] = False

                edited_df = st.data_editor(
                    display_df,
                    hide_index=True,
                    width="stretch",
                    disabled=["username", "otp_date"],
                    column_config={
                        "username": "Username",
                        "otp_date": "OTP Date",
                        "otp": "OTP",
                        "send": st.column_config.CheckboxColumn(
                            "Send"
                        )
                    }
                )

                selected_users = edited_df[
                    edited_df["send"] == True
                ]

                if st.button(
                    "Send",
                    width="stretch"
                ):

                    if selected_users.empty:
                        st.warning("Pilih minimal 1 user")
                        st.stop()

                    success_count = 0

                    for _, row in selected_users.iterrows():

                        success, _ = attendance.send_otp_email(
                            row["username"]
                        )

                        if success:
                            success_count += 1

                    st.success(
                        f"Total {success_count} OTP Berhasil Dikirim"
                    )

            with st.expander("👤 User Management"):
                email = st.text_input("Email", key="create_email").strip()
                new_username = st.text_input("New Username", key="create_username").strip()
                new_password = st.text_input("Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
                is_admin = st.checkbox("Admin Access")

                if st.button("Create User", width="stretch"):
                    if new_username == "":
                        st.error("Username tidak boleh kosong")
                        st.stop()

                    if email == "":
                        st.error("Email wajib diisi")
                        st.stop()

                    if new_password != confirm_password:
                        st.error("Password tidak cocok")
                        st.stop()

                    success = attendance.create_user(
                        new_username,
                        new_password,
                        is_admin,
                        email
                    )

                    if success:

                        attendance.send_welcome_email(
                            new_username,
                            new_password,
                            email
                        )

                        st.success("User berhasil dibuat & Welcome Email Terkirim")

                        st.session_state.df_users = attendance.fetch_users()
                        time.sleep(2)

                        st.rerun()

            if st.button("Logout", width="stretch"):
                st.session_state.clear()
                st.rerun()

    # ================= ANALYTICS =================
        st.divider()
        st.subheader("📊 Analytics Dashboard")

        summary, status, trend = get_analytics_from_df(df_all)

    # ================= TODAY OVERVIEW =================

        today_str = datetime.datetime.now().strftime("%Y-%m-%d")

        df_today_overview = df_all[
            df_all["waktu"].astype(str).str.startswith(today_str)
        ].copy()

        clock_in_today = len(
            df_today_overview[df_today_overview["type"] == "IN"]
        )

        clock_out_today = len(
            df_today_overview[df_today_overview["type"] == "OUT"]
        )

        izin_sakit_today = len(
            df_today_overview[
                df_today_overview["keterangan"].isin(["Izin", "Sakit"])
            ]
        )

        belum_clock_out = max(
            clock_in_today - clock_out_today,
            0
        )

        if summary is None:
            st.info("Belum ada data analytics")
        else:

            st.markdown("### 📌 Today Attendance Overview")

            col1, col2, col3, col4 = st.columns(4)

            col1.metric(
                "Clock In",
                clock_in_today
            )

            col2.metric(
                "Clock Out",
                clock_out_today
            )

            col3.metric(
                "Belum Clock Out",
                belum_clock_out
            )

            col4.metric(
                "Izin / Sakit",
                izin_sakit_today
            )

            # ===== SUMMARY =====
            st.markdown("### 👤 Summary Per User")
            st.dataframe(summary, width="stretch", hide_index=True)

            st.markdown("### 📊 Attendance Status Distribution")

            status_chart = (
                status.groupby("keterangan")["jumlah"]
                .sum()
                .reset_index()
            )

            status_chart = status_chart.set_index("keterangan")

            st.bar_chart(status_chart)

    # ================= USER =================
    else:

        with st.sidebar:
            st.title(f"Welcome, {st.session_state.username} 👋🏼")

            df_user = df_all[
                df_all["username"] == st.session_state.username
            ].copy()

            history = df_user[df_user["type"] != "INIT"].sort_values("waktu", ascending=False)
            history = history.copy()

            if not history.empty:
                st.subheader("📜 Riwayat Absensi")
                history_display = history.drop(
                    columns=["id", "created_at", "username", "duration_hours", "latitude", "lokasi"],
                    errors="ignore"
                )

                st.dataframe(history_display, width="stretch", hide_index=True,)
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
            df_user["waktu"].astype(str).str.startswith(today)
        ]

        if df_today.empty:
            st.info("ℹ️ Belum ada aktivitas hari ini")
        else:
            last = df_today.iloc[0]

            bulan_map = {
                "Jan": "Jan",
                "Feb": "Feb",
                "Mar": "Mar",
                "Apr": "Apr",
                "May": "Mei",
                "Jun": "Jun",
                "Jul": "Jul",
                "Aug": "Agu",
                "Sep": "Sep",
                "Oct": "Okt",
                "Nov": "Nov",
                "Dec": "Des"
            }

            if last.get("type") == "IN":

                waktu_clock_in = pd.to_datetime(
                    last.get("waktu")
                )

                formatted_time = waktu_clock_in.strftime(
                    "%H:%M WIB • %d %b %Y"
                )

                for eng, indo in bulan_map.items():
                    formatted_time = formatted_time.replace(
                        eng,
                        indo
                    )

                st.warning(
                    f"🟡 Clock In berhasil sejak {formatted_time}"
                )

            elif last.get("type") == "OUT":

                duration = last.get("duration", "-")

                st.info(
                    f"🕰️ Total Durasi: {duration}"
                )

        # ===== RESULT =====
        result = st.session_state.get("last_result")
        if result:

            if result == "clock_in":
                st.success("✅ Clock In berhasil!")
            elif result == "clock_out":
                st.success("✅ Clock Out berhasil!")
            elif result == "already_clocked_out":
                st.warning(f"❗️Hari Ini (**{last.get('hari', '-')}**), Sudah Clock Out")
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

        if st.button(
            "Clock In / Out",
            width="stretch",
        ):

            current_click = time.time()

            # =========================
            # ANTI DOUBLE CLICK
            # =========================
            if (
                current_click -
                st.session_state.last_attendance_time
            ) < 15:  # 15 detik cooldown

                st.warning(
                    "⚠️ Mohon tunggu beberapa detik sebelum mencoba lagi."
                )

                st.stop()

            st.session_state.last_attendance_time = current_click


            # 🔒 HARDENING: pastikan lokasi ada
            if lat is None or lon is None:
                st.error("❌ Lokasi belum terdeteksi.")
                st.stop()

            # 🔒 VALIDASI LOKASI
            if not is_within_allowed_location(
                current_location,
                ALLOWED_LOCATION
            ):
                st.error("❌ Anda tidak berada di lokasi yang diizinkan.")
                st.stop()

            with st.spinner("Memproses Absensi..."):

                time.sleep(1)

                st.session_state.last_result = attendance.save_attendance(
                    st.session_state.username,
                    hari,
                    jadwal,
                    current_time,
                    current_location,
                    message,
                    df_all
                )

            attendance.fetch_today_only.clear()

            st.rerun()