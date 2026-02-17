import discord
from discord.ext import commands
import os, requests, random, datetime
from flask import Flask
from threading import Thread

# --- 1. ЖИЗНЕОБЕСПЕЧЕНИЕ (RENDER) ---
app = Flask('')
@app.route('/')
def home(): return "Evolution Omega Core: Online"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- 2. НАСТРОЙКИ ---
TOKEN = os.getenv("DISCORD_TOKEN")
MOD_ID = os.getenv("MOD_CHANNEL_ID")
OCR_KEY = os.getenv("OCR_API_KEY") # Ключ для "зрения" бота

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

db = {} # База в памяти
BAD_WORDS = ["банворд1", "оск2", "мат3"] # Список запрещенных слов

def get_u(uid):
    uid = str(uid)
    if uid not in db:
        db[uid] = {"elo": 1000, "wins": 0, "money": 500, "xp": 0, "lvl": 1, "warns": 0}
    return db[uid]

# --- 3. ФИЛЬТР И УРОВНИ ---
@bot.event
async def on_message(msg):
    if msg.author.bot: return
    
    # Анти-мат
    if any(w in msg.content.lower() for w in BAD_WORDS):
        await msg.delete()
        return await msg.channel.send(f"🚫 {msg.author.mention}, банворды запрещены!", delete_after=5)

    # Опыт (XP)
    u = get_u(msg.author.id)
    u['xp'] += random.randint(5, 10)
    if u['xp'] >= u['lvl'] * 100:
        u['lvl'] += 1
        await msg.channel.send(f"🆙 {msg.author.mention} поднял уровень до **{u['lvl']}**!")

    await bot.process_commands(msg)

# --- 4. КОМАНДА С ИИ-ЗРЕНИЕМ (ГЛАВНАЯ) ---
@bot.command()
async def result(ctx):
    """Отправить скрин на проверку ИИ"""
    if not ctx.message.attachments:
        return await ctx.send("❌ Прикрепи скриншот матча!")

    status_msg = await ctx.send("👁️ **ИИ Evolution сканирует скриншот...**")
    img_url = ctx.message.attachments[0].url

    try:
        # Запрос к нейросети OCR.space
        ocr_url = f"https://api.ocr.space/parse/imageurl?apikey={OCR_KEY}&url={img_url}&language=eng"
        res = requests.get(ocr_url).json()
        
        parsed_text = ""
        if res.get("ParsedResults"):
            parsed_text = res["ParsedResults"][0]["ParsedText"].lower()
        
        # Логика распознавания
        is_win = any(w in parsed_text for w in ["victory", "win", "победа", "winner"])
        elo_advice = 25 if is_win else -20
        verdict = "ПОБЕДА ✅" if is_win else "ПОРАЖЕНИЕ/НЕЯСНО ⚠️"

        # Отчет в админ-канал
        m_chan = bot.get_channel(int(MOD_ID))
        emb = discord.Embed(title="🤖 ОТЧЕТ ИИ-ЗРЕНИЯ", color=0x00ff00 if is_win else 0xff0000)
        emb.add_field(name="👤 Игрок", value=ctx.author.mention)
        emb.add_field(name="👁️ Прочитанный текст", value=f"```{parsed_text[:200] if parsed_text else 'Текст не найден'}```")
        emb.add_field(name="🤖 Вердикт ИИ", value=f"**{verdict}**\nСоветую: `{elo_advice}` ELO")
        emb.set_image(url=img_url)
        emb.set_footer(text=f"ID:{ctx.author.id}|ELO:{elo_advice}")

        msg = await m_chan.send(embed=emb)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        await status_msg.edit(content="📡 **Система:** Скриншот просканирован и отправлен админам!")

    except Exception as e:
        await status_msg.edit(content="❌ Ошибка ИИ. Проверь OCR_API_KEY в Render.")

# --- 5. ВСЕ ОСТАЛЬНЫЕ КОМАНДЫ (25 ШТУК) ---

@bot.command()
async def profile(ctx, m: discord.Member = None):
    m = m or ctx.author; u = get_u(m.id)
    e = discord.Embed(title=f"👤 Профиль: {m.name}", color=0x00ffcc)
    e.add_field(name="📈 ELO", value=u['elo']); e.add_field(name="🏆 Победы", value=u['wins'])
    e.add_field(name="✨ Уровень", value=u['lvl']); e.add_field(name="💰 Монеты", value=u['money'])
    await ctx.send(embed=e)

@bot.command()
@commands.has_permissions(administrator=True)
async def give_elo(ctx, m: discord.Member, a: int):
    u = get_u(m.id); u['elo'] += a
    await ctx.send(f"✅ {m.mention} начислено {a} ELO вручную.")

