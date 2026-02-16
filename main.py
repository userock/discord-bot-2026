import discord
from discord.ext import commands
import os, requests, random, datetime, asyncio
from flask import Flask
from threading import Thread

# --- ЖИЗНЕОБЕСПЕЧЕНИЕ ---
app = Flask('')
@app.route('/')
def home(): return "Evolution Mega-System Online"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

TOKEN = os.getenv("DISCORD_TOKEN")
MOD_CHANNEL_ID = os.getenv("MOD_CHANNEL_ID")
OCR_API_KEY = os.getenv("OCR_API_KEY")
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Глобальная база данных (в памяти)
db = {} # {user_id: {"elo": 1000, "wins": 0, "streak": 0, "money": 100, "warns": 0}}

def get_data(user_id):
    u_id = str(user_id)
    if u_id not in db:
        db[u_id] = {"elo": 1000, "wins": 0, "streak": 0, "money": 100, "warns": 0}
    return db[u_id]

# --- 1-5: СИСТЕМА ИИ И СТАТИСТИКИ ---

@bot.command()
async def result(ctx):
    """Отправить скриншот на анализ ИИ"""
    if not ctx.message.attachments:
        return await ctx.send("❌ Прикрепи скриншот!")
    
    msg = await ctx.send("🔍 ИИ сканирует изображение...")
    img_url = ctx.message.attachments[0].url
    
    try:
        ocr_url = f"https://api.ocr.space/parse/imageurl?apikey={OCR_API_KEY}&url={img_url}"
        res = requests.get(ocr_url).json()
        text = res["ParsedResults"][0]["ParsedText"].lower() if res.get("ParsedResults") else ""
        
        outcome = "ПОБЕДА" if any(w in text for w in ["victory", "win", "победа"]) else "ПОРАЖЕНИЕ"
        elo = random.randint(20, 30) if outcome == "ПОБЕДА" else random.randint(-20, -15)
        
        mod_chan = bot.get_channel(int(MOD_CHANNEL_ID))
        embed = discord.Embed(title="🤖 Анализ ИИ", color=0x00ff00)
        embed.add_field(name="Игрок", value=ctx.author.mention)
        embed.add_field(name="Вердикт", value=outcome)
        embed.set_image(url=img_url)
        embed.set_footer(text=f"ID:{ctx.author.id}|ELO:{elo}")
        
        m = await mod_chan.send(embed=embed)
        await m.add_reaction("✅")
        await m.add_reaction("❌")
        await msg.edit(content="✅ Скриншот у модераторов!")
    except:
        await msg.edit(content="❌ Ошибка чтения скрина.")

@bot.command()
async def profile(ctx, m: discord.Member = None):
    """Твой профиль и ранг"""
    m = m or ctx.author
    u = get_data(m.id)
    await ctx.send(f"👤 **{m.name}**\n📈 ELO: `{u['elo']}`\n🏆 Побед: `{u['wins']}`\n🔥 Стрик: `{u['streak']}`")

@bot.command()
async def top(ctx):
    """Топ-10 игроков хаба"""
    items = sorted(db.items(), key=lambda x: x[1]['elo'], reverse=True)[:10]
    res = "🏆 **Лидеры Evolution:**\n"
    for i, (uid, info) in enumerate(items, 1):
        res += f"{i}. <@{uid}> — `{info['elo']}` ELO\n"
    await ctx.send(res or "Список пуст")

@bot.command()
async def check(ctx):
    """Техническая проверка бота"""
    await ctx.send("🛰️ Система: **ACTIVE**\n📡 ИИ-модуль: **READY**")

@bot.command()
async def promo(ctx):
    """Получить стартовый бонус"""
    u = get_data(ctx.author.id)
    u['money'] += 500
    await ctx.send("🎁 Тебе начислено 500 монет!")

# --- 6-12: МОДЕРАЦИЯ И УПРАВЛЕНИЕ ---

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, m: discord.Member, *, r=None):
    await m.ban(reason=r)
    await ctx.send(f"🔨 {m.name} забанен.")

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, m: discord.Member, *, r=None):
    await m.kick(reason=r)
    await ctx.send(f"👢 {m.name} кикнут.")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, a: int):
    await ctx.channel.purge(limit=a+1)

