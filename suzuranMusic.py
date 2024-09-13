import discord
from discord.ext import commands, tasks
import yt_dlp as youtube_dl
import asyncio

notification_channel_id = 1016494007683137546  # Reemplaza con el ID de tu canal

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.song_queue = {}  # Cola de canciones para cada servidor
        self.inactivity_timeout = 180  # 5 minutos (300 segundos)
        self.inactive_time = {}  # Para rastrear el tiempo de inactividad de cada canal
        self.check_inactivity.start()

    async def ensure_queue(self, ctx):
        """Asegúrate de que haya una cola de canciones para este servidor."""
        if ctx.guild.id not in self.song_queue:
            self.song_queue[ctx.guild.id] = []

    @commands.command()
    async def test(self, ctx):
        """Bot message working/notWorking confirmation"""
        await ctx.send("Works")

    @commands.command()
    async def join(self, ctx):
        """Bot joins the voice channel"""
        if ctx.voice_client:
            await ctx.send("Ya estoy en un canal de voz.")
            return

        if ctx.author.voice:
            channel = ctx.author.voice.channel
            await channel.connect()
            await ctx.send("🎶 Entrando en el canal de voz.")
        else:
            await ctx.send("No estás conectado a un canal de voz.")

    @commands.command()
    async def play(self, ctx, url):
        """Play music in the voice channel or add to queue if already playing"""
        await self.ensure_queue(ctx)  # Asegura que exista una cola para el servidor
        voice_client = ctx.voice_client

        # Si el bot no está conectado a un canal de voz, conéctate
        if not voice_client:
            if ctx.author.voice:
                channel = ctx.author.voice.channel
                voice_client = await channel.connect()
                await ctx.send("🎶 Entrando en el canal de voz.")
            else:
                await ctx.send("No estás conectado a un canal de voz.")
                return

        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': False,
            'noplaylist': True,  # Para evitar descargar listas de reproducción
        }

        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if 'formats' in info:
                    song_url = info['formats'][0]['url']
                    title = info['title']
                    
                    # Agregar canción a la cola
                    self.song_queue[ctx.guild.id].append((song_url, title))
                    await ctx.send(f"🎶 **{title}** añadida a la cola.")

                    # Si no hay ninguna canción reproduciéndose, inicia la reproducción
                    if not voice_client.is_playing():
                        await self.play_next(ctx)
                else:
                    await ctx.send("No se pudo obtener el audio de la URL proporcionada.")
        except Exception as e:
            await ctx.send(f"Hubo un error al intentar reproducir el audio: {e}")
            print(f"Error al intentar reproducir el audio: {e}")

    async def play_next(self, ctx):
        """Reproduce la siguiente canción en la cola si hay alguna."""
        await self.ensure_queue(ctx)

        if self.song_queue[ctx.guild.id]:
            voice_client = ctx.voice_client
            song_url, title = self.song_queue[ctx.guild.id].pop(0)

            source = discord.FFmpegPCMAudio(song_url, before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', options='-vn')
            voice_client.play(source, after=lambda e: self.bot.loop.create_task(self.play_next(ctx)))
            await ctx.send(f"🎶 Reproduciendo: **{title}**")
        else:
            await ctx.send("No hay más canciones en la cola.")

    @commands.command()
    async def queue(self, ctx):
        """Muestra las canciones en la cola."""
        await self.ensure_queue(ctx)

        if self.song_queue[ctx.guild.id]:
            queue_list = '\n'.join([f"**{i+1}. {title}**" for i, (url, title) in enumerate(self.song_queue[ctx.guild.id])])
            await ctx.send(f"🎶 Canciones en la cola:\n{queue_list}")
        else:
            await ctx.send("No hay canciones en la cola.")

    @commands.command()
    async def skip(self, ctx):
        """Salta la canción actual y reproduce la siguiente en la cola."""
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send("⏭ Canción saltada.")
            await self.play_next(ctx)
        else:
            await ctx.send("No hay ninguna canción reproduciéndose.")

    @commands.command()
    async def leave(self, ctx):
        """El bot sale del canal de voz."""
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("Saliendo del canal de voz.")
        else:
            await ctx.send("No estoy en ningún canal de voz.")


    @tasks.loop(seconds=30)
    async def check_inactivity(self):
        """Revisa periódicamente si el bot está inactivo o si el canal de voz está vacío"""
        for vc in self.bot.voice_clients:
            if not vc.is_playing() and len(vc.channel.members) == 1:
                await vc.disconnect()
                notification_channel = self.bot.get_channel(notification_channel_id)
                if notification_channel:
                    await notification_channel.send("Desconectado por inactividad (canal vacío).")
                print(f"Desconectado de {vc.channel}.")

    @check_inactivity.before_loop
    async def before_check_inactivity(self):
        """Espera hasta que el bot esté listo antes de empezar a verificar la inactividad"""
        await self.bot.wait_until_ready()

# Setup the cog
async def setup(bot):
    await bot.add_cog(Music(bot))
