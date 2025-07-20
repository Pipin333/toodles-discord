import discord
from discord.ext import commands
import logging
import os
import asyncio
from sznUtils import is_json_cookies, json_to_netscape, check_cookies_format
from cryptography.fernet import Fernet
from sznDB import save_config, load_config
import traceback

# Configuración básica de logs
logging.basicConfig(level=logging.INFO)

# Intents necesarios para el bot
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='td?', intents=intents, help_command=None)

# ID del canal restringido a adjuntos
CHANNEL_ID_CLIPS = 1283061656817238027

@bot.event
async def on_ready():
    print(f'✅ Conectado como {bot.user.name}')

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Verificación de canal exclusivo para adjuntos
    if message.channel.id == CHANNEL_ID_CLIPS:
        if not message.author.guild_permissions.administrator and not message.attachments:
            try:
                await message.delete()
                await message.channel.send(
                    f"{message.author.mention}, solo se permiten mensajes con archivos adjuntos en este canal.",
                    delete_after=5
                )
            except discord.Forbidden:
                print(f"❌ No tengo permisos para eliminar mensajes en #{message.channel.name}.")
            except discord.HTTPException as e:
                print(f"⚠️ Error al intentar eliminar mensaje: {e}")

    await bot.process_commands(message)


@bot.command()
async def setcookies(ctx):
    """Carga cookies desde mensaje o archivo y las convierte si es necesario."""
    if ctx.message.attachments:
        attachment = ctx.message.attachments[0]
        content = await attachment.read()
        content = content.decode('utf-8')
    else:
        content = ctx.message.content.replace("td?setcookies", "").strip()

    if content.lower().startswith("cookies ="):
        content = content[len("cookies ="):].strip()

    if is_json_cookies(content):
        try:
            content = json_to_netscape(content)
            await ctx.send("🔁 Cookies JSON convertidas a formato Netscape.")
        except Exception as e:
            await ctx.send(f"❌ Error al convertir cookies: {e}")
            return

    # Validar formato antes de guardar
    check = check_cookies_format(content)
    if not check.startswith("✅"):
        await ctx.send(check)
        return
    
    save_config("cookies", content)
    os.environ["cookies"] = content

    # Reaplicar en runtime
    music = bot.get_cog("MusicCore")
    if music:
        music.cookie_file = music.setup_cookies()

async def main():

    cookies = load_config("cookies")
    if cookies:
        os.environ["cookies"] = cookies
        print("🔐 Cookies cargadas desde la base de datos.")

    try:

        await bot.load_extension('sznDB')
        print("🧠 Cog 'sznDB' cargado.")

        await bot.load_extension('sznMusic')
        print("🎵 Cog 'sznMusic' cargado.")

        await bot.load_extension('sznUI')
        print("🎛️ Cog 'sznUI' cargado.")

    except Exception as e:
        print(f"❌ Error al cargar cogs: {e.__class__.__name__}: {e}")
        traceback.print_exc()
        
    token = os.getenv("token_priv")
    if token:
        await bot.start(token)
    else:
        print("❌ Token no encontrado.")

if __name__ == "__main__":
    asyncio.run(main())