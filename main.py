import discord
from discord.ext import commands
import asyncio

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'✅ БОТ В СЕТИ! Имя: {bot.user}')

@bot.command()
async def test(ctx):
    await ctx.send('🚀 Бот успешно переехал и работает!')

async def main():
    token = 'MTQ3MjYzMDMyMTQzMzI4NDYxOQ.GJw4FT.sBRiBG3Bh5ta3rbgH1rHPK3IPDfHaOBc1AbZIc'
    await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
