# Usa una imagen base de Python
FROM python:3.11-slim

# Instala FFmpeg y muestra su version para asegurar su correcta instalacion
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    ffmpeg -version

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos de tu proyecto
COPY . .

# Instala las dependencias
RUN pip install -r requirements.txt

# Ejecuta el bot
CMD ["python", "main.py"]
