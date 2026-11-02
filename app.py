import os
from datetime import date
from functools import wraps

import mysql.connector
from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash)
from werkzeug.security import check_password_hash

from db import query, execute

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "kunci-lokal-untuk-pengembangan")


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "id_admin" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper



@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        admin = query("SELECT * FROM admin WHERE username=%s", (username,), one=True)
        if admin and check_password_hash(admin["password_hash"], password):
            session["id_admin"] = admin["id_admin"]
            session["nama"] = admin["nama_lengkap"]
            return redirect(url_for("dashboard"))
        flash("Username atau password salah.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    r = query(
        """SELECT COUNT(*) AS total_item,
                  COALESCE(SUM(stok), 0) AS total_stok,
                  COALESCE(SUM(stok <= stok_minimum), 0) AS total_menipis,
                  (SELECT COUNT(*) FROM supplier) AS total_supplier
           FROM sparepart""", one=True)
    menipis = query(
        """SELECT kode, nama, stok, stok_minimum, satuan FROM sparepart
           WHERE stok <= stok_minimum ORDER BY stok ASC""")
    masuk = query(
        """SELECT m.tanggal_masuk, s.nama, m.jumlah
           FROM barang_masuk m JOIN sparepart s ON s.id_sparepart = m.id_sparepart
           ORDER BY m.tanggal_masuk DESC, m.id_masuk DESC LIMIT 5""")
    keluar = query(
        """SELECT k.tanggal_keluar, s.nama, k.jumlah
           FROM barang_keluar k JOIN sparepart s ON s.id_sparepart = k.id_sparepart
           ORDER BY k.tanggal_keluar DESC, k.id_keluar DESC LIMIT 5""")
    return render_template("dashboard.html", r=r, menipis=menipis,
                           masuk=masuk, keluar=keluar)



@app.route("/sparepart")
@login_required
def sparepart():
    cari = request.args.get("q", "").strip()
    sql = "SELECT * FROM sparepart"
    params = ()
    if cari:
        sql += " WHERE nama LIKE %s OR kode LIKE %s OR kategori LIKE %s"
        params = (f"%{cari}%",) * 3
    sql += " ORDER BY nama"
    return render_template("sparepart.html", data=query(sql, params), cari=cari)


