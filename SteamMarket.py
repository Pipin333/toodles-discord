import discord
from discord.ext import commands, tasks
import aiohttp
import json
import os
import logging
from datetime import datetime

API = os.getenv("STEAM_API")

class SteamMarket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = API
        self.tracked_items = {}
        self.alerts = {}  # Almacenará alertas por usuario
        self.check_price_updates.start()  # Inicia la tarea periódica de verificación de precios

    async def get_item_data(self, market_hash_name):
        """Obtiene los datos del artículo desde la API de SteamAPIs."""
        url = f"https://api.steamapis.com/market/item/730/{market_hash_name}?api_key={self.api_key}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        logging.error(f"Error en la API: {response.status}")
                        return None
                    return await response.json()
        except Exception as e:
            logging.error(f"Error al obtener datos del artículo: {e}")
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

    def load_tracked_items(self):
        """Cargar los artículos rastreados desde un archivo JSON."""
        try:
            with open('tracked_items.json', 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            return {}

    def save_tracked_items(self):
        """Guardar los artículos rastreados en un archivo JSON."""
        with open('tracked_items.json', 'w') as file:
            json.dump(self.tracked_items, file, indent=4)

    @commands.command()
    async def track(self, ctx, market_hash_name: str):
        """Realiza un seguimiento de los datos del artículo."""
        if market_hash_name in self.tracked_items:
            await ctx.send(f"El artículo '{market_hash_name}' ya está siendo rastreado.")
            return

        data = await self.get_item_data(market_hash_name)
        if data:
            self.tracked_items[market_hash_name] = data
            self.save_tracked_items()
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

    @commands.command()
    async def set_alert(self, ctx, market_hash_name: str, price_threshold: float):
        """Establece una alerta de precio para un artículo."""
        user_id = ctx.author.id
        if user_id not in self.alerts:
            self.alerts[user_id] = {}
        self.alerts[user_id][market_hash_name] = price_threshold
        await ctx.send(f"Alerta establecida: serás notificado cuando el precio de '{market_hash_name}' sea menor a {price_threshold}.")

    @tasks.loop(minutes=5)  # Ajusta la frecuencia según tus necesidades
    async def check_price_updates(self):
        """Verifica los cambios de precios de los artículos rastreados."""
        for item, old_data in self.tracked_items.items():
            new_data = await self.get_item_data(item)
            if new_data and 'lowest_price' in new_data:
                old_price = float(old_data.get('lowest_price', 0).replace('€', '').replace('$', ''))
                new_price = float(new_data.get('lowest_price', 0).replace('€', '').replace('$', ''))
                if abs(new_price - old_price) / old_price > 0.05:
                    logging.info(f"El precio de {item} cambió de {old_price} a {new_price}")
                    # Aquí podrías enviar un mensaje de Discord o alertar de otra manera

                # Verificar si hay alertas configuradas
                for user_id, user_alerts in self.alerts.items():
                    if item in user_alerts and new_price < user_alerts[item]:
                        user = self.bot.get_user(user_id)
                        if user:
                            await user.send(f"Alerta: El precio de '{item}' ha bajado a {new_price}!")

            self.tracked_items[item] = new_data
        self.save_tracked_items()

    @commands.command()
    async def market_stats(self, ctx):
        """Muestra estadísticas globales del mercado de Steam."""
        url = f"https://api.steamapis.com/market/stats/730?api_key={self.api_key}"
        data = await self.get_item_data(url)
        if data:
            total_items = data.get('total_items', 'No disponible')
            top_category = data.get('top_category', 'No disponible')
            await ctx.send(f"Estadísticas del mercado:\nTotal de artículos: {total_items}\nCategoría más vendida: {top_category}")
        else:
            await ctx.send("No se pudieron obtener las estadísticas del mercado.")

async def setup(bot):
    await bot.add_cog(SteamMarket(bot))
