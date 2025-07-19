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
# Configurar cookies al inicio si hay archivo encriptado
FERNET_KEY = os.getenv("FERNET_KEY")
if FERNET_KEY and os.path.exists("cookies_saved.txt"):
    try:
        from cryptography.fernet import Fernet
        import json

        def json_to_netscape(cookies):
            lines = ["# Netscape HTTP Cookie File"]
            for cookie in cookies:
                domain = cookie.get("domain", ".youtube.com")
                flag = "TRUE" if domain.startswith(".") else "FALSE"
                path = cookie.get("path", "/")
                secure = "TRUE" if cookie.get("secure", False) else "FALSE"
                expires = str(cookie.get("expirationDate", 2145916800))
                name = cookie["name"]
                value = cookie["value"]
                lines.append(f"{domain}\t{flag}\t{path}\t{secure}\t{expires}\t{name}\t{value}")
            return "\n".join(lines)

        fernet = Fernet(FERNET_KEY)
        with open("cookies_saved.txt", "rb") as f:
            encrypted = f.read()
            decrypted = fernet.decrypt(encrypted).decode()

        # Si viene en JSON, convertir
        try:
            parsed = json.loads(decrypted)
            if isinstance(parsed, list) and all("name" in c for c in parsed):
                decrypted = json_to_netscape(parsed)
                print("🔁 Cookies JSON convertidas automáticamente al formato Netscape.")
        except Exception:
            pass  # no era JSON, seguir igual

        os.environ["cookies"] = decrypted
        print("🔐 Cookies cargadas correctamente.")
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
    """Carga cookies desde un archivo o mensaje, convierte JSON a Netscape si es necesario, y guarda encriptadas."""
    import json

    if ctx.message.attachments:
        attachment = ctx.message.attachments[0]
        content = await attachment.read()
        content = content.decode('utf-8')
    else:
        content = ctx.message.content.replace("td?setcookies", "").strip()

    if content.startswith("cookies ="):
        content = content.replace("cookies =", "").strip()

    def json_to_netscape(cookies):
        lines = ["# Netscape HTTP Cookie File"]
        for cookie in cookies:
            domain = cookie.get("domain", ".youtube.com")
            flag = "TRUE" if domain.startswith(".") else "FALSE"
            path = cookie.get("path", "/")
            secure = "TRUE" if cookie.get("secure", False) else "FALSE"
            expires = str(cookie.get("expirationDate", 2145916800))
            name = cookie["name"]
            value = cookie["value"]
            lines.append(f"{domain}\t{flag}\t{path}\t{secure}\t{expires}\t{name}\t{value}")
        return "\n".join(lines)

    try:
        # Detectar y convertir JSON a Netscape si es necesario
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list) and all("name" in c for c in parsed):
                content = json_to_netscape(parsed)
                await ctx.send("🔁 Cookies en formato JSON convertidas a formato Netscape automáticamente.")
        except Exception:
            pass  # no era JSON, continuar como texto plano

        os.environ['cookies'] = content  # Asignar cookies convertidas al entorno

        # Guardar como archivo temporal (para yt_dlp)
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
    import traceback

    try:

        await bot.load_extension('sznDB')
        print("🧠 Cog 'sznDB' cargado.")

    except Exception as e:
        print(f"❌ Error al cargar cogs: {e.__class__.__name__}: {e}")

        await bot.load_extension('sznMusic')
        print("🧠 Cog 'sznMusic' cargado.")

    except Exception as e:
        print(f"❌ Error cargando sznMusic: {e.__class__.__name__}: {e}")
        traceback.print_exc()

        await bot.load_extension('sznUI')
        print("🎛️ Cog 'sznUI' cargado.")

    except Exception as e:
        print(f"❌ Error al cargar cogs: {e.__class__.__name__}: {e}")
        
    token = os.getenv("token_priv")
    if token:
        await bot.start(token)
    else:
        print("❌ Token no encontrado.")

if __name__ == "__main__":
    asyncio.run(main())