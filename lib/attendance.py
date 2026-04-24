import pandas as pd
import bcrypt
import random
from datetime import datetime
import streamlit as st
from app import init_otp
from lib.airtable import request
from lib.config import get_config

cfg = get_config()

# ================= CACHE =================

@st.cache_data(ttl=300)  # cache selama 5 menit
def fetch_users():
    data = request("GET", cfg["TABLE_USERS"])
    if not data:
        return pd.DataFrame()
    rows = [r.get("fields", {}) | {"id": r["id"]} for r in data.get("records", [])]
    return pd.DataFrame(rows)


@st.cache_data(ttl=120) # cache selama 2 menit
def fetch_all():
    records = []
    offset = None

    while True:
        params = {"offset": offset} if offset else {}
        data = request("GET", cfg["TABLE_ATTENDANCE"], params=params)

        if not data:
            return pd.DataFrame()

        records.extend(data.get("records", []))
        offset = data.get("offset")

        if not offset:
            break

    rows = [r.get("fields", {}) for r in records]
    df = pd.DataFrame(rows)

    if not df.empty and "Waktu" in df.columns:
        df = df.sort_values("Waktu", ascending=False)

    return df


# ================= USER =================

def get_user(username):
    df = fetch_users()
    if df.empty:
        return None

    user = df[df["Username"] == username]

    if user.empty:
        return None

    user = user.iloc[0].to_dict()

    # 🔥 FIX KRITIS DI SINI
    raw_admin = user.get("IsAdmin", False)
    user["IsAdmin"] = str(raw_admin).lower() in ["true", "1", "yes"]

    return user


def update_user(record_id, fields):
    res = request(
        "PATCH",
        cfg["TABLE_USERS"],
        json={"records": [{"id": record_id, "fields": fields}]}
    )

    fetch_users.clear()  # invalidate cache
    return res is not None

def ensure_admin_exists():
    df = fetch_users()

    if df.empty:
        need_admin = True
    else:
        if "IsAdmin" not in df.columns:
            need_admin = True
        else:
            admin_flags = df["IsAdmin"].astype(str).str.lower().isin(["true", "1", "yes"])
            need_admin = not admin_flags.any()

    if need_admin:
        hashed = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()

        insert_user({
            "Username": "admin",
            "PasswordHash": hashed,
            "IsAdmin": True,
            "OTP": "",
            "OTP_Date": ""
        })

def create_user_airtable(username, password, is_admin=False):

    # 🔐 HASH PASSWORD
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    payload = {
        "Username": username,
        "PasswordHash": hashed,
        "IsAdmin": bool(is_admin)
    }

    # 🔥 NON ADMIN → OTP LANGSUNG ADA
    if not is_admin:
        payload["OTP"] = str(random.SystemRandom().randint(100000, 999999))
        payload["OTP_Date"] = datetime.now().strftime("%Y-%m-%d")

    success = insert_user(payload)

    if not success:
        return False

    # 🔥 SYNC KE ATTENDANCE TABLE (INIT RECORD)
    if not is_admin:
        insert_record({
            "Username": username,
            "Hari": "-",
            "Keterangan": "INIT",
            "Waktu": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Lokasi": "-",
            "Pesan": "Auto create user",
            "Type": "INIT",
            "Duration": ""
        })

    return True


def insert_user(payload):
    res = request("POST", cfg["TABLE_USERS"], json={"records": [{"fields": payload}]})
    fetch_users.clear()
    return res is not None


# ================= OTP =================

