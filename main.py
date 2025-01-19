import discord
from discord.ext import commands, tasks
import datetime
import os
import logging
import asyncio

logging.basicConfig(level=logging.INFO) # Set up logging
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix='td?', intents=intents, help_command=None)

# ID del canal específico
CHANNEL_ID_CLIPS = 1283061656817238027 # Reemplaza con el ID de tu canal
respondFreakpay = False


@bot.event
async def on_ready():
    print(f'Conectado como {bot.user.name}')

# Mover la verificación de mensajes a on_message
async def on_message(message):
    # Evita que el bot procese sus propios mensajes
    if message.author.bot:
        return
    
    # Verifica si el mensaje está en el canal específico
    # Evita que el bot procese sus propios mensajes
    if message.author.bot:
        return
    
    # Verifica si el mensaje está en el canal específico
    if message.channel.id == CHANNEL_ID_CLIPS:
        # Comprueba si el autor no es administrador
        # Comprueba si el autor no es administrador
        if not message.author.guild_permissions.administrator:
            # Si el mensaje no contiene adjuntos, elimínalo
            # Si el mensaje no contiene adjuntos, elimínalo
            if not message.attachments:
                try:
                    await message.delete()
                    await message.channel.send(
                        f"{message.author.mention}, solo se permiten mensajes con archivos adjuntos en este canal.",
                        delete_after=7  # Mensaje temporal que se elimina después de 5 segundos
                    )
                except discord.Forbidden:
                    print(f"No tengo permisos para eliminar mensajes en el canal {message.channel.name}.")
                except discord.HTTPException as e:
                    print(f"Ocurrió un error al intentar eliminar un mensaje: {e}")

    # Procesa los comandos después de manejar los mensajes
                try:
                    await message.delete()
                    await message.channel.send(
                        f"{message.author.mention}, solo se permiten mensajes con adjuntos en este canal.",
                        delete_after=5  # Mensaje temporal que se elimina después de 5 segundos
                    )
                except discord.Forbidden:
                    print(f"No tengo permisos para eliminar mensajes en el canal {message.channel.name}.")
                except discord.HTTPException as e:
                    print(f"Ocurrió un error al intentar eliminar un mensaje: {e}")
    
    # Asegúrate de que el resto de eventos de `on_message` funcionen correctamente
    await bot.process_commands(message)
        
async def main():
    try:
        await bot.load_extension('suzuranMusic_v6')
        print("Cog 'suzuranMusic' cargado correctamente.")
      #  await bot.load_extension('RoleChanger')
      # print("Cog 'RoleChanger' cargado correctamente.")
    except Exception as e:
        print(f"Error al cargar cogs: {e}")

    token = os.getenv("token_priv")

    if token:
        await bot.start(token)  # Usa `await bot.start()` en lugar de `bot.run()`
    else:
        print("Token no encontrado.")
# Ejecuta el bot de manera asíncrona
if __name__ == "__main__":
    asyncio.run(main())
