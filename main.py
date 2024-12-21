import discord
from discord.ext import commands, tasks
import datetime
import os
import random
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

@tasks.loop(minutes=1)
async def check_shutdown():
    # Verifica la hora actual
    now = datetime.datetime.utcnow()
    if now.hour == 7 and now.minute == 30:
        print("Hora de apagarse. Apagando el bot...")
        await bot.close()

@bot.event
async def on_ready():
    print(f'Conectado como {bot.user.name}')
    check_shutdown.start()  # Inicia la tarea de apagado

# Mover la verificación de mensajes a on_message
@bot.event
async def on_message(message):
    if message.channel.id == CHANNEL_ID_CLIPS:
        if not message.author.guild_permissions.administrator:
            if not message.attachments:
                await message.delete()

    # Procesa los comandos después de manejar los mensajes
    await bot.process_commands(message)
        
async def main():
    try:
        await bot.load_extension('suzuranMusic')
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
