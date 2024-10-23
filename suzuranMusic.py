import discord
import random
from discord.ext import commands, tasks
import yt_dlp as youtube_dl
import asyncio
import time
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
import concurrent.futures

SPOTIFY_CLIENT_ID = os.getenv('client_id')
SPOTIFY_CLIENT_SECRET = os.getenv('client_secret')

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.song_queue = []
        self.current_song = None
        self.voice_client = None
        self.check_inactivity.start()
        self.start_time = None
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
        
        self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET))

    async def delete_user_message(self, ctx):
        await asyncio.sleep(0.1)
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            await ctx.send("No tengo permisos para borrar mensajes.")
        except discord.HTTPException as e:
            await ctx.send(f"Error al borrar el mensaje: {e}")
    
    def format_duration(self, duration):
        """Convierte la duración de la canción de segundos a minutos:segundos"""
        minutes, seconds = divmod(duration, 60)
        return f"{minutes}:{seconds:02d}"

    @commands.command()
    async def play(self, ctx, search: str):
        # Conectar al canal de voz si no está conectado
        if not ctx.voice_client:
            if ctx.author.voice:
                channel = ctx.author.voice.channel
                self.voice_client = await channel.connect()
            else:
                await ctx.send("Debes estar en un canal de voz para usar este comando.")
                return
        await self.delete_user_message(ctx)            

        if not ctx.voice_client.is_connected():
            await ctx.send("No estoy conectado a un canal de voz.")
            return

        if "youtube.com" in search or "youtu.be" in search:
            await self.play_youtube_playlist(ctx, search)
        elif "spotify.com" in search:
            await self.load_spotify_playlist(ctx, search)
        else:
            await self.search_and_queue_youtube(ctx, search)


    async def load_spotify_playlist(self, ctx, playlist_url: str):
        await ctx.send("Cargando playlist de Spotify...")
        playlist_id = playlist_url.split("/")[-1].split("?")[0]

        try:
            results = self.sp.playlist_tracks(playlist_id)
            tracks = results['items']

            tasks = [
                self.add_song_to_queue(ctx, track['track'])
                for track in tracks
            ]
            await asyncio.gather(*tasks)

            await ctx.send(f"🎶 Se añadieron {len(tracks)} canciones de Spotify a la cola.")
        except Exception as e:
            await ctx.send(f"Error al procesar la playlist de Spotify: {e}")

    async def add_song_to_queue(self, ctx, track):
        song_name = track['name']
        artist_name = track['artists'][0]['name']
        search_query = f"{song_name} {artist_name}"
        await self.search_and_queue_youtube(ctx, search_query)

    async def add_songs_to_queue(self, ctx, playlist):
        """Añade canciones de una playlist a la cola en lotes."""
        max_songs_to_add = 5
        songs = playlist.get('tracks', [])
        total_batches = (len(songs) + max_songs_to_add - 1) // max_songs_to_add

        for i in range(0, len(songs), max_songs_to_add):
            batch = songs[i:i + max_songs_to_add]
            for song in batch:
                self.song_queue.append({
                    'title': song['title'],
                    'url': song['url'],
                    'duration': song.get('duration', 0)
                })
            
            current_batch_number = (i // max_songs_to_add) + 1
            await ctx.send(f"Añadidas {len(batch)} canciones al lote {current_batch_number} de {total_batches}.")

            await asyncio.sleep(1)  # Pausa entre lotes para evitar saturar el servidor

        await ctx.send("Todos los lotes han sido añadidos.")

    async def play_spotify_playlist(self, ctx, playlist_url: str):
        """Reproduce canciones de una playlist de Spotify."""
        try:
            playlist_id = playlist_url.split("/")[-1].split("?")[0]
            results = self.sp.playlist_tracks(playlist_id)
            tracks = results['items']

            await self.add_songs_to_queue(ctx, {'tracks': [{'title': track['track']['name'], 'url': track['track']['external_urls']['spotify']} for track in tracks]})

            await ctx.send(f"🎶 Se añadieron {len(tracks)} canciones de Spotify a la cola.")
        except Exception as e:
            await ctx.send(f"Error al procesar la playlist de Spotify: {e}")

    async def play_youtube_playlist(self, ctx, playlist_url: str):
        """Reproduce canciones de una playlist de YouTube utilizando hilos para no bloquear."""
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'noplaylist': False,  # Cambia a False para procesar playlists
        }

        try:
            playlist_info = await asyncio.to_thread(lambda: youtube_dl.YoutubeDL(ydl_opts).extract_info(playlist_url, download=False))
            entries = playlist_info.get('entries', [])

            for entry in entries:
                video_title = entry.get('title')
                video_url = entry.get('url')

                await self.queue_song(ctx, video_url, video_title)

            await ctx.send(f"🎶 Se añadieron {len(entries)} canciones de YouTube a la cola.")
        except Exception as e:
            await ctx.send(f"Error al procesar la playlist de YouTube: {e}")

    async def search_and_queue_youtube(self, ctx, search_query: str):
        """Realiza una búsqueda en YouTube y añade la canción a la cola sin bloquear el hilo principal."""
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'noplaylist': True,  # Cambia a False para procesar playlists
        }

        try:
            # Ejecuta yt_dlp en un hilo separado para no bloquear el hilo principal
            info = await asyncio.to_thread(lambda: youtube_dl.YoutubeDL(ydl_opts).extract_info(f"ytsearch:{search_query}", download=False))
            if info.get('entries'):
                song_info = info['entries'][0]
                song_url = song_info['url']
                song_title = song_info['title']

                await self.queue_song(ctx, song_url, song_title)
            else:
                await ctx.send("No se encontró la canción.")
        except Exception as e:
            await ctx.send(f"Error al intentar añadir la canción: {e}")

    async def queue_song(self, ctx, song_url: str, song_title: str):
        """Añade una canción a la cola y la reproduce si no hay otras canciones"""
        self.song_queue.append({'url': song_url, 'title': song_title})

        if not self.voice_client or not self.voice_client.is_playing():
            await self._play_song(ctx)

    async def _play_song(self, ctx):
        """Reproduce una canción desde la cola"""
        if self.song_queue:
            song = self.song_queue.pop(0)
            song_url = song['url']
            song_title = song['title']
            self.current_song = song  # Actualiza la canción actual
            self.start_time = time.time()  # Establece el tiempo de inicio

            if self.voice_client and self.voice_client.is_connected():
                source = discord.FFmpegPCMAudio(song_url, before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', options='-vn')
                self.voice_client.play(source, after=lambda e: self.bot.loop.create_task(self.play_next(ctx)))
                await ctx.send(f"🎶 Ahora reproduciendo: **{song_title}**")
            else:
                await ctx.send("No estoy conectado a un canal de voz.")
        else:
            await ctx.send("No hay más canciones en la cola.")

    async def play_next(self, ctx):
        """Reproduce la siguiente canción en la cola"""
        if self.song_queue:
            await self._play_song(ctx)
        else:
            await ctx.send("No hay más canciones en la cola.")

async def setup(bot):
   await bot.add_cog(Music(bot))
