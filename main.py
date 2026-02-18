import discord
from discord.ext import commands, tasks
import os, random, datetime, asyncio
from flask import Flask
from threading import Thread

# --- 1. СИСТЕМА ВЕЧНОЙ РАБОТЫ (ANTI-SLEEP) ---
app = Flask('')
@app.route('/')
def home(): return "Evolution Mega-System: Online"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- 2. НАСТРОЙКИ ---
TOKEN = os.getenv("DISCORD_TOKEN")
MOD_ID = os.getenv("HUB_ID") 

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

db = {} # База данных (в памяти)

def get_u(uid):
    uid = str(uid)
    if uid not in db:
        db[uid] = {
            "elo": 1000, "wins": 0, "losses": 0, "k": 0, "a": 0, "d": 0, 
            "money": 1000, "xp": 0, "lvl": 1, "inv": [], "warns": 0
        }
    return db[uid]

# --- 3. ЦИКЛ АКТИВНОСТИ (ЧТОБЫ НЕ ВЫЛЕТАЛ) ---
@tasks.loop(minutes=3)
async def stay_active():
    now = datetime.datetime.now().strftime("%H:%M")
    await bot.change_presence(activity=discord.Streaming(name=f"HUB | {now}", url="https://twitch.tv/404"))

# --- 4. СОБЫТИЯ И АВТО-МОДЕР ---
BAD_WORDS = ["хуй", "сука", "пидор", "еблан", "гандон", "мразь"]

@bot.event
async def on_ready():
    print(f"✅ Бот {bot.user.name} вошел в сеть!")
    stay_active.start()

@bot.event
async def on_message(msg):
    if msg.author.bot: return
    
    # Фильтр мата
    if any(w in msg.content.lower() for w in BAD_WORDS):
        try:
            await msg.delete()
            return await msg.channel.send(f"🚫 {msg.author.mention}, не матерись!", delete_after=5)
        except: pass

    # Система опыта
    u = get_u(msg.author.id)
    u['xp'] += random.randint(5, 15)
    if u['xp'] >= u['lvl'] * 150:
        u['lvl'] += 1
        u['xp'] = 0
        u['money'] += 2000
        await msg.channel.send(f"🎊 **LVL UP!** {msg.author.mention} достиг **{u['lvl']} уровня**! Награда: **2000$**")
    
    await bot.process_commands(msg)

