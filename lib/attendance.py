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
<body style="font-family: Arial, sans-serif; background-color:#f4f4f4; padding:20px;">

    <div style="
        max-width:500px;
        margin:auto;
        background:white;
        padding:30px;
        border-radius:12px;
    ">

        <h2 style="color:#333;">
            Welcome to Monitoring Attendance System
        </h2>

        <p>Hello <b>{username}</b>,</p>

        <p>
            Your account has been successfully registered.
        </p>

        <div style="
            background:#f8fafc;
            padding:20px;
            border-radius:10px;
            margin:25px 0;
        ">

            <p style="margin:0 0 10px 0;">
                <b>Account Information</b>
            </p>

            <p style="margin:5px 0;">
                Username:
                <b>{username}</b>
            </p>

            <p style="margin:5px 0;">
                Password:
                <b>{password}</b>
            </p>

        </div>

        <div style="margin:30px 0; text-align:center;">

            <a
                href="https://mmsa-mikroskil.streamlit.app/"
                style="
                    background-color:#2563eb;
                    color:white;
                    padding:12px 24px;
                    text-decoration:none;
                    border-radius:8px;
                    font-weight:bold;
                    display:inline-block;
                "
            >
                Open Website
            </a>

        </div>

        <p>
            Website:
            <br>
            <a href="https://mmsa-mikroskil.streamlit.app/">
                https://mmsa-mikroskil.streamlit.app/
            </a>
        </p>

        <div style="
            background:#fef3c7;
            padding:15px;
            border-radius:10px;
            margin-top:20px;
        ">

            <p style="
                margin:0;
                color:#92400e;
                font-weight:bold;
            ">
                For security reasons, please change your password immediately.
            </p>

        </div>

        <p style="margin-top:20px;">
            Please mark this email as safe / not spam to ensure future OTP emails are received properly.
        </p>

        <hr style="margin:30px 0;">

        <p style="font-size:12px; color:gray;">
            Student Affairs Office
        </p>

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
        <body style="font-family: Arial, sans-serif; background-color:#f4f4f4; padding:20px;">

            <div style="
                max-width:500px;
                margin:auto;
                background:white;
                padding:30px;
                border-radius:12px;
                box-shadow:0 2px 8px rgba(0,0,0,0.1);
            ">

                <h2 style="color:#333;">
                    Universitas Mikroskil Student Affairs Office
                </h2>

                <hr style="margin:30px 0;">

                <p>Hello <b>{username}</b>,</p>

                <p>
                    Your OTP code for verification is:
                </p>

                <div style="
                    font-size:32px;
                    font-weight:bold;
                    letter-spacing:4px;
                    color:#2563eb;
                    text-align:center;
                    margin:30px 0;
                ">
                    {otp}
                </div>

                <p>
                    This OTP is valid for today only.
                </p>
                <p>
                    Please do not share this OTP with anyone. If you did not request this, please ignore this email.
                </p>

                <hr style="margin:30px 0;">

                <p style="font-size:12px; color:gray;">
                    Monitoring Attendance System (UM.SAO) - Developed by N044 </a>
                </p>

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