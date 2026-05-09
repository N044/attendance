# 📍 Monitoring Management System - Geolocation-Based Attendance

## 🚀 Overview
This project is a **Geolocation-Based Attendance System** designed for **monitoring management**, ensuring **secure and accurate** check-ins. It incorporates **TOTP verification** to prevent account sharing and enhance system integrity. 

Built with **Streamlit** and deployed on **Streamlit Cloud**, this system is optimized for seamless and efficient attendance tracking.

## ✨ Features
- 📌 **Geolocation-Based Attendance** – Ensures users check in from the correct location.
- 🔒 **TOTP Verification** – Adds an extra security layer using Google Authenticator.
- ☁️ **Streamlit Cloud Deployment** – Lightweight and easy to access.
- 📊 **Admin Dashboard** – Provides an overview of user attendance records.
- 📝 **CSV Data Storage** – No database required; all records are stored in CSV files.

## 🏗️ Tech Stack
- **Python** 🐍 (Main programming language)
- **Streamlit** 🎈 (Frontend & Backend framework)
- **PyOTP** 🔑 (For TOTP-based authentication)
- **Geopy & Geolocation APIs** 🌍 (For location validation)
- **Pandas** 📊 (For handling CSV data storage)

## 📦 Installation & Setup
1. **Clone the repository:**  
   ```bash
   git clone https://github.com/N044/attendance.git
   cd your-repo
   ```

2. **Install dependencies:**  
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**  
   ```bash
   streamlit run app.py
   ```

## 🔑 Usage
1. **Attendance check-in** – Users verify their location and confirm check-in.
2. **Admin verification** – Admins can view/edit attendance records via a dashboard & provide OTP Code.

## 📌 Future Enhancements
- ✅ Implement facial recognition for additional security.
- ✅ Add notifications for attendance confirmation.
- ✅ Expand reporting & analytics features.

## 💡 Contribution
Feel free to fork this repo and submit a pull request! 🤝

---
🚀 **Developed with passion by Noah!** 💙

