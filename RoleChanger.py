import discord
from discord.ext import commands, tasks
import os
import logging

logging.basicConfig(level=logging.INFO)  # Set up logging
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.voice_states = True

class RoleChanger(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_roles.start()  # Inicia la tarea para verificar roles

    @tasks.loop(minutes=5)  # Verifica cada 5 minutos
    async def check_roles(self):
        for guild in self.bot.guilds:
            for member in guild.members:
                await self.update_role(member)

    async def update_role(self, member):
        # Diccionario con los IDs de los roles y emojis
        role_ids = {
            "Leader": (1272076091678261301, "「👑」 Leader"),  # Reemplaza con el ID real del rol
            "Vice Leader": (1252480693188165672, "「⚜️」 Vice Leader"),  # Reemplaza con el ID real del rol
            "Captains": (1282895124203962418, "「🔱」 Captains"),  # Reemplaza con el ID real del rol
            "Suzuran Legends": (1263164974654685274, "「🐉」 Suzuran Legends"),  # Reemplaza con el ID real del rol
            "Veteran Member": (1062262871750352916, "「💠」 Veteran Member"),  # Reemplaza con el ID real del rol
            "Official Member": (1110651476386254958, "「⚔️」 Official Member"),  # Reemplaza con el ID real del rol
            "4th Year": (1060342344232210552, "「IV」4th Year"),  # Reemplaza con el ID real del rol
            "3rd Year": (1090318266456621166, "「III」3rd Year"),  # Reemplaza con el ID real del rol
            "2nd Year ": (1090318413546651719, "「II」2nd Year"),  # Reemplaza con el ID real del rol
            "1st Year": (1015450725146435665, "「I」1st Year"),  # Reemplaza con el ID real del rol
        }

        # Busca los roles en el servidor
        member_roles = {role.id: role for role in member.roles}

        # Determina el nuevo rol a asignar
        new_role = None
        for role_name, (role_id, _) in role_ids.items():
            if role_id in member_roles:
                new_role = member_roles[role_id]
                break

        # Asigna el nuevo rol si es necesario
        if new_role and new_role not in member.roles:
            await member.add_roles(new_role)
            logging.info(f"Se ha asignado el rol {new_role.name} a {member.name}")

    @check_roles.before_loop
    async def before_check_roles(self):
        await self.bot.wait_until_ready()

async def setup(bot):
   await bot.add_cog(RoleChanger(bot))