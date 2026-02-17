import discord
from discord.ext import commands
import os, random, datetime, asyncio
from flask import Flask
from threading import Thread

# --- 1. СИСТЕМА ЖИЗНЕОБЕСПЕЧЕНИЯ (ДЛЯ RENDER) ---
app = Flask('')
@app.route('/')
def home(): return "Evolution Mega-System: Online & Stable"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- 2. ИНИЦИАЛИЗАЦИЯ И НАСТРОЙКИ ---
TOKEN = os.getenv("DISCORD_TOKEN")
MOD_ID = os.getenv("HUB_ID") 

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Глобальная база данных (в оперативной памяти)
db = {}

def get_u(uid):
    uid = str(uid)
    if uid not in db:
        db[uid] = {
            "elo": 1000, "wins": 0, "losses": 0, 
            "k": 0, "a": 0, "d": 0, 
            "money": 1000, "xp": 0, "lvl": 1, 
            "inv": [], "last_work": None
        }
    return db[uid]

# --- 3. АВТО-МОДЕРАЦИЯ И СИСТЕМА УРОВНЕЙ ---
BAD_WORDS = ["хуй", "сука", "пидор", "еблан", "гандон", "мразь"]

@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user.name} готов к уничтожению багов!")
    await bot.change_presence(activity=discord.Game(name="Evolution | !help"))

@bot.event
async def on_message(msg):
    if msg.author.bot: return
    
    # Моментальный фильтр мата
    if any(w in msg.content.lower() for w in BAD_WORDS):
        try:
            await msg.delete()
            return await msg.channel.send(f"🚫 {msg.author.mention}, фильтруй базар!", delete_after=5)
        except: pass

    # Прокачка уровня за общение
    u = get_u(msg.author.id)
    u['xp'] += random.randint(5, 15)
    xp_to_lvl = u['lvl'] * 150
    if u['xp'] >= xp_to_lvl:
        u['lvl'] += 1
        u['xp'] = 0
        u['money'] += 2000
        await msg.channel.send(f"🎊 {msg.author.mention} апнул **{u['lvl']} LVL**! Лови бонус **2000$**")
    
    await bot.process_commands(msg)

# --- 4. СИСТЕМА ПРОВЕРКИ РЕЗУЛЬТАТОВ (БЕЗ ГЛЮКОВ ИИ) ---
@bot.command()
async def result(ctx, k: int, a: int, d: int, status: str = "win"):
    """
    Отправка статки: !result [Убийства] [Ассисты] [Смерти] [win/loss] + СКРИН
    """
    if not ctx.message.attachments:
        return await ctx.send("❌ А где скриншот? Прикрепи таблицу результатов!")

    # Расчет рейтинга
    elo_change = 25 if status.lower() == "win" else -20
    m_chan = bot.get_channel(int(MOD_ID))
    
    if not m_chan:
        return await ctx.send("❌ Ошибка: Проверь HUB_ID в настройках Render!")

    # Формируем тикет для админа
    emb = discord.Embed(title="🛡️ НОВАЯ ПРОВЕРКА СТАТИСТИКИ", color=0x7289da, timestamp=datetime.datetime.now())
    emb.add_field(name="👤 Игрок", value=ctx.author.mention, inline=True)
    emb.add_field(name="🏆 Итог", value=status.upper(), inline=True)
    emb.add_field(name="📊 Введенные данные", value=f"K/A/D: **{k} / {a} / {d}**", inline=False)
    emb.set_image(url=ctx.message.attachments[0].url)
    # Прячем инфу в футер для кнопок
    emb.set_footer(text=f"ID:{ctx.author.id}|ELO:{elo_change}|K:{k}|A:{a}|D:{d}")

    msg = await m_chan.send(embed=emb)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    await ctx.send(f"📡 Данные `{k}/{a}/{d}` улетели админам. Жди галочку!")

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or str(reaction.message.channel.id) != MOD_ID: return
    if not user.guild_permissions.manage_messages: return
    
    emb = reaction.message.embeds[0]
    try:
        data = dict(item.split(":") for item in emb.footer.text.split("|"))
    except: return

    u = get_u(data['ID'])

    if str(reaction.emoji) == "✅":
        u['elo'] += int(data['ELO'])
        u['k'] += int(data['K']); u['a'] += int(data['A']); u['d'] += int(data['D'])
        if int(data['ELO']) > 0: u['wins'] += 1
        else: u['losses'] += 1
        await reaction.message.channel.send(f"✅ Стата игрока <@{data['ID']}> подтверждена. ELO: **{u['elo']}**")
    
    elif str(reaction.emoji) == "❌":
        await reaction.message.channel.send(f"❌ Заявка игрока <@{data['ID']}> отклонена админом.")
    
    await reaction.message.delete()

