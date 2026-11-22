
import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "vulnerable.db"


def crear_base_de_datos():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            rol TEXT NOT NULL,
            bio TEXT
        )
    """)

    cursor.execute("SELECT id, password FROM usuarios")
    usuarios = cursor.fetchall()

    if not usuarios:
        # Usuarios de prueba con contraseñas protegidas
        nuevos_usuarios = [
            (
                "admin",
                generate_password_hash("admin123"),
                "admin",
                "Cuenta de administrador del sistema."
            ),
            (
                "alumno",
                generate_password_hash("12345"),
                "user",
                "Soy un estudiante aprendiendo hacking."
            )
        ]

        cursor.executemany("""
            INSERT INTO usuarios
            (username, password, rol, bio)
            VALUES (?, ?, ?, ?)
        """, nuevos_usuarios)

        print("Usuarios de prueba creados con contraseñas protegidas.")

    else:
        actualizados = 0

        # Migrar contraseñas antiguas sin borrar usuarios ni biografías
        for user_id, password in usuarios:
            if password.startswith(("scrypt:", "pbkdf2:")):
                continue

            password_hash = generate_password_hash(password)

            cursor.execute(
                "UPDATE usuarios SET password = ? WHERE id = ?",
                (password_hash, user_id)
            )

            actualizados += 1

        print(f"Contraseñas migradas: {actualizados}")

    conn.commit()
    conn.close()
    print("Base de datos protegida correctamente.")


if __name__ == "__main__":
    crear_base_de_datos()
