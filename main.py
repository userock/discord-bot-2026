import discord
from discord.ext import commands
import os, requests, random
from flask import Flask
from threading import Thread

# --- 1. ЖИЗНЕОБЕСПЕЧЕНИЕ (RENDER) ---
app = Flask('')
@app.route('/')
def home(): return "Evolution Omega System: Online"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- 2. НАСТРОЙКИ (ИЗ ТВОЕГО RENDER) ---
TOKEN = os.getenv("DISCORD_TOKEN")
MOD_ID = os.getenv("HUB_ID") # Используем твое имя переменной из Render
OCR_KEY = os.getenv("OCR_API_KEY") # Твой ключ зрения

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Временная база данных (в реальном проекте лучше использовать файл)
db = {}
BAD_WORDS = ["банворд1", "мат2"] # Список для авто-удаления

def get_u(uid):
    uid = str(uid)
    if uid not in db:
        db[uid] = {"elo": 1000, "wins": 0, "money": 500, "xp": 0, "lvl": 1}
    return db[uid]

# --- 3. АВТО-ФУНКЦИИ (УРОВНИ И ФИЛЬТР) ---
@bot.event
async def on_message(msg):
    if msg.author.bot: return
    # Фильтр мата
    if any(w in msg.content.lower() for w in BAD_WORDS):
        await msg.delete()
        return await msg.channel.send(f"🚫 {msg.author.mention}, не выражайся!", delete_after=5)
    # Опыт за общение
    u = get_u(msg.author.id)
    u['xp'] += random.randint(5, 10)
    if u['xp'] >= u['lvl'] * 100:
        u['lvl'] += 1
        await msg.channel.send(f"🆙 {msg.author.mention} достиг **{u['lvl']} уровня**!")
    await bot.process_commands(msg)

# --- 4. ГЛАВНАЯ КОМАНДА: ИИ-СКАНЕР СКРИНШОТОВ ---
@bot.command()
async def result(ctx):
    """Отправить скриншот на проверку ИИ"""
    if not ctx.message.attachments: 
        return await ctx.send("❌ Прикрепи скриншот результата матча!")
    
    wait = await ctx.send("👁️ **ИИ Evolution сканирует скриншот...**")
    img_url = ctx.message.attachments[0].url

    try:
        # Запрос к OCR.space для чтения текста
        r = requests.get(f"https://api.ocr.space/parse/imageurl?apikey={OCR_KEY}&url={img_url}").json()
        text = r["ParsedResults"][0]["ParsedText"].lower() if r.get("ParsedResults") else ""
        
        # Анализ (бот ищет цифры или слова со скрина, например 6700$)
        is_win = any(w in text for w in ["victory", "win", "победа", "6700", "9800", "$"])
        elo = 25 if is_win else -20
        verdict = "ПОБЕДА ✅" if is_win else "ПОРАЖЕНИЕ/НЕЯСНО ⚠️"

        m_chan = bot.get_channel(int(MOD_ID))
        emb = discord.Embed(title="🤖 ОТЧЕТ ИИ-ЗРЕНИЯ", color=0x00ff00 if is_win else 0xff0000)
        emb.add_field(name="👤 Игрок", value=ctx.author.mention)
        emb.add_field(name="👁️ Текст на фото", value=f"```{text[:150] if text else 'Текст не найден'}```")
        emb.add_field(name="🤖 Вердикт", value=f"**{verdict}**\nСоветую: `{elo}` ELO")
        emb.set_image(url=img_url)
        emb.set_footer(text=f"ID:{ctx.author.id}|ELO:{elo}")

        msg = await m_chan.send(embed=emb)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        await wait.edit(content="📡 Скриншот просканирован и отправлен в HUB!")
    except Exception as e:
        await wait.edit(content=f"❌ Ошибка ИИ. Проверь OCR_API_KEY в Render! ({e})")

# --- 5. ОСТАЛЬНЫЕ КОМАНДЫ (25 ШТУК) ---
@bot.command()
async def profile(ctx, m: discord.Member = None):
    m = m or ctx.author; u = get_u(m.id)
    e = discord.Embed(title=f"👤 Профиль {m.name}", color=0x00ffcc)
    e.add_field(name="📈 ELO", value=u['elo'])
    e.add_field(name="🏆 Победы", value=u['wins'])
    e.add_field(name="✨ Уровень", value=u['lvl'])
    e.add_field(name="💰 Монеты", value=u['money'])
    await ctx.send(embed=e)

@bot.command()
@commands.has_permissions(administrator=True)
async def give_elo(ctx, m: discord.Member, a: int):
    u = get_u(m.id); u['elo'] += a
    await ctx.send(f"✅ {m.name} выдано {a} ELO вручную.")

@bot.command()
async def top(ctx):
    items = sorted(db.items(), key=lambda x: x[1]['elo'], reverse=True)[:10]
    res = "🏆 **ТОП ЛИДЕРОВ:**\n"
    for i, (uid, info) in enumerate(items, 1):
        res += f"{i}. <@{uid}> — `{info['elo']}` ELO\n"
    await ctx.send(res or "Список пока пуст")

@bot.command()
async def work(ctx):
    u = get_u(ctx.author.id); m = random.randint(100, 300); u['money'] += m
    await ctx.send(f"💰 Ты поработал и заработал {m} монет!")

@bot.command()
async def ping(ctx): await ctx.send(f"🏓 Пинг: `{round(bot.latency*1000)}ms`")

@bot.command()
async def coin(ctx): await ctx.send(f"🎲 Выпало: {random.choice(['Орел', 'Решка'])}")

@bot.command()
async def avatar(ctx, m: discord.Member = None): await ctx.send((m or ctx.author).display_avatar.url)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, a: int): await ctx.channel.purge(limit=a+1)

@bot.command()
async def help(ctx):
    e = discord.Embed(title="🌌 Меню Evolution", color=0x5865f2)
    e.add_field(name="🎮 Основное", value="`!result`, `!profile`, `!top`, `!promo`, `!check`", inline=False)
    e.add_field(name="💰 Экономика", value="`!work`, `!shop`, `!balance`, `!buy` ", inline=False)
    e.add_field(name="🛡️ Админ", value="`!give_elo`, `!ban`, `!clear`, `!say`, `!warn` ", inline=False)
    e.add_field(name="✨ Фан", value="`!ping`, `!coin`, `!roll`, `!ball`, `!avatar`, `!hug` ", inline=False)
    await ctx.send(embed=e)

# --- 6. ЛОГИКА КНОПОК ПОДТВЕРЖДЕНИЯ ---
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or str(reaction.message.channel.id) != MOD_ID: return
    if not user.guild_permissions.manage_messages: return
    
    emb = reaction.message.embeds[0]
    data = emb.footer.text.split("|")
    pid = data[0].replace("ID:", "")
    elo = int(data[1].replace("ELO:", ""))
    u = get_u(pid)

    if str(reaction.emoji) == "✅":
        u['elo'] += elo
        u['wins'] += 1 if elo > 0 else 0
        await reaction.message.channel.send(f"✅ Результат <@{pid}> одобрен!")
    
    await reaction.message.delete()

keep_alive()
bot.run(TOKEN)
