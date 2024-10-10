import discord
from discord.ext import commands, tasks
import requests
from bs4 import BeautifulSoup
import re

class SteamMarketTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.item_url = "https://steamcommunity.com/market/listings/730/Sticker%20|%20MouseSports%20(Tape)"
        self.last_price = None
        self.check_price.start()

    def get_price(self):
        """Obtiene el precio del ítem y otras estadísticas del mercado de Steam."""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
        }
        
        response = requests.get(self.item_url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Obtener el precio del ítem
        price_element = soup.find("span", {"class": "market_listing_price market_listing_price_with_fee"})
        if price_element:
            price_text = price_element.get_text(strip=True)
        else:
            price_text = None

        # Obtener estadísticas adicionales (ventas recientes, órdenes de compra/venta)
        sales_info = self.get_market_statistics(soup)
        
        return price_text, sales_info

    def get_market_statistics(self, soup):
        """Obtiene estadísticas del mercado (órdenes de compra, venta y ventas recientes) usando scraping."""
        stats = {}

        # Obtener ventas recientes
        recent_sales_element = soup.find("div", {"id": "largeiteminfo_iteminfo_content"})
        recent_sales_text = recent_sales_element.get_text(strip=True) if recent_sales_element else None
        sales_pattern = re.compile(r"(\d+) sold in the last 24 hours")
        match = sales_pattern.search(recent_sales_text)
        stats['recent_sales'] = match.group(1) if match else "No data"

        # Obtener el precio más bajo de venta
        sell_orders_element = soup.find("span", {"id": "market_commodity_orders_header"})
        if sell_orders_element:
            sell_orders_text = sell_orders_element.get_text(strip=True)
            stats['lowest_sell_order'] = sell_orders_text.split(" ")[-1]

        # Obtener el precio más alto de compra
        buy_orders_element = soup.find("span", {"id": "market_commodity_buyrequests_header"})
        if buy_orders_element:
            buy_orders_text = buy_orders_element.get_text(strip=True)
            stats['highest_buy_order'] = buy_orders_text.split(" ")[-1]

        return stats

    @tasks.loop(minutes=5)
    async def check_price(self):
        """Verifica el precio del ítem en intervalos regulares y envía notificaciones si cambia."""
        current_price, sales_info = self.get_price()

        if current_price and self.last_price != current_price:
            channel = self.bot.get_channel(YOUR_CHANNEL_ID)
            await channel.send(f"El precio de {self.item_url} ha cambiado a {current_price}.")
            await channel.send(f"Ventas recientes: {sales_info['recent_sales']} en las últimas 24 horas.\n"
                               f"Orden de venta más baja: {sales_info['lowest_sell_order']}\n"
                               f"Orden de compra más alta: {sales_info['highest_buy_order']}")
            self.last_price = current_price

    @commands.command(name='track_item')
    async def track_item(self, ctx, *, url):
        """Inicia el seguimiento de un ítem del mercado de Steam."""
        self.item_url = url
        await ctx.send(f"Comenzando a seguir el ítem en {url}")

    @commands.command(name='stop_tracking')
    async def stop_tracking(self, ctx):
        """Detiene el seguimiento del ítem."""
        self.check_price.cancel()
        await ctx.send("Seguimiento detenido.")

    @commands.command(name='set_channel')
    async def set_channel(self, ctx):
        """Define el canal donde se enviarán las notificaciones de precios."""
        global YOUR_CHANNEL_ID
        YOUR_CHANNEL_ID = ctx.channel.id
        await ctx.send(f"Canal para notificaciones configurado: {ctx.channel.name}")

    @check_price.before_loop
    async def before_check_price(self):
        """Espera a que el bot esté listo antes de comenzar a verificar los precios."""
        await self.bot.wait_until_ready()

# Cargar el cog en el bot
async def setup(bot):
    await bot.add_cog(SteamMarketTracker(bot))
