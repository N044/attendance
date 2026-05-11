import pandas as pd
import bcrypt
import random
import streamlit as st
import resend
import pytz
from datetime import datetime, timezone
from lib.supabase_client import supabase

resend.api_key = st.secrets["RESEND_API_KEY"]

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

        params = {
            "from": "Attendance <onboarding@resend.dev>",
            "to": [email],
            "subject": "Your OTP Code",
            "html": f"""
            <h2>Monitoring Attendance OTP</h2>

            <p>Hello {username},</p>

            <p>Your OTP Code:</p>

            <h1>{otp}</h1>

            <p>Please do not share this OTP.</p>
            """
        }

        response = resend.Emails.send(params)
        print("Resend response:", response)

        if response:
            return True, f"OTP berhasil dikirim ke {email}"

        return False, "Gagal mengirim OTP"

    except Exception as e:

        return False, str(e)

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