# --- 5. КРАСИВОЕ МЕНЮ HELP ---
@bot.command()
async def help(ctx):
    emb = discord.Embed(title="📜 МЕНЮ КОМАНД EVOLUTION", color=0x5865f2, timestamp=datetime.datetime.now())
    emb.set_thumbnail(url=bot.user.display_avatar.url)
    
    emb.add_field(name="🎮 ГЕЙМИНГ & РЕЙТИНГ", value=(
        "`!result K A D win/loss` — Отправить результат со скрином\n"
        "`!profile [@user]` — Посмотреть профиль и статистику\n"
        "`!top` — Топ-10 игроков по ELO рейтингу\n"
        "`!elo` — Твой текущий рейтинг"
    ), inline=False)
    
    emb.add_field(name="💰 ЭКОНОМИКА & ИГРЫ", value=(
        "`!work` — Пойти работать (раз в 10 мин)\n"
        "`!daily` — Забрать ежедневную награду\n"
        "`!casino [ставка]` — Испытать удачу (55% шанс)\n"
        "`!shop` — Открыть магазин товаров\n"
        "`!buy [название]` — Купить предмет из магазина"
    ), inline=False)
    
    emb.add_field(name="🛠️ МОДЕРАЦИЯ & СЕРВИС", value=(
        "`!clear [число]` — Удалить сообщения\n"
        "`!warn [@user]` — Выдать предупреждение\n"
        "`!ping` — Проверить задержку бота\n"
        "`!add_money [@user] [число]` — Выдать валюту (Админ)"
    ), inline=False)
    
    emb.set_footer(text=f"Запросил: {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=emb)

# --- 6. КОМАНДЫ РЕЙТИНГА ---
@bot.command()
async def result(ctx, k: int, a: int, d: int, status: str = "win"):
    if not ctx.message.attachments:
        return await ctx.send("❌ Прикрепи скриншот таблицы!")
    
    elo_change = 25 if status.lower() == "win" else -20
    m_chan = bot.get_channel(int(MOD_ID))
    
    if not m_chan: return await ctx.send("❌ Настрой HUB_ID в Render!")

    emb = discord.Embed(title="⚔️ НОВАЯ ПРОВЕРКА", color=0x7289da)
    emb.add_field(name="👤 Игрок", value=ctx.author.mention, inline=True)
    emb.add_field(name="🏆 Итог", value=status.upper(), inline=True)
    emb.add_field(name="📊 Стата", value=f"**{k} / {a} / {d}**", inline=False)
    emb.set_image(url=ctx.message.attachments[0].url)
    emb.set_footer(text=f"ID:{ctx.author.id}|ELO:{elo_change}|K:{k}|A:{a}|D:{d}")

    msg = await m_chan.send(embed=emb)
    for r in ["✅", "❌"]: await msg.add_reaction(r)
    await ctx.send(f"📡 Данные `{k}/{a}/{d}` отправлены в HUB!")

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or str(reaction.message.channel.id) != MOD_ID: return
    if not user.guild_permissions.manage_messages: return
    
    emb = reaction.message.embeds[0]
    data = dict(item.split(":") for item in emb.footer.text.split("|"))
    u = get_u(data['ID'])

    if str(reaction.emoji) == "✅":
        u['elo'] += int(data['ELO'])
        u['k'] += int(data['K']); u['a'] += int(data['A']); u['d'] += int(data['D'])
        if int(data['ELO']) > 0: u['wins'] += 1
        else: u['losses'] += 1
        await reaction.message.channel.send(f"✅ Подтверждено для <@{data['ID']}>!")
    elif str(reaction.emoji) == "❌":
        await reaction.message.channel.send(f"❌ Отклонено для <@{data['ID']}>.")
    await reaction.message.delete()

# --- 7. ЭКОНОМИКА ---
@bot.command()
async def work(ctx):
    u = get_u(ctx.author.id)
    gain = random.randint(300, 900)
    u['money'] += gain
    await ctx.send(f"⛏️ {ctx.author.mention}, ты отработал и получил **{gain}$**")

@bot.command()
async def casino(ctx, bet: int):
    u = get_u(ctx.author.id)
    if bet > u['money'] or bet <= 0: return await ctx.send("❌ Недостаточно средств!")
    if random.random() > 0.45:
        u['money'] += bet
        await ctx.send(f"🎰 **ПОБЕДА!** Ты выиграл **{bet}$**. Баланс: {u['money']}$")
    else:
        u['money'] -= bet
        await ctx.send(f"📉 **ЛУЗ!** Ты проиграл **{bet}$**. Баланс: {u['money']}$")

SHOP_ITEMS = {"VIP-Статус": 20000, "Премиум-Кейс": 10000, "Ник-Цвет": 5000}

@bot.command()
async def shop(ctx):
    e = discord.Embed(title="🛒 МАГАЗИН", color=0xffd700)
    for i, p in SHOP_ITEMS.items(): e.add_field(name=i, value=f"Цена: `{p}$`", inline=False)
    await ctx.send(embed=e)

@bot.command()
async def buy(ctx, *, item: str):
    u = get_u(ctx.author.id)
    if item in SHOP_ITEMS and u['money'] >= SHOP_ITEMS[item]:
        u['money'] -= SHOP_ITEMS[item]; u['inv'].append(item)
        await ctx.send(f"🛍️ Куплено: **{item}**!")
    else: await ctx.send("❌ Ошибка покупки.")

# --- 8. ПРОФИЛЬ И СТАТИСТИКА ---
@bot.command()
async def profile(ctx, m: discord.Member = None):
    m = m or ctx.author; u = get_u(m.id)
    e = discord.Embed(title=f"👤 ПРОФИЛЬ: {m.name}", color=0x00ffcc)
    e.add_field(name="📈 ELO", value=f"**{u['elo']}**", inline=True)
    e.add_field(name="✨ LVL", value=f"**{u['lvl']}**", inline=True)
    e.add_field(name="💰 БАЛАНС", value=f"**{u['money']}$**", inline=True)
    e.add_field(name="⚔️ K/A/D", value=f"`{u['k']} / {u['a']} / {u['d']}`", inline=False)
    e.add_field(name="🏆 МАТЧИ", value=f"Побед: {u['wins']} | Поражений: {u['losses']}")
    e.set_thumbnail(url=m.display_avatar.url)
    await ctx.send(embed=e)

# --- 9. АДМИНКА ---
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 10):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🗑️ Удалено **{amount}** сообщений.", delete_after=3)

@bot.command()
@commands.has_permissions(administrator=True)
async def add_money(ctx, m: discord.Member, amount: int):
    get_u(m.id)['money'] += amount
    await ctx.send(f"✅ Выдано **{amount}$** игроку {m.mention}")

@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Понг! `{round(bot.latency * 1000)}ms`")

# --- ЗАПУСК ---
keep_alive()
bot.run(TOKEN)
