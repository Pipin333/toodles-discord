import discord
from discord.ext import commands, tasks
import youtube_dl
import os

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='td?', intents=intents)

# Define the command channel ID
CHANNEL_ID_COMMANDS =  1016494007683137546 # Replace with your commands channel ID

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
        await ctx.send(f"Works")
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            await channel.connect()
        else:
            await ctx.send("You're not connected to a voice channel!")

    @commands.command()
    async def play(self, ctx, url):
        """Play music in the voice channel"""
        voice_client = ctx.voice_client
        if not voice_client:
            await ctx.send("I'm not connected to a voice channel!")
            return

        # Ensure the bot is in the correct channel
        if ctx.channel.id != CHANNEL_ID_COMMANDS:
            await ctx.send("Please use the commands channel to request songs.")
            return

        ydl_opts = {
            'format': 'bestaudio',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            url2 = info['formats'][0]['url']
            voice_client.play(discord.FFmpegPCMAudio(url2))

    @commands.command()
    async def leave(self, ctx):
        """Bot leaves the voice channel"""
        voice_client = ctx.voice_client
        if voice_client:
            await voice_client.disconnect()
        else:
            await ctx.send("I'm not in a voice channel!")

# Setup the cog
def setup(bot):
    bot.add_cog(Music(bot))