@app.route("/sparepart/tambah", methods=["GET", "POST"])
@login_required
def sparepart_tambah():
    if request.method == "POST":
        f = request.form
        try:
            execute(
                """INSERT INTO sparepart
                   (kode, nama, kategori, satuan, harga_jual, stok_minimum, lokasi_rak)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (f["kode"].strip(), f["nama"].strip(), f["kategori"].strip(),
                 f["satuan"].strip() or "pcs", f["harga_jual"] or 0,
                 int(f["stok_minimum"] or 0), f["lokasi_rak"].strip()))
            flash("Sparepart ditambahkan. Isi stoknya lewat menu Barang Masuk.", "ok")
            return redirect(url_for("sparepart"))
        except mysql.connector.errors.IntegrityError:
            flash("Kode sparepart sudah dipakai.", "error")
    return render_template("sparepart_form.html", item=None, judul="Tambah Sparepart")


@app.route("/sparepart/<int:id>/edit", methods=["GET", "POST"])
@login_required
def sparepart_edit(id):
    item = query("SELECT * FROM sparepart WHERE id_sparepart=%s", (id,), one=True)
    if not item:
        flash("Data tidak ditemukan.", "error")
        return redirect(url_for("sparepart"))
    if request.method == "POST":
        f = request.form
        try:
            execute(
                """UPDATE sparepart SET kode=%s, nama=%s, kategori=%s, satuan=%s,
                   harga_jual=%s, stok_minimum=%s, lokasi_rak=%s
                   WHERE id_sparepart=%s""",
                (f["kode"].strip(), f["nama"].strip(), f["kategori"].strip(),
                 f["satuan"].strip() or "pcs", f["harga_jual"] or 0,
                 int(f["stok_minimum"] or 0), f["lokasi_rak"].strip(), id))
            flash("Data diperbarui.", "ok")
            return redirect(url_for("sparepart"))
        except mysql.connector.errors.IntegrityError:
            flash("Kode sparepart sudah dipakai.", "error")
    return render_template("sparepart_form.html", item=item, judul="Edit Sparepart")


@app.route("/sparepart/<int:id>/hapus", methods=["POST"])
@login_required
def sparepart_hapus(id):
    try:
        execute("DELETE FROM sparepart WHERE id_sparepart=%s", (id,))
        flash("Sparepart dihapus.", "ok")
    except mysql.connector.errors.IntegrityError:
        flash("Tidak bisa dihapus: sparepart ini sudah punya riwayat barang masuk/keluar.", "error")
    return redirect(url_for("sparepart"))



@app.route("/supplier")
@login_required
def supplier():
    data = query("SELECT * FROM supplier ORDER BY nama_supplier")
    return render_template("supplier.html", data=data)


@app.route("/supplier/tambah", methods=["GET", "POST"])
@login_required
def supplier_tambah():
    if request.method == "POST":
        f = request.form
        execute(
            """INSERT INTO supplier (nama_supplier, kontak, telepon, kota, alamat)
               VALUES (%s,%s,%s,%s,%s)""",
            (f["nama_supplier"].strip(), f["kontak"].strip(), f["telepon"].strip(),
             f["kota"].strip(), f["alamat"].strip()))
        flash("Supplier ditambahkan.", "ok")
        return redirect(url_for("supplier"))
    return render_template("supplier_form.html", item=None, judul="Tambah Supplier")


@app.route("/supplier/<int:id>/edit", methods=["GET", "POST"])
@login_required
def supplier_edit(id):
    item = query("SELECT * FROM supplier WHERE id_supplier=%s", (id,), one=True)
    if not item:
        flash("Data tidak ditemukan.", "error")
        return redirect(url_for("supplier"))
    if request.method == "POST":
        f = request.form
        execute(
            """UPDATE supplier SET nama_supplier=%s, kontak=%s, telepon=%s,
               kota=%s, alamat=%s WHERE id_supplier=%s""",
            (f["nama_supplier"].strip(), f["kontak"].strip(), f["telepon"].strip(),
             f["kota"].strip(), f["alamat"].strip(), id))
        flash("Supplier diperbarui.", "ok")
        return redirect(url_for("supplier"))
    return render_template("supplier_form.html", item=item, judul="Edit Supplier")


@app.route("/supplier/<int:id>/hapus", methods=["POST"])
@login_required
def supplier_hapus(id):
    try:
        execute("DELETE FROM supplier WHERE id_supplier=%s", (id,))
        flash("Supplier dihapus.", "ok")
    except mysql.connector.errors.IntegrityError:
        flash("Tidak bisa dihapus: supplier ini sudah punya riwayat pengiriman.", "error")
    return redirect(url_for("supplier"))



@app.route("/masuk", methods=["GET", "POST"])
@login_required
def masuk():
    if request.method == "POST":
        f = request.form
        jumlah = int(f["jumlah"] or 0)
        if jumlah <= 0:
            flash("Jumlah harus lebih dari 0.", "error")
        else:
            try:
                execute(
                    """INSERT INTO barang_masuk
                       (id_sparepart, id_supplier, id_admin, jumlah,
                        harga_beli, tanggal_masuk, no_faktur)
                       VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                    (f["id_sparepart"], f["id_supplier"], session["id_admin"],
                     jumlah, f["harga_beli"] or 0, f["tanggal_masuk"],
                     f["no_faktur"].strip()))
                flash("Barang masuk dicatat. Stok bertambah otomatis.", "ok")
                return redirect(url_for("masuk"))
            except mysql.connector.Error as e:
                flash(f"Gagal menyimpan: {e.msg}", "error")

    daftar_sp = query("SELECT id_sparepart, kode, nama, stok FROM sparepart ORDER BY nama")
    daftar_sup = query("SELECT id_supplier, nama_supplier FROM supplier ORDER BY nama_supplier")
    riwayat = query(
        """SELECT m.tanggal_masuk, m.no_faktur, s.nama AS sparepart,
                  sp.nama_supplier, m.jumlah, m.harga_beli, a.nama_lengkap AS petugas
           FROM barang_masuk m
           JOIN sparepart s ON s.id_sparepart = m.id_sparepart
           JOIN supplier sp ON sp.id_supplier = m.id_supplier
           JOIN admin a     ON a.id_admin     = m.id_admin
           ORDER BY m.tanggal_masuk DESC, m.id_masuk DESC LIMIT 20""")
    return render_template("masuk.html", daftar_sp=daftar_sp, daftar_sup=daftar_sup,
                           riwayat=riwayat, hari_ini=date.today().isoformat())


