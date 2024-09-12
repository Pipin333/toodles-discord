# Usa una imagen base de Python
FROM python:3.11-slim

# Instala ffmpeg y otras dependencias
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean

# Establece el directorio de trabajo en el contenedor
WORKDIR /app

# Copia los archivos necesarios al contenedor
COPY requirements.txt requirements.txt
COPY . .

# Instala las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Expone el puerto (opcional, si tu bot usa un puerto específico)
EXPOSE 80

# Define el comando para ejecutar tu bot
CMD ["python", "main.py"]
