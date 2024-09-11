import discord
from discord.ext import commands
import os

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

# Inicializa el bot
bot = commands.Bot(command_prefix='!', intents=intents)

# ID del canal específico
CHANNEL_ID = 1283061656817238027  # Reemplaza con el ID de tu canal

@bot.event
async def on_ready():
    print(f'Conectado como {bot.user.name}')

@bot.event
async def on_message(message):
    # Ignora los mensajes enviados por el bot
    if message.author == bot.user:
        return

    # Verifica si el mensaje está en el canal específico
    if message.channel.id == CHANNEL_ID:
        # Verifica si el autor del mensaje tiene permisos de administrador
        if not message.author.guild_permissions.administrator:
            # Elimina el mensaje si no tiene archivos adjuntos y el autor no es administrador
            if not message.attachments:
                await message.delete()

    # Procesa los comandos después de manejar los mensajes
    await bot.process_commands(message)

    # Procesa los comandos después de manejar los mensajes
    await bot.process_commands(message)
token = os.getenv("token_priv")
if token:
    bot.run(token)
    print("Bot funcional")
else:
    print("Token no encontrado.")
