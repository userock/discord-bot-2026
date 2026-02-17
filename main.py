import discord
from discord.ext import commands
import os, random, re, requests
from io import BytesIO
from flask import Flask
from threading import Thread

# Пытаемся подключить встроенный ИИ
try:
    import pytesseract
    from PIL import Image
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

# --- 1. СЕРВЕР ДЛЯ RENDER ---
app = Flask('')
@app.route('/')
def home(): return "Evolution Omega System Online"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- 2. НАСТРОЙКИ ---
TOKEN = os.getenv("DISCORD_TOKEN")
MOD_ID = os.getenv("HUB_ID") 

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

db = {} 
BAD_WORDS = ["хуй", "сука", "пидор"] # Список для авто-удаления

def get_u(uid):
    uid = str(uid)
    if uid not in db:
        db[uid] = {"elo": 1000, "wins": 0, "money": 500, "xp": 0, "lvl": 1, "k": 0, "d": 0, "warns": 0}
    return db[uid]

# --- 3. АВТО-ФИЛЬТР И ОПЫТ ---
@bot.event
async def on_message(msg):
    if msg.author.bot: return
    if any(w in msg.content.lower() for w in BAD_WORDS):
        await msg.delete()
        return await msg.channel.send(f"🚫 {msg.author.mention}, следи за языком!", delete_after=5)
    
    u = get_u(msg.author.id)
    u['xp'] += random.randint(5, 12)
    if u['xp'] >= u['lvl'] * 100:
        u['lvl'] += 1
        await msg.channel.send(f"🆙 {msg.author.mention} поднял уровень до **{u['lvl']}**!")
    await bot.process_commands(msg)

# --- 4. КОМАНДА РЕЗУЛЬТАТА (ВСТРОЕННЫЙ ИИ) ---
@bot.command()
async def result(ctx):
    """1. ИИ сканирует скриншот сам"""
    if not ctx.message.attachments:
        return await ctx.send("❌ Прикрепи скриншот таблицы!")
    
    wait = await ctx.send("👁️ **ИИ Evolution сканирует скриншот (без ключей)...**")
    
    try:
        url = ctx.message.attachments[0].url
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        
        # Считываем текст
        text = pytesseract.image_to_string(img, lang='eng+rus').lower()
        
        # Ищем K/D/A (три числа подряд)
        stats = re.findall(r'(\d+)[\s/](\d+)[\s/](\d+)', text)
        k, a, d = (0, 0, 0)
        if stats:
            k, a, d = stats[0]

        # Ищем победу
        is_win = any(w in text for w in ["victory", "win", "победа", "winner"])
        elo_val = 25 if is_win else -20
        verdict = "ПОБЕДА ✅" if is_win else "ПОРАЖЕНИЕ/НЕЯСНО ⚠️"

        m_chan = bot.get_channel(int(MOD_ID))
        emb = discord.Embed(title="🤖 ИИ-ОТЧЕТ ПО СКРИНШОТУ", color=0x00ff00 if is_win else 0xff0000)
        emb.add_field(name="👤 Игрок", value=ctx.author.mention)
        emb.add_field(name="📊 Стата (К/А/D)", value=f"**{k} / {a} / {d}**")
        emb.add_field(name="🏆 Итог", value=verdict)
        emb.set_image(url=url)
        emb.set_footer(text=f"ID:{ctx.author.id}|ELO:{elo_val}|K:{k}|D:{d}")
        
        m = await m_chan.send(embed=emb)
        await m.add_reaction("✅"); await m.add_reaction("❌")
        await wait.edit(content=f"📡 Считано: `{k}/{a}/{d}`. Отправлено админам!")
        
    except Exception as e:
        await wait.edit(content="❌ Ошибка ИИ. Возможно, файл apt.txt не настроен на хостинге.")

# --- 5. КОМАНДЫ ДЛЯ ВСЕХ (ИГРА, ЭКОНОМИКА, ФАН) ---
@bot.command()
async def profile(ctx, m: discord.Member = None):
    """2. Профиль"""
    m = m or ctx.author; u = get_u(m.id)
    e = discord.Embed(title=f"👤 {m.name}", color=0x00ffcc)
    e.add_field(name="📈 ELO", value=u['elo']); e.add_field(name="⚔️ Kills", value=u['k'])
    e.add_field(name="✨ LVL", value=u['lvl']); e.add_field(name="💰 Cash", value=u['money'])
    await ctx.send(embed=e)

@bot.command()
async def top(ctx):
    """3. Топ игроков"""
    items = sorted(db.items(), key=lambda x: x[1]['elo'], reverse=True)[:10]
    res = "🏆 **ТОП-10 ХАБА:**\n"
    for i, (uid, info) in enumerate(items, 1): res += f"{i}. <@{uid}> — `{info['elo']}` ELO\n"
    await ctx.send(res or "Список пуст")

