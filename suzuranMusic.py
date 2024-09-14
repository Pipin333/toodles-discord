import discord
from discord.ext import commands, tasks
import yt_dlp as youtube_dl
import asyncio
import time

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.song_queue = []  # Lista para almacenar las canciones en cola
        self.current_song = None  # La canción que se está reproduciendo actualmente
        self.voice_client = None  # Conexión de voz del bot
        self.play_next_song = asyncio.Event()  # Evento para gestionar la reproducción de la siguiente canción
        self.check_inactivity.start()  # Iniciar la tarea de verificación de inactividad
        self.start_time = None  # Variable para registrar el inicio de la canción

    def delete_user_message(self, ctx):
        await asyncio.sleep(0.3)
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
    async def delete_test(self, ctx):
        """Test if the bot can delete a message"""
        try:
            await ctx.message.delete()
            await ctx.send("Mensaje eliminado.")
        except discord.Forbidden:
            await ctx.send("No tengo permisos para borrar mensajes.")
        except discord.HTTPException as e:
            await ctx.send(f"Error al intentar eliminar el mensaje: {e}")

    @commands.command()
    async def help(self, ctx):
        """Muestra una lista de comandos disponibles"""
        help_message = (
            "**Comandos de Toodles Music:**\n"
            "`td?help` - Muestra este mensaje.\n"
            "`td?join` - Conecta el bot al canal de voz.\n"
            "`td?play <título>` - Agrega una canción a la cola y empieza a reproducir si no hay ninguna canción en curso.\n"
            "`td?np` - Muestra la canción actual y el tiempo de reproducción.\n"
            "`td?queue` - Muestra la cola actual de canciones.\n"
            "`td?qAdd [posición] <título>` - Agrega una canción a una posición específica en la cola.\n"
            "`td?qMove <índice actual> <nuevo índice>` - Mueve una canción a una nueva posición en la cola.\n"
            "`td?qRemove <índice>` - Elimina una canción de la cola por su índice.\n"
            "`td?qClear` - Limpia la cola de canciones.\n"
            "`td?skip` - Salta la canción actual.\n"
            "`td?pause` - Pausa la canción actual.\n"
            "`td?resume` - Reanuda la canción pausada.\n"
            "`td?stop` - Detiene la canción actual y limpia la cola.\n"
            "`td?leave` - Desconecta el bot del canal de voz.\n"
        )
        await ctx.send(help_message)

    @commands.command()
    async def join(self, ctx):
        """Bot joins the voice channel"""
        
        if ctx.voice_client:
            await ctx.send("Ya estoy en un canal de voz.")
        else:
            if ctx.author.voice:
                channel = ctx.author.voice.channel
                self.voice_client = await channel.connect()
                await ctx.send("🎶 Entrando en el canal de voz.")
            else:
                await ctx.send("No estás conectado a un canal de voz.")
        await self.delete_user_message(ctx)
                
    @commands.command()
    async def play(self, ctx, *, search: str):
        """Agrega una canción a la cola y empieza la reproducción si no se está reproduciendo ya"""
        if not ctx.author.voice:
            await ctx.send("Necesitas estar en un canal de voz para reproducir música.")
            return

        if not ctx.voice_client:
            channel = ctx.author.voice.channel
            self.voice_client = await channel.connect()
            await ctx.send("🎶 Conectando al canal de voz...")

        # Buscar información de la canción
        ydl_opts = {
            'format': 'bestaudio/best',
            'verbose': True,
            'quiet': False,
            'noplaylist': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
        }

        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch:{search}", download=False)
                if info.get('entries'):
                    # Tomar la primera canción encontrada
                    song_info = info['entries'][0]
                    song_url = song_info['url']
                    song_title = song_info['title']
                    song_duration = song_info.get('duration', 0)  # Obtener duración

                    # Añadir la canción a la cola
                    self.song_queue.append({'url': song_url, 'title': song_title, 'duration': song_duration})

                    await ctx.send(f"🎶 Canción añadida a la cola: **{song_title}**")

                    # Si no hay ninguna canción reproduciéndose, empieza la reproducción
                    if not self.voice_client.is_playing() and not self.current_song:
                        if self.voice_client:  # Verifica que voice_client no sea None
                            await self._play_song(ctx)
                        else:
                            await ctx.send("No se pudo conectar al canal de voz.")
                else:
                    await ctx.send("No se encontró la canción.")
        except Exception as e:
            await ctx.send(f"Error al intentar reproducir la canción: {e}")
            print(f"Error al intentar reproducir la canción: {e}")

    @commands.command()
    async def search(self, ctx, *, query: str):
        """Busca canciones en YouTube y permite elegir entre las primeras coincidencias"""

        ydl_opts = {
            'format': 'bestaudio/best',
            'verbose': True,
            'quiet': False,
            'noplaylist': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
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

    async def _play_song(self, ctx):
        """Reproduce una canción desde la cola"""
        if self.song_queue:
            song = self.song_queue.pop(0)
            song_url = song['url']
            song_title = song['title']
            song_duration = song.get('duration', 0)  # Obtener la duración si está disponible
            total_duration = self.format_duration(song_duration)

            if self.voice_client and self.voice_client.is_connected():
                source = discord.FFmpegPCMAudio(song_url, before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', options='-vn')
                self.voice_client.play(source, after=lambda e: self.bot.loop.create_task(self.play_next(ctx)))  # Reproducir la canción y configurar para la siguiente
                self.current_song = song
                self.start_time = time.time()  # Inicializar el tiempo de inicio

                # Anunciar la reproducción de la canción con la duración total
                await ctx.send(f"Reproduciendo: **{song_title}** (Duración: {total_duration})")
            else:
                await ctx.send("No estoy conectado a un canal de voz.")
        else:
            self.current_song = None


    async def play_next(self, ctx):
        """Reproduce la siguiente canción en la cola"""
        if self.song_queue:
            await self._play_song(ctx)
        else:
            self.current_song = None
            await ctx.send("No hay más canciones en la cola.")

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

    @commands.command()
    async def queue(self, ctx):
        """Muestra la cola de canciones"""
        if self.song_queue:
            queue_message = "**Cola de canciones:**\n"
            for idx, song in enumerate(self.song_queue):
                formatted_duration = self.format_duration(song.get('duration', 0))
                queue_message += f"{idx + 1}. **{song['title']}** ({formatted_duration})\n"
            await ctx.send(queue_message)
        else:
            await ctx.send("La cola de canciones está vacía.")

    @commands.command()
    async def qAdd(self, ctx, position: int, *, title: str):
        """Agrega una canción a una posición específica en la cola"""
        if position < 1:
            await ctx.send("La posición debe ser mayor que 0.")
            return
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'verbose': True,
            'quiet': False,
            'noplaylist': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
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

    @commands.command()
    async def qMove(self, ctx, current_index: int, new_index: int):
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

    @commands.command()
    async def qRemove(self, ctx, index: int):
        """Elimina una canción de la cola por su índice"""
        if index < 1 or index > len(self.song_queue):
            await ctx.send("Índice fuera de rango.")
            return

        removed_song = self.song_queue.pop(index - 1)
        await ctx.send(f"🎶 Canción eliminada: **{removed_song['title']}**")

    @commands.command()
    async def qClear(self, ctx):
        """Limpia la cola de canciones"""
        self.song_queue.clear()
        await ctx.send("🎵 Cola de canciones limpia.")

    @commands.command()
    async def skip(self, ctx):
        """Salta la canción actual"""
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()
            await self.play_next(ctx)
        else:
            await ctx.send("No se está reproduciendo ninguna canción.")

    @commands.command()
    async def pause(self, ctx):
        """Pausa la canción actual"""
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.pause()
            await ctx.send("⏸️ Canción pausada.")
        else:
            await ctx.send("No se está reproduciendo ninguna canción.")

    @commands.command()
    async def resume(self, ctx):
        """Reanuda la canción pausada"""
        if self.voice_client and self.voice_client.is_paused():
            self.voice_client.resume()
            await ctx.send("▶️ Canción reanudada.")
        else:
            await ctx.send("No hay ninguna canción pausada.")

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

