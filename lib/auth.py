import bcrypt

# Simulasi pengguna dengan password yang sudah di-hash
users = {
    "user1": {"password": bcrypt.hashpw(b"password123", bcrypt.gensalt()), "isAdmin": False},
    "user2": {"password": bcrypt.hashpw(b"anotherpassword", bcrypt.gensalt()), "isAdmin": False},
    "admin": {"password": bcrypt.hashpw(b"admin123", bcrypt.gensalt()), "isAdmin": True}
}

# Fungsi untuk memeriksa password
def check_password(password_hash, user_password):
    return bcrypt.checkpw(user_password.encode('utf-8'), password_hash)

# Fungsi untuk memeriksa apakah pengguna valid
def is_valid_user(username, password):
    if username in users:
        return check_password(users[username]["password"], password)
    return False