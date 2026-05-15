import pandas as pd
import bcrypt
import random
import streamlit as st
import pytz
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from lib.supabase_client import supabase

JAKARTA_TZ = pytz.timezone("Asia/Jakarta")

def now_jakarta():
    return datetime.now(JAKARTA_TZ)

# ================= CACHE =================

@st.cache_data(ttl=1800)  # cache selama 30 menit
def fetch_users():
    res = supabase.table("users").select("*").execute()

    if not res.data:
        return pd.DataFrame()
    
    return pd.DataFrame(res.data)


@st.cache_data(ttl=3600) # cache selama 1 jam
def fetch_all():

    res = supabase.table("attendance") \
        .select("*") \
        .order("waktu", desc=True) \
        .execute()

    if not res.data:
        return pd.DataFrame()

    return pd.DataFrame(res.data)

# ================= TODAY ONLY (PRODUCTION) =================

@st.cache_data(ttl=300)  # 5 menit (aktif hari ini)
def fetch_today_only():
    today = now_jakarta().strftime("%Y-%m-%d")


    res = supabase.table("attendance") \
        .select("*") \
        .gte("waktu", today) \
        .order("waktu", desc=True) \
        .execute()

    if not res.data:
        return pd.DataFrame()

    return pd.DataFrame(res.data)


# ================= USER =================

