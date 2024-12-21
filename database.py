import os
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# URL de la base de datos desde las variables de entorno (esto lo maneja Railway)
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://usuario:contraseña@localhost:5432/nombre_basedatos')

# Crear el motor de la base de datos PostgreSQL
engine = create_engine(DATABASE_URL, echo=True)

# Crear la base para los modelos
Base = declarative_base()

# Definir el modelo para la tabla `songs`
class Song(Base):
    __tablename__ = 'songs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    url = Column(String)
    artist = Column(String)
    duration = Column(Integer)
    played_count = Column(Integer, default=0)

    def __repr__(self):
        return f"<Song(id={self.id}, title={self.title}, artist={self.artist}, played_count={self.played_count})>"

# Crear las tablas en la base de datos si no existen
Base.metadata.create_all(engine)

# Crear una sesión para interactuar con la base de datos
Session = sessionmaker(bind=engine)
session = Session()

# Función para agregar o actualizar una canción
def add_or_update_song(title, url=None, artist=None, duration=0):
    """Agrega o actualiza una canción en la base de datos de PostgreSQL."""
    # Verificar si la canción ya existe
    existing_song = session.query(Song).filter(Song.title == title).first()

    if existing_song:
        # Incrementar el contador si ya existe
        existing_song.played_count += 1
        session.commit()
    else:
        # Agregar una nueva canción
        new_song = Song(title=title, url=url, artist=artist, duration=duration)
        session.add(new_song)
        session.commit()

def get_top_songs(limit=10):
    """Obtiene las canciones más reproducidas."""
    top_songs = session.query(Song.title, Song.played_count).order_by(Song.played_count.desc()).limit(limit).all()
    return top_songs

# Función para configurar la base de datos (aunque ya se crea al inicio)
def setup_database():
    """Crea las tablas si no existen."""
    Base.metadata.create_all(engine)
    print("Tablas creadas si no existían.")