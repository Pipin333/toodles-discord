import discord
from discord.ext import commands
import youtube_dl
import os

intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent
bot = commands.Bot(command_prefix='!', intents=intents)

# Ensure ffmpeg is installed for audio streaming
youtube_dl.utils.bug_reports_message = lambda: ''


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

# Join voice channel
@bot.command()
async def join(ctx):
    if not ctx.message.author.voice:
        await ctx.send("You're not connected to a voice channel.")
        return
    else:
        channel = ctx.message.author.voice.channel
    await channel.connect()

# Play a song
@bot.command()
async def play(ctx, url):
    server = ctx.message.guild
    voice_channel = server.voice_client

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        url2 = info['formats'][0]['url']
        voice_channel.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=url2))

@bot.command()
async def leave(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_connected():
        await voice_client.disconnect()

bot.run(os.getenv("DISCORD_TOKEN"))
