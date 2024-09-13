import discord
from discord.ext import commands, tasks
import yt_dlp as youtube_dl
import asyncio

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.song_queue = []  # Lista para almacenar las canciones en cola
        self.current_song = None  # La canción que se está reproduciendo actualmente
        self.voice_client = None  # Conexión de voz del bot
        self.play_next_song = asyncio.Event()  # Evento para gestionar la reproducción de la siguiente canción
        self.check_inactivity.start()  # Iniciar la tarea de verificación de inactividad
    
    @commands.command()
    async def join(self, ctx):
        """Bot joins the voice channel"""
        if ctx.voice_client:
            await ctx.send("Ya estoy en un canal de voz.")
            return

        if ctx.author.voice:
            channel = ctx.author.voice.channel
            self.voice_client = await channel.connect()
            await ctx.send("🎶 Entrando en el canal de voz.")
        else:
            await ctx.send("No estás conectado a un canal de voz.")
    
    @commands.command()
    async def play(self, ctx, *, search: str):
        """Agrega una canción a la cola y empieza la reproducción si no se está reproduciendo ya"""
        if not ctx.author.voice:  # Verificar si el usuario está en un canal de voz
            await ctx.send("Necesitas estar en un canal de voz para reproducir música.")
            return
    
        if not ctx.voice_client:  # Conectarse al canal si el bot no está ya en un canal de voz
            channel = ctx.author.voice.channel
            self.voice_client = await channel.connect()
            await ctx.send("🎶 Conectando al canal de voz...")
    
        # Añadir la canción a la cola
        self.song_queue.append(search)
        await ctx.send(f"🎶 Canción añadida a la cola: **{search}**")
    
        # Si no hay ninguna canción reproduciéndose, empieza la reproducción
        if not self.voice_client.is_playing() and not self.current_song:
            await self.play_next(ctx)
    
    async def play_next(self, ctx):
        """Reproduce la siguiente canción en la cola"""
        if self.song_queue:
            search = self.song_queue.pop(0)  # Obtener la primera canción de la cola
            self.current_song = search  # Establecer la canción actual
            await self._play_song(ctx, search)  # Reproducir la canción
        else:
            self.current_song = None  # No hay canciones en la cola
    
    async def _play_song(self, ctx, search):
        """Reproduce una canción usando streaming"""
        ydl_opts = {
            'format': 'bestaudio/best',
            'verbose': True,
            'quiet': False,
            'noplaylist': True,  # Evitar listas de reproducción
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',  # Puedes cambiar a 'm4a', 'flac', 'wav', etc.
                'preferredquality': '320',  # Cambiar el bitrate a 192kbps (puedes usar 320 para mejor calidad)
            }],
        }

        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch:{search}", download=False)  # Búsqueda de la canción por nombre
                if info.get('entries'):
                    # Tomar la primera canción encontrada
                    song_info = info['entries'][0]
                    song_url = song_info['url']
                    source = discord.FFmpegPCMAudio(song_url, before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', options='-vn')
                    self.voice_client.play(source, after=lambda e: self.bot.loop.create_task(self.play_next(ctx)))  # Reproducir la canción y configurar para la siguiente
                    await ctx.send(f"Reproduciendo: **{song_info['title']}**")
                else:
                    await ctx.send("No se encontró la canción.")
        except Exception as e:
            await ctx.send(f"Error al intentar reproducir la canción: {e}")
            print(f"Error al intentar reproducir la canción: {e}")

    @commands.command()
    async def skip(self, ctx):
        """Salta la canción actual"""
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()  # Detener la canción actual
            await ctx.send("⏭ Saltando canción.")
        else:
            await ctx.send("No hay ninguna canción reproduciéndose.")

    @commands.command()
    async def pause(self, ctx):
        """Pausa la canción actual"""
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.pause()  # Pausar la canción
            await ctx.send("⏸ Canción pausada.")
        else:
            await ctx.send("No hay ninguna canción reproduciéndose o ya está pausada.")
    
    @commands.command()
    async def resume(self, ctx):
        """Reanuda la canción pausada"""
        if self.voice_client and self.voice_client.is_paused():
            self.voice_client.resume()  # Reanudar la canción
            await ctx.send("▶ Reanudando la canción.")
        else:
            await ctx.send("No hay ninguna canción pausada o no estoy en un canal de voz.")
    
    @commands.command()
    async def stop(self, ctx):
        """Detiene la canción actual y limpia la cola"""
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()  # Detener la canción actual
            self.song_queue.clear()  # Limpiar la cola de canciones
            self.current_song = None  # Resetear la canción actual
            await ctx.send("🛑 Canción detenida y cola limpiada.")
        else:
            await ctx.send("No hay ninguna canción reproduciéndose.")

    @commands.command()
    async def queue(self, ctx):
        """Muestra la cola actual de canciones"""
        if self.song_queue:
            queue_list = "\n".join(f"{idx + 1}. {song}" for idx, song in enumerate(self.song_queue))
            await ctx.send(f"🎵 Cola actual:\n{queue_list}")
        else:
            await ctx.send("La cola de canciones está vacía.")
    
    @commands.command()
    async def qAdd(self, ctx, position: int = None, *, search: str):
        """Agrega una canción a una posición específica en la cola"""
        if position is None or position > len(self.song_queue):
            # Añadir la canción al final de la cola si no se especifica posición o si la posición es mayor que la cola actual
            self.song_queue.append(search)
            await ctx.send(f"🎶 Canción añadida al final de la cola: **{search}**")
        else:
            # Insertar la canción en la posición especificada (1-basado)
            self.song_queue.insert(position - 1, search)
            await ctx.send(f"🎶 Canción añadida a la posición {position} en la cola: **{search}**")
    
    @commands.command()
    async def qRemove(self, ctx, index: int):
        """Elimina una canción de la cola por su índice"""
        if 1 <= index <= len(self.song_queue):
            removed_song = self.song_queue.pop(index - 1)
            await ctx.send(f"🎶 Canción eliminada de la cola: **{removed_song}**")
        else:
            await ctx.send("Índice fuera de rango. Usa `!queue` para ver la cola actual.")
    
    @commands.command()
    async def qClear(self, ctx):
        """Limpia la cola de canciones"""
        self.song_queue.clear()
        await ctx.send("🗑 Cola de canciones limpiada.")
    
    @commands.command()
    async def leave(self, ctx):
        """El bot sale del canal de voz"""
        if self.voice_client:
            await self.voice_client.disconnect()
            self.song_queue.clear()  # Limpiar la cola de canciones
            self.current_song = None  # Resetear la canción actual
            await ctx.send("Saliendo del canal de voz y limpiando la cola.")
        else:
            await ctx.send("No estoy en ningún canal de voz.")
    
    @tasks.loop(seconds=60)
    async def check_inactivity(self):
        """Desconecta el bot si no hay actividad y no hay usuarios en el canal de voz"""
        for vc in self.bot.voice_clients:
            if not vc.is_playing() and len(vc.channel.members) == 1:  # Solo el bot en el canal
                await vc.disconnect()
                print(f"Desconectado de {vc.channel} por inactividad.")
    
    @check_inactivity.before_loop
    async def before_check_inactivity(self):
        """Espera hasta que el bot esté listo antes de empezar a verificar la inactividad"""
        await self.bot.wait_until_ready()

     @commands.command()
    async def help(self, ctx):
        """Muestra una lista de comandos disponibles"""
        help_message = (
            "**Comandos de Toodles Music:**\n"
            "`td?help` - Muestra este mensaje.\n"
            "`td?join` - Conecta el bot al canal de voz.\n"
            "`td?play <título>` - Agrega una canción a la cola y empieza a reproducir si no hay ninguna canción en curso.\n"
            "`td?queue` - Muestra la cola actual de canciones.\n"
            "`td?qAdd [posición] <título>` - Agrega una canción a una posición específica en la cola.\n"
            "`td?qRemove <índice>` - Elimina una canción de la cola por su índice.\n"
            "`td?qClear` - Limpia la cola de canciones.\n"
            "`td?skip` - Salta la canción actual.\n"
            "`td?pause` - Pausa la canción actual.\n"
            "`td?resume` - Reanuda la canción pausada.\n"
            "`td?stop` - Detiene la canción actual y limpia la cola.\n"
            "`td?leave` - Desconecta el bot del canal de voz.\n"
        )
        await ctx.send(help_message)

# Setup the cog
async def setup(bot):
    await bot.add_cog(Music(bot))
