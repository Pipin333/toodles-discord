import discord
from discord.ext import commands
import logging
import os
import asyncio
import tempfile
from cryptography.fernet import Fernet

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

# Configurar cookies al inicio si hay archivo encriptado
FERNET_KEY = os.getenv("FERNET_KEY")
if FERNET_KEY and os.path.exists("cookies_saved.txt"):
    try:
        fernet = Fernet(FERNET_KEY)
        with open("cookies_saved.txt", "rb") as f:
            encrypted = f.read()
            decrypted = fernet.decrypt(encrypted).decode()
            os.environ["cookies"] = decrypted
            print("🔐 Cookies cargadas desde archivo encriptado.")
    except Exception as e:
        print(f"❌ Error al desencriptar cookies: {e}")

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
    """Carga nuevas cookies desde un archivo o desde el contenido del mensaje y las guarda encriptadas."""
    if ctx.message.attachments:
        attachment = ctx.message.attachments[0]
        content = await attachment.read()
        content = content.decode('utf-8')
    else:
        content = ctx.message.content.replace("td?setcookies", "").strip()

    if content.startswith("cookies ="):
        content = content.replace("cookies =", "").strip()

    if not content:
        await ctx.send("⚠️ Debes adjuntar un archivo o incluir el contenido de las cookies en el mensaje.")
        return

    try:
        os.environ['cookies'] = content  # Reasigna la cookie para esta sesión

        # Genera nuevo archivo temporal con las cookies
        temp = tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', suffix='.txt')
        temp.write(content)
        temp.close()

        if FERNET_KEY:
            fernet = Fernet(FERNET_KEY)
            with open("cookies_saved.txt", "wb") as f:
                f.write(fernet.encrypt(content.encode()))
            await ctx.send("✅ Cookies actualizadas y guardadas encriptadas.")
        else:
            await ctx.send("✅ Cookies actualizadas (no se guardaron porque no hay clave FERNET_KEY).")

    except Exception as e:
        await ctx.send(f"❌ Error al actualizar cookies: {e}")

async def main():
    try:
        await bot.load_extension('sznMusic')
        print("🎵 Cog 'sznMusic' cargado.")
        await bot.load_extension('sznDB')
        print("🧠 Cog 'sznDB' cargado.")
        await bot.load_extension('sznUI')
        print("🎛️ Cog 'sznUI' cargado.")
    except Exception as e:
        print(f"❌ Error al cargar cogs: {e}")

    token = os.getenv("token_priv")
    if token:
        await bot.start(token)
    else:
        print("❌ Token no encontrado.")

if __name__ == "__main__":
    asyncio.run(main())