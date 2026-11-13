FROM python:3.10-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias para psycopg2 y compilaciones
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requerimientos e instalar librerías de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código del proyecto
COPY . .

# Exponer el puerto predeterminado de Cloud Run
EXPOSE 8080

# Comando para arrancar Streamlit usando el puerto dinámico
CMD sh -c "streamlit run app.py --server.port=${PORT:-8080} --server.address=0.0.0.0"