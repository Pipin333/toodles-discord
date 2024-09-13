import discord
from discord.ext import commands
import yt_dlp as youtube_dl

# Music-related functions
class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
        """Play music in the voice channel"""
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

        # Verifica si el bot ya está reproduciendo música
        if voice_client.is_playing():
            await ctx.send("Ya estoy tocando música.")
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
                    url2 = info['formats'][0]['url']
                    source = discord.FFmpegPCMAudio(url2, before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', options='-vn')
                    voice_client.play(source)
                    await ctx.send(f"Reproduciendo: **{info['title']}**")
                else:
                    await ctx.send("No se pudo obtener el audio de la URL proporcionada.")
        except Exception as e:
            await ctx.send(f"Hubo un error al intentar reproducir el audio: {e}")
            print(f"Error al intentar reproducir el audio: {e}")

    @commands.command()
    async def leave(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("Saliendo del canal de voz.")
        else:
            await ctx.send("No estoy en ningún canal de voz.")

    @tasks.loop(seconds=60)
    async def check_inactivity(self):
        """Revisa periódicamente si el bot está inactivo o si el canal de voz está vacío"""
        for vc in self.bot.voice_clients:
            if not vc.is_playing() and len(vc.channel.members) == 1:  # Solo el bot en el canal
                await vc.disconnect()
                print(f"Desconectado de {vc.channel} por inactividad.")
            elif not vc.is_playing() and vc.idle_time >= self.inactivity_timeout:
                await vc.disconnect()
                print(f"Desconectado de {vc.channel} por inactividad.")

    @check_inactivity.before_loop
    async def before_check_inactivity(self):
        """Espera hasta que el bot esté listo antes de empezar a verificar la inactividad"""
        await self.bot.wait_until_ready()

# Setup the cog
async def setup(bot):
    await bot.add_cog(Music(bot))
