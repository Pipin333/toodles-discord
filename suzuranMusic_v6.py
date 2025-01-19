import discord
from discord.ext import commands
from discord.ui import Button, View
import yt_dlp as youtube_dl
import asyncio
import os
import time
import random
import math
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
from database import setup_database, add_or_update_song, get_top_songs

SPOTIFY_CLIENT_ID = os.getenv('client_id')
SPOTIFY_CLIENT_SECRET = os.getenv('client_secret')

class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.song_queue = []
        self.current_song = None
        self.voice_client = None
        self.executor = asyncio.Semaphore(3)  # Limit concurrent tasks
        self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET))
        setup_database()
        print("Bot iniciado correctamente.")

    async def connect_to_voice(self, ctx):
        if not ctx.author.voice:
            embed = discord.Embed(title="Error", description="Debes estar en un canal de voz para usar este comando.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return None
        
        if not self.voice_client:
            self.voice_client = await ctx.author.voice.channel.connect()
        return self.voice_client

    @commands.command()
    async def play(self, ctx, *, query: str):
        voice_client = await self.connect_to_voice(ctx)
        if not voice_client:
            return

        if "youtube.com" in query or "youtu.be" in query:
            await self.add_song_from_youtube(ctx, query)
        elif "spotify.com" in query:
            if "track" in query:
                await self.add_song_from_spotify(ctx, query)
            elif "playlist" in query:
                await self.add_playlist_from_spotify(ctx, query)
        else:
            await self.search_and_add_youtube(ctx, query)

    async def add_song_from_youtube(self, ctx, url):
        ydl_opts = {'format': 'bestaudio/best', 'noplaylist': True, 'quiet': True}
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            song = {'title': info['title'], 'url': info['url'], 'duration': info.get('duration', 0)}
            self.song_queue.append(song)
            add_or_update_song(song['title'], song['url'], duration=song['duration'])
            embed = discord.Embed(title="Canción Añadida", description=f"🎶 **{song['title']}** ha sido añadida a la cola.", color=discord.Color.green())
            await ctx.send(embed=embed)
        if not self.current_song:
            await self.start_playing(ctx)

    async def add_song_from_spotify(self, ctx, url):
        track_id = url.split("/")[-1].split("?")[0]
        track_info = self.sp.track(track_id)
        song_name = track_info['name']
        artist_name = track_info['artists'][0]['name']
        search_query = f"{song_name} {artist_name}"
        await self.search_and_add_youtube(ctx, search_query)

    async def add_playlist_from_spotify(self, ctx, url):
        playlist_id = url.split("/")[-1].split("?")[0]
        results = self.sp.playlist_tracks(playlist_id)
        for item in results['items']:
            track = item['track']
            song_name = track['name']
            artist_name = track['artists'][0]['name']
            search_query = f"{song_name} {artist_name}"
            await self.search_and_add_youtube(ctx, search_query)

    async def search_and_add_youtube(self, ctx, query):
        ydl_opts = {'format': 'bestaudio/best', 'quiet': True, 'default_search': 'ytsearch'}
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            song_info = info['entries'][0]
            song = {'title': song_info['title'], 'url': song_info['url'], 'duration': song_info.get('duration', 0)}
            self.song_queue.append(song)
            add_or_update_song(song['title'], song['url'], duration=song['duration'])
            embed = discord.Embed(title="Canción Añadida", description=f"🎶 **{song['title']}** ha sido añadida a la cola.", color=discord.Color.green())
            await ctx.send(embed=embed)
        if not self.current_song:
            await self.start_playing(ctx)

    async def start_playing(self, ctx):
        if not self.song_queue:
            embed = discord.Embed(title="Cola Vacía", description="No hay canciones en la cola.", color=discord.Color.orange())
            await ctx.send(embed=embed)
            return

        self.current_song = self.song_queue.pop(0)
        embed = discord.Embed(title="Reproduciendo Ahora", description=f"🎶 **{self.current_song['title']}**", color=discord.Color.blue())
        await ctx.send(embed=embed)

        def after_playing(error):
            if error:
                print(f"Error en la reproducción: {error}")
            self.current_song = None
            if self.song_queue:
                self.bot.loop.create_task(self.start_playing(ctx))

        self.voice_client.play(discord.FFmpegPCMAudio(self.current_song['url']), after=after_playing)

    @commands.command()
    async def controls(self, ctx):
        class MusicControls(View):
            def __init__(self, cog, ctx):
                super().__init__(timeout=60)
                self.cog = cog
                self.ctx = ctx

            @discord.ui.button(label="⏯️ Reproducir/Pausar", style=discord.ButtonStyle.primary)
            async def play_pause(self, interaction: discord.Interaction, button: Button):
                if not self.cog.voice_client or not self.cog.current_song:
                    embed = discord.Embed(title="Error", description="No hay canción en reproducción.", color=discord.Color.red())
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    if self.cog.voice_client.is_playing():
                        self.cog.voice_client.pause()
                        embed = discord.Embed(title="Pausado", description="⏸️ Canción pausada.", color=discord.Color.orange())
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                    elif self.cog.voice_client.is_paused():
                        self.cog.voice_client.resume()
                        embed = discord.Embed(title="Reanudado", description="▶️ Canción reanudada.", color=discord.Color.green())
                        await interaction.response.send_message(embed=embed, ephemeral=True)

            @discord.ui.button(label="⏭️ Siguiente", style=discord.ButtonStyle.secondary)
            async def skip(self, interaction: discord.Interaction, button: Button):
                if self.cog.song_queue:
                    self.cog.voice_client.stop()
                    await self.cog.start_playing(self.ctx)
                    embed = discord.Embed(title="Saltado", description="⏭️ Canción saltada.", color=discord.Color.green())
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    embed = discord.Embed(title="Cola Vacía", description="No hay más canciones en la cola.", color=discord.Color.orange())
                    await interaction.response.send_message(embed=embed, ephemeral=True)

            @discord.ui.button(label="⏹️ Detener", style=discord.ButtonStyle.danger)
            async def stop(self, interaction: discord.Interaction, button: Button):
                if self.cog.voice_client:
                    await self.cog.voice_client.disconnect()
                    self.cog.voice_client = None
                    self.cog.song_queue.clear()
                    self.cog.current_song = None
                    embed = discord.Embed(title="Detenido", description="⏹️ Reproducción detenida y desconectado.", color=discord.Color.red())
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    embed = discord.Embed(title="Error", description="No estoy conectado a un canal de voz.", color=discord.Color.red())
                    await interaction.response.send_message(embed=embed, ephemeral=True)

        view = MusicControls(self, ctx)
        embed = discord.Embed(title="Controles de Reproducción", description="Usa los botones a continuación para controlar la música.", color=discord.Color.blue())
        await ctx.send(embed=embed, view=view)

    @commands.command()
    async def historial(self, ctx):
        """Muestra las canciones más reproducidas."""
        top_songs = get_top_songs(5)
        if top_songs:
            description = "\n".join([f"{idx + 1}. {title} - {count} reproducciones" for idx, (title, count) in enumerate(top_songs)])
            embed = discord.Embed(title="Top Canciones Más Reproducidas", description=description, color=discord.Color.blue())
        else:
            embed = discord.Embed(title="Historial Vacío", description="No hay canciones en el historial.", color=discord.Color.orange())
        await ctx.send(embed=embed)

    @commands.command()
    async def queue(self, ctx):
        if not self.song_queue:
            embed = discord.Embed(title="Cola Vacía", description="La cola está vacía.", color=discord.Color.orange())
            await ctx.send(embed=embed)
            return

        queue_message = "\n".join([f"{idx + 1}. {song['title']} ({self.format_duration(song['duration'])})" for idx, song in enumerate(self.song_queue)])
        embed = discord.Embed(title="Cola de Canciones", description=queue_message, color=discord.Color.blue())
        await ctx.send(embed=embed)

    @commands.command(name="np")
    async def now_playing(self, ctx):
        """Muestra la canción actualmente en reproducción."""
        if self.current_song:
            elapsed_time = time.time() - self.start_time
            elapsed_str = self.format_duration(elapsed_time)
            duration_str = self.format_duration(self.current_song.get('duration', 0))
            embed = discord.Embed(
                title="Reproduciendo Ahora",
                description=f"🎶 **{self.current_song['title']}**\n⏳ Tiempo transcurrido: {elapsed_str}/{duration_str}",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="Sin Reproducción", description="⚠️ No hay ninguna canción reproduciéndose en este momento.", color=discord.Color.orange())
            await ctx.send(embed=embed)

    @commands.command(name="shuffle")
    async def shuffle(self, ctx):
        """Revuelve las canciones en la cola."""
        if self.song_queue:
            random.shuffle(self.song_queue)
            embed = discord.Embed(title="Cola Revuelta", description="🔀 La cola ha sido revuelta.", color=discord.Color.green())
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="Cola Vacía", description="⚠️ La cola está vacía, no hay nada que revolver.", color=discord.Color.orange())
            await ctx.send(embed=embed)

    @commands.command()
    async def skip(self, ctx):
        """Salta la canción actual."""
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()
            await self.start_playing(ctx)
            embed = discord.Embed(title="Saltado", description="⏭️ Canción saltada.", color=discord.Color.green())
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="Error", description="⚠️ No se está reproduciendo ninguna canción.", color=discord.Color.red())
            await ctx.send(embed=embed)

    @commands.command()
    async def clear(self, ctx):
        """Limpia la cola de canciones."""
        self.song_queue.clear()
        embed = discord.Embed(title="Cola Limpiada", description="🗑️ La cola de canciones ha sido limpiada.", color=discord.Color.green())
        await ctx.send(embed=embed)

    def format_duration(self, duration):
        hours, remainder = divmod(duration, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

async def setup(bot):
    await bot.add_cog(MusicCog(bot))