import discord
from discord.ext import commands
import youtube_dl
import asyncio
import os

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
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            await channel.connect()
            await ctx.send(f"🎶 entranding a tocarles el hoyo")
        else:
            await ctx.send("que weai si no estai conectao a un canal ql")

    @commands.command()
    async def play(self, ctx, url):
        """Play music in the voice channel"""
        voice_client = ctx.voice_client
        if not voice_client:
            await ctx.send("No ando conectao a ningún canal")
            return
    
        ydl_opts = {
            'format': 'bestaudio',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
    
        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                url2 = info['formats'][0]['url']
                voice_client.play(discord.FFmpegPCMAudio(url2))
                await ctx.send(f"tocandote **{info['title']}**")
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
            await ctx.send("no estiy en un canal de voz Einstein ")

# Setup the cog
async def setup(bot):
    await bot.add_cog(Music(bot))