def send_welcome_email(
        username,
        password
):

    try:

        user = get_user(username)

        if not user:
            return False, "User tidak ditemukan"

        email = user.get("email")

        if not email or pd.isna(email):
            return False, "Email belum tersedia"

        email = str(email).strip()

        sender_email = st.secrets["EMAIL_SENDER"]
        sender_password = st.secrets["EMAIL_PASSWORD"]

        msg = MIMEMultipart()

        msg["From"] = f"Monitoring Attendance <{sender_email}>"
        msg["To"] = email
        msg["Subject"] = "Welcome to Monitoring Attendance System"

        body = f"""
        <html>
        <body style="
            margin:0;
            padding:24px;
            background:#eef2ff;
            font-family:Arial,sans-serif;
        ">

            <div style="
                max-width:560px;
                margin:auto;
                background:white;
                border-radius:24px;
                overflow:hidden;
            ">

                <!-- TOP BANNER -->
                <div style="
                    background:#f8fafc;
                    padding:36px 28px;
                    text-align:center;
                    border-bottom:4px solid #2563eb;
                ">

                    <div style="
                        font-size:46px;
                        margin-bottom:10px;
                    ">
                        🎉
                    </div>

                    <h1 style="
                        margin:0;
                        color:#111827;
                        font-size:28px;
                        font-weight:800;
                    ">
                        You’re In!
                    </h1>

                    <p style="
                        margin-top:12px;
                        color:#4b5563;
                        font-size:15px;
                        line-height:1.6;
                    ">
                        Your account<br>
                        is officially ready ✨
                    </p>

                </div>

                <!-- MAIN CONTENT -->
                <div style="padding:30px;">

                    <!-- GREETING -->
                    <div style="
                        background:#f9fafb;
                        border-radius:18px;
                        padding:22px;
                        margin-bottom:24px;
                        border:1px solid #e5e7eb;
                    ">

                        <p style="
                            margin:0;
                            color:#111827;
                            font-size:16px;
                            line-height:1.8;
                        ">
                            Hey <b>{username}</b> 👋<br><br>

                            Bipp.. Bippp 🤖<br>
                            Full access Granted to the system. Time to clock in ⏳
                        </p>

                    </div>

                    <!-- LOGIN CARD -->
                    <div style="
                        background:#f8fafc;
                        border-radius:18px;
                        padding:18px;
                        margin-top:24px;
                        border:2px solid #2563eb;
                    ">

                        <p style="
                            margin-top:0;
                            margin-bottom:14px;
                            font-size:15px;
                            font-weight:bold;
                            color:#2563eb;
                        ">
                            🔐 Login Details
                        </p>

                        <table
                            width="100%"
                            cellpadding="0"
                            cellspacing="0"
                            role="presentation"
                        >

                            <tr>

                                <!-- USERNAME -->
                                <td
                                    width="48%"
                                    valign="top"
                                    style="padding-right:6px;"
                                >

                                    <p style="
                                        margin:0 0 6px;
                                        font-size:11px;
                                        color:#4b5563;
                                    ">
                                        Username
                                    </p>

                                    <div style="
                                        background:white;
                                        color:#111827;
                                        padding:10px 8px;
                                        border-radius:10px;
                                        font-weight:bold;
                                        font-size:14px;
                                        text-align:center;
                                        border:1px solid #d1d5db;
                                        word-break:break-word;
                                    ">
                                        {username}
                                    </div>

                                </td>

                                <!-- PASSWORD -->
                                <td
                                    width="48%"
                                    valign="top"
                                    style="padding-left:6px;"
                                >

                                    <p style="
                                        margin:0 0 6px;
                                        font-size:11px;
                                        color:#4b5563;
                                    ">
                                        Password
                                    </p>

                                    <div style="
                                        background:white;
                                        color:#111827;
                                        padding:10px 8px;
                                        border-radius:10px;
                                        font-weight:bold;
                                        font-size:14px;
                                        text-align:center;
                                        border:1px solid #d1d5db;
                                        word-break:break-word;
                                    ">
                                        {password}
                                    </div>

                                </td>

                            </tr>

                        </table>

                    </div>

                    <!-- CTA -->
                    <div style="
                        text-align:center;
                        margin:34px 0;
                    ">

                        <a
                            href="https://mmsa-mikroskil.streamlit.app/"
                            style="
                                background:#2563eb;
                                color:white;
                                text-decoration:none;
                                padding:15px 28px;
                                border-radius:999px;
                                display:inline-block;
                                font-weight:bold;
                                font-size:15px;
                            "
                        >
                            Launch 🚀
                        </a>

                    </div>

                    <!-- ALERT -->
                    <div style="
                        background:#fff7ed;
                        border-radius:16px;
                        padding:18px;
                        border:1px solid #fdba74;
                    ">

                        <p style="
                            margin:0;
                            color:#9a3412;
                            font-size:14px;
                            line-height:1.7;
                        ">
                            ⚠️ Friendly reminder:<br>
                            Change your password to keep your account secure 🔒
                        </p>

                    </div>

                    <!-- OTP INFO -->
                    <div style="
                        margin-top:18px;
                        background:#eff6ff;
                        border-radius:16px;
                        padding:18px;
                        border:1px solid #93c5fd;
                    ">

                        <p style="
                            margin:0;
                            color:#1e40af;
                            font-size:14px;
                            line-height:1.7;
                        ">
                            💌 One more thing!<br>
                            Mark this email as safe / not spam so future OTP emails land safely in your inbox 👻
                        </p>

                    </div>

                    <!-- FOOTER -->
                    <div style="
                        margin-top:34px;
                        text-align:center;
                    ">

                        <p style="
                            margin:0;
                            color:#9ca3af;
                            font-size:12px;
                            line-height:1.8;
                        ">
                            Monitoring Attendance System (MMSA)<br>
                            Student Affairs Office · Universitas Mikroskil
                        </p>

                    </div>

                </div>

            </div>

        </body>
        </html>
        """

        msg.attach(MIMEText(body, "html"))

        server = smtplib.SMTP(
            "smtp.gmail.com",
            587
        )

        server.starttls()

        server.login(
            sender_email,
            sender_password
        )

        server.sendmail(
            sender_email,
            email,
            msg.as_string()
        )

        server.quit()

        return True, "Welcome email berhasil dikirim"

    except Exception as e:

        print("WELCOME EMAIL ERROR:", e)

        return False, str(e)

