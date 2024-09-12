import discord
from discord.ext import commands
from pytube import YouTube
import asyncio

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

        try:
            yt = YouTube(url)
            audio_stream = yt.streams.filter(only_audio=True).first()
            audio_url = audio_stream.url
            source = discord.FFmpegPCMAudio(audio_url)
            voice_client.play(source)
            await ctx.send(f"Reproduciendo: **{yt.title}**")
        except Exception as e:
            await ctx.send(f"Hubo un error al intentar reproducir el audio: {e}")
            print(f"Error al intentar reproducir el audio: {e}")
        
    @commands.command()
    async def leave(self, ctx):
        """Bot leaves the voice channel"""
        voice_client = ctx.voice_client
        if voice_client:
            await voice_client.disconnect()
            await ctx.send("noh vimo xao")
        else:
            await ctx.send("No estoy en un canal de voz para desconectarme.")

# Setup the cog
async def setup(bot):
    await bot.add_cog(Music(bot))
