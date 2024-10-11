import discord
from discord.ext import commands
import aiohttp
import json

class SteamMarket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = 'TU_API_KEY'  # Añade aquí tu clave de SteamAPIs.com
        self.tracked_items = {}  # Diccionario para seguir los artículos rastreados

    async def get_item_data(self, market_hash_name):
        """Obtiene los datos del artículo desde la API de SteamAPIs."""
        url = f"https://api.steamapis.com/market/item/730/{market_hash_name}?api_key={self.api_key}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return None
                    return await response.json()
        except Exception as e:
            print(f"Error al obtener datos del artículo: {e}")
            return None

    @commands.command()
    async def lowest_price(self, ctx, market_hash_name: str):
        """Obtiene el precio mínimo de un artículo a partir del nombre en el mercado."""
        data = await self.get_item_data(market_hash_name)
        if data and 'lowest_price' in data:
            await ctx.send(f"El precio mínimo es: **{data['lowest_price']}**")
        else:
            await ctx.send("No se pudo obtener el precio mínimo.")

    @commands.command()
    async def volume_sold(self, ctx, market_hash_name: str):
        """Muestra el número total de artículos vendidos en las últimas 24 horas."""
        data = await self.get_item_data(market_hash_name)
        if data and 'volume_sold' in data:
            await ctx.send(f"Número de artículos vendidos en las últimas 24 horas: **{data['volume_sold']}**")
        else:
            await ctx.send("No se pudo obtener el volumen vendido.")

    @commands.command()
    async def median_price(self, ctx, market_hash_name: str):
        """Obtiene el precio medio de un artículo a partir del nombre en el mercado."""
        data = await self.get_item_data(market_hash_name)
        if data and 'median_price' in data:
            await ctx.send(f"El precio medio es: **{data['median_price']}**")
        else:
            await ctx.send("No se pudo obtener el precio medio.")

    @commands.command()
    async def buy_orders(self, ctx, market_hash_name: str):
        """Muestra el número de órdenes de compra para un artículo."""
        data = await self.get_item_data(market_hash_name)
        if data and 'buy_orders' in data:
            await ctx.send(f"Número de órdenes de compra: **{data['buy_orders']}**")
        else:
            await ctx.send("No se pudo obtener el número de órdenes de compra.")

    @commands.command()
    async def sell_orders(self, ctx, market_hash_name: str):
        """Muestra el número de artículos en venta para un artículo."""
        data = await self.get_item_data(market_hash_name)
        if data and 'sell_orders' in data:
            await ctx.send(f"Número de artículos en venta: **{data['sell_orders']}**")
        else:
            await ctx.send("No se pudo obtener el número de artículos en venta.")

    @commands.command()
    async def track(self, ctx, market_hash_name: str):
        """Realiza un seguimiento de los datos del artículo."""
        data = await self.get_item_data(market_hash_name)
        if data:
            self.tracked_items[market_hash_name] = data  # Guardar datos en el diccionario
            await ctx.send(f"Artículo '{market_hash_name}' añadido a seguimiento.")
        else:
            await ctx.send("No se pudo añadir el artículo a seguimiento.")

    @commands.command()
    async def track_info(self, ctx, market_hash_name: str):
        """Muestra la información del artículo rastreado."""
        if market_hash_name in self.tracked_items:
            data = self.tracked_items[market_hash_name]
            await ctx.send(f"Información del artículo:\n```json\n{json.dumps(data, indent=2)}\n```")
        else:
            await ctx.send("No se está rastreando este artículo.")

async def setup(bot):
    await bot.add_cog(SteamMarket(bot))