# --- 5. ЭКОНОМИКА, КАЗИНО И МАГАЗИН ---
@bot.command()
async def work(ctx):
    u = get_u(ctx.author.id)
    earn = random.randint(300, 800)
    u['money'] += earn
    await ctx.send(f"⛏️ {ctx.author.mention}, ты отпахал смену и заработал **{earn}$**")

@bot.command()
async def casino(ctx, bet: int):
    u = get_u(ctx.author.id)
    if bet > u['money'] or bet <= 0: return await ctx.send("❌ Не хватает бабла!")
    
    if random.random() > 0.55:
        u['money'] += bet
        await ctx.send(f"🎰 **ПОБЕДА!** Ты поднял **{bet}$**. Баланс: {u['money']}$")
    else:
        u['money'] -= bet
        await ctx.send(f"📉 **ЛУЗ!** Ты слил **{bet}$**. Баланс: {u['money']}$")

SHOP = {"VIP-Статус": 15000, "Смена-Ника": 5000, "Кейс-Удачи": 3000}

@bot.command()
async def shop(ctx):
    e = discord.Embed(title="🛒 Магазин Evolution", color=0xffd700)
    for item, price in SHOP.items():
        e.add_field(name=item, value=f"Цена: `{price}$`", inline=False)
    e.set_footer(text="Купить: !buy [название]")
    await ctx.send(embed=e)

@bot.command()
async def buy(ctx, *, item: str):
    u = get_u(ctx.author.id)
    if item in SHOP:
        if u['money'] >= SHOP[item]:
            u['money'] -= SHOP[item]
            u['inv'].append(item)
            await ctx.send(f"🛍️ Успешно куплено: **{item}**!")
        else: await ctx.send("❌ Иди работай, денег нет!")
    else: await ctx.send("❌ Такого товара нет в списке.")

# --- 6. СТАТИСТИКА И ТОП ---
@bot.command()
async def profile(ctx, m: discord.Member = None):
    m = m or ctx.author; u = get_u(m.id)
    e = discord.Embed(title=f"👤 Профиль {m.name}", color=0x00ffcc)
    e.add_field(name="📈 Рейтинг", value=f"**{u['elo']} ELO**", inline=True)
    e.add_field(name="✨ Уровень", value=f"**{u['lvl']} LVL**", inline=True)
    e.add_field(name="💰 Кошелек", value=f"**{u['money']}$**", inline=True)
    e.add_field(name="⚔️ K / A / D", value=f"`{u['k']} / {u['a']} / {u['d']}`", inline=False)
    e.add_field(name="🏆 Матчи", value=f"W: {u['wins']} | L: {u['losses']}")
    e.set_thumbnail(url=m.display_avatar.url)
    await ctx.send(embed=e)

@bot.command()
async def top(ctx):
    items = sorted(db.items(), key=lambda x: x[1]['elo'], reverse=True)[:10]
    res = "🏆 **ТОП-10 ИГРОКОВ ПО ELO:**\n"
    for i, (uid, info) in enumerate(items, 1):
        res += f"{i}. <@{uid}> — `{info['elo']}` ELO\n"
    await ctx.send(res or "Топ пуст.")

# --- 7. АДМИН-ПАНЕЛЬ ---
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 10):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🗑️ Снесено **{amount}** сообщений.", delete_after=3)

@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Пинг: `{round(bot.latency * 1000)}ms`")

@bot.command()
async def help(ctx):
    e = discord.Embed(title="📜 СПИСОК КОМАНД", color=0x5865f2)
    e.add_field(name="🎮 ИГРА", value="`!result K A D win/loss` (со скрином)\n`!profile`, `!top`", inline=False)
    e.add_field(name="💰 ЭКОНОМИКА", value="`!work`, `!shop`, `!buy`, `!casino`", inline=False)
    e.add_field(name="🛠️ СЕРВИС", value="`!ping`, `!clear`", inline=False)
    await ctx.send(embed=e)

# --- ЗАПУСК ---
keep_alive()
bot.run(TOKEN)
