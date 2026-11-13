FROM python:3.10-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias para bases de datos
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el código y la carpeta .streamlit con los secretos
COPY . .

# Exponer el puerto predeterminado que exige Cloud Run
EXPOSE 8080

# Comando de inicio para Streamlit adaptado al puerto dinámico
CMD sh -c "streamlit run app.py --server.port=${PORT:-8080} --server.address=0.0.0.0"