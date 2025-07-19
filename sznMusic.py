print("🧪 sznMusic.py ha sido leído por Python")

import discord
from discord.ext import commands, tasks
import yt_dlp as youtube_dl
import os
import tempfile
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
from database import add_or_update_song

SPOTIFY_CLIENT_ID = os.getenv('client_id')
SPOTIFY_CLIENT_SECRET = os.getenv('client_secret')

def __init__(self, bot):
    self.bot = bot
    self.song_queue = []
    self.current_song = None
    self.voice_client = None
    self.radio_seed_id = None
    self.radio_mode = False
    self.radio_temperature = 0.75

    try:
        print("🔁 Iniciando conexión con Spotify...")
        self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET
        ))
        print("✅ Conexión a Spotify establecida.")
    except Exception as e:
        print(f"❌ Error al conectar con Spotify: {e}")
        self.sp = None

    try:
        self.cookie_file = self.setup_cookies()
    except Exception as e:
        print(f"❌ Error al preparar cookies: {e}")
        self.cookie_file = None

    try:
        self.inactivity_check.start()
    except Exception as e:
        print(f"❌ Error al iniciar inactivity_check: {e}")

def setup_cookies(self):
        cookies_content = os.getenv('cookies')
        if not cookies_content:
            print("⚠️ No se encontraron cookies en las variables de entorno.")
            return None

        try:
            temp = tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', suffix='.txt')
            temp.write(cookies_content)
            temp.close()
            print(f"✅ Cookies cargadas en archivo temporal: {temp.name}")
            return temp.name
        except Exception as e:
            print(f"❌ Error al crear archivo de cookies: {e}")
            return None

def get_ydl_opts(self):
        opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'default_search': 'ytsearch',
            'noplaylist': True
        }
        if self.cookie_file:
            opts['cookiefile'] = self.cookie_file
        return opts

