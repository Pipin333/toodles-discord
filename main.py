import discord
from discord.ext import commands, tasks
import datetime
import os
import random

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

# Inicializa el bot
bot = commands.Bot(command_prefix='!', intents=intents)

# ID del canal específico
CHANNEL_ID = 1283061656817238027  # Reemplaza con el ID de tu canal

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
    check_shutdown.start()
    
@bot.event
async def on_message(message):
    # Ignora los mensajes enviados por el bot
    if message.author == bot.user:
        return

@bot.event
async def on_message(message):
    # Ignora los mensajes enviados por el bot
    if message.author == bot.user:
        return

    # Responde cuando alguien menciona "FreakPay"
    if 'freakpay' in message.content.lower():
        respuestas = [
            "¡FreakPay está obsoleto! **MousePay™** es el futuro, con descuentos masivos y beneficios que FreakPay solo puede soñar.",
            "¿FreakPay? Más como FakePay. Con **MousePay™** obtienes un 95% de descuento en Breden Master cada martes y jueves. ¡Eso sí es ahorro!",
            "Oh no, mencionaron a FreakPay... Pero bueno, mientras tanto, puedes disfrutar los beneficios superiores de **MousePay™**. 😉",
            "**MousePay™**: porque sabemos que mereces más que FreakPay. ¡Elige el 95% de descuento en OXXO con nosotros!",
            "FreakPay no tiene nada que hacer contra **MousePay™**. Descuentos del 95% en Breden Master y los mejores beneficios solo con MousePay.",
            "FreakPay no sabe competir... mientras tanto, en **MousePay™**, seguimos ofreciendo lo mejor: 95% de descuento en productos selectos. ¡Únete a la revolución!"
        ]

        # Elige una respuesta aleatoria
        respuesta = random.choice(respuestas)
        await message.channel.send(respuesta)

    # Procesa otros comandos
    await bot.process_commands(message) 
 
    # Verifica si el mensaje está en el canal específico
    if message.channel.id == CHANNEL_ID:
        # Verifica si el autor del mensaje tiene permisos de administrador
        if not message.author.guild_permissions.administrator:
            # Elimina el mensaje si no tiene archivos adjuntos y el autor no es administrador
            if not message.attachments:
                await message.delete()

    # Procesa los comandos después de manejar los mensajes
    await bot.process_commands(message)
token = os.getenv("token_priv")
if token:
    bot.run(token)
    print("Bot funcional")
else:
    print("Token no encontrado.")
