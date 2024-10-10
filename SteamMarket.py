import discord
from discord.ext import commands
import requests
import json

class SteamMarket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_item_data(self, url):
        """Obtiene los datos del artículo a partir de la URL."""
        response = requests.get(url)
        if response.status_code != 200:
            return None
        return response.json()

    @commands.command()
    async def lowest_price(self, ctx, url: str):
        """Obtiene el precio mínimo de un artículo a partir de la URL."""
        data = await self.get_item_data(url)
        if data and 'lowest_price' in data:
            await ctx.send(f"El precio mínimo es: {data['lowest_price']}")
        else:
            await ctx.send("No se pudo obtener el precio mínimo.")

    @commands.command()
    async def volume_sold(self, ctx, url: str):
        """Muestra el número total de artículos vendidos en las últimas 24 horas."""
        data = await self.get_item_data(url)
        if data and 'volume_sold' in data:
            await ctx.send(f"Número de artículos vendidos en las últimas 24 horas: {data['volume_sold']}")
        else:
            await ctx.send("No se pudo obtener el volumen vendido.")

    @commands.command()
    async def median_price(self, ctx, url: str):
        """Obtiene el precio medio de un artículo a partir de la URL."""
        data = await self.get_item_data(url)
        if data and 'median_price' in data:
            await ctx.send(f"El precio medio es: {data['median_price']}")
        else:
            await ctx.send("No se pudo obtener el precio medio.")

    @commands.command()
    async def buy_orders(self, ctx, url: str):
        """Muestra el número de órdenes de compra para un artículo a partir de la URL."""
        data = await self.get_item_data(url)
        if data and 'buy_orders' in data:
            await ctx.send(f"Número de órdenes de compra: {data['buy_orders']}")
        else:
            await ctx.send("No se pudo obtener el número de órdenes de compra.")

    @commands.command()
    async def sell_orders(self, ctx, url: str):
        """Muestra el número de artículos en venta para un artículo a partir de la URL."""
        data = await self.get_item_data(url)
        if data and 'sell_orders' in data:
            await ctx.send(f"Número de artículos en venta: {data['sell_orders']}")
        else:
            await ctx.send("No se pudo obtener el número de artículos en venta.")

    @commands.command()
    async def track(self, ctx, url: str):
        """Realiza un seguimiento de los datos del artículo."""
        data = await self.get_item_data(url)
        if data:
            # Guardar datos en algún lugar o en la memoria
            await ctx.send("Artículo añadido a seguimiento.")
        else:
            await ctx.send("No se pudo añadir el artículo a seguimiento.")

    @commands.command()
    async def track_info(self, ctx, url: str):
        """Muestra la información del artículo rastreado."""
        data = await self.get_item_data(url)
        if data:
            # Muestra la información relevante del seguimiento
            await ctx.send(f"Información del artículo: {json.dumps(data, indent=2)}")
        else:
            await ctx.send("No se pudo obtener la información del artículo.")

def setup(bot):
    bot.add_cog(SteamMarket(bot))
