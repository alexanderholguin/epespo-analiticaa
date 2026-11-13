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

# Generar automáticamente el archivo de secretos de Streamlit dentro del contenedor
RUN mkdir -p /app/.streamlit
RUN echo '[users.admin_epespo]\nname = "Secretaría General"\nrole = "admin"\npassword_hash = "03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4"\n\n[users.direccion_epespo]\nname = "Dirección Académica"\nrole = "viewer"\npassword_hash = "0a373ff255c276ae8ffb22a074092b77e8ea75abeb52f758ee6e7920155b46d0"' > /app/.streamlit/secrets.toml

# Exponer el puerto predeterminado que exige Cloud Run
EXPOSE 8080

# Comando de inicio para Streamlit adaptado al puerto dinámico
CMD sh -c "streamlit run app.py --server.port=${PORT:-8080} --server.address=0.0.0.0"