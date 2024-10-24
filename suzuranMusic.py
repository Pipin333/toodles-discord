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
import math

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
        self.is_preloading = False  # Indicador para controlar la precarga

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
    
    def format_duration(seconds):
        """Formatea la duración en un formato mm:ss."""
        minutes, seconds = divmod(seconds, 60)
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

        # Verificar si el bot está conectado
        if not ctx.voice_client.is_connected():
            await ctx.send("No estoy conectado a un canal de voz.")
            return

        # Añadir las canciones a la cola
        if "youtube.com" in search or "youtu.be" in search:
            await self.play_youtube_playlist(ctx, search)
        elif "spotify.com" in search:
            await self.play_spotify_first_song(ctx, search)
        else:
            await self.search_and_queue_youtube(ctx, search)

    async def play_next(self, ctx):
        """Reproduce la siguiente canción en la cola."""
        await self._play_song(ctx)

    async def play_youtube_playlist(self, ctx, playlist_url: str):
        """Añade todas las canciones de la playlist como placeholders, luego carga las URLs en segundo plano"""
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'noplaylist': False,  # Procesar toda la playlist, no solo el primer video
        }

        try:
            # Extraer información completa de la playlist
            playlist_info = await asyncio.to_thread(lambda: youtube_dl.YoutubeDL(ydl_opts).extract_info(playlist_url, download=False))

            entries = playlist_info.get('entries', [])
            total_songs = len(entries)

            await ctx.send(f"🔄 Cargando playlist de YouTube con {total_songs} canciones...")

            # Añadir todas las canciones como placeholders en la cola
            for entry in entries:
                video_title = entry.get('title')
                await self.queue_song(ctx, video_title)  # Añadir canciones como placeholders (sin URL)

            await ctx.send(f"🎶 Se añadieron {total_songs} canciones a la cola. Las URLs se están cargando en segundo plano.")

            # Cargar las URLs en segundo plano mientras las canciones aparecen en la cola
            await self.load_songs_in_background(ctx, self.song_queue)
        except Exception as e:
            await ctx.send(f"⚠️ Error al procesar la playlist de YouTube: {e}")
            
    async def play_spotify_first_song(self, ctx, playlist_url: str):
        """Reproduce la primera canción de una playlist de Spotify, y añade el resto como placeholders"""
        playlist_id = playlist_url.split("/")[-1].split("?")[0]

        try:
            # Cargar la primera página de canciones (máximo 100)
            results = self.sp.playlist_tracks(playlist_id, limit=100, offset=0)
            tracks = results['items']
            total_songs = results['total']

            # Mensaje inicial
            await ctx.send(f"🔄 Cargando playlist de Spotify con {total_songs} canciones...")

            # Reproducir la primera canción
            first_track = tracks[0]['track']
            song_name = first_track['name']
            artist_name = first_track['artists'][0]['name']
            search_query = f"{song_name} {artist_name}"

            await self.search_and_queue_youtube(ctx, search_query)

            # Añadir el resto de las canciones a la cola como placeholders
            for track in tracks[1:]:
                song_name = track['track']['name']
                artist_name = track['track']['artists'][0]['name']
                search_query = f"{song_name} {artist_name}"
                await self.queue_song(ctx, search_query)

            # Si hay más de 100 canciones, llamar a `load_remaining_spotify_songs` para paginar
            if total_songs > 100:
                await self.load_remaining_spotify_songs(ctx, playlist_id, total_songs, 100)
            else:
                await ctx.send(f"🎶 Se añadieron todas las canciones a la cola.")

        except Exception as e:
            await ctx.send(f"⚠️ Error al procesar la playlist de Spotify: {e}")

    async def load_remaining_spotify_songs(self, ctx, playlist_id: str, total_songs: int, offset: int):
        """Carga las canciones restantes de una playlist de Spotify usando paginación"""
        try:
            # Paginación para cargar las canciones restantes de 100 en 100
            while offset < total_songs:
                results = self.sp.playlist_tracks(playlist_id, limit=100, offset=offset)
                tracks = results['items']

                # Añadir las canciones a la cola como placeholders
                for track in tracks:
                    song_name = track['track']['name']
                    artist_name = track['track']['artists'][0]['name']
                    search_query = f"{song_name} {artist_name}"
                    await self.queue_song(ctx, search_query)

                offset += 100  # Incrementar el offset para la siguiente página
                await asyncio.sleep(1)  # Pausa para no sobrecargar el bot

            await ctx.send(f"🎶 Se añadieron todas las canciones de la playlist de Spotify a la cola.")

        except Exception as e:
            await ctx.send(f"⚠️ Error al cargar las canciones restantes de Spotify: {e}")

    async def search_and_queue_youtube(self, ctx, search_query: str):
        """Realiza una búsqueda en YouTube y añade la canción a la cola sin bloquear el hilo principal."""
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'noplaylist': True,
        }

        try:
            async with self.semaphore:  # Limitar tareas concurrentes
                info = await asyncio.to_thread(lambda: youtube_dl.YoutubeDL(ydl_opts).extract_info(f"ytsearch:{search_query}", download=False))
                if info.get('entries'):
                    song_info = info['entries'][0]
                    song_url = song_info['url']  # Puedes guardar la URL aquí
                    song_title = song_info['title']

                    await self.queue_song(ctx, song_title)  # Solo pasa el título
                else:
                    await ctx.send("No se encontró la canción.")
        except Exception as e:
            await ctx.send(f"Error al intentar añadir la canción: {e}")

    async def queue_song(self, ctx, song_title: str):
        """Añade una canción como placeholder a la cola (sin URL por el momento)"""
        song = {'title': song_title, 'url': None, 'loaded': False, 'duration': 0}  # Incluye duración aquí
        self.song_queue.append(song)
        await ctx.send(f"🔸 Añadido a la cola: **{song_title}** (Pendiente de carga de URL)")

        if not self.voice_client or not self.voice_client.is_playing():
            await self._play_song(ctx)

    async def _play_song(self, ctx):
        """Reproduce una canción desde la cola, cargando la URL si es necesario"""
        if self.song_queue:
            song = self.song_queue.pop(0)

            # Si la canción no está cargada (URL es None), la cargamos ahora
            if not song['loaded']:
                song = await self.load_song_url(song['title'])

            song_url = song['url']
            song_title = song['title']
            self.current_song = song  # Actualiza la canción actual
            self.start_time = time.time()

            if self.voice_client.is_connected():
                source = discord.FFmpegPCMAudio(song_url, before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', options='-vn')
                self.voice_client.play(source, after=lambda e: self.bot.loop.create_task(self.play_next(ctx)))

                # Inicia la precarga de la siguiente canción
                await self.preload_next_song(ctx)

                await ctx.send(f"🎶 Ahora reproduciendo: **{song_title}**")
            else:
                await ctx.send("⚠️ No estoy conectado a un canal de voz.")
        else:
            await ctx.send("⚠️ No hay más canciones en la cola.")

    async def preload_next_song(self, ctx):
        """Carga la URL de la próxima canción en la cola, asegurándose de que solo una canción se cargue a la vez."""
        if self.is_preloading:
            return  # Si ya se está precargando, salimos de la función

        self.is_preloading = True  # Marcamos que estamos precargando

        if len(self.song_queue) > 0:  # Verifica si hay más canciones en la cola
            next_song = self.song_queue[0]  # Mira la siguiente canción sin sacarla de la cola
            if not next_song['loaded']:
                loaded_song = await self.load_song_url(next_song['title'])
                self.song_queue[0] = loaded_song  # Actualiza la canción en la cola con la URL cargada

        self.is_preloading = False  # Reiniciamos el indicador de precarga

    async def load_song_url(self, song_title):
        """Carga la URL de una canción usando YouTube y extrae su duración."""
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'noplaylist': True,
        }

        try:
            info = await asyncio.to_thread(lambda: youtube_dl.YoutubeDL(ydl_opts).extract_info(f"ytsearch:{song_title}", download=False))
            if info.get('entries'):
                song_info = info['entries'][0]
                song_url = song_info['url']
                song_duration = song_info.get('duration', 0)  # Obtener duración de la canción
                return {'title': song_title, 'url': song_url, 'duration': song_duration, 'loaded': True}
        except Exception as e:
            return {'title': song_title, 'url': None, 'duration': 0, 'loaded': False}
            
    async def play_youtube_playlist(self, ctx, playlist_url: str):
        """Añade todas las canciones de la playlist como placeholders, luego carga las URLs en segundo plano"""
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'noplaylist': False,  # Procesar toda la playlist, no solo el primer video
        }

        try:
            # Extraer información completa de la playlist
            playlist_info = await asyncio.to_thread(lambda: youtube_dl.YoutubeDL(ydl_opts).extract_info(playlist_url, download=False))

            entries = playlist_info.get('entries', [])
            total_songs = len(entries)

            await ctx.send(f"🔄 Cargando playlist de YouTube con {total_songs} canciones...")

            # Añadir todas las canciones como placeholders en la cola
            for entry in entries:
                video_title = entry.get('title')
                await self.queue_song(ctx, video_title)  # Añadir canciones como placeholders (sin URL)

            await ctx.send(f"🎶 Se añadieron {total_songs} canciones a la cola. Las URLs se están cargando en segundo plano.")

            # Cargar las URLs en segundo plano
            await self.load_songs_in_background(ctx)
        except Exception as e:
            await ctx.send(f"⚠️ Error al procesar la playlist de YouTube: {e}")

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
            total_duration = self.current_song.get('duration', 0)  # Duración total de la canción
            formatted_elapsed_time = self.format_duration(elapsed_time)
            formatted_total_duration = self.format_duration(total_duration)
            
            await ctx.send(f"🎶 Reproduciendo ahora: **{self.current_song['title']}** \nTiempo transcurrido: {formatted_elapsed_time} / {formatted_total_duration}")
        else:
            await ctx.send("No hay ninguna canción reproduciéndose en este momento.")
        
        await self.delete_user_message(ctx)

    @commands.command()
    async def queue(self, ctx):
        """Muestra la cola de canciones en páginas de 15 elementos"""
        items_per_page = 15
        total_songs = len(self.song_queue)
        
        if total_songs == 0:
            await ctx.send("La cola de canciones está vacía.")
            return

        # Calcular el número total de páginas
        total_pages = math.ceil(total_songs / items_per_page)

        # Función que genera el contenido de una página
        def get_page(page_num):
            start_idx = (page_num - 1) * items_per_page
            end_idx = min(start_idx + items_per_page, total_songs)
            queue_message = f"**Cola de canciones - Página {page_num}/{total_pages}:**\n"
            
            for idx, song in enumerate(self.song_queue[start_idx:end_idx], start=start_idx + 1):
                song_status = "Cargada" if song['loaded'] else "Pendiente de cargar"
                queue_message += f"{idx}. **{song['title']}** ({song_status})\n"
            
            return queue_message

        # Mostrar la primera página
        current_page = 1
        message = await ctx.send(get_page(current_page))

        # Añadir reacciones para la paginación
        if total_pages > 1:
            await message.add_reaction('⬅️')  # Para retroceder
            await message.add_reaction('➡️')  # Para avanzar

            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ['⬅️', '➡️'] and reaction.message.id == message.id

            # Loop para controlar la navegación
            while True:
                try:
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
                    
                    if str(reaction.emoji) == '➡️' and current_page < total_pages:
                        current_page += 1
                        await message.edit(content=get_page(current_page))
                    elif str(reaction.emoji) == '⬅️' and current_page > 1:
                        current_page -= 1
                        await message.edit(content=get_page(current_page))

                    # Eliminar la reacción del usuario para evitar confusión
                    await message.remove_reaction(reaction, user)

                except asyncio.TimeoutError:
                    # Eliminar las reacciones si se acaba el tiempo
                    await message.clear_reactions()
                    break

    @commands.command()
    async def shuffle(self, ctx):
        """Revuelve las canciones en la cola"""
        random.shuffle(self.song_queue)
        await ctx.send("La cola de canciones ha sido revuelta.")
            
    @commands.command(name='q')
    async def queue_short(self, ctx, *, search: str):
        """Abreviación del comando queue"""
        await self.queue(self, ctx)

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