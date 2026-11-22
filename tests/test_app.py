
import unittest
import sqlite3
import tempfile
import re
from pathlib import Path
from werkzeug.security import generate_password_hash
import app as proyecto


class PruebasSeguridad(unittest.TestCase):

    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.directorio_original = proyecto.BASE_DIR
        proyecto.BASE_DIR = Path(self.temporal.name)

        conexion = sqlite3.connect(
            proyecto.BASE_DIR / "vulnerable.db"
        )

        conexion.execute("""
            CREATE TABLE usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                rol TEXT NOT NULL,
                bio TEXT
            )
        """)

        conexion.execute(
            """INSERT INTO usuarios
               (username, password, rol, bio)
               VALUES (?, ?, ?, ?)""",
            (
                "admin",
                generate_password_hash("admin123"),
                "admin",
                "BIOGRAFIA ORIGINAL"
            )
        )

        conexion.commit()
        conexion.close()

        self.cliente = proyecto.app.test_client()

    def tearDown(self):
        proyecto.BASE_DIR = self.directorio_original
        self.temporal.cleanup()

    def obtener_token(self, pagina):
        html = pagina.get_data(as_text=True)

        resultado = re.search(
            r'name="csrf_token"\s+value="([^"]+)"',
            html
        )

        self.assertIsNotNone(resultado)
        return resultado.group(1)

    def iniciar_sesion(self, usuario, password):
        pagina = self.cliente.get("/login")
        token = self.obtener_token(pagina)

        return self.cliente.post(
            "/login",
            data={
                "csrf_token": token,
                "username": usuario,
                "password": password
            }
        )

    def test_login_correcto(self):
        respuesta = self.iniciar_sesion("admin", "admin123")
        self.assertEqual(respuesta.status_code, 302)

    def test_password_incorrecta(self):
        respuesta = self.iniciar_sesion("admin", "incorrecta")
        self.assertEqual(respuesta.status_code, 401)

    def test_sql_injection_bloqueada(self):
        respuesta = self.iniciar_sesion(
            "admin' --", "incorrecta123"
        )
        self.assertEqual(respuesta.status_code, 401)

    def test_csrf_bloqueado(self):
        self.iniciar_sesion("admin", "admin123")

        respuesta = self.cliente.post(
            "/update_bio",
            data={"nueva_bio": "ATAQUE CSRF"}
        )

        self.assertEqual(respuesta.status_code, 400)

        datos = proyecto.db_query(
            "SELECT bio FROM usuarios WHERE username = ?",
            ("admin",)
        )
        self.assertEqual(datos[0]["bio"], "BIOGRAFIA ORIGINAL")

    def test_xss_bloqueado(self):
        self.iniciar_sesion("admin", "admin123")

        pagina = self.cliente.get("/dashboard")
        token = self.obtener_token(pagina)

        respuesta = self.cliente.post(
            "/update_bio",
            data={
                "csrf_token": token,
                "nueva_bio": "<img src=x onerror=alert(1)>"
            },
            follow_redirects=True
        )

        html = respuesta.get_data(as_text=True)

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("&lt;img", html)
        self.assertNotIn("<img src=x onerror=", html)

    def test_dashboard_sin_sesion(self):
        respuesta = self.cliente.get("/dashboard")
        self.assertEqual(respuesta.status_code, 302)


if __name__ == "__main__":
    unittest.main()
