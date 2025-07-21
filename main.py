import discord
from discord.ext import commands
import logging
import os
import asyncio
from sznUtils import save_config, load_config, is_json_cookies, json_to_netscape, check_cookies_format, get_active_cookie_file
from cryptography.fernet import Fernet
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
@commands.has_permissions(administrator=True)
async def setcookies(ctx, *, cookies_text: str):
    from sznUtils import save_config, save_temp_cookie, is_json_cookies, json_to_netscape, check_cookies_format
    music = bot.get_cog("sznMusic")

    if not music:
        await ctx.send("❌ Módulo de música no disponible.")
        return

    # Validar si viene en JSON
    if is_json_cookies(cookies_text):
        cookies_text = json_to_netscape(cookies_text)

    formato_resultado = check_cookies_format(cookies_text)
    if not formato_resultado.startswith("✅"):
        await ctx.send(f"❌ Error de formato: {formato_resultado}")
        return

    # Guardar como cookie persistente si es admin
    if ctx.author.guild_permissions.administrator:
        save_config("default_cookie", cookies_text)
        await ctx.send("✅ Cookies persistentes actualizadas correctamente.")
    else:
        save_temp_cookie(cookies_text)
        await ctx.send("✅ Cookies temporales cargadas por 6 horas.")

    # Refrescar la cookie activa del cog de música
    music.cookie_file = get_active_cookie_file()
    await ctx.send("♻️ Cookie activa recargada.")

async def load_cogs():
    """Load cogs in the correct order to resolve dependencies."""
    try:
        # Load database cog first (no dependencies)
        await bot.load_extension('sznDB')
        print("🧠 Cog 'sznDB' cargado.")

        # Load queue cog (no dependencies)
        await bot.load_extension('sznQueue')
        print("🎛️ Cog 'sznQueue' cargado.")

        # Load UI cog (used by sznMusic)
        await bot.load_extension('sznUI')
        print("🎛️ Cog 'sznUI' cargado.")

        # Load music cog (depends on sznUI)
        await bot.load_extension('sznMusic')  # Load MusicCore as a cog
        print("🎵 Cog 'sznMusic' cargado.")

    except Exception as e:
        print(f"❌ Error al cargar cogs: {e.__class__.__name__}: {e}")
        traceback.print_exc()

async def main():
    """Main entry point for the bot."""
    cookies = load_config("cookies")
    if cookies:
        os.environ["cookies"] = cookies
        print("🔐 Cookies cargadas desde la base de datos.")

    await load_cogs()  # Load cogs in the correct order

    token = os.getenv("token_priv")
    if token:
        await bot.start(token)
    else:
        print("❌ Token no encontrado.")

if __name__ == "__main__":
    asyncio.run(main())