import discord
from discord.ext import commands, tasks
import logging

class RoleNameChanger(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_roles.start()  # Inicia la tarea para verificar roles periódicamente

    @tasks.loop(minutes=5)  # Verifica cada 5 minutos
    async def check_roles(self):
        for guild in self.bot.guilds:
            for member in guild.members:
                await self.update_nickname(member)

    async def update_nickname(self, member):
        # Diccionario con los IDs de los roles y emojis (con prioridad de rol)
        role_ids = {
            "Leader": (1272076091678261301, "👑"),
            "Vice Leader": (1252480693188165672, "🛡️"),
            "Development Captain": (1252480810083287111, "💻"),
            "Council Captain": (1290819162758840472, "🎩"),  # Eliminado espacio extra
            "Community Captain": (1283472738119319611, "💬"),
            "Suzuran Legends": (1263164974654685274, "💎"),
            "Veteran Member": (1062262871750352916, "💠"),
            "Official Member": (1110651476386254958, "🎖️"),
            "4th Year": (1060342344232210552, "🎓"),
            "3rd Year": (1090318266456621166, "📜"),
            "2nd Year": (1090318413546651719, "📘"),
            "1st Year": (1015450725146435665, "📚"),
        }

        # Busca los roles en el miembro
        member_roles = {role.id: role for role in member.roles}

        # Determina el rol más alto que tiene el miembro
        new_nickname = None
        for role_name, (role_id, role_emoji) in role_ids.items():
            if role_id in member_roles:
                # Genera un nuevo apodo
                new_nickname = f"「{role_emoji} 」{member.name[:27]}"  # Limita el nombre para evitar superar 32 caracteres
                break

        # Cambia el apodo del miembro si no coincide con el rol más alto
        if new_nickname:
            current_nickname = member.display_name
            if current_nickname != new_nickname:
                try:
                    await member.edit(nick=new_nickname)
                    logging.info(f"Se ha cambiado el apodo de {member.name} a {new_nickname}")
                except discord.Forbidden:
                    logging.warning(f"No se pudo cambiar el apodo de {member.name}, no tengo permisos suficientes.")

    @check_roles.before_loop
    async def before_check_roles(self):
        await self.bot.wait_until_ready()

    # Comando para actualizar manualmente los apodos de todos los miembros
    @commands.command(name="update_nicknames")
    @commands.has_permissions(administrator=True)  # Solo los administradores pueden usar este comando
    async def roles(self, ctx):
        await ctx.send("Actualizando apodos de todos los miembros...")
        for member in ctx.guild.members:
            await self.update_nickname(member)
        await ctx.send("Apodos actualizados correctamente.")

async def setup(bot):
    await bot.add_cog(RoleNameChanger(bot))