def send_otp_email(username):

    try:

        user = get_user(username)

        if not user:
            return False, "User tidak ditemukan"

        email = user.get("email")

        if not email or pd.isna(email):
            return False, "Email belum tersedia"

        email = str(email).strip()

        otp = str(user.get("otp", "")).strip()

        if not email:
            return False, "Email belum tersedia"

        if not otp:
            return False, "OTP belum tersedia"

        sender_email = st.secrets["EMAIL_SENDER"]
        sender_password = st.secrets["EMAIL_PASSWORD"]
        cc_email = "noah.napitupulu@mikroskil.ac.id"

        msg = MIMEMultipart()

        msg["From"] = f"Attendance System <{sender_email}>"
        msg["To"] = email
        msg["Cc"] = cc_email
        msg["Subject"] = "Attendance OTP Verification"

        body = f"""
        <html>
        <body style="
            margin:0;
            padding:24px;
            background:#eef2ff;
            font-family:Arial,sans-serif;
        ">

            <div style="
                max-width:520px;
                margin:auto;
                background:white;
                border-radius:24px;
                overflow:hidden;
            ">

                <!-- HEADER -->
                <div style="
                    background:#f8fafc;
                    padding:30px 28px;
                    text-align:center;
                    border-bottom:4px solid #2563eb;
                ">

                    <div style="
                        font-size:42px;
                        margin-bottom:10px;
                    ">
                        🔐
                    </div>

                    <h1 style="
                        margin:0;
                        color:#111827;
                        font-size:26px;
                        font-weight:800;
                    ">
                        OTP Verification
                    </h1>

                    <p style="
                        margin-top:12px;
                        color:#4b5563;
                        font-size:15px;
                        line-height:1.6;
                    ">
                        Monitoring Attendance System
                    </p>

                </div>

                <!-- CONTENT -->
                <div style="padding:28px;">

                    <!-- GREETING -->
                    <div style="
                        background:#f9fafb;
                        border-radius:18px;
                        padding:20px;
                        margin-bottom:22px;
                        border:1px solid #e5e7eb;
                    ">

                        <p style="
                            margin:0;
                            color:#111827;
                            font-size:16px;
                            line-height:1.8;
                        ">
                            Hey <b>{username}</b> 👋<br><br>

                            Security check detected 🤖<br>
                            Use the OTP below to continue.
                        </p>

                    </div>

                    <!-- OTP CARD -->
                    <div style="
                        background:#f8fafc;
                        border-radius:20px;
                        padding:24px 18px;
                        text-align:center;
                        border:2px solid #2563eb;
                    ">

                        <p style="
                            margin-top:0;
                            margin-bottom:14px;
                            font-size:13px;
                            letter-spacing:2px;
                            font-weight:bold;
                            color:#2563eb;
                        ">
                            YOUR OTP CODE
                        </p>

                        <div style="
                            background:white;
                            color:#111827;
                            display:inline-block;
                            padding:16px 20px;
                            border-radius:16px;
                            font-size:30px;
                            font-weight:900;
                            letter-spacing:6px;
                            border:1px solid #d1d5db;
                            max-width:100%;
                            box-sizing:border-box;
                        ">
                            {otp}
                        </div>

                    </div>

                    <!-- VALIDITY -->
                    <div style="
                        margin-top:22px;
                        background:#eff6ff;
                        border-radius:16px;
                        padding:18px;
                        border:1px solid #93c5fd;
                    ">

                        <p style="
                            margin:0;
                            color:#1e40af;
                            font-size:14px;
                            line-height:1.7;
                        ">
                            ⏳ This OTP is valid for today only.<br>
                            Don’t share this code with anyone.
                        </p>

                    </div>

                    <!-- IGNORE -->
                    <div style="
                        margin-top:18px;
                        background:#fff7ed;
                        border-radius:16px;
                        padding:18px;
                        border:1px solid #fdba74;
                    ">

                        <p style="
                            margin:0;
                            color:#9a3412;
                            font-size:14px;
                            line-height:1.7;
                        ">
                            Didn’t request this OTP?<br>
                            No worries — you can safely ignore this email 👌
                        </p>

                    </div>

                    <!-- FOOTER -->
                    <div style="
                        margin-top:34px;
                        text-align:center;
                    ">

                        <p style="
                            margin:0;
                            color:#9ca3af;
                            font-size:12px;
                            line-height:1.8;
                        ">
                            Monitoring Attendance System (UM.SAO)<br>
                            Student Affairs Office · Universitas Mikroskil
                        </p>

                    </div>

                </div>

            </div>

        </body>
        </html>
        """

        msg.attach(MIMEText(body, "html"))
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        print("SEND OTP TO:", email)

        recipients = [email, cc_email]
        time.sleep(1)  # delay untuk menghindari masalah rate limit
        server.sendmail(sender_email, recipients, msg.as_string())
        server.quit()

    except Exception as e:
        print("EMAIL ERROR:", e)
        return False, str(e)
    
    return True, "OTP berhasil dikirim ke email"

