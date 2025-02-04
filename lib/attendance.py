import pandas as pd
import os

FILE_PATH = 'data/absensi.csv'

# Fungsi untuk menyimpan data absensi
def save_attendance(username, hari, keterangan, waktu, lokasi, message=""):
    # Check if file exists and set header flag
    header_needed = not os.path.exists(FILE_PATH)
    
    # Prepare data with message (if any)
    df = pd.DataFrame({
        'Hari': [hari],
        'Keterangan': [keterangan],
        'Waktu': [waktu],
        'Lokasi': [lokasi],
        'Username': [username],
        'Pesan': [message]  # New column for optional message
    })
    
    # Save the data to CSV
    df.to_csv(FILE_PATH, mode='a', header=header_needed, index=False)

# Fungsi untuk menampilkan riwayat absensi
def show_attendance_history(username):
    if os.path.exists(FILE_PATH):
        df_absensi = pd.read_csv(FILE_PATH)
        df_user = df_absensi[df_absensi['Username'] == username]
        return df_user
    else:
        return pd.DataFrame(columns=['Hari', 'Keterangan', 'Waktu', 'Lokasi', 'Username', 'Pesan'])  # Include 'Pesan' column