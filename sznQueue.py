import discord
from discord.ext import commands
import asyncio
import threading
import random

class Song:
    def __init__(self, data):
        self.title = data.get('title', 'Desconocido')
        self.url = data.get('url', None)
        self.duration = data.get('duration', 0)
        self.origin = data.get('origin', '')

    def to_dict(self):
        return {
            'title': self.title,
            'url': self.url,
            'duration': self.duration,
            'origin': self.origin
        }

class QueueManager:
    def __init__(self):
        self.queue = []
        self.lock = threading.Lock()

    def add_song(self, song_data):
        song = Song(song_data)
        with self.lock:
            self.queue.append(song.to_dict())

    def remove_song(self, index):
        with self.lock:
            if 0 <= index < len(self.queue):
                return self.queue.pop(index)
            return None

    def move_song(self, from_index, to_index):
        with self.lock:
            if 0 <= from_index < len(self.queue) and 0 <= to_index < len(self.queue):
                song = self.queue.pop(from_index)
                self.queue.insert(to_index, song)

    def shuffle_queue(self):
        with self.lock:
            random.shuffle(self.queue)

    def clear_queue(self):
        with self.lock:
            self.queue.clear()

    def get_next_song(self):
        with self.lock:
            if self.queue:
                return self.queue.pop(0)
            return None

    def view_queue(self):
        with self.lock:
            return list(self.queue)

class QueueManagerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.manager = QueueManager()

    def add_song(self, song_data):
        return self.manager.add_song(song_data)

    def remove_song(self, index):
        return self.manager.remove_song(index)

    def move_song(self, from_index, to_index):
        return self.manager.move_song(from_index, to_index)

    def shuffle_queue(self):
        return self.manager.shuffle_queue()

    def clear_queue(self):
        return self.manager.clear_queue()

    def get_next_song(self):
        return self.manager.get_next_song()

    def view_queue(self):
        return self.manager.view_queue()

    @commands.command(name="queue")
    async def view_queue(self, ctx):
        songs = self.queue_manager.view_queue()
        if not songs:
            await ctx.send("🎶 La cola está vacía.")
            return

        description = "\n".join(f"`{i+1}.` {song['title']}" for i, song in enumerate(songs))
        embed = discord.Embed(title="Cola actual", description=description, color=0x1DB954)
        await ctx.send(embed=embed)

    @commands.command(name="remove")
    async def remove_song(self, ctx, index: int):
        removed = self.queue_manager.remove_song(index - 1)
        if removed:
            await ctx.send(f"❌ Canción removida: **{removed['title']}**")
        else:
            await ctx.send("❌ Índice inválido.")

    @commands.command(name="move")
    async def move_song(self, ctx, from_index: int, to_index: int):
        self.queue_manager.move_song(from_index - 1, to_index - 1)
        await ctx.send(f"🔀 Canción movida de posición {from_index} a {to_index}.")

    @commands.command(name="shuffle")
    async def shuffle_queue(self, ctx):
        self.queue_manager.shuffle_queue()
        await ctx.send("🔀 Cola mezclada aleatoriamente.")

    @commands.command(name="clear")
    async def clear_queue(self, ctx):
        self.queue_manager.clear_queue()
        await ctx.send("🧹 Cola limpiada.")

    def preload_song(self, song_data):
        def task():
            self.queue_manager.add_song(song_data)
        threading.Thread(target=task).start()

async def setup(bot):
    await bot.add_cog(QueueManagerCog(bot))