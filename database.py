import sqlite3

DB_FILE = "music_bot.db"

def setup_database():
    """Crea la base de datos y las tablas si no existen."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Crear tabla de canciones
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS songs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT,
            artist TEXT,
            duration INTEGER,
            played_count INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def add_or_update_song(title, url=None, artist=None, duration=0):
    """Agrega o actualiza una canción en la base de datos."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Verificar si la canción ya existe
    cursor.execute("SELECT id, played_count FROM songs WHERE title = ?", (title,))
    result = cursor.fetchone()

    if result:
        # Incrementar el contador si ya existe
        song_id, played_count = result
        cursor.execute("UPDATE songs SET played_count = ? WHERE id = ?", (played_count + 1, song_id))
    else:
        # Agregar una nueva canción
        cursor.execute("INSERT INTO songs (title, url, artist, duration) VALUES (?, ?, ?, ?)",
                       (title, url, artist, duration))

    conn.commit()
    conn.close()

def get_top_songs(limit=10):
    """Obtiene las canciones más reproducidas."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT title, played_count FROM songs ORDER BY played_count DESC LIMIT ?", (limit,))
    top_songs = cursor.fetchall()
    conn.close()
    return top_songs
