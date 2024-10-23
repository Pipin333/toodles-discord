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

        # Semaphore to limit concurrent tasks for loading songs
        self.semaphore = asyncio.Semaphore(3)  # Limiting to 3 concurrent tasks

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

        # Cargar y reproducir solo la primera canción de inmediato
        if "youtube.com" in search or "youtu.be" in search:
            await self.play_youtube_first_song(ctx, search)
            # Luego, cargar el resto en segundo plano
            await self.load_remaining_youtube_songs(ctx, search)
        elif "spotify.com" in search:
            await self.play_spotify_first_song(ctx, search)
            await self.load_remaining_spotify_songs(ctx, search)
        else:
            await self.search_and_queue_youtube(ctx, search)

    async def play_youtube_first_song(self, ctx, playlist_url: str):
        """Reproduce solo la primera canción de una playlist de YouTube para dar prioridad a la reproducción."""
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'noplaylist': False,  # Procesar playlist
        }

        try:
            # Cargar solo la primera canción de la playlist
            playlist_info = await asyncio.to_thread(lambda: youtube_dl.YoutubeDL(ydl_opts).extract_info(playlist_url, download=False))
            first_song = playlist_info['entries'][0]
            video_url = first_song['url']
            video_title = first_song['title']

            await self.queue_song(ctx, video_url, video_title)
            await ctx.send(f"🎶 Ahora reproduciendo: **{video_title}**")
        except Exception as e:
            await ctx.send(f"Error al procesar la primera canción de YouTube: {e}")

    async def load_remaining_youtube_songs(self, ctx, playlist_url: str):
        """Carga las canciones restantes de una playlist de YouTube en segundo plano."""
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'noplaylist': False,
        }

        try:
            playlist_info = await asyncio.to_thread(lambda: youtube_dl.YoutubeDL(ydl_opts).extract_info(playlist_url, download=False))
            entries = playlist_info.get('entries', [])[1:]  # Omitir la primera canción

            for entry in entries:
                video_title = entry.get('title')
                video_url = entry.get('url')

                # Añadir las canciones restantes a la cola
                async with self.semaphore:  # Controlar las tareas concurrentes
                    await self.queue_song(ctx, video_url, video_title)
                await asyncio.sleep(1)  # Pausa para no sobrecargar el sistema

            await ctx.send(f"🎶 Se añadieron {len(entries)} canciones adicionales de YouTube a la cola.")
        except Exception as e:
            await ctx.send(f"Error al cargar las canciones adicionales de YouTube: {e}")

    async def play_spotify_first_song(self, ctx, playlist_url: str):
        """Reproduce la primera canción de una playlist de Spotify."""
        playlist_id = playlist_url.split("/")[-1].split("?")[0]

        try:
            results = self.sp.playlist_tracks(playlist_id)
            first_track = results['items'][0]['track']

            song_name = first_track['name']
            artist_name = first_track['artists'][0]['name']
            search_query = f"{song_name} {artist_name}"

            await self.search_and_queue_youtube(ctx, search_query)
        except Exception as e:
            await ctx.send(f"Error al procesar la primera canción de Spotify: {e}")

    async def load_remaining_spotify_songs(self, ctx, playlist_url: str):
        """Carga las canciones restantes de una playlist de Spotify en segundo plano."""
        playlist_id = playlist_url.split("/")[-1].split("?")[0]

        try:
            results = self.sp.playlist_tracks(playlist_id)
            tracks = results['items'][1:]  # Omitir la primera canción

            for track in tracks:
                song_name = track['track']['name']
                artist_name = track['track']['artists'][0]['name']
                search_query = f"{song_name} {artist_name}"

                async with self.semaphore:  # Controlar las tareas concurrentes
                    await self.search_and_queue_youtube(ctx, search_query)
                await asyncio.sleep(1)  # Pausa para no sobrecargar el sistema

            await ctx.send(f"🎶 Se añadieron {len(tracks)} canciones adicionales de Spotify a la cola.")
        except Exception as e:
            await ctx.send(f"Error al cargar las canciones adicionales de Spotify: {e}")

    async def search_and_queue_youtube(self, ctx, search_query: str):
        """Realiza una búsqueda en YouTube y añade la canción a la cola sin bloquear el hilo principal."""
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'noplaylist': True,
        }

        try:
            # Ejecuta yt_dlp en un hilo separado para no bloquear el hilo principal
            async with self.semaphore:  # Limitar tareas concurrentes
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

    @commands.command(name='p')
    async def play_short(self, ctx, *, search: str):
        """Abreviación del comando play"""
        await self.play(ctx, search)

    @commands.command()
    async def search(self, ctx, *, query: str):
        """Busca canciones en YouTube y permite elegir entre las primeras coincidencias"""

        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'noplaylist': False,  # Cambia a False para procesar playlists
        }

        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch:{query}", download=False)
                if 'entries' in info:
                    search_results = info['entries'][:5]
                    results_message = "Canciones encontradas:\n"
                    for idx, entry in enumerate(search_results):
                        title = entry.get('title', 'Sin título')
                        duration = entry.get('duration', 0)
                        formatted_duration = self.format_duration(duration)
                        results_message += f"{idx + 1}. {title} (Duración: {formatted_duration})\n"
                    
                    await ctx.send(results_message + "Responde con el número de la canción que quieres reproducir.")
                    
                    def check(msg):
                        return msg.author == ctx.author and msg.channel == ctx.channel and msg.content.isdigit()
                    
                    try:
                        response = await self.bot.wait_for('message', timeout=30.0, check=check)
                        choice = int(response.content) - 1
                        if 0 <= choice < len(search_results):
                            selected_song = search_results[choice]
                            song = {
                                'url': selected_song['url'],
                                'title': selected_song['title'],
                                'duration': selected_song.get('duration', 0)  # Guardar duración
                            }
                            self.song_queue.append(song)
                            await ctx.send(f"🎶 Canción seleccionada: {selected_song['title']} añadida a la cola.")
                            
                            # Verificar si el bot está en un canal de voz antes de intentar reproducir
                            if not self.voice_client or not self.voice_client.is_connected():
                                if ctx.author.voice:
                                    channel = ctx.author.voice.channel
                                    self.voice_client = await channel.connect()
                                else:
                                    await ctx.send("No estoy en un canal de voz. Conéctame a un canal y vuelve a intentar.")
                            else:
                                if not self.voice_client.is_playing() and not self.current_song:
                                    await self._play_song(ctx)
                        else:
                            await ctx.send("Número de canción inválido.")
                    except asyncio.TimeoutError:
                        await ctx.send("Se agotó el tiempo para seleccionar una canción.")
                else:
                    await ctx.send("No se encontraron canciones.")
        except Exception as e:
            await ctx.send(f"Error durante la búsqueda: {e}")
            print(f"Error durante la búsqueda: {e}")

        await self.delete_user_message(ctx)

    @commands.command()
    async def np(self, ctx):
        """Muestra la canción que se está reproduciendo actualmente"""
        if self.current_song:
            if self.start_time is None:
                await ctx.send("No se pudo determinar el tiempo transcurrido.")
                return

            elapsed_time = int(time.time() - self.start_time)
            total_duration = self.current_song.get('duration', 0)
            formatted_elapsed_time = self.format_duration(elapsed_time)
            formatted_total_duration = self.format_duration(total_duration)
            
            await ctx.send(f"🎶 Reproduciendo ahora: **{self.current_song['title']}** \nTiempo transcurrido: {formatted_elapsed_time} / {formatted_total_duration}")
        else:
            await ctx.send("No hay ninguna canción reproduciéndose en este momento.")
        
        await self.delete_user_message(ctx)

    @commands.command()
    async def queue(self, ctx):
        """Muestra la cola de canciones"""
        if self.song_queue:
            max_length = 2000
            queue_message = "**Cola de canciones:**\n"
            current_message = ""

            for idx, song in enumerate(self.song_queue):
                formatted_duration = self.format_duration(song.get('duration', 0))
                song_info = f"{idx + 1}. **{song['title']}** ({formatted_duration})\n"

                if len(current_message) + len(song_info) > max_length:
                    await ctx.send(current_message)
                    current_message = song_info  # Comienza un nuevo mensaje
                else:
                    current_message += song_info

            if current_message:  # Envía el último mensaje si hay contenido
                await ctx.send(current_message)
        else:
            await ctx.send("La cola de canciones está vacía.")

        await self.delete_user_message(ctx)

    @commands.command()
    async def shuffle(self, ctx):
        """Revuelve la cola de canciones."""
        if len(self.song_queue) > 1:
            random.shuffle(self.song_queue)
            await ctx.send("🔀 La cola de canciones ha sido revuelta.")
        else:
            await ctx.send("No hay suficientes canciones en la cola para revolver.")  
        await self.delete_user_message(ctx)
        
    @commands.command(name='q')
    async def queue_short(self, ctx, *, search: str):
        """Abreviación del comando queue"""
        await self.queue(ctx, search)

    @commands.command()
    async def add(self, ctx, position: int, *, title: str):
        """Agrega una canción a una posición específica en la cola"""
        if position < 1:
            await ctx.send("La posición debe ser mayor que 0.")
            return
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'noplaylist': False,  # Cambia a False para procesar playlists
        }
        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch:{title}", download=False)
                if info.get('entries'):
                    song_info = info['entries'][0]
                    song_url = song_info['url']
                    song_title = song_info['title']
                    song_duration = song_info.get('duration', 0)
                    
                    song = {'url': song_url, 'title': song_title, 'duration': song_duration}
                    self.song_queue.insert(position - 1, song)
                    await ctx.send(f"🎶 Canción añadida a la posición {position}: **{song_title}**")
                else:
                    await ctx.send("No se encontró la canción.")
        except Exception as e:
            await ctx.send(f"Error al intentar agregar la canción: {e}")
            print(f"Error al intentar agregar la canción: {e}")
        await self.delete_user_message(ctx)

    @commands.command()
    async def move(self, ctx, current_index: int, new_index: int):
        """Mueve una canción a una nueva posición en la cola"""
        if current_index < 1 or new_index < 1:
            await ctx.send("Los índices deben ser mayores que 0.")
            return

        if current_index - 1 >= len(self.song_queue) or new_index - 1 >= len(self.song_queue):
            await ctx.send("Índice fuera de rango.")
            return

        song = self.song_queue.pop(current_index - 1)
        self.song_queue.insert(new_index - 1, song)
        await ctx.send(f"🎶 Canción movida de la posición {current_index} a la posición {new_index}.")
        await self.delete_user_message(ctx)

    @commands.command()
    async def remove(self, ctx, index: int):
        """Elimina una canción de la cola por su índice"""
        if index < 1 or index > len(self.song_queue):
            await ctx.send("Índice fuera de rango.")
            return

        removed_song = self.song_queue.pop(index - 1)
        await ctx.send(f"🎶 Canción eliminada: **{removed_song['title']}**")
        await self.delete_user_message(ctx)

    @commands.command()
    async def clear(self, ctx):
        """Limpia la cola de canciones"""
        self.song_queue.clear()
        await ctx.send("🎵 Cola de canciones limpia.")
        await self.delete_user_message(ctx)

    @commands.command()
    async def skip(self, ctx):
        """Salta la canción actual"""
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()
            await self.play_next(ctx)
        else:
            await ctx.send("No se está reproduciendo ninguna canción.")
        await self.delete_user_message(ctx)

    @commands.command()
    async def pause(self, ctx):
        """Pausa la canción actual"""
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.pause()
            await ctx.send("⏸️ Canción pausada.")
        else:
            await ctx.send("No se está reproduciendo ninguna canción.")
        await self.delete_user_message(ctx)

    @commands.command()
    async def resume(self, ctx):
        """Reanuda la canción pausada"""
        if self.voice_client and self.voice_client.is_paused():
            self.voice_client.resume()
            await ctx.send("▶️ Canción reanudada.")
        else:
            await ctx.send("No hay ninguna canción pausada.")
        await self.delete_user_message(ctx)

    @commands.command()
    async def stop(self, ctx):
        """Detiene la canción actual y limpia la cola"""
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()
            self.song_queue.clear()
            self.current_song = None
            await ctx.send("🛑 Canción detenida y cola de canciones limpia.")
        else:
            await ctx.send("No se está reproduciendo ninguna canción.")
        await self.delete_user_message(ctx)

    @commands.command()
    async def leave(self, ctx):
        """Desconecta al bot del canal de voz"""
        if self.voice_client:
            await self.voice_client.disconnect()
            self.voice_client = None
            self.song_queue.clear()
            self.current_song = None
            await ctx.send("👋 Desconectado del canal de voz.")
        else:
            await ctx.send("No estoy en un canal de voz.")
        await self.delete_user_message(ctx)

    @tasks.loop(seconds=60)
    async def check_inactivity(self):
        """Verifica si el bot debe desconectarse por inactividad"""
        if self.voice_client and not self.voice_client.is_playing():
            if not self.song_queue:
                await self.voice_client.disconnect()
                self.voice_client = None
                self.song_queue.clear()
                self.current_song = None
                print("Desconectado por inactividad.")


async def setup(bot):
   await bot.add_cog(Music(bot))