def format_duration(self, duration):
        hours, remainder = divmod(duration, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

async def connect_to_voice(self, ctx):
        if not ctx.author.voice:
            await ctx.send("Debes estar en un canal de voz para usar este comando.")
            return None
        if not self.voice_client:
            self.voice_client = await ctx.author.voice.channel.connect()
        return self.voice_client

async def add_song(self, ctx, title, url=None, duration=0, origin="🎵 Añadida manualmente"):
        song = {'title': title, 'url': url, 'duration': duration, 'origin': origin}
        self.song_queue.append(song)
        add_or_update_song(title, url or 'ytsearch:' + title, duration=duration)
        await ctx.send(f"🎶 Añadido a la cola: **{title}**")
        if not self.current_song:
            await self.play_next(ctx)

async def search_youtube(self, query):
        ydl_opts = self.get_ydl_opts()
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            return info['entries'][0] if 'entries' in info else info

async def add_from_youtube(self, ctx, query, origin="🔁 Recomendación por radio"):
        match = self.bot.musicdb.find_similar_song(query)
        if match:
            await self.add_song(ctx, match.title, match.url, match.duration, origin)
            return
        info = await self.search_youtube(query)
        await self.add_song(ctx, info['title'], info['url'], info.get('duration', 0), origin)

async def add_from_spotify(self, ctx, url):
        track_id = url.split("/")[-1].split("?")[0]
        track = self.sp.track(track_id)
        query = f"{track['name']} {track['artists'][0]['name']}"
        await self.add_from_youtube(ctx, query, origin=f"🎵 Pedida desde Spotify por {ctx.author.name}")

async def add_playlist_from_spotify(self, ctx, url):
        playlist_id = url.split("/")[-1].split("?")[0]
        results = self.sp.playlist_tracks(playlist_id)
        for item in results['items']:
            track = item['track']
            query = f"{track['name']} {track['artists'][0]['name']}"
            await self.add_from_youtube(ctx, query, origin=f"🎵 Pedida desde playlist por {ctx.author.name}")

async def play_next(self, ctx):
        if not self.song_queue:
            if self.radio_mode and self.radio_seed_id:
                await self.expand_radio_queue(ctx)
            else:
                await ctx.send("La cola está vacía.")
                self.current_song = None
                return

        self.current_song = self.song_queue.pop(0)
        ui = self.bot.get_cog("MusicUI")
        if ui:
            await ui.notify_now_playing(ctx, self.current_song['title'], self.current_song.get('origin'))

        self.bot.musicdb.log_song(self.current_song['title'])

        def after_playing(error):
            if error:
                print(f"Error al reproducir: {error}")
            self.bot.loop.create_task(self.play_next(ctx))

        self.voice_client.play(
            discord.FFmpegPCMAudio(self.current_song['url']),
            after=after_playing
        )

@commands.command(name="p")
async def play(self, ctx, *, query):
        await self.connect_to_voice(ctx)
        if "spotify.com/track" in query:
            await self.add_from_spotify(ctx, query)
        elif "spotify.com/playlist" in query:
            await self.add_playlist_from_spotify(ctx, query)
        else:
            await self.add_from_youtube(ctx, query)

@commands.command()
async def skip(self, ctx):
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()

@commands.command()
async def pause(self, ctx):
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.pause()
            await ctx.send("⏸️ Canción pausada.")

@commands.command()
async def resume(self, ctx):
        if self.voice_client and self.voice_client.is_paused():
            self.voice_client.resume()
            await ctx.send("▶️ Canción reanudada.")

@commands.command()
async def clear(self, ctx):
        self.song_queue.clear()
        await ctx.send("🧹 Cola de canciones limpiada.")

@commands.command(name="np")
async def now_playing(self, ctx):
        if self.current_song:
            duration_str = self.format_duration(self.current_song.get('duration', 0))
            await ctx.send(f"🎵 Reproduciendo: **{self.current_song['title']}** ({duration_str})")
        else:
            await ctx.send("No hay ninguna canción en reproducción.")

@commands.command()
async def queue(self, ctx):
        if not self.song_queue:
            await ctx.send("🎵 La cola está vacía.")
            return

        msg = "**Cola de canciones:**\n"
        for i, song in enumerate(self.song_queue, 1):
            duration = self.format_duration(song.get('duration', 0))
            msg += f"{i}. **{song['title']}** ({duration})\n"
        await ctx.send(msg)

@tasks.loop(seconds=60)
async def inactivity_check(self):
        if self.voice_client and not self.voice_client.is_playing() and not self.song_queue:
            await self.voice_client.disconnect()
            self.voice_client = None
            self.current_song = None
            print("✅ Desconectado por inactividad.")

@commands.command()
async def radio(self, ctx, *, arg: str = "0.75"):
        if arg.lower() == "off":
            self.radio_mode = False
            self.radio_seed_id = None
            await ctx.send("🛑 Modo radio desactivado.")
            return

        try:
            temperatura = float(arg)
        except ValueError:
            await ctx.send("❌ Parámetro inválido. Usa un número entre 0.0 y 1.0 o 'off'.")
            return

        if not self.current_song:
            await ctx.send("No hay ninguna canción reproduciéndose para iniciar el modo radio.")
            return

        title = self.current_song['title']
        results = self.sp.search(q=title, type='track', limit=1)
        if not results['tracks']['items']:
            await ctx.send("No se encontró la canción en Spotify para generar recomendaciones.")
            return

        self.radio_seed_id = results['tracks']['items'][0]['id']
        self.radio_mode = True
        self.radio_temperature = max(0.0, min(temperatura, 1.0))
        await ctx.send(f"🔁 Modo radio activado (temperatura {self.radio_temperature:.2f}). Se mantendrá la cola con canciones similares.")
        await self.expand_radio_queue(ctx)

async def setup(bot):
    await bot.add_cog(MusicCore(bot))