def get_user(username):
    df = fetch_users()
    if df.empty:
        return None

    user = df[df["username"] == username]

    if user.empty:
        return None

    user = user.iloc[0].to_dict()

    # 🔥 FIX KRITIS DI SINI
    raw_admin = user.get("isadmin", False)
    user["isadmin"] = str(raw_admin).lower() in ["true", "1", "yes"]

    return user


def update_user(record_id, fields):
    res = supabase.table("users") \
    .update(fields) \
    .eq("id", record_id) \
    .execute()

    fetch_users.clear()  # invalidate cache
    return res is not None

def ensure_admin_exists():

    df = fetch_users()

    if df.empty:

        insert_user({
            "username": "admin",
            "passwordhash": bcrypt.hashpw(
                "admin123".encode(),
                bcrypt.gensalt()
            ).decode(),
            "isadmin": True,
            "otp": "",
            "otp_date": ""
        })

        return

    # 🔥 cek username admin
    existing_admin = df[
        df["username"].astype(str).str.lower() == "admin"
    ]

    if existing_admin.empty:

        insert_user({
            "username": "admin",
            "passwordhash": bcrypt.hashpw(
                "admin123".encode(),
                bcrypt.gensalt()
            ).decode(),
            "isadmin": True,
            "otp": "",
            "otp_date": ""
        })

def create_user(username, password, is_admin=False, email=""):

    # 🔐 HASH PASSWORD
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    payload = {
        "username": username,
        "passwordhash": hashed,
        "isadmin": bool(is_admin),
        "email": email
    }

    # 🔥 NON ADMIN → OTP LANGSUNG ADA
    if not is_admin:
        payload["otp"] = str(random.SystemRandom().randint(100000, 999999))
        payload["otp_date"] = now_jakarta().strftime("%Y-%m-%d")

    success = insert_user(payload)

    if not success:
        return False

    # 🔥 SYNC KE ATTENDANCE TABLE (INIT RECORD)
    if not is_admin:
        insert_record({
            "username": username,
            "hari": "-",
            "keterangan": "INIT",
            "waktu": datetime.now(timezone.utc).isoformat(),
            "lokasi": "-",
            "pesan": "Auto create user",
            "type": "INIT",
            "duration": "-",
            "duration_hours": 0
        })

    return True

def reset_password_with_otp(username, otp_input, new_password):

    user = get_user(username)

    if not user:
        return False, "User tidak ditemukan"

    stored_otp = str(user.get("otp", "")).strip()

    if stored_otp != str(otp_input).strip():
        return False, "OTP tidak valid"

    hashed = bcrypt.hashpw(
        new_password.encode(),
        bcrypt.gensalt()
    ).decode()

    res = supabase.table("users") \
        .update({
            "passwordhash": hashed
        }) \
        .eq("username", username) \
        .execute()

    fetch_users.clear()

    if res.data is not None:
        return True, "Password berhasil direset"

    return False, "Gagal reset password"


def insert_user(payload):

    existing = supabase.table("users") \
        .select("username") \
        .eq("username", payload["username"]) \
        .execute()

    if existing.data:
        return False

    res = supabase.table("users") \
        .insert(payload) \
        .execute()

    fetch_users.clear()

    return res.data is not None


# ================= OTP =================

def ensure_daily_otp(user):
    today = now_jakarta().strftime("%Y-%m-%d")

    if str(user.get("otp_date", "")) == today:
        return user.get("otp")

    new_otp = str(random.SystemRandom().randint(100000, 999999))

    update_user(user["id"], {
        "otp": new_otp,
        "otp_date": today
    })

    return new_otp


def validate_otp(username, otp_input):
    user = get_user(username)
    if not user:
        return False

    otp = ensure_daily_otp(user)
    return str(otp) == str(otp_input)


# ================= GLOBAL OTP SYNC =================

def sync_otp_once_per_day():
    df = fetch_users()
    if df.empty:
        return

    today = now_jakarta().strftime("%Y-%m-%d")

    if "otp_date" not in df.columns:
        sync_all_user_otp()
        return

    # kalau sudah hari ini → STOP
    df_non_admin = df[df["isadmin"] != True]

    if (df_non_admin["otp_date"].astype(str) == today).all():
        return

    sync_all_user_otp()


