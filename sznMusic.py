print("🧪 sznMusic.py ha sido leído por Python")

import discord
from discord.ext import commands, tasks
from yt_dlp import YoutubeDL
import os
import tempfile
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
from database import add_or_update_song
from sznUtils import get_active_cookie_file

SPOTIFY_CLIENT_ID = os.getenv('client_id')
SPOTIFY_CLIENT_SECRET = os.getenv('client_secret')

class MusicCore(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.song_queue = []
        self.current_song = None
        self.voice_client = None
        self.radio_seed_id = None
        self.radio_mode = False
        self.radio_temperature = 0.75
        self.MusicUI = bot.get_cog("sznUI")

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
            self.cookie_file = get_active_cookie_file()
        except Exception as e:
            print(f"❌ Error al preparar cookies: {e}")
            self.cookie_file = None

        try:
            self.inactivity_check.start()
        except Exception as e:
            print(f"❌ Error al iniciar inactivity_check: {e}")

    def get_ydl_opts(self):
        return {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            'cookiefile': self.cookie_file if self.cookie_file else None,
            "default_search": "ytsearch",
        }

    def format_duration(self, duration):
        hours, remainder = divmod(duration, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
    
    def get_music_ui(self):
        if not self.MusicUI:
            self.MusicUI = self.bot.get_cog("sznUI")
        return self.MusicUI    

    async def connect_to_voice(self, ctx):
        if not ctx.author.voice:
            await ctx.send(embed=self.get_music_ui().embed_simple_message(self, "Debes estar en un canal de voz para usar este comando."))
            return None
        if not self.voice_client:
            self.voice_client = await ctx.author.voice.channel.connect()
        return self.voice_client

    async def add_song(self, ctx, title, url=None, duration=0, origin="🎵 Añadida manualmente"):
        song = {'title': title, 'url': url, 'duration': duration, 'origin': origin}
        self.queue_manager.add_song(song)
        add_or_update_song(title, url or 'ytsearch:' + title, duration=duration)
        await ctx.send(embed=self.get_music_ui().embed_song_added(title))
        if not self.current_song:
            await self.play_next(ctx)

    async def search_youtube(self, query, max_results=5):
        ydl_opts = self.get_ydl_opts()
        ydl_opts["noplaylist"] = True
        ydl_opts["extract_flat"] = "in_playlist"
        ydl_opts["default_search"] = f"ytsearch{max_results}:"
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            return info['entries'] if 'entries' in info else [info]

    @commands.command(name="search")
    async def search(self, ctx, *, query):
        results = await self.search_youtube(query, max_results=5)
        if not results:
            await ctx.send(embed=self.get_music_ui().embed_simple_message(self, "❌ No se encontraron resultados."))
            return

        ui = self.get_music_ui()
        if ui:
            view = await ui.create_search_results_view(ctx, results, self)
            await ctx.send("🔎 Selecciona una canción para añadirla a la cola:", view=view)

    async def handle_search_selection(self, ctx, info, origin="🎯 Seleccionada desde búsqueda"):
        await self.connect_to_voice(ctx)
        await self.add_song(ctx, info['title'], info['url'], info.get('duration', 0), origin)

    async def add_from_youtube(self, ctx, query, origin="🔁 Recomendación por radio"):
        musicdb = getattr(self.bot, "musicdb", None)
        print(f"🔍 Acceso a self.bot.musicdb: {hasattr(self.bot, 'musicdb')}")
        if musicdb:
            match = musicdb.find_similar_song(query)
        else:
            print("⚠️ self.bot.musicdb no está disponible aún.")
            match = None

        if match:
            await self.add_song(ctx, match.title, match.url, match.duration, origin)
            return
        info = await self.search_youtube(query)
        await self.add_song(ctx, info[0]['title'], info[0]['url'], info[0].get('duration', 0), origin)

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
        next_song = self.queue_manager.get_next_song()
        if not next_song:
            if self.radio_mode and self.radio_seed_id:
                await self.expand_radio_queue(ctx)
                next_song = self.queue_manager.get_next_song()
            if not next_song:
                await ctx.send(embed=self.get_music_ui().embed_simple_message(self, "La cola está vacía."))
                self.current_song = None
                return

        self.current_song = next_song
        ui = self.get_music_ui()
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
            await ctx.send(embed=self.get_music_ui().embed_simple_message(self, "⏸️ Canción pausada."))

    @commands.command()
    async def resume(self, ctx):
        if self.voice_client and self.voice_client.is_paused():
            self.voice_client.resume()
            await ctx.send(embed=self.get_music_ui().embed_simple_message(self, "▶️ Canción reanudada."))

    @commands.command(name="np")
    async def now_playing(self, ctx):
        if self.current_song:
            duration_str = self.format_duration(self.current_song.get('duration', 0))
            await ctx.send(embed=self.get_music_ui().embed_simple_message(self, f"🎵 Reproduciendo: **{self.current_song['title']}** ({duration_str})"))
        else:
            await ctx.send(embed=self.get_music_ui().embed_simple_message(self, "No hay ninguna canción en reproducción."))

    @tasks.loop(seconds=60)
    async def inactivity_check(self):
        if self.voice_client and not self.voice_client.is_playing() and not self.queue_manager.view_queue():
            await self.voice_client.disconnect()
            self.voice_client = None
            self.current_song = None
            print("✅ Desconectado por inactividad.")

    @commands.command()
    async def radio(self, ctx, *, arg: str = "0.75"):
        if arg.lower() == "off":
            self.radio_mode = False
            self.radio_seed_id = None
            await ctx.send(embed=self.get_music_ui().embed_simple_message(self, "🛑 Modo radio desactivado."))
            return

        try:
            temperatura = float(arg)
        except ValueError:
            await ctx.send(embed=self.get_music_ui().embed_simple_message(self, "❌ Parámetro inválido. Usa un número entre 0.0 y 1.0 o 'off'."))
            return

        if not self.current_song:
            await ctx.send(embed=self.get_music_ui().embed_simple_message(self, "No hay ninguna canción reproduciéndose para iniciar el modo radio."))
            return

        title = self.current_song['title']
        results = self.sp.search(q=title, type='track', limit=1)
        items = results.get('tracks', {}).get('items', [])
        if not items or not items[0].get('id'):
            await ctx.send(embed=self.get_music_ui().embed_simple_message(self, "No se encontró un track válido para generar recomendaciones."))
            return

        self.radio_seed_id = items[0]['id']
        self.radio_mode = True
        self.radio_temperature = max(0.0, min(temperatura, 1.0))
        await ctx.send(embed=self.get_music_ui().embed_simple_message(self, f"🔁 Modo radio activado (temperatura {self.radio_temperature:.2f}). Se mantendrá la cola con canciones similares."))
        await self.expand_radio_queue(ctx)

    async def expand_radio_queue(self, ctx, seed_id=None, temperature=0.75):
        try:
            if not seed_id:
                seed_id = self.radio_seed_id
            if not seed_id:
                await ctx.send(embed=self.get_music_ui().embed_simple_message(self, "❌ No hay una canción base para generar recomendaciones."))
                return

            recs = self.sp.recommendations(
                seed_tracks=[seed_id],
                limit=5,
                target_valence=temperature,
                target_energy=temperature
            )

            if not recs.get('tracks'):
                await ctx.send(embed=self.get_music_ui().embed_simple_message(self, "Spotify no pudo generar recomendaciones con esta canción."))
                return

            await ctx.send(embed=self.get_music_ui().embed_simple_message(self, "🎧 Añadiendo canciones sugeridas al modo radio..."))

            for track in recs['tracks']:
                title = track['name']
                artist = track['artists'][0]['name']
                query = f"{title} {artist}"
                await self.add_from_youtube(ctx, query)

        except Exception as e:
            await ctx.send(embed=self.get_music_ui().embed_simple_message(self, f"⚠️ Error al expandir la cola de radio: {e}"))

print("🧪 Ejecutando setup() de sznMusic")

async def setup(bot):
    await bot.add_cog(MusicCore(bot))
