# Usa una imagen base de Python
FROM python:3.11-slim

# Instala FFmpeg
RUN apt-get update && \
    apt-get install -y ffmpeg

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos de tu proyecto
COPY . .

# Instala las dependencias
RUN pip install -r requirements.txt

# Ejecuta el bot
CMD ["python", "main.py"]
