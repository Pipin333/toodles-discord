import discord
from discord.ext import commands
import youtube_dl
import aiohttp
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

class PlaylistManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.song_queue = []  # Cola de canciones

        # Configura las credenciales de Spotify
        self.spotify = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id = os.getenv('client_id'),
            client_secret = os.getenv('client_secret')
        ))

    # Función para obtener canciones de una playlist de YouTube
    def get_youtube_playlist(self, url):
        ydl_opts = {
            'extract_flat': True,  # Solo queremos los títulos y URLs, no descargarlos
            'quiet': True
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            playlist_dict = ydl.extract_info(url, download=False)
            return [entry['url'] for entry in playlist_dict['entries']]

    # Función para obtener canciones de una playlist de Spotify
    async def get_spotify_playlist(self, playlist_url):
        playlist_id = playlist_url.split("/")[-1].split("?")[0]
        results = self.spotify.playlist_tracks(playlist_id)
        tracks = [track['track']['name'] + " " + track['track']['artists'][0]['name'] for track in results['items']]
        return tracks

    @commands.command()
    async def add_playlist(self, ctx, url: str):
        """Añade una playlist de YouTube o Spotify a la cola de reproducción."""
        if "youtube.com/playlist" in url:
            # Es una playlist de YouTube
            youtube_urls = self.get_youtube_playlist(url)
            self.song_queue.extend(youtube_urls)
            await ctx.send(f"Se añadieron {len(youtube_urls)} canciones de YouTube a la cola.")

        elif "spotify.com/playlist" in url:
            # Es una playlist de Spotify
            spotify_tracks = await self.get_spotify_playlist(url)
            for track in spotify_tracks:
                # Busca la versión de YouTube de cada canción de Spotify
                youtube_url = await self.search_youtube(track)
                if youtube_url:
                    self.song_queue.append(youtube_url)
            await ctx.send(f"Se añadieron {len(spotify_tracks)} canciones de Spotify a la cola.")

        else:
            await ctx.send("URL no válida. Solo se admiten playlists de YouTube o Spotify.")

    async def search_youtube(self, query):
        """Función para buscar una canción en YouTube y devolver el URL del video."""
        ydl_opts = {
            'quiet': True,
            'format': 'bestaudio',
            'noplaylist': True
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            try:
                result = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
                return result['webpage_url']
            except Exception as e:
                print(f"Error buscando en YouTube: {e}")
                return None

async def setup(bot):
    await bot.add_cog(PlaylistManager(bot))