@bot.command()
async def work(ctx):
    """4. Работа"""; u = get_u(ctx.author.id); g = random.randint(100, 300); u['money'] += g
    await ctx.send(f"💰 Ты заработал {g} монет!")

@bot.command()
async def balance(ctx): """5. Баланс"""; await ctx.send(f"💵 Баланс: {get_u(ctx.author.id)['money']} монет")
@bot.command()
async def promo(ctx): """6. Промо"""; u = get_u(ctx.author.id); u['money'] += 1000; await ctx.send("🎁 +1000 монет!")
@bot.command()
async def shop(ctx): """7. Магазин"""; await ctx.send("🛒 1. VIP (5000) - `!buy 1`")
@bot.command()
async def coin(ctx): """8. Монетка"""; await ctx.send(f"🎲 {random.choice(['Орел', 'Решка'])}")
@bot.command()
async def roll(ctx, limit: int = 100): """9. Рандом"""; await ctx.send(f"🎲 {random.randint(1, limit)}")
@bot.command()
async def ball(ctx, *, q): """10. Шар"""; await ctx.send(f"🔮 {random.choice(['Да', 'Нет', 'Наверное'])}")
@bot.command()
async def hug(ctx, m: discord.Member): """11. Обнять"""; await ctx.send(f"🤗 {ctx.author.mention} обнял {m.mention}")
@bot.command()
async def avatar(ctx, m: discord.Member = None): """12. Ава"""; await ctx.send((m or ctx.author).display_avatar.url)
@bot.command()
async def server(ctx): """13. Сервер"""; await ctx.send(f"🏰 Участников: {ctx.guild.member_count}")
@bot.command()
async def ping(ctx): """14. Пинг"""; await ctx.send(f"🏓 `{round(bot.latency*1000)}ms`")
@bot.command()
async def check(ctx): """15. Статус"""; await ctx.send("🛰️ Система: ONLINE")
@bot.command()
async def rules(ctx): """16. Правила"""; await ctx.send("📜 Не спамить, не читерить!")
@bot.command()
async def ticket(ctx): """17. Тикет"""; await ctx.send("🆘 Админы вызваны!")
@bot.command()
async def admins(ctx): """18. Админы"""; await ctx.send("🛡️ Список: @Owner, @Moderator")
@bot.command()
async def buy(ctx, i: int): 
    """19. Купить"""; u = get_u(ctx.author.id)
    if i == 1 and u['money'] >= 5000: u['money'] -= 5000; await ctx.send("✅ Куплено!")
    else: await ctx.send("❌ Нет денег")

# --- 6. АДМИН КОМАНДЫ ---
@bot.command()
@commands.has_permissions(administrator=True)
async def give_elo(ctx, m: discord.Member, a: int): """20. Дать ELO"""; get_u(m.id)['elo'] += a; await ctx.send("✅")

@bot.command()
@commands.has_permissions(administrator=True)
async def set_elo(ctx, m: discord.Member, a: int): """21. Стат ELO"""; get_u(m.id)['elo'] = a; await ctx.send("⚙️")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, m: discord.Member): """22. Бан"""; await m.ban(); await ctx.send("🔨")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, a: int): """23. Чистка"""; await ctx.channel.purge(limit=a+1)

@bot.command()
@commands.has_permissions(administrator=True)
async def say(ctx, *, t): """24. Сказать"""; await ctx.message.delete(); await ctx.send(t)

@bot.command()
async def help(ctx):
    """25. Меню команд"""
    e = discord.Embed(title="🌌 Omega System Menu", color=0x5865f2)
    e.add_field(name="🎮 Игра", value="`!result`, `!profile`, `!top`, `!promo`", inline=False)
    e.add_field(name="💰 Эконом", value="`!work`, `!shop`, `!balance`, `!buy`", inline=False)
    e.add_field(name="✨ Разное", value="`!ping`, `!coin`, `!roll`, `!ball`, `!avatar`, `!rules`", inline=False)
    await ctx.send(embed=e)

# --- 7. ЛОГИКА КНОПОК ---
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or str(reaction.message.channel.id) != MOD_ID: return
    if not user.guild_permissions.manage_messages: return
    
    emb = reaction.message.embeds[0]
    data = dict(item.split(":") for item in emb.footer.text.split("|"))
    
    u = get_u(data['ID'])
    if str(reaction.emoji) == "✅":
        u['elo'] += int(data['ELO'])
        u['k'] += int(data['K'])
        u['wins'] += 1 if int(data['ELO']) > 0 else 0
        await reaction.message.channel.send(f"✅ Одобрено для <@{data['ID']}>")
    
    await reaction.message.delete()

keep_alive()
bot.run(TOKEN)
