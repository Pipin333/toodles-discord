# Usa una imagen base de Python
FROM python:3.9

# Instala FFmpeg
RUN apt-get update && \
    apt-get install -y ffmpeg

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos de tu proyecto al contenedor
COPY . /app

# Instala las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Comando por defecto para ejecutar el bot
CMD ["python", "main.py"]