@bot.command()
@commands.has_permissions(administrator=True)
async def warn(ctx, m: discord.Member):
    u = get_data(m.id)
    u['warns'] += 1
    await ctx.send(f"⚠️ {m.mention} получил варн! ({u['warns']}/3)")

@bot.command()
async def rules(ctx):
    await ctx.send("📜 **Правила:** 1. Не спамить. 2. Уважать модеров. 3. Не юзать софт.")

@bot.command()
async def ticket(ctx, *, r="Поддержка"):
    ch = await ctx.guild.create_text_channel(f"ticket-{ctx.author.name}")
    await ch.send(f"🆘 {ctx.author.mention}, админы скоро будут. Причина: {r}")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def close(ctx):
    await ctx.channel.delete()

# --- 13-20: ЭКОНОМИКА И ФАН ---

@bot.command()
async def work(ctx):
    u = get_data(ctx.author.id)
    m = random.randint(50, 150)
    u['money'] += m
    await ctx.send(f"💰 Ты заработал {m} монет!")

@bot.command()
async def balance(ctx):
    u = get_data(ctx.author.id)
    await ctx.send(f"💵 Баланс: `{u['money']}` монет")

@bot.command()
async def coin(ctx, side):
    """Монетка: !coin орел"""
    res = random.choice(["орел", "решка"])
    await ctx.send(f"🎲 Выпало: **{res}**. {'Ты выиграл!' if side.lower() == res else 'Проигрыш.'}")

@bot.command()
async def roll(ctx):
    await ctx.send(f"🎲 Число: **{random.randint(1, 100)}**")

@bot.command()
async def hug(ctx, m: discord.Member):
    await ctx.send(f"🤗 {ctx.author.mention} обнял {m.mention}!")

@bot.command()
async def rip(ctx, m: discord.Member):
    await ctx.send(f"⚰️ {m.name} отлетел... Press F.")

@bot.command()
async def ball(ctx, *, q):
    await ctx.send(f"🔮 {random.choice(['Да', 'Нет', 'Скорее всего', 'Никогда'])}")

@bot.command()
async def server(ctx):
    await ctx.send(f"🏰 Сервер: {ctx.guild.name}\n👥 Людей: {ctx.guild.member_count}")

# --- 21-25: СЛУЖЕБНЫЕ ---

@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Понг! `{round(bot.latency * 1000)}ms`")

@bot.command()
async def avatar(ctx, m: discord.Member = None):
    m = m or ctx.author
    await ctx.send(m.display_avatar.url)

@bot.command()
async def say(ctx, *, t):
    if ctx.author.guild_permissions.administrator:
        await ctx.message.delete()
        await ctx.send(t)

@bot.command()
async def admins(ctx):
    await ctx.send("🛡️ В сети: `@Owner`, `@Admin` (напиши в тикет если что)")

@bot.command()
async def help(ctx):
    emb = discord.Embed(title="📖 Команды Evolution", color=0xff5500)
    emb.add_field(name="🎮 Игровые", value="`!result`, `!profile`, `!top`, `!promo`, `!work`, `!balance`")
    emb.add_field(name="🛠️ Админ", value="`!ban`, `!kick`, `!clear`, `!warn`, `!say`, `!close`")
    emb.add_field(name="🎉 Фан", value="`!coin`, `!roll`, `!hug`, `!ball`, `!rip`, `!avatar`")
    emb.add_field(name="🛰️ Система", value="`!check`, `!rules`, `!ticket`, `!server`, `!ping`, `!admins`")
    await ctx.send(embed=emb)

# --- ОБРАБОТКА ПОДТВЕРЖДЕНИЯ ---
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or str(reaction.message.channel.id) != MOD_CHANNEL_ID: return
    if not user.guild_permissions.manage_messages: return
    
    emb = reaction.message.embeds[0]
    fdata = emb.footer.text.split("|")
    pid = int(fdata[0].replace("ID:", ""))
    elo = int(fdata[1].replace("ELO:", ""))
    
    player = await bot.fetch_user(pid)
    u = get_data(pid)

    if str(reaction.emoji) == "✅":
        u['elo'] += elo
        u['wins'] += 1 if elo > 0 else 0
        await reaction.message.channel.send(f"🟢 Подтверждено для {player.name}!")
        await player.send(f"🎉 Матч подтвержден! Твое ELO: {u['elo']}")
    
    await reaction.message.delete()

keep_alive()
bot.run(TOKEN)
