import pandas as pd
import bcrypt
import random
from datetime import datetime
from lib.airtable import request
from lib.config import get_config

cfg = get_config()

# ================= USERS =================

def fetch_users():
    data = request("GET", cfg["TABLE_USERS"])
    if not data:
        return pd.DataFrame()
    rows = [r.get("fields", {}) for r in data.get("records", [])]
    return pd.DataFrame(rows)


def get_user(username):
    data = request("GET", cfg["TABLE_USERS"])

    if not data:
        return None

    for r in data.get("records", []):
        fields = r.get("fields", {})

        if fields.get("Username") == username:
            fields["id"] = r["id"]

            # 🔥 AUTO REFRESH OTP
            fields["OTP"] = ensure_daily_otp(fields)

            return fields

    return None


def insert_user(payload):
    res = request("POST", cfg["TABLE_USERS"], json={"records": [{"fields": payload}]})
    return res is not None


def update_user(record_id, fields):
    return request(
        "PATCH",
        cfg["TABLE_USERS"],
        json={"records": [{"id": record_id, "fields": fields}]}
    )


# ================= OTP =================

# def generate_otp_for_user(username):
#     user = get_user(username)
#     if not user:
#         return None

#     today = datetime.now().strftime("%Y-%m-%d")

#     if user.get("OTP") and str(user.get("OTP_Date")) == today:
#         return user.get("OTP")

#     new_otp = str(random.randint(100000, 999999))

#     update_user(user["id"], {
#         "OTP": new_otp,
#         "OTP_Date": today
#     })

#     return new_otp

def ensure_daily_otp(user):
    today = datetime.now().strftime("%Y-%m-%d")

    otp = user.get("OTP")
    otp_date = str(user.get("OTP_Date", ""))

    if not otp or otp_date != today:
        new_otp = str(random.randint(100000, 999999))  # ✅ 6 digit

        update_user(user["id"], {
            "OTP": new_otp,
            "OTP_Date": today
        })

        return new_otp

    return otp

def validate_otp(username, otp_input):
    user = get_user(username)

    if not user:
        return False

    return str(user.get("OTP")) == str(otp_input)

def sync_all_user_otp():
    data = request("GET", cfg["TABLE_USERS"])

    if not data:
        return

    today = datetime.now().strftime("%Y-%m-%d")

    updates = []

    for r in data.get("records", []):
        fields = r.get("fields", {})

        otp_date = str(fields.get("OTP_Date", ""))

        if otp_date != today:
            new_otp = str(random.randint(100000, 999999))

            updates.append({
                "id": r["id"],
                "fields": {
                    "OTP": new_otp,
                    "OTP_Date": today
                }
            })

    # batch update (maks 10 per request Airtable)
    for i in range(0, len(updates), 10):
        batch = updates[i:i+10]

        request(
            "PATCH",
            cfg["TABLE_USERS"],
            json={"records": batch}
        )

def is_today_synced():
    df = fetch_users()

    if df.empty:
        return False

    today = datetime.now().strftime("%Y-%m-%d")

    return all(str(x) == today for x in df.get("OTP_Date", []))

# ================= PASSWORD =================

def reset_password_with_otp(username, otp_input, new_password):
    user = get_user(username)

    if not user:
        return False, "User tidak ditemukan"

    today = datetime.now().strftime("%Y-%m-%d")

    if user.get("OTP") != str(otp_input) or str(user.get("OTP_Date")) != today:
        return False, "OTP salah atau expired"

    hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()

    update_user(user["id"], {
        "PasswordHash": hashed
    })

    return True, "Password berhasil direset"


# ================= ADMIN =================

def ensure_admin_exists():
    df = fetch_users()

    if df.empty or not df.get("IsAdmin", pd.Series()).fillna(False).any():

        hashed = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()

        insert_user({
            "Username": "admin",
            "PasswordHash": hashed,
            "IsAdmin": True
        })


# ================= CREATE USER =================

