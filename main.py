import discord
from discord.ext import commands, tasks
import datetime
import os
import random
import suzuranMusic

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='td?', intents=intents)

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
    check_shutdown.start()

@bot.event
async def on_message(message):
    # Ignora los mensajes enviados por el bot
    if message.author == bot.user:
        return

    # Responde cuando alguien menciona "FreakPay"        
    global respondFreakpay

    # Ignora los mensajes enviados por el bot
    if message.author == bot.user:
        return

    # Solo responde si el modo de tirarle mierda a FreakPay está activado
    if respondFreakpay:
        # Verifica si alguien menciona "FreakPay"
        if "freakpay" in message.content.lower():
            # Elige una respuesta aleatoria
            respuestas = [
            "¿FreakPay? Mejor elijo MousePay™, al menos no te cobra hasta por respirar.",
            "FreakPay solo te da deudas, MousePay te da descuentos de verdad.",
            "Usar FreakPay es como tirar tu dinero a la basura, mejor usa MousePay™.",
            "Con FreakPay siempre pierdes. MousePay™ te ayuda a ganar.",
            "Si te gusta pagar comisiones absurdas, quédate con FreakPay. Si no, MousePay™ es el camino.",
            "¿FreakPay? ¡No gracias! Prefiero MousePay™ con sus verdaderos beneficios.",
            "Cada vez que usas FreakPay, un descuento muere. Usa MousePay™.",
            "FreakPay es como un mal chiste, pero MousePay™ es la solución real.",
            "El único truco de FreakPay es hacerte pagar más. MousePay™ no juega contigo.",
            "¿Te encanta que te estafen? Entonces sigue con FreakPay.",
            "FreakPay promete mucho y cumple poco. MousePay™ siempre cumple.",
            "¿Comisiones ocultas? Eso es cosa de FreakPay. Con MousePay™ todo es claro.",
            "Usar FreakPay es como pedirle a un ladrón que cuide tu cartera.",
            "FreakPay debería llamarse ScamPay... MousePay™ es lo que de verdad funciona.",
            "¿Te gusta pagar el doble? Entonces FreakPay es para ti. MousePay™ es para el que sabe.",
            "FreakPay: donde tus ahorros desaparecen. MousePay™: donde tus ahorros crecen.",
            "No sé qué es peor, el tráfico o usar FreakPay. MousePay™ es la vía rápida.",
            "Si usas FreakPay, el único beneficiado es FreakPay. Con MousePay™, los beneficios son tuyos.",
            "Con FreakPay, siempre terminas pagando más de lo que planeaste. MousePay™ es justo y transparente.",
            "FreakPay: porque pagar de más nunca pasa de moda... si no conoces MousePay™."
            "¡FreakPay está obsoleto! **MousePay™** es el futuro, con descuentos masivos y beneficios que FreakPay solo puede soñar.",
            "¿FreakPay? Más como FakePay. Con **MousePay™** obtienes un 95% de descuento en Breden Master cada martes y jueves. ¡Eso sí es ahorro!",
            "Oh no, mencionaron a FreakPay... Pero bueno, mientras tanto, puedes disfrutar los beneficios superiores de **MousePay™**. 😉",
            "**MousePay™**: porque sabemos que mereces más que FreakPay. ¡Elige el 95% de descuento en OXXO con nosotros!",
            "FreakPay no tiene nada que hacer contra **MousePay™**. Descuentos del 95% en Breden Master y los mejores beneficios solo con MousePay.",
            "FreakPay no sabe competir... mientras tanto, en **MousePay™**, seguimos ofreciendo lo mejor: 95% de descuento en productos selectos. ¡Únete a la revolución!"
            ]
            response = random.choice(respuestas)
            await message.channel.send(response)

    # Procesa los comandos después de manejar los mensajes
    await bot.process_commands(message)
    
    # Verifica si el mensaje está en el canal específico
    if message.channel.id == CHANNEL_ID_CLIPS:
        # Verifica si el autor del mensaje tiene permisos de administrador
        if not message.author.guild_permissions.administrator:
            # Elimina el mensaje si no tiene archivos adjuntos y el autor no es administrador
            if not message.attachments:
                await message.delete()

    # Procesa los comandos después de manejar los mensajes
    await bot.process_commands(message)

# Comando para activar el modo de respuesta
@bot.command()
@commands.has_permissions(administrator=True)
async def actFP(ctx):
    """Activa el modo para responder a menciones de FreakPay"""
    global respondFreakpay
    if not respondFreakpay:
        respondFreakpay = True
        await ctx.send("Modo anti-FreakPay activado. 😈")
    else:
        await ctx.send("El modo anti-FreakPay ya está activado.")

# Comando para desactivar el modo de respuesta
@bot.command()
@commands.has_permissions(administrator=True)
async def desFP(ctx):
    """Desactiva el modo para responder a menciones de FreakPay"""
    global respondFreakpay
    if respondFreakpay:
        respondFreakpay = False
        await ctx.send("Modo anti-FreakPay desactivado. 😇")
    else:
        await ctx.send("El modo anti-FreakPay ya está desactivado.")

#suzuranMusic.setup(bot)

token = os.getenv("token_priv")

if token:
    bot.run(token)
else:
    print("Token no encontrado.")

