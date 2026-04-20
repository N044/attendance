import streamlit as st

def get_config():
    try:
        return {
            "BASE_ID": st.secrets["AIRTABLE_BASE_ID"],
            "TOKEN": st.secrets["AIRTABLE_TOKEN"],
            "TABLE_ATTENDANCE": st.secrets["AIRTABLE_TABLE_ATTENDANCE"],
            "TABLE_USERS": st.secrets["AIRTABLE_TABLE_USERS"],
        }
    except Exception:
        raise RuntimeError(
            "Secrets tidak ditemukan atau tidak lengkap.\n"
            "Pastikan secrets.toml berisi:\n"
            "AIRTABLE_BASE_ID, AIRTABLE_TOKEN,\n"
            "AIRTABLE_TABLE_ATTENDANCE, AIRTABLE_TABLE_USERS"
        )