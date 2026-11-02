
import os
import mysql.connector

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", ""),
    "database": os.environ.get(
        "DB_NAME", "inventaris_sparepart"
    ),
    "port": int(os.environ.get("DB_PORT", "3306")),
}

# Aktifkan SSL jika menggunakan database Aiven
if DB_CONFIG["host"] != "localhost":
    DB_CONFIG.update({
        "ssl_ca": os.path.join(
            os.path.dirname(__file__), "ca.pem"
        ),
        "ssl_verify_cert": True,
        "ssl_verify_identity": True
    })


def get_conn():
    """Membuka koneksi ke MySQL."""
    return mysql.connector.connect(**DB_CONFIG)


def query(sql, params=None, one=False):
    """Untuk SELECT (mengambil data)."""
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params or ())
        return cur.fetchone() if one else cur.fetchall()
    finally:
        conn.close()


def execute(sql, params=None):
    """Untuk INSERT, UPDATE, dan DELETE."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, params or ())
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()