def create_user_airtable(username, password, is_admin=False):

    # 🔐 HASH
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    payload = {
        "Username": username,
        "PasswordHash": hashed,
        "IsAdmin": is_admin
    }

    if not is_admin:
        payload["OTP"] = str(random.randint(100000, 999999))
        payload["OTP_Date"] = datetime.now().strftime("%Y-%m-%d")

    success = insert_user(payload)

    if not success:
        return False

    # =============================
    # 🔥 SYNC KE ATTENDANCE TABLE
    # =============================
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


# ================= ATTENDANCE =================

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


def insert_record(payload):
    res = request(
        "POST",
        cfg["TABLE_ATTENDANCE"],
        json={"records": [{"fields": payload}]}
    )
    return res is not None


def get_today_attendance(username):
    df = fetch_all()

    if df.empty:
        return df

    today = datetime.now().strftime("%Y-%m-%d")

    df_today = df[
        (df["Username"] == username) &
        (df["Waktu"].str.startswith(today))
    ]

    # 🔥 WAJIB: buang INIT
    df_today = df_today[df_today["Type"] != "INIT"]

    return df_today


def save_attendance(username, hari, ket, waktu, lokasi, pesan=""):

    df_today = get_today_attendance(username)

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

    df_today = get_today_attendance(u)

    if not df_today.empty:
        last = df_today.iloc[0]
        if last["Type"] == "IN":
            return "already_clocked_in"

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

    t1 = pd.to_datetime(last["Waktu"], errors='coerce')
    t2 = pd.to_datetime(w, errors='coerce')

    # =========================
    # 🔥 FIX TIMEZONE MISMATCH
    # =========================
    if t1.tzinfo is not None:
        t1 = t1.tz_convert(None)

    if t2.tzinfo is not None:
        t2 = t2.tz_convert(None)

    # =========================
    # VALIDATION
    # =========================
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

def get_analytics():
    df = fetch_all()

    if df.empty:
        return None, None, None

    # =========================
    # 🔥 ENSURE COLUMNS EXIST
    # =========================
    required_cols = [
        "Username", "Keterangan", "Waktu",
        "Duration", "Type"
    ]

    for col in required_cols:
        if col not in df.columns:
            df[col] = ""

    # =========================
    # 🔥 CLEAN DATA
    # =========================
    df = df[df["Type"] != "INIT"]

    df['Duration'] = df['Duration'].astype(str).str.replace(" jam", "", regex=False)
    df['Duration'] = pd.to_numeric(df['Duration'], errors='coerce').fillna(0)

    df['Waktu'] = pd.to_datetime(df['Waktu'], errors='coerce')

    df_out = df[df['Type'] == 'OUT']

    # =========================
    # SUMMARY
    # =========================
    summary = df_out.groupby('Username').agg(
        Total_Jam=('Duration', 'sum'),
        Rata_Jam=('Duration', 'mean'),
        Total_Hari=('Duration', 'count')
    ).reset_index()

    summary['Rata_Jam'] = summary['Rata_Jam'].round(2)
    summary['Total_Jam'] = summary['Total_Jam'].round(2)

    # =========================
    # STATUS
    # =========================
    status = df.groupby(['Username', 'Keterangan']).size().reset_index(name='Jumlah')

    # =========================
    # TREND
    # =========================
    df_out['Tanggal'] = df_out['Waktu'].dt.date

    trend = df_out.groupby(['Tanggal', 'Username']).agg(
        Jam=('Duration', 'sum')
    ).reset_index()

    return summary, status, trend

def show_attendance_history(username):
    df = fetch_all()

    if df.empty:
        return df

    # 🔥 ensure kolom ada
    required_cols = ["Username", "Waktu", "Type", "Keterangan", "Duration"]
    for col in required_cols:
        if col not in df.columns:
            df[col] = ""

    # 🔥 filter user
    df_user = df[df["Username"] == username]

    # 🔥 remove INIT biar tidak ganggu UI
    df_user = df_user[df_user["Type"] != "INIT"]

    # 🔥 sorting terbaru di atas
    df_user = df_user.sort_values("Waktu", ascending=False)

    return df_user