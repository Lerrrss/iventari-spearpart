from werkzeug.security import generate_password_hash
from db import query, execute

username = input("Username: ").strip()
password = input("Password: ")
hash_baru = generate_password_hash(password)

ada = query("SELECT id_admin FROM admin WHERE username=%s", (username,), one=True)

if ada:
    execute("UPDATE admin SET password_hash=%s WHERE id_admin=%s",
            (hash_baru, ada["id_admin"]))
    print("Password admin yang sudah ada berhasil diperbarui.")
else:
    nama = input("Nama lengkap: ").strip()
    execute("INSERT INTO admin (username, password_hash, nama_lengkap) VALUES (%s,%s,%s)",
            (username, hash_baru, nama))
    print("Admin baru berhasil dibuat.")