# ================= BARANG KELUAR =================
@app.route("/keluar", methods=["GET", "POST"])
@login_required
def keluar():
    if request.method == "POST":
        f = request.form
        jumlah = int(f["jumlah"] or 0)
        if jumlah <= 0:
            flash("Jumlah harus lebih dari 0.", "error")
        else:
            try:
                execute(
                    """INSERT INTO barang_keluar
                       (id_sparepart, id_admin, jumlah, tanggal_keluar, tujuan, keterangan)
                       VALUES (%s,%s,%s,%s,%s,%s)""",
                    (f["id_sparepart"], session["id_admin"], jumlah,
                     f["tanggal_keluar"], f["tujuan"].strip(), f["keterangan"].strip()))
                flash("Barang keluar dicatat. Stok berkurang otomatis.", "ok")
                return redirect(url_for("keluar"))
            except mysql.connector.Error as e:
                # Pesan "Stok tidak cukup" datang dari trigger di MySQL
                flash(f"Gagal menyimpan: {e.msg}", "error")

    daftar_sp = query("SELECT id_sparepart, kode, nama, stok, satuan FROM sparepart ORDER BY nama")
    riwayat = query(
        """SELECT k.tanggal_keluar, s.nama AS sparepart, k.jumlah, s.satuan,
                  k.tujuan, k.keterangan, a.nama_lengkap AS petugas
           FROM barang_keluar k
           JOIN sparepart s ON s.id_sparepart = k.id_sparepart
           JOIN admin a     ON a.id_admin     = k.id_admin
           ORDER BY k.tanggal_keluar DESC, k.id_keluar DESC LIMIT 20""")
    return render_template("keluar.html", daftar_sp=daftar_sp, riwayat=riwayat,
                           hari_ini=date.today().isoformat())



LAPORAN = {
    "stok":   ("Laporan Stok Barang",   "v_laporan_stok",          None),
    "masuk":  ("Laporan Barang Masuk",  "v_laporan_barang_masuk",  "tanggal_masuk"),
    "keluar": ("Laporan Barang Keluar", "v_laporan_barang_keluar", "tanggal_keluar"),
    "mutasi": ("Rekap Mutasi Stok",     "v_laporan_mutasi_stok",   None),
}


@app.route("/laporan/<jenis>")
@login_required
def laporan(jenis):
    if jenis not in LAPORAN:
        return redirect(url_for("dashboard"))
    judul, view, kolom_tgl = LAPORAN[jenis]
    dari = request.args.get("dari", "")
    sampai = request.args.get("sampai", "")

    sql = f"SELECT * FROM {view}"          # nama view berasal dari daftar di atas, aman
    params = []
    if kolom_tgl and dari and sampai:
        sql += f" WHERE {kolom_tgl} BETWEEN %s AND %s ORDER BY {kolom_tgl}"
        params = [dari, sampai]

    data = query(sql, params)
    kolom = list(data[0].keys()) if data else []
    return render_template("laporan.html", judul=judul, jenis=jenis, data=data,
                           kolom=kolom, ada_tanggal=bool(kolom_tgl),
                           dari=dari, sampai=sampai)


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")