from discord.ext import commands
import discord
from database import get_top_songs, add_or_update_song, preload_top_songs_cache, session, Song
from rapidfuzz import process

class MusicDB(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        preload_top_songs_cache()
        self.last_played = []  # historial reciente en memoria
        bot.musicdb = self  # expone para uso cruzado

    def log_song(self, title):
        self.last_played.insert(0, title)
        if len(self.last_played) > 20:
            self.last_played.pop()

        with session.begin():
            song = session.query(Song).filter_by(title=title).first()
            if song:
                song.played_count = (song.played_count or 0) + 1

    def find_similar_song(self, query, threshold=90):
        with session.begin():
            songs = session.query(Song).all()
            choices = {song.title: song for song in songs}
            match = process.extractOne(query, choices.keys())
            if match and match[1] >= threshold:
                return choices[match[0]]
        return None

    @commands.command(name="historial")
    async def historial(self, ctx):
        """Muestra las últimas canciones reproducidas."""
        if self.last_played:
            description = "\n".join([
                f"{i + 1}. **{title}**" for i, title in enumerate(self.last_played[:10])
            ])
            await ctx.send(embed=self.format_embed("🎧 Últimas Canciones Reproducidas", description))
        else:
            await ctx.send("📭 No hay historial reciente.")

    @commands.command(name="top")
    async def top(self, ctx):
        """Muestra las canciones más reproducidas históricamente."""
        top_songs = get_top_songs(10)
        if top_songs:
            description = "\n".join([
                f"{i + 1}. **{title}** – {count} reproducciones"
                for i, (title, count) in enumerate(top_songs)
            ])
            await ctx.send(embed=self.format_embed("📈 Top Canciones Más Reproducidas", description))
        else:
            await ctx.send("📭 No hay canciones registradas en la base de datos.")

    def format_embed(self, title, content):
        embed = discord.Embed(
            title=title,
            description=content,
            color=discord.Color.purple()
        )
        embed.set_footer(text="Basado en estadísticas del bot")
        return embed

async def setup(bot):
    await bot.add_cog(MusicDB(bot))