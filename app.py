from flask import Flask, request, render_template_string, redirect, session
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import check_password_hash
from pathlib import Path
from datetime import timedelta
import sqlite3
import secrets
import os

app = Flask(__name__)
# --- CONFIGURACIÓN SEGURA ---
BASE_DIR = Path(__file__).resolve().parent
SECRET_FILE = BASE_DIR / ".flask_secret"

if not SECRET_FILE.exists():
    SECRET_FILE.write_text(secrets.token_hex(32), encoding="utf-8")

app.config["SECRET_KEY"] = (
    os.environ.get("FLASK_SECRET_KEY")
    or SECRET_FILE.read_text(encoding="utf-8").strip()
)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False  # Solo HTTP local; True al usar HTTPS
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)

csrf = CSRFProtect(app)

# --- ENCABEZADOS HTTP DE SEGURIDAD (MITIGACIONES OWASP ZAP) ---
@app.after_request
def agregar_encabezados_seguridad(response):
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; object-src 'none'; "
        "base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
    )
    response.headers["Permissions-Policy"] = (
        "geolocation=(), camera=(), microphone=()"
    )
    response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
    return response

# --- BASE DE DATOS: SQL INJECTION MITIGADA ---
def db_query(query, params=()):
    conn = sqlite3.connect(BASE_DIR / "vulnerable.db")
    conn.row_factory = sqlite3.Row

    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchall()
        conn.commit()
        return result
    finally:
        conn.close()

# --- LOGIN: SQL INJECTION Y CONTRASEÑAS PROTEGIDAS ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("username", "")
        pw = request.form.get("password", "")

        usuarios = db_query(
            "SELECT id, username, password FROM usuarios WHERE username = ?",
            (user,)
        )
        if usuarios and check_password_hash(usuarios[0]["password"], pw):
            session.clear()
            session.permanent = True
            session["user_id"] = usuarios[0]["id"]
            return redirect("/dashboard")

        return "<h3>Acceso denegado</h3><a href='/login'>Volver</a>", 401

    html = """
    <h2>Login del Sistema Académico</h2>

    <form method="POST">
        <input type="hidden"
               name="csrf_token"
               value="{{ csrf_token() }}">
        Usuario:
        <input type="text" name="username"><br>

        Password:
        <input type="password" name="password"><br>

        <input type="submit" value="Ingresar">
    </form>
    """

    return render_template_string(html)

# --- DASHBOARD: XSS MITIGADA ---
@app.route("/dashboard")
def dashboard():
    user_id = session.get("user_id")

    if not user_id:
        return redirect("/login")

    datos = db_query(
        "SELECT id, username, rol, bio FROM usuarios WHERE id = ?",
        (user_id,)
    )

    if not datos:
        session.clear()
        return redirect("/login")

    html = """
    <h1>Panel de {{ datos['username'] }}</h1>
    <p><b>Rol:</b> {{ datos['rol'] }}</p>
    <p><b>Biografía:</b> {{ datos['bio'] }}</p>

    <hr>

    <h3>Actualizar Biografía (Protegida contra CSRF)</h3>

    <form action="/update_bio" method="POST">
        <input type="hidden"
               name="csrf_token"
               value="{{ csrf_token() }}">

        <input type="text"
               name="nueva_bio"
               placeholder="Escribe algo...">

        <input type="submit" value="Guardar Cambios">
    </form>

    <br>
    <form action="/logout" method="POST">
        <input type="hidden"
               name="csrf_token"
               value="{{ csrf_token() }}">

        <button type="submit">Cerrar Sesión</button>
    </form>
    """

    return render_template_string(html, datos=datos[0])

# --- ACTUALIZAR BIOGRAFÍA: CSRF Y SQLI MITIGADAS ---
@app.route("/update_bio", methods=["POST"])
def update_bio():
    user_id = session.get("user_id")

    if not user_id:
        return redirect("/login")

    nueva_bio = request.form.get("nueva_bio", "")

    db_query(
        "UPDATE usuarios SET bio = ? WHERE id = ?",
        (nueva_bio, user_id)
    )

    return redirect("/dashboard")

# --- CERRAR SESIÓN ---
@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect("/login")

# --- PÁGINA PRINCIPAL ---
@app.route("/")
def home():
    return redirect("/login")

if __name__ == "__main__":
    # Depurador desactivado
    app.run(debug=False, host="127.0.0.1", port=5000)
