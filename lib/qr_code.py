import subprocess
import sys
import qrcode
import datetime
from io import BytesIO
import cv2
from PIL import Image
import streamlit as st

# Fungsi untuk menghasilkan QR Code harian
def generate_daily_qr_code(secret_key):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    qr_code_data = f"{today}-{secret_key}"
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_code_data)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer, qr_code_data

# Fungsi untuk memindai QR Code
def scan_qr_code():
    
    cap = cv2.VideoCapture(0)  # Gunakan kamera default (index 0)

    if not cap or not cap.isOpened():
        st.error("Tidak dapat mengakses kamera. Pastikan kamera terhubung atau gunakan perangkat yang mendukung.")
        return None

    qr_code_data = None
    st.write("Membuka kamera... Arahkan kamera ke QR Code.")

    # Placeholder untuk tampilan frame
    frame_placeholder = st.empty()

    # Inisialisasi state untuk tombol berhenti
    if "stop_scan" not in st.session_state:
        st.session_state.stop_scan = False

    # Tombol berhenti di luar loop
    if st.button("Berhenti"):
        st.session_state.stop_scan = True

    while not st.session_state.stop_scan:
        ret, frame = cap.read()
        if not ret:
            st.error("Gagal membaca frame dari kamera.")
            break

        # Konversi frame ke RGB untuk ditampilkan di Streamlit
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        decoded_objects = qrcode.decode(Image.fromarray(frame))

        # Jika QR Code ditemukan
        if decoded_objects:
            qr_code_data = decoded_objects[0].data.decode('utf-8')
            st.success(f"QR Code berhasil dipindai: {qr_code_data}")
            break

        # Tampilkan frame di Streamlit (hanya satu frame yang diperbarui)
        frame_placeholder.image(frame, caption="Arahkan kamera ke QR Code", use_column_width=True)

    # Tutup kamera setelah selesai
    cap.release()
    cv2.destroyAllWindows()

    # Reset state tombol setelah selesai
    st.session_state.stop_scan = False

    return qr_code_data