def sync_all_user_otp():
    df = fetch_users()
    if df.empty:
        return

    today = now_jakarta().strftime("%Y-%m-%d")

    for _, row in df.iterrows():

        if row.get("isadmin") == True:
            continue
        
        supabase.table("users") \
            .update({
                "otp": str(random.SystemRandom().randint(100000, 999999)),
                "otp_date": today
            }) \
            .eq("id", row["id"]) \
            .execute()

    fetch_users.clear()


# ================= ATTENDANCE =================

def insert_record(payload):
    res = supabase.table("attendance") \
    .insert(payload) \
    .execute()

    fetch_today_only.clear()  # invalidate cache hari ini
    fetch_all.clear()  # invalidate cache

    return res.data is not None


def save_attendance(username, hari, ket, waktu, lokasi, pesan, df):

    today = now_jakarta().strftime("%Y-%m-%d")
    df_temp = df.copy()

    df_temp["waktu_dt"] = pd.to_datetime(
        df_temp["waktu"],
        errors="coerce",
        utc=True
    )

    today_date = now_jakarta().date()

    valid_dates = df_temp["waktu_dt"].notna()

    df_today = df_temp[
        (df_temp["username"] == username) &
        (df_temp["type"] != "INIT") &
        valid_dates &
        (df_temp["waktu_dt"].apply(lambda x: x.date()) == today_date)
    ]

    if not df_today.empty:
        last = df_today.iloc[0]

        if last["type"] == "OUT":
            return "already_clocked_out"

        if last["keterangan"] in ["Sakit", "Izin"]:
            return "no_clock_out_needed"

        if last["type"] == "IN":
            return _clock_out(username, hari, ket, waktu, lokasi, pesan, last)

    return _clock_in(username, hari, ket, waktu, lokasi, pesan)


def _clock_in(u, h, k, w, loc, msg):

    payload = {
        "username": u,
        "hari": h,
        "keterangan": k,
        "waktu": w,
        "lokasi": str(loc),
        "pesan": msg or "",
        "type": "IN",
        "duration": "-",
        "duration_hours": 0
    }

    return "clock_in" if insert_record(payload) else "failed"


def _clock_out(u, h, k, w, loc, msg, last):

    t1 = pd.to_datetime(last["waktu"], errors='coerce').tz_localize(None)
    t2 = pd.to_datetime(w, errors='coerce').tz_localize(None)

    if pd.isna(t1) or pd.isna(t2):
        return "failed"

    duration_raw = (t2 - t1).total_seconds() / 3600

    # 🔥 floor ke 2 desimal (bukan round)
    duration = int(duration_raw * 100) / 100

    payload = {
        "username": u,
        "hari": h,
        "keterangan": k,
        "waktu": w,
        "lokasi": str(loc),
        "pesan": msg or "",
        "type": "OUT",
        "duration": format_duration(duration),
        "duration_hours": round(duration, 2)  # untuk analytics, tetap simpan sebagai number
    }

    return "clock_out" if insert_record(payload) else "failed"


# ================= ANALYTICS =================

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


def get_analytics_from_df(df):

    if df.empty:
        return None, None, None

    df = df[df["type"] != "INIT"]

    df["waktu"] = pd.to_datetime(
        df["waktu"],
        errors="coerce",
        utc=True
    )

    df = df.dropna(subset=["waktu"])

    df_out = df[df["type"] == "OUT"].copy()

    df_out["duration_hours"] = pd.to_numeric(
        df_out["duration_hours"],
        errors="coerce"
)

    summary = df_out.groupby("username").agg(
        Total_Jam=("duration_hours", "sum"),
        Rata_Jam=("duration_hours", "mean"),
        Total_Hari=("duration_hours", "count")
    ).reset_index()

    status = df.groupby(["username", "keterangan"]).size().reset_index(name="jumlah")

    df_out["tanggal"] = df_out["waktu"].dt.date
    trend = df_out.groupby(
        ["tanggal"]
    ).agg(
        jam=("duration_hours", "sum")
    ).reset_index()

    return summary, status, trend

def show_attendance_history(df, username):
    if df.empty:
        return df

    df = df[df["type"] != "INIT"]

    return df[df["username"] == username].sort_values("waktu", ascending=False)