import discord
from discord.ext import commands, tasks
import os, random, datetime, asyncio
from flask import Flask
from threading import Thread

# --- ЖИЗНЕОБЕСПЕЧЕНИЕ ---
app = Flask('')
@app.route('/')
def home(): return "Evolution Hyper-Engine: Online"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- CONFIG ---
TOKEN = os.getenv("DISCORD_TOKEN")
MOD_ID = os.getenv("MOD_CHANNEL_ID")
LOG_ID = os.getenv("LOG_CHANNEL_ID")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ГЛОБАЛЬНАЯ БАЗА
db = {} 
# БАНВОРДЫ (расширенный список)
BANNED_WORDS = ["запрещенка1", "мат2", "оск3", "плохоеслово4"]

def get_u(uid):
    uid = str(uid)
    if uid not in db:
        db[uid] = {"elo": 1000, "wins": 0, "money": 0, "xp": 0, "lvl": 1, "warns": 0}
    return db[uid]

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.streaming, name="Project Evolution", url="https://twitch.tv/faceit"))
    print(f"💎 HYPER SYSTEM {bot.user} READY")

# --- СИСТЕМА УРОВНЕЙ И ФИЛЬТР ---
@bot.event
async def on_message(msg):
    if msg.author.bot: return
    
    # 1. Анти-банворд
    if any(w in msg.content.lower() for w in BANNED_WORDS):
        await msg.delete()
        u = get_u(msg.author.id)
        u['warns'] += 1
        await msg.channel.send(f"🚫 {msg.author.mention}, фильтруй базар! Предупреждение ({u['warns']}/3)", delete_after=5)
        return

    # 2. Начисление XP
    u = get_u(msg.author.id)
    u['xp'] += random.randint(5, 15)
    if u['xp'] >= u['lvl'] * 100:
        u['lvl'] += 1
        await msg.channel.send(f"🆙 {msg.author.mention} поднял уровень до **{u['lvl']}**!")

    await bot.process_commands(msg)

# --- ИИ И МАТЧИ ---
@bot.command()
async def result(ctx, score: str = "0-0"):
    """Залить скрин матча"""
    if not ctx.message.attachments:
        return await ctx.send("❌ Где скриншот?")
    
    try:
        w, l = map(int, score.split("-"))
        elo = random.randint(25, 30) if w > l else random.randint(-20, -15)
    except: elo = 20

    m_chan = bot.get_channel(int(MOD_ID))
    emb = discord.Embed(title="⚔️ НОВЫЙ РЕПОРТ", color=0x7289da)
    emb.add_field(name="Игрок", value=ctx.author.mention, inline=True)
    emb.add_field(name="Счет", value=score, inline=True)
    emb.set_image(url=ctx.message.attachments[0].url)
    emb.set_footer(text=f"ID:{ctx.author.id}|ELO:{elo}")
    
    m = await m_chan.send(embed=emb)
    await m.add_reaction("✅")
    await m.add_reaction("❌")
    await ctx.send("📡 Заявка улетела модерам.")

# --- ЭКОНОМИКА И МАГАЗИН ---
@bot.command()
async def work(ctx):
    u = get_u(ctx.author.id)
    m = random.randint(100, 300); u['money'] += m
    await ctx.send(f"🏦 Ты заработал **{m}** 🪙")

@bot.command()
async def shop(ctx):
    emb = discord.Embed(title="🛒 Магазин Ролей", description="Купи роль: `!buy [номер]`", color=0x00ff00)
    emb.add_field(name="1. VIP Статус", value="Цена: 5000 🪙")
    emb.add_field(name="2. Элита Хаба", value="Цена: 10000 🪙")
    await ctx.send(embed=emb)

@bot.command()
async def buy(ctx, item: int):
    u = get_u(ctx.author.id)
    if item == 1 and u['money'] >= 5000:
        u['money'] -= 5000
        await ctx.send("✅ Ты купил VIP!")
    elif item == 2 and u['money'] >= 10000:
        u['money'] -= 10000
        await ctx.send("✅ Ты купил статус Элита!")
    else:
        await ctx.send("❌ Недостаточно средств.")

# --- ПРОФИЛЬ И ТОП ---
@bot.command()
async def profile(ctx, m: discord.Member = None):
    m = m or ctx.author
    u = get_u(m.id)
    emb = discord.Embed(title=f"👤 Профиль {m.name}", color=0xff5500)
    emb.add_field(name="📈 ELO", value=u['elo'], inline=True)
    emb.add_field(name="✨ Уровень", value=u['lvl'], inline=True)
    emb.add_field(name="💰 Баланс", value=u['money'], inline=True)
    emb.add_field(name="🏆 Победы", value=u['wins'], inline=True)
    emb.set_thumbnail(url=m.display_avatar.url)
    await ctx.send(embed=emb)

# --- МОДЕРАЦИЯ ---
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, a: int): await ctx.channel.purge(limit=a+1)

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, m: discord.Member, *, r=None):
    await m.ban(reason=r); await ctx.send(f"🔨 {m.name} забанен.")

# --- ЛОГИКА РЕАКЦИЙ ---
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or str(reaction.message.channel.id) != MOD_ID: return
    if not user.guild_permissions.manage_messages: return
    
    emb = reaction.message.embeds[0]
    data = emb.footer.text.split("|")
    pid = int(data[0].replace("ID:", ""))
    elo = int(data[1].replace("ELO:", ""))
    
    u = get_u(pid)
    if str(reaction.emoji) == "✅":
        u['elo'] += elo
        u['wins'] += 1 if elo > 0 else 0
        await reaction.message.channel.send(f"✅ Готово для <@{pid}>")
    await reaction.message.delete()

# --- ВСПОМОГАТЕЛЬНЫЕ ---
@bot.command()
async def help(ctx):
    e = discord.Embed(title="🌌 Командный Центр Evolution", color=0x5865f2)
    e.add_field(name="🎮 Игра", value="`!result`, `!profile`, `!top`, `!shop`, `!buy`")
    e.add_field(name="💰 Эконом", value="`!work`, `!balance`, `!promo`")
    e.add_field(name="🛡️ Админ", value="`!ban`, `!kick`, `!clear`, `!warn`, `!say`")
    e.add_field(name="👾 Фан", value="`!coin`, `!roll`, `!ball`, `!hug`, `!avatar`")
    e.add_field(name="⚙️ Тех", value="`!ping`, `!server`, `!ticket`, `!rules`, `!admins`")
    await ctx.send(embed=e)

keep_alive()
bot.run(TOKEN)