@bot.command()
async def top(ctx):
    items = sorted(db.items(), key=lambda x: x[1]['elo'], reverse=True)[:10]
    res = "🏆 **ТОП-10 ХАБА:**\n"
    for i, (uid, info) in enumerate(items, 1): res += f"{i}. <@{uid}> — `{info['elo']}` ELO\n"
    await ctx.send(res or "Список пуст")

@bot.command()
async def work(ctx):
    u = get_u(ctx.author.id); m = random.randint(50, 200); u['money'] += m
    await ctx.send(f"💰 Ты заработал {m} монет!")

@bot.command()
async def shop(ctx): await ctx.send("🛒 **Магазин:**\n1. VIP (5000 монет) - `!buy 1`")

@bot.command()
async def buy(ctx, i: int):
    u = get_u(ctx.author.id)
    if i == 1 and u['money'] >= 5000: u['money'] -= 5000; await ctx.send("✅ VIP куплен!")
    else: await ctx.send("❌ Недостаточно монет.")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, a: int): await ctx.channel.purge(limit=a+1)

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, m: discord.Member): await m.ban(); await ctx.send(f"🔨 {m.name} забанен!")

@bot.command()
async def promo(ctx):
    u = get_u(ctx.author.id); u['money'] += 1000; await ctx.send("🎁 Промокод активирован! +1000 монет.")

@bot.command()
async def ping(ctx): await ctx.send(f"🏓 `{round(bot.latency*1000)}ms`")

@bot.command()
async def coin(ctx): await ctx.send(f"🎲 {random.choice(['Орел', 'Решка'])}")

@bot.command()
async def roll(ctx): await ctx.send(f"🎲 {random.randint(1, 100)}")

@bot.command()
async def hug(ctx, m: discord.Member): await ctx.send(f"🤗 Обнял {m.mention}")

@bot.command()
async def ball(ctx, *, q): await ctx.send(f"🔮 {random.choice(['Да', 'Нет', 'Возможно'])}")

@bot.command()
async def avatar(ctx, m: discord.Member = None): await ctx.send((m or ctx.author).display_avatar.url)

@bot.command()
async def server(ctx): await ctx.send(f"🏰 Участников: {ctx.guild.member_count}")

@bot.command()
async def rules(ctx): await ctx.send("📜 Не читерить, не спамить, уважать админов.")

@bot.command()
async def check(ctx): await ctx.send("🛰️ Система: **ACTIVE**")

@bot.command()
async def admins(ctx): await ctx.send("🛡️ По всем вопросам к @Owner.")

@bot.command()
@commands.has_permissions(administrator=True)
async def say(ctx, *, t): await ctx.message.delete(); await ctx.send(t)

@bot.command()
@commands.has_permissions(administrator=True)
async def warn(ctx, m: discord.Member):
    u = get_u(m.id); u['warns'] += 1; await ctx.send(f"⚠️ {m.mention} получил варн!")

@bot.command()
async def balance(ctx): u = get_u(ctx.author.id); await ctx.send(f"💵 Баланс: {u['money']} монет")

@bot.command()
async def ticket(ctx): await ctx.send("🆘 Создай тикет в канале #support!")

@bot.command()
async def help(ctx):
    e = discord.Embed(title="⚙️ Команды Evolution", color=0x5865f2)
    e.add_field(name="🎮 Игра", value="`!result`, `!profile`, `!top`, `!promo`")
    e.add_field(name="💰 Эконом", value="`!work`, `!shop`, `!balance`, `!buy`")
    e.add_field(name="🛡️ Админ", value="`!give_elo`, `!ban`, `!clear`, `!say`, `!warn`")
    e.add_field(name="✨ Разное", value="`!ping`, `!coin`, `!roll`, `!ball`, `!hug`, `!avatar`, `!server`, `!rules`, `!check`, `!admins`, `!ticket`")
    await ctx.send(embed=e)

# --- 6. ОБРАБОТКА ПОДТВЕРЖДЕНИЯ ---
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or str(reaction.message.channel.id) != MOD_ID: return
    if not user.guild_permissions.manage_messages: return
    
    emb = reaction.message.embeds[0]; data = emb.footer.text.split("|")
    pid = data[0].replace("ID:", ""); elo = int(data[1].replace("ELO:", ""))
    u = get_u(pid)

    if str(reaction.emoji) == "✅":
        u['elo'] += elo; u['wins'] += 1 if elo > 0 else 0
        await reaction.message.channel.send(f"✅ Одобрено для <@{pid}>!")
    
    await reaction.message.delete()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(f"🚫 {ctx.author.mention}, у тебя нет прав!")

keep_alive()
bot.run(TOKEN)
