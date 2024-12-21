import asyncio
import concurrent.futures
import math
import os
import random
import subprocess
import time

import discord
import spotipy
import yt_dlp as youtube_dl
from discord.ext import commands, tasks
from spotipy.oauth2 import SpotifyClientCredentials

from database import setup_database, add_or_update_song, get_top_songs

SPOTIFY_CLIENT_ID = os.getenv('client_id')
SPOTIFY_CLIENT_SECRET = os.getenv('client_secret')

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.song_queue = []  # Lista que almacenará las canciones en cola
        self.current_song = None
        self.voice_client = None
        self.check_inactivity.start()
        self.start_time = None
        self.cache = {}
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
        self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET))
        self.is_preloading = False  # Indicador para controlar la precarga
        self.is_preloading = False  # Indicador para controlar la precarga
        self.start_time = None  # Inicializa el tiempo de reproducción
        self.cache = {}  # Diccionario para caché
        # Semaphore to limit concurrent tasks for loading songs
        self.semaphore = asyncio.Semaphore(3)  # Limiting to 3 concurrent tasks
        setup_database()
        print("Cog 'Music' inicializado correctamente.")

        try:
            subprocess.run(
                ["ffmpeg", "-version"],  # Comando para verificar FFmpeg
                stdout=subprocess.DEVNULL,  # Suprime la salida estándar
                stderr=subprocess.DEVNULL   # Suprime la salida de error
            )
            print("FFmpeg precargado correctamente.")
        except FileNotFoundError:
            print("Error: FFmpeg no está instalado o no está en el PATH.")

    async def delete_user_message(self, ctx):
        await asyncio.sleep(0.1)
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            await ctx.send("No tengo permisos para borrar mensajes.")
        except discord.HTTPException as e:
            await ctx.send(f"Error al borrar el mensaje: {e}")
    
    def format_duration(self, duration):
        """Convierte una duración en segundos a un formato legible (HH:MM:SS)"""
        hours, remainder = divmod(duration, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"


    @commands.command()
    async def help(self, ctx):
        """Muestra una lista de comandos disponibles"""
        help_message = (
            "**Comandos de Toodles Music:**\n"
            "`td?help` - Muestra este mensaje.\n"
            "`td?join` - Conecta el bot al canal de voz.\n"
            "`td?play / td?p <título>` - Agrega una canción a la cola y empieza a reproducir si no hay ninguna canción en curso.\n"
            "`td?search <título>` - Busca el nombre de una canccion y muestra una lista con las coincidencias.\n"
            "`td?queue / td?q` - Muestra la cola actual de canciones.\n"
            "`td?add [posición] <título>` - Agrega una canción a una posición específica en la cola.\n"
            "`td?remove <índice>` - Elimina una canción de la cola por su índice.\n"
            "`td?clear` - Limpia la cola de canciones.\n"
            "`td?skip` - Salta la canción actual.\n"
            "`td?pause` - Pausa la canción actual.\n"
            "`td?resume` - Reanuda la canción pausada.\n"
            "`td?stop` - Detiene la canción actual y limpia la cola.\n"
            "`td?leave` - Desconecta el bot del canal de voz.\n"
            "`td?shuffle` - Revuelve la cola de canciones actual.\n"
        )
        await ctx.send(help_message)

    
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

        # Precarga el proceso de FFmpeg para la primera canción
        if not self.current_song:
            self.voice_client.stop()
            self.voice_client.play(discord.FFmpegPCMAudio('', options='-vn'), after=None)

        # Manejo de URLs
        if "youtube.com/watch" in search or "youtu.be/" in search:
            await self.search_and_queue_youtube(ctx, search)
        elif "spotify.com/track" in search:
            await self.play_spotify_track(ctx, search)
        elif "spotify.com/playlist" in search:
            await self.play_spotify_playlist(ctx, search)
        elif "youtube.com/playlist" in search:
            await self.play_youtube_playlist(ctx, search)
        else:
            await self.search_and_queue_youtube(ctx, search)  # Búsqueda genérica


    @commands.command(name='p')
    async def play_short(self, ctx, *, search: str):
        """Abreviación del comando play"""
        await self.play(ctx, search)

    async def play_next(self, ctx):
        """Reproduce la siguiente canción en la cola."""
        await self._play_song(ctx)

    async def load_songs_in_background(self, ctx):
        """Carga las URLs de las canciones en segundo plano."""
        while self.song_queue:
            song = self.song_queue[0]  # Ver la primera canción en la cola
            if not song['loaded']:
                loaded_song = await self.load_song_url(song['title'])  # Cargar la URL
                if loaded_song and loaded_song['url']:
                    # Actualizar la canción en la cola
                    song['url'] = loaded_song['url']
                    song['loaded'] = True
                    await ctx.send(f"🔸 URL cargada para: **{song['title']}**")
            await asyncio.sleep(1)  # Pausa para no sobrecargar el bot

    async def play_spotify_track(self, ctx, track_url: str):
        """Busca una canción individual de Spotify y la añade a la cola."""
        track_id = track_url.split("/")[-1].split("?")[0]

        try:
            # Obtener información de la canción de Spotify
            track_info = self.sp.track(track_id)
            song_name = track_info.get('name', 'Canción desconocida')
            artist_name = track_info['artists'][0]['name']
            search_query = f"{song_name} {artist_name}"

            # Buscar en YouTube y añadir a la cola
            await self.search_and_queue_youtube(ctx, search_query)

        except Exception as e:
            await ctx.send(f"⚠️ Error al procesar la canción de Spotify: {e}")

    async def play_spotify_playlist(self, ctx, playlist_id: str):
        try:
            # Verificar si los datos están en caché
            if playlist_id in self.cache:
                tracks = self.cache[playlist_id]['data']  # Recuperar de la caché
                await ctx.send("✅ Playlist cargada desde la caché.")
            else:
                # Realizar la solicitud a la API de Spotify
                results = self.sp.playlist_items(playlist_id, limit=100, offset=0)
                tracks = results.get('items', [])

                # Guardar datos en la caché con timestamp
                self.cache[playlist_id] = {
                    'data': tracks,
                    'timestamp': time.time()
                }
                await ctx.send("🔄 Playlist cargada desde Spotify.")

            # Procesar canciones obtenidas
            for track in tracks:
                song = track.get('track', {})
                if not song.get('is_playable', True):
                    continue
                song_name = song.get('name', "Canción desconocida")
                artist_data = song.get('artists', [{}])
                artist = artist_data[0].get('name', 'Artista desconocido') if artist_data else 'Artista desconocido'

                # Usar nombre y artista para añadir la canción a la cola
                search_query = f"{song_name} {artist}"

                # Opcional: Guardar las canciones también en la base de datos
                add_or_update_song(song_name, artist=artist)  # Función importada

                # Añadir la canción a la cola
                await self.queue_song(ctx, search_query)

            await ctx.send(f"🎶 Todas las canciones de la playlist han sido añadidas a la cola.")
        except Exception as e:
            await ctx.send(f"⚠️ Error: {e}")



    async def play_youtube_url(self, ctx, video_url: str):
        """Reproduce una canción desde una URL de YouTube"""
        ydl_opts = {
            'format': 'bestaudio/best',
            'verbose': True,
            'quiet': False,
            'noplaylist': True,
            'cachedir': False  # Asegurarse de que no trate de cargar listas de reproducción
        }

        try:
            # Extraer información del video de YouTube
            video_info = await asyncio.to_thread(lambda: youtube_dl.YoutubeDL(ydl_opts).extract_info(video_url, download=False))  # Extrae info en hilo separado
            
            # Obtener el título y la URL para la reproducción
            video_title = video_info.get('title')
            video_url = video_info.get('url')

            # Añadir la canción a la cola y reproducir
            await self.queue_song(ctx, video_title)  # Modifica según cómo gestiones la cola
            await ctx.send(f"🎶 Reproduciendo: **{video_title}**")
        except Exception as e:
            await ctx.send(f"⚠️ Error al cargar la canción de YouTube: {e}")

    async def play_youtube_playlist(self, ctx, playlist_url: str):
        """
        Reproduce una playlist de YouTube en el canal de voz actual.

        Args:
            ctx: Contexto del comando.
            playlist_url: URL de la playlist de YouTube.

        Returns:
            Añade las canciones de la playlist a la cola y comienza a reproducir.
        """
        try:
            # Validar que el usuario está en un canal de voz
            if not ctx.author.voice or not ctx.author.voice.channel:
                await ctx.send("❌ Debes estar en un canal de voz para usar este comando.")
                return

            # Conectarse al canal de voz del usuario si aún no está conectado
            if not self.voice_client or not self.voice_client.is_connected():
                channel = ctx.author.voice.channel
                self.voice_client = await channel.connect()

            # Crear opciones para obtener la información de la playlist usando youtube_dl
            ydl_opts = {
                'quiet': True,
                'extract_flat': True  # Extraer solo los metadatos, no descargar el video
            }

            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(playlist_url, download=False)

            # Verificar si la URL es realmente una playlist
            if 'entries' not in info:
                await ctx.send("❌ La URL proporcionada no es una playlist válida de YouTube.")
                return

            playlist_title = info.get('title', 'Playlist desconocida')
            playlist_entries = info['entries']

            # Enviar mensaje al usuario
            await ctx.send(f"📃 Procesando la playlist: **{playlist_title}** con {len(playlist_entries)} canciones.")

            # Agregar las canciones de la playlist a la cola
            for entry in playlist_entries:
                song_url = entry.get('url', None)
                if not song_url:
                    continue

                # Usar la función queue_song o un equivalente para agregar canciones a la cola
                await self.queue_song(ctx, song_url)

            # Reproducir la primera canción si no se está reproduciendo nada
            if not self.current_song:
                await self.play_next(ctx)

            await ctx.send(f"✅ Playlist **'{playlist_title}'** añadida a la cola.")

        except Exception as e:
            await ctx.send("❌ Ocurrió un error al procesar la playlist.")
            print(f"Error en play_youtube_playlist(): {e}")

    async def search_and_queue_youtube(self, ctx, search: str):
        """Realiza una búsqueda en YouTube y añade la canción a la cola sin bloquear el hilo principal."""
        ydl_opts = {
            'format': 'bestaudio/best',
            'verbose': True,
            'quiet': False,
            'noplaylist': True,
            'cachedir': False,
            'default_search': 'ytsearch'
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            try:
                # Aquí utilizamos la variable `search` directamente
                info = ydl.extract_info(search, download=False)  # Cambia download=True a False para obtener solo la información
                if 'entries' in info:
                    # Si hay múltiples entradas (como en listas de reproducción)
                    for entry in info['entries']:
                        title = entry['title']
                        url = entry['url']
                        await self.queue_song(ctx, title)
                else:
                    title = info['title']
                    url = info['url']
                    await self.queue_song(ctx, title)
            except Exception as e:
                await ctx.send(f"Ocurrió un error al buscar la canción: {str(e)}")

    async def queue_song(self, ctx, song_title: str):
        """Añade una canción como placeholder a la cola (sin URL por el momento)"""
        song = {'title': song_title, 'url': None, 'loaded': False, 'duration': 0}  # Incluye duración aquí
        self.song_queue.append(song)
        await ctx.send(f"🔸 Añadido a la cola: **{song_title}** (Pendiente de carga de URL)")

        if not self.voice_client or not self.voice_client.is_playing():
            await self._play_song(ctx)

    async def _play_song(self, ctx):
        """Reproduce una canción desde la cola y la registra en la base de datos."""
        if self.song_queue:
            song = self.song_queue.pop(0)

            # Si la canción no está cargada, cargarla ahora
            if not song['loaded']:
                song = await self.load_song_url(song['title'])

            song_url = song['url']
            song_title = song['title']
            song_artist = song.get('artist', 'Desconocido')  # Suponiendo que hay un campo 'artist'
            song_duration = song['duration']
            self.current_song = song  # Actualiza la canción actual
            self.start_time = time.time()

            try:
                if self.voice_client.is_connected():
                    source = discord.FFmpegPCMAudio(
                        song_url, 
                        before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 
                        options='-vn'
                    )
                    self.voice_client.play(
                        source, 
                        after=lambda e: self.bot.loop.create_task(self.play_next(ctx))
                    )

                    add_or_update_song(song_title, url=song_url, artist=song_artist, duration=song_duration)  # Incluye parámetros explícitos
                    add_or_update_song(song_title, song_url, artist=song_artist, duration=song_duration)

                    # Inicia la precarga de la siguiente canción
                    await self.preload_next_song(ctx)

                    await ctx.send(f"🎶 Ahora reproduciendo: **{song_title}**")
                else:
                    await ctx.send("⚠️ No estoy conectado a un canal de voz.")
            except Exception as e:
                print(f"Error al reproducir la canción: {e}")
                await ctx.send("⚠️ Hubo un error al intentar reproducir la canción.")
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
            'verbose': True,
            'quiet': False,
            'noplaylist': True,
            'cachedir': False
        }

        try:
            info = await asyncio.to_thread(lambda: youtube_dl.YoutubeDL(ydl_opts).extract_info(f"ytsearch:{song_title}", download=False))
            if info.get('entries'):
                song_info = info['entries'][0]
                song_url = song_info['url']
                song_duration = song_info.get('duration', 0)  # Obtener duración de la canción
                return {'title': song_title, 'url': song_url, 'duration': song_duration, 'loaded': True}
        except Exception as e:
            print(f"Error al cargar la URL de la canción: {e}")
            return {'title': song_title, 'url': None, 'duration': 0, 'loaded': False}

    @commands.command()
    async def search(self, ctx, *, query: str):
        """Busca canciones en YouTube y permite elegir entre las primeras coincidencias."""
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,  # Evita mostrar mensajes verbosos
            'cachedir': False
        }

        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                # Realiza la búsqueda usando ytsearch
                info = ydl.extract_info(f"ytsearch:{query}", download=False)
                if 'entries' in info:
                    search_results = info['entries'][:10]  # Limitar a las primeras 10 entradas
                    results_message = "🎵 Canciones encontradas:\n"
                    
                    for idx, entry in enumerate(search_results):
                        title = entry.get('title', 'Sin título')
                        duration = entry.get('duration', 0)
                        formatted_duration = self.format_duration(duration)
                        results_message += f"{idx + 1}. **{title}** (Duración: {formatted_duration})\n"

                    await ctx.send(results_message + "Responde con el número de la canción que quieres reproducir.")

                    def check(msg):
                        return (msg.author == ctx.author and
                                msg.channel == ctx.channel and
                                msg.content.isdigit())

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

    @commands.command(name='np')
    async def np(self, ctx):
        """Muestra la canción que se está reproduciendo actualmente."""
        if self.current_song:
            total_duration = self.current_song['duration']  # Asegúrate de que 'duration' esté definido
            song_title = self.current_song['title']

            while self.voice_client.is_playing():  # Verifica si la canción aún se está reproduciendo
                elapsed_time = time.time() - self.start_time
                formatted_elapsed_time = self.format_duration(elapsed_time)
                formatted_total_duration = self.format_duration(total_duration)

                # Enviar el mensaje con el estado actual de la canción
                await ctx.send(f"🎶 Ahora reproduciendo: **{song_title}**\n⏳ Tiempo transcurrido: {formatted_elapsed_time}/{formatted_total_duration}")
                await asyncio.sleep(1)  # Espera un segundo antes de actualizar nuevamente

        else:
            await ctx.send("⚠️ No hay ninguna canción reproduciéndose en este momento.")


    @commands.command(name='queue', aliases=['q'])
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
                song_status = "Cargada" if song.get('loaded', False) else "Pendiente de cargar"
                queue_message += f"{idx}. **{song['title']}** ({song_status})\n"
            
            return queue_message

        # Mostrar la primera página
        current_page = 1
        message = await ctx.send(get_page(current_page))

        # Añadir reacciones para la paginación
        if total_pages > 1:  # Agrega reacciones solo si hay muchas páginas
            await message.add_reaction('⬅️')  # Para retroceder
            await message.add_reaction('➡️')  # Para avanzar

            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ['⬅️', '➡️'] and reaction.message.id == message.id

            # Loop para controlar la navegación
            while True:
                try:
                    # Reducir el tiempo de espera a 10 segundos
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=20.0, check=check)

                    # Mejorar la responsividad cambiando la página solo si la reacción es válida
                    if str(reaction.emoji) == '➡️' and current_page < total_pages:
                        current_page += 1
                        await message.edit(content=get_page(current_page))
                    elif str(reaction.emoji) == '⬅️' and current_page > 1:
                        current_page -= 1
                        await message.edit(content=get_page(current_page))

                    # Eliminar la reacción del usuario inmediatamente para evitar confusión
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

    @commands.command()
    async def add(self, ctx, position: int, *, title: str):
        """Agrega una canción a una posición específica en la cola"""
        if position < 1:
            await ctx.send("La posición debe ser mayor que 0.")
            return
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'verbose': True,
            'quiet': False,
            'noplaylist': False,  # Cambia a False para procesar playlists
            'cachedir': False
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
        """Mueve una canción a una nueva posición en la cola y la carga si se mueve al índice 1"""
        song_title = self.current_song['title'] 
        
        if current_index < 1 or new_index < 1:
            await ctx.send("⚠️ No se encontraron canciones.")
            return

        if current_index - 1 >= len(self.song_queue) or new_index - 1 >= len(self.song_queue):
            await ctx.send("Índice fuera de rango.")
            return

        song = self.song_queue.pop(current_index - 1)
        self.song_queue.insert(new_index - 1, song)
        
        await ctx.send(f"🎶 Canción {song_title}movida de la posición {current_index} a la posición {new_index}.")
        await self.delete_user_message(ctx)

        # Si la canción se mueve al índice 1, la carga
        if new_index == 1:
            await self.preload_next_song(ctx)  # Cargar la canción en el índice 1

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

    @commands.command(name="historial")
    async def historial(self, ctx):
        """Muestra las canciones más reproducidas."""
        from database import get_top_songs

        top_songs = get_top_songs(5)
        if top_songs:
            message = "**Top 5 canciones más reproducidas:**\n"
            for idx, (title, count) in enumerate(top_songs, start=1):
                message += f"{idx}. {title} - {count} reproducciones\n"
            await ctx.send(message)
        else:
            await ctx.send("No hay canciones en el historial.")


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

    @tasks.loop(seconds=120)
    async def check_inactivity(self):
        """Verifica si el bot debe desconectarse por inactividad"""
        if self.voice_client and not self.voice_client.is_playing():
            if not self.song_queue and not self.is_preloading:  # Verificar si no está cargando canciones
                await self.voice_client.disconnect()
                self.voice_client = None
                self.song_queue.clear()
                self.current_song = None
                print("Desconectado por inactividad.")

    @commands.command(name="canciondb", help="Añade una canción o una playlist a la base de datos.")
    async def add_song(self, ctx, link: str):
        """
        Comando para agregar canciones individuales o playlists a la base de datos.

        Args:
          ctx: Contexto del comando.
          link: Enlace a la canción o playlist.

        Returns:
          Mensaje indicando éxito o error.
        """
        try:
            if "youtube.com" in link or "youtu.be" in link:
                # Detectar y manejar playlists de YouTube
                with youtube_dl.YoutubeDL({'quiet': True, 'extract_flat': 'playlist'}) as ydl:
                    info = ydl.extract_info(link, download=False)

                if 'entries' in info:  # Es una playlist
                    # Procesar todas las canciones de la playlist
                    await ctx.send(f"🎵 Procesando playlist **{info['title']}** con {len(info['entries'])} canciones...")
                    added_songs = 0
                    for entry in info['entries']:
                        title = entry.get('title', 'Unknown Title')
                        url = entry.get('url', link)
                        duration = entry.get('duration', 0)  # En segundos
                        artist = entry.get('uploader', 'Unknown Artist')

                        add_or_update_song(title=title, url=url, artist=artist, duration=duration)
                        added_songs += 1

                    await ctx.send(f"✅ Playlist procesada: {added_songs} canciones añadidas a la base de datos.")
                else:  # Es una canción individual
                    title = info.get('title', 'Unknown Title')
                    url = info.get('webpage_url', link)
                    duration = info.get('duration', 0)  # En segundos
                    artist = info.get('uploader', 'Unknown Artist')

                    add_or_update_song(title=title, url=url, artist=artist, duration=duration)
                    await ctx.send(f"🎵 La canción **'{title}'** ha sido añadida a la base de datos.")

            elif "spotify.com" in link:
                # Detectar y manejar playlists de Spotify
                if "playlist" in link:
                    # Extraer información de la playlist
                    playlist_info = self.sp.playlist(link)

                    await ctx.send(
                        f"🎵 Procesando playlist **{playlist_info['name']}** con {playlist_info['tracks']['total']} canciones...")

                    # Número total de canciones en la playlist
                    total_tracks = playlist_info['tracks']['total']
                    added_songs = 0

                    # Procesar la playlist en bloques de 99 canciones
                    for offset in range(0, total_tracks, 99):
                        # Obtener un bloque de máximo 99 canciones
                        tracks_chunk = self.sp.playlist_items(link, offset=offset, limit=99)['items']

                        for item in tracks_chunk:
                            track = item['track']
                            title = track['name']
                            url = track['external_urls']['spotify']
                            duration = track['duration_ms'] // 1000
                            artist = ", ".join([artist['name'] for artist in track['artists']])

                            add_or_update_song(title=title, url=url, artist=artist, duration=duration)
                            added_songs += 1

                        await ctx.send(
                            f"✅ Procesado bloque de 99 canciones. Total procesado: {added_songs}/{total_tracks}.")

                    # Respuesta final al terminar de procesar todos los bloques
                    await ctx.send(
                        f"✅ Playlist completa procesada: {added_songs} canciones añadidas a la base de datos.")
                else:  # Es una canción individual
                    track_info = self.sp.track(link)
                    title = track_info['name']
                    url = link
                    duration = track_info['duration_ms'] // 1000
                    artist = ", ".join([artist['name'] for artist in track_info['artists']])

                    add_or_update_song(title=title, url=url, artist=artist, duration=duration)
                    await ctx.send(f"🎵 La canción **'{title}'** ha sido añadida a la base de datos.")

            else:
                # No es un enlace reconocido
                await ctx.send(
                    "❌ No se reconoce el tipo de enlace proporcionado. Solo se soportan YouTube y Spotify por ahora.")

        except Exception as e:
            # Si algo falla durante el proceso
            await ctx.send("❌ Ocurrió un error al intentar procesar el enlace y añadir la canción o playlist.")
            await ctx.send(f"Error en add_song con link '{link}': {e}")
            await ctx.send(f"Error en add_song con link '{link}': {type(e).__name__} - {e}")

async def setup(bot):
   await bot.add_cog(Music(bot))
