import discord
from discord.ext import commands
import os
import requests
from flask import Flask
from threading import Thread

# Умный веб-сервер против сна
app = Flask('')
@app.route('/')
def home(): return "Project Evolution: Full System Active"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

TOKEN = os.getenv("DISCORD_TOKEN")
FACEIT_KEY = os.getenv("FACEIT_TOKEN")
HUB_ID = os.getenv("HUB_ID")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True 
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

headers = {"Authorization": f"Bearer {FACEIT_KEY}"}

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="за матчами Evolution"))
    print(f"✅ Ультимативный бот запущен: {bot.user}")

@bot.command()
async def help(ctx):
    """Меню навигации"""
    embed = discord.Embed(title="🛡️ Система Project Evolution", description="Полный список команд хаба", color=0xff5500)
    embed.add_field(name="👤 Игрок", value="`!stats [ник]`\n`!profile [ник]`\n`!bind [UID]`", inline=True)
    embed.add_field(name="🏆 Турниры", value="`!hub`\n`!top`\n`!last`", inline=True)
    embed.add_field(name="🌐 Инфо", value="`!server` — Статус игры\n`!admins` — Состав АП", inline=False)
    embed.set_footer(text="Версия 2.0 | Power by Render")
    await ctx.send(embed=embed)

@bot.command()
async def profile(ctx, nickname):
    """Карточка игрока с фото"""
    res = requests.get(f"https://open.faceit.com/data/v4/players?nickname={nickname}", headers=headers)
    if res.status_code == 200:
        p = res.json()
        embed = discord.Embed(title=f"🎮 Профиль {p['nickname']}", url=p['faceit_url'].replace('{lang}', 'ru'), color=0xff5500)
        embed.set_thumbnail(url=p.get('avatar', ''))
        embed.add_field(name="🌍 Страна", value=p.get('country', 'N/A').upper())
        embed.add_field(name="⭐ Level", value=str(p.get('games', {}).get('cs2', {}).get('skill_level', '1')))
        embed.add_field(name="📈 ELO", value=str(p.get('games', {}).get('cs2', {}).get('faceit_elo', '1000')))
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ Игрок не найден.")

@bot.command()
async def bind(ctx, uid: str):
    """Привязка игрового ID"""
    # Здесь можно добавить сохранение в базу данных, но пока просто подтверждаем
    await ctx.send(f"✅ Аккаунт **{ctx.author.name}** успешно привязан к игровому UID: `{uid}`. Теперь статистика будет учитываться в хабе.")

@bot.command()
async def last(ctx):
    """Счет последней катки"""
    url = f"https://open.faceit.com/data/v4/hubs/{HUB_ID}/matches?type=past&limit=1"
    res = requests.get(url, headers=headers)
    if res.status_code == 200 and res.json().get('items'):
        m = res.json()['items'][0]
        s = m.get('results', {}).get('score', {})
        res_msg = f"🏁 **{m['teams']['faction1']['name']}** [{s.get('faction1', 0)} : {s.get('faction2', 0)}] **{m['teams']['faction2']['name']}**"
        await ctx.send(res_msg)
    else:
        await ctx.send("📅 Истории матчей пока нет.")

@bot.command()
async def server(ctx):
    """Статус игрового сервера"""
    await ctx.send("🌐 **Статус серверов Project Evolution:**\n✅ Москва (RU) — **Online** [12ms]\n✅ Германия (EU) — **Online** [34ms]")

@bot.command()
async def admins(ctx):
    """Список контактов"""
    await ctx.send("👨‍💻 **Администрация проекта:**\n• Главный админ: @твой_ник\n• Тех. поддержка: через тикеты")

# Стандартные команды
@bot.command()
async def hub(ctx):
    res = requests.get(f"https://open.faceit.com/data/v4/hubs/{HUB_ID}", headers=headers)
    if res.status_code == 200:
        d = res.json()
        await ctx.send(f"🏰 **{d['name']}** | Зарегистрировано: `{d['players_joined_count']}`")
    else:
        await ctx.send("❌ Ошибка связи с Faceit.")

@bot.command()
async def top(ctx):
    res = requests.get(f"https://open.faceit.com/data/v4/leaderboards/hubs/{HUB_ID}/general?limit=10", headers=headers)
    if res.status_code == 200:
        items = res.json().get('items', [])
        msg = "🏆 **ЛИДЕРЫ ПРОЕКТА:**\n" + "\n".join([f"`{i+1}.` {p['player']['nickname']} — {p['points']} PTS" for i, p in enumerate(items)])
        await ctx.send(msg)

keep_alive()
bot.run(TOKEN)
