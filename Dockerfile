FROM python:3.10-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias para bases de datos y compilaciones
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código del proyecto
COPY . .

# Generar automáticamente el archivo secrets.toml con los hashes SHA-256 correctos
RUN python -c 'import hashlib, pathlib; \
admin_hash = hashlib.sha256(b"admin1234").hexdigest(); \
viewer_hash = hashlib.sha256(b"viewer1234").hexdigest(); \
content = f"""[users.admin_epespo]\nname = \\"Secretaría General\\"\nrole = \\"admin\\"\npassword_hash = \\"{admin_hash}\\"\n\n[users.direccion_epespo]\nname = \\"Dirección Académica\\"\nrole = \\"viewer\\"\npassword_hash = \\"{viewer_hash}\\"\n"""; \
pathlib.Path("/app/.streamlit").mkdir(parents=True, exist_ok=True); \
pathlib.Path("/app/.streamlit/secrets.toml").write_text(content)'

# Exponer el puerto predeterminado que exige Cloud Run
EXPOSE 8080

# Comando de inicio para Streamlit adaptado al puerto dinámico
CMD sh -c "streamlit run app.py --server.port=${PORT:-8080} --server.address=0.0.0.0"