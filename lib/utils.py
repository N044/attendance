import streamlit as st

# Fungsi Logout
def logout():
    st.session_state.is_logged_in = False
    st.session_state.username = ""
    st.session_state.is_admin = False
    st.rerun()  # Refresh halaman setelah logout