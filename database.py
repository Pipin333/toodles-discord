import os
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# URL de la base de datos desde las variables de entorno (esto lo maneja Railway)
DATABASE_URL = os.getenv('DATABASE_URL')

# Crear el motor de la base de datos PostgreSQL
engine = create_engine(DATABASE_URL, echo=True, pool_size=5, max_overflow=10)

# Crear la base para los modelos
Base = declarative_base()

# Definir el modelo para la tabla `songs`
class Song(Base):
    __tablename__ = 'songs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False, index=True)
    url = Column(String)
    artist = Column(String, index=True)
    duration = Column(Integer)
    played_count = Column(Integer, default=0, index=True)

    def __repr__(self):
        return f"<Song(id={self.id}, title={self.title}, artist={self.artist}, played_count={self.played_count})>"

# Crear las tablas en la base de datos si no existen
Base.metadata.create_all(engine)

# Crear una sesión para interactuar con la base de datos
Session = sessionmaker(bind=engine)
session = Session()

# Función para agregar o actualizar una canción
def add_or_update_song(title, url=None, artist=None, duration=0):
    # Verificar si la canción ya está en la base de datos
    with session.begin():
        existing_song = session.query(Song).filter_by(title=title, artist=artist).first()
    if existing_song:
        return existing_song  # La canción ya existe, no hacer nada más

    # Si no existe, crear una nueva entrada
    new_song = Song(
        title=title,
        url=url,
        artist=artist,
        duration=duration
    )
    with session.begin():
        session.add(new_song)

    preload_top_songs_cache(limit=10)  # Update cache
    return new_song


def get_top_songs(limit=10, offset=0):
    """Obtiene las canciones más reproducidas."""
    with session.begin():
        top_songs = (
            session.query(Song.title, Song.played_count)
            .order_by(Song.played_count.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )
    return top_songs

    return top_songs

# Función para configurar la base de datos (aunque ya se crea al inicio)
def setup_database():
    """Crea las tablas si no existen."""
    Base.metadata.create_all(engine)
    print("Tablas creadas si no existían.")
cached_songs = {}

def preload_top_songs_cache(limit=10):
    """Precarga las canciones más reproducidas en un diccionario de caché."""
    global cached_songs
    top_songs = get_top_songs(limit=limit)
    cached_songs = {song.title: song.played_count for song in top_songs}


    preload_top_songs_cache(limit=10)
    print("Tablas creadas si no existían.")
