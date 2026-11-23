
FROM python:3.15-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalar dependencias
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Incorporar aplicación y pruebas automatizadas
COPY app.py init_db.py ./
COPY tests/ ./tests/

# Ejecutar con usuario sin privilegios
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 5000

# Inicializar base de datos y ejecutar Flask
CMD ["sh", "-c", "python init_db.py && exec gunicorn --bind 0.0.0.0:5000 --workers 1 app:app"]
