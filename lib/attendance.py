import pandas as pd
import os

# Ubah path file absensi sesuai dengan lokasi baru
FILE_PATH = 'data/absensi.csv'  # Misalnya file dipindahkan ke folder 'data'

# Fungsi untuk menyimpan data absensi
def save_attendance(username, hari, keterangan, waktu, qr_code_data):
    header_needed = not os.path.exists(FILE_PATH)
    df = pd.DataFrame({'Hari': [hari], 'Keterangan': [keterangan], 'Waktu': [waktu], 'QR Code': [qr_code_data], 'Username': [username]})
    df.to_csv(FILE_PATH, mode='a', header=header_needed, index=False)

# Fungsi untuk menampilkan riwayat absensi
def show_attendance_history(username):
    if os.path.exists(FILE_PATH):
        df_absensi = pd.read_csv(FILE_PATH)
        df_user = df_absensi[df_absensi['Username'] == username]
        return df_user
    else:
        return pd.DataFrame(columns=['Hari', 'Keterangan', 'Waktu', 'QR Code', 'Username'])