def ensure_daily_otp(user):
    today = datetime.now().strftime("%Y-%m-%d")

    if str(user.get("OTP_Date", "")) == today:
        return user.get("OTP")

    new_otp = str(random.SystemRandom().randint(100000, 999999))

    update_user(user["id"], {
        "OTP": new_otp,
        "OTP_Date": today
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

    today = datetime.now().strftime("%Y-%m-%d")
    init_otp(today)
    

    if "OTP_Date" not in df.columns:
        sync_all_user_otp()
        return

    # kalau sudah hari ini → STOP
    if (df["OTP_Date"].astype(str) == today).all():
        return

    sync_all_user_otp()


def sync_all_user_otp():
    df = fetch_users()
    if df.empty:
        return

    today = datetime.now().strftime("%Y-%m-%d")

    updates = []

    for _, row in df.iterrows():
        if str(row.get("OTP_Date", "")) != today:
            updates.append({
                "id": row["id"],
                "fields": {
                    "OTP": str(random.SystemRandom().randint(100000, 999999)),
                    "OTP_Date": today
                }
            })

    for i in range(0, len(updates), 10):
        request("PATCH", cfg["TABLE_USERS"], json={"records": updates[i:i+10]})

    fetch_users.clear()


# ================= ATTENDANCE =================

def insert_record(payload):
    res = request(
        "POST",
        cfg["TABLE_ATTENDANCE"],
        json={"records": [{"fields": payload}]}
    )
    fetch_all.clear()
    return res is not None


def save_attendance(username, hari, ket, waktu, lokasi, pesan, df):

    df_today = df[
        (df["Username"] == username) &
        (df["Type"] != "INIT") &
        (df["Waktu"].astype(str).str.startswith(datetime.now().strftime("%Y-%m-%d")))
    ]

    if not df_today.empty:
        last = df_today.iloc[0]

        if last["Type"] == "OUT":
            return "already_clocked_out"

        if last["Keterangan"] in ["Sakit", "Izin"]:
            return "no_clock_out_needed"

        if last["Type"] == "IN":
            return _clock_out(username, hari, ket, waktu, lokasi, pesan, last)

    return _clock_in(username, hari, ket, waktu, lokasi, pesan)


def _clock_in(u, h, k, w, loc, msg):

    payload = {
        "Username": u,
        "Hari": h,
        "Keterangan": k,
        "Waktu": w,
        "Lokasi": str(loc),
        "Pesan": msg or "",
        "Type": "IN",
        "Duration": ""
    }

    return "clock_in" if insert_record(payload) else "failed"


def _clock_out(u, h, k, w, loc, msg, last):

    t1 = pd.to_datetime(last["Waktu"], errors='coerce').tz_localize(None)
    t2 = pd.to_datetime(w, errors='coerce').tz_localize(None)

    if pd.isna(t1) or pd.isna(t2):
        return "failed"

    duration = round((t2 - t1).total_seconds() / 3600, 2)

    payload = {
        "Username": u,
        "Hari": h,
        "Keterangan": k,
        "Waktu": w,
        "Lokasi": str(loc),
        "Pesan": msg or "",
        "Type": "OUT",
        "Duration": f"{duration} Jam"
    }

    return "clock_out" if insert_record(payload) else "failed"


# ================= ANALYTICS =================

def get_analytics_from_df(df):

    if df.empty:
        return None, None, None

    df = df[df["Type"] != "INIT"]

    if "Duration" not in df.columns:
        df["Duration"] = "0"

    df["Duration"] = pd.to_numeric(
        df["Duration"].astype(str).str.replace(" Jam", ""),
        errors="coerce"
    ).fillna(0)

    df["Waktu"] = pd.to_datetime(df["Waktu"], errors="coerce")

    df_out = df[df["Type"] == "OUT"]

    summary = df_out.groupby("Username").agg(
        Total_Jam=("Duration", "sum"),
        Rata_Jam=("Duration", "mean"),
        Total_Hari=("Duration", "count")
    ).reset_index()

    status = df.groupby(["Username", "Keterangan"]).size().reset_index(name="Jumlah")

    df_out["Tanggal"] = df_out["Waktu"].dt.date
    trend = df_out.groupby(["Tanggal", "Username"]).agg(Jam=("Duration", "sum")).reset_index()

    return summary, status, trend

def show_attendance_history(df, username):
    if df.empty:
        return df

    df = df[df["Type"] != "INIT"]

    return df[df["Username"] == username].sort_values("Waktu", ascending=False)