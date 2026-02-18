import discord
from discord.ext import commands, tasks
import os, json, random, datetime, time, asyncio, logging
from flask import Flask
from threading import Thread

# ==============================================================================
# [1] СЕРВЕР ЖИЗНЕОБЕСПЕЧЕНИЯ (24/7 RENDER KEEP-ALIVE)
# ==============================================================================
app = Flask('')
@app.route('/')
def home(): return "Evolution Titan Core v20: SYSTEM ONLINE"
def run_web(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run_web, daemon=True).start()

# ==============================================================================
# [2] НАСТРОЙКИ И КОНФИГ
# ==============================================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')

TOKEN = os.getenv("DISCORD_TOKEN")
HUB_ID = os.getenv("HUB_ID")
PREFIX = "!"

# Настройки рангов (ELO)
RANKS = {
    "Bronze": 0, "Silver": 1200, "Gold": 1600,
    "Platinum": 2000, "Diamond": 2500, "Immortal": 3000
}

# Настройки магазина
SHOP = {
    "role_vip": {"type": "role", "price": 50000, "name": "V.I.P Status", "role_id": "create_role_vip"},
    "case_common": {"type": "case", "price": 2000, "name": "📦 Обычный кейс", "drop": [1000, 5000]},
    "case_rare": {"type": "case", "price": 10000, "name": "🔥 Редкий кейс", "drop": [5000, 25000]},
    "license_gun": {"type": "item", "price": 5000, "name": "🔫 Лицензия на оружие", "desc": "Позволяет делать !crime без штрафа"}
}

# ==============================================================================
# [3] БАЗА ДАННЫХ (TITAN DB ENGINE)
# ==============================================================================
class Database:
    def __init__(self, file="titan_core.json"):
        self.file = file
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.file):
            try:
                with open(self.file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: return {}
        return {}

    def save(self):
        try:
            with open(self.file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Save Error: {e}")

    def get(self, uid):
        uid = str(uid)
        if uid not in self.data:
            self.data[uid] = {
                "elo": 1000, "money": 1000, "bank": 0,
                "lvl": 1, "xp": 0,
                "stats": {"k": 0, "a": 0, "d": 0, "w": 0, "l": 0},
                "timers": {"work": 0, "crime": 0, "daily": 0},
                "inventory": [],
                "streak": 0
            }
            self.save()
        return self.data[uid]

db = Database()

# ==============================================================================
# [4] УТИЛИТЫ И ПОМОЩНИКИ
# ==============================================================================
bot = commands.Bot(command_prefix=PREFIX, intents=discord.Intents.all(), help_command=None)

def get_rank_name(elo):
    current = "Bronze"
    for r, v in RANKS.items():
        if elo >= v: current = r
    return current

def create_bar(current, total, length=10):
    percent = min(current / total, 1.0)
    filled = int(percent * length)
    return "🟦" * filled + "⬜" * (length - filled)

async def check_roles(member, elo):
    if not member: return
    rank_name = get_rank_name(elo)
    role = discord.utils.get(member.guild.roles, name=rank_name)
    if role and role not in member.roles:
        to_remove = [r for r in member.roles if r.name in RANKS]
        await member.remove_roles(*to_remove)
        await member.add_roles(role)

# ==============================================================================
# [5] ИГРОВОЙ МОДУЛЬ (RESULT & HUB)
# ==============================================================================
@bot.command()
async def result(ctx, k: int, a: int, d: int, res: str = "win"):
    if not ctx.message.attachments:
        return await ctx.send("❌ **ОШИБКА:** Нет скриншота! Прикрепите доказательство.")
    
    if not HUB_ID: return await ctx.send("❌ **System Error:** HUB_ID не настроен.")
    hub = bot.get_channel(int(HUB_ID))
    
    status = res.lower()
    elo_calc = 25 if status == "win" else -20
    color = 0x2ecc71 if status == "win" else 0xe74c3c

    emb = discord.Embed(title="📡 ВХОДЯЩИЙ ОТЧЕТ", color=color, timestamp=datetime.datetime.now())
    emb.set_author(name=f"Agent: {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
    emb.add_field(name="ИСХОД", value=f"**{status.upper()}**", inline=True)
    emb.add_field(name="РЕЙТИНГ", value=f"{'+' if elo_calc > 0 else ''}{elo_calc}", inline=True)
    emb.add_field(name="K / A / D", value=f"```\n{k} / {a} / {d}\n```", inline=False)
    emb.set_image(url=ctx.message.attachments[0].url)
    emb.set_footer(text=f"PAYLOAD:{ctx.author.id}|{elo_calc}|{k}|{a}|{d}")

    msg = await hub.send(embed=emb)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    await ctx.send(f"✅ {ctx.author.mention}, отчет отправлен в HUB.")

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot: return
    if str(reaction.message.channel.id) != str(HUB_ID): return
    if not user.guild_permissions.manage_messages: return

    emb = reaction.message.embeds[0]
    if not emb.footer.text or "PAYLOAD:" not in emb.footer.text: return

    try:
        data = emb.footer.text.split("PAYLOAD:")[1].split("|")
        uid, elo_add, k, a, d = int(data[0]), int(data[1]), int(data[2]), int(data[3]), int(data[4])
    except: return

    u = db.get(uid)
    memb = reaction.message.guild.get_member(uid)

    if str(reaction.emoji) == "✅":
        u['elo'] += elo_add
        u['stats']['k'] += k; u['stats']['a'] += a; u['stats']['d'] += d
        if elo_add > 0: u['stats']['w'] += 1
        else: u['stats']['l'] += 1
        db.save()
        if memb: await check_roles(memb, u['elo'])
        await reaction.message.channel.send(f"✅ **ОДОБРЕНО:** <@{uid}> (Elo: {u['elo']})")
        await reaction.message.delete()
    
    elif str(reaction.emoji) == "❌":
        await reaction.message.channel.send(f"❌ **ОТКЛОНЕНО:** <@{uid}>")
        await reaction.message.delete()

# ==============================================================================
# [6] ЭКОНОМИКА: РАБОТА, КРИМИНАЛ, ЕЖЕДНЕВКИ
# ==============================================================================
@bot.command()
async def work(ctx):
    u = db.get(ctx.author.id)
    if time.time() < u['timers']['work']:
        rem = int(u['timers']['work'] - time.time())
        return await ctx.send(f"⏳ **Отдыхай:** {rem//60}м {rem%60}с")

    earn = random.randint(500, 1500) * u['lvl'] # Чем выше лвл, тем больше денег
    u['money'] += earn
    u['timers']['work'] = time.time() + 600
    db.save()
    
    emb = discord.Embed(description=f"🔨 Ты отработал смену и получил **{earn}$**", color=0x00ff00)
    await ctx.send(embed=emb)

@bot.command()
async def crime(ctx):
    u = db.get(ctx.author.id)
    if time.time() < u['timers']['crime']:
        return await ctx.send("⏳ Полиция ищет тебя. Жди.")
    
    chance = 40 if "license_gun" not in u['inventory'] else 60
    
    if random.randint(1, 100) < chance:
        earn = random.randint(2000, 5000)
        u['money'] += earn
        msg = f"🔫 **УСПЕХ!** Ты ограбил ларек и вынес **{earn}$**"
        color = 0x000000
    else:
        fine = random.randint(500, 1000)
        u['money'] -= fine
        msg = f"🚓 **ВАС ПОВЯЗАЛИ!** Штраф: **{fine}$**"
        color = 0xff0000
    
    u['timers']['crime'] = time.time() + 1200
    db.save()
    await ctx.send(embed=discord.Embed(description=msg, color=color))

@bot.command()
async def daily(ctx):
    u = db.get(ctx.author.id)
    now = time.time()
    if now < u['timers']['daily']:
        return await ctx.send("❌ Ты уже получал бонус сегодня.")
    
    u['streak'] += 1
    bonus = 1000 + (u['streak'] * 100)
    if bonus > 5000: bonus = 5000
    
    u['money'] += bonus
    u['timers']['daily'] = now + 86400
    db.save()
    await ctx.send(f"📅 **ЕЖЕДНЕВКА:** +{bonus}$ (Стрик: {u['streak']} дн.)")

@bot.command()
async def transfer(ctx, member: discord.Member, amount: int):
    sender = db.get(ctx.author.id)
    receiver = db.get(member.id)
    
    if amount <= 0 or sender['money'] < amount:
        return await ctx.send("❌ Недостаточно средств.")
    
    sender['money'] -= amount
    receiver['money'] += amount
    db.save()
    await ctx.send(f"💸 **ПЕРЕВОД:** {ctx.author.mention} перевел **{amount}$** -> {member.mention}")

# ==============================================================================
# [7] ИНВЕНТАРЬ И МАГАЗИН
# ==============================================================================
@bot.command()
async def shop(ctx):
    emb = discord.Embed(title="🛒 ЧЕРНЫЙ РЫНОК", color=0x2b2d31)
    for key, item in SHOP.items():
        price = item['price']
        name = item['name']
        emb.add_field(name=f"{name}", value=f"Цена: `{price}$`\nID: `{key}`", inline=False)
    emb.set_footer(text="Купить: !buy [ID]")
    await ctx.send(embed=emb)

@bot.command()
async def buy(ctx, item_id: str):
    u = db.get(ctx.author.id)
    if item_id not in SHOP: return await ctx.send("❌ Такого товара нет.")
    
    item = SHOP[item_id]
    if u['money'] < item['price']: return await ctx.send("❌ Нет денег.")
    
    if item['type'] == 'role':
        # Логика выдачи роли (нужно настроить role_id)
        await ctx.send("✅ Роль куплена (функция требует настройки ID ролей).")
    elif item['type'] == 'case':
        u['money'] -= item['price']
        win = random.randint(item['drop'][0], item['drop'][1])
        u['money'] += win
        await ctx.send(f"📦 Вы открыли кейс и нашли **{win}$**!")
    else:
        u['money'] -= item['price']
        u['inventory'].append(item_id)
        await ctx.send(f"✅ Вы купили **{item['name']}**")
    
    db.save()

@bot.command()
async def inventory(ctx):
    u = db.get(ctx.author.id)
    if not u['inventory']: return await ctx.send("🎒 Твой рюкзак пуст.")
    
    items = [SHOP[i]['name'] for i in u['inventory'] if i in SHOP]
    await ctx.send(embed=discord.Embed(title="🎒 ИНВЕНТАРЬ", description="\n".join(items), color=0xffa500))

# ==============================================================================
# [8] КАЗИНО (СЛОТЫ И КОСТИ)
# ==============================================================================
@bot.command()
async def slots(ctx, amount: int):
    u = db.get(ctx.author.id)
    if amount > u['money'] or amount <= 0: return await ctx.send("❌ Некорректная ставка.")
    
    emojis = ["🍒", "🍋", "🍇", "7️⃣", "💎"]
    a, b, c = random.choice(emojis), random.choice(emojis), random.choice(emojis)
    
    msg = f"🎰 **SLOTS**\n> | {a} | {b} | {c} |"
    
    if a == b == c:
        win = amount * 5
        u['money'] += win
        msg += f"\n\n💰 **JACKPOT!** Выигрыш: {win}$"
    elif a == b or b == c or a == c:
        win = amount * 2
        u['money'] += win
        msg += f"\n\n💵 **Win!** Выигрыш: {win}$"
    else:
        u['money'] -= amount
        msg += f"\n\n📉 **Lose.** -{amount}$"
    
    db.save()
    await ctx.send(embed=discord.Embed(description=msg, color=0xf1c40f))

# ==============================================================================
# [9] ПРОФИЛЬ И XP (ГРАФИКА)
# ==============================================================================
@bot.event
async def on_message(message):
    if message.author.bot: return
    await bot.process_commands(message)
    
    # Система XP
    u = db.get(message.author.id)
    u['xp'] += random.randint(5, 15)
    needed = u['lvl'] * 500
    
    if u['xp'] >= needed:
        u['lvl'] += 1
        u['xp'] = 0
        reward = u['lvl'] * 1000
        u['money'] += reward
        db.save()
        await message.channel.send(f"🆙 **LEVEL UP!** {message.author.mention} апнул **{u['lvl']}** ур. (+{reward}$)")
    db.save()

@bot.command()
async def profile(ctx, member: discord.Member = None):
    member = member or ctx.author
    u = db.get(member.id)
    
    rank = get_rank_name(u['elo'])
    needed = u['lvl'] * 500
    bar = create_bar(u['xp'], needed)
    
    stats = u['stats']
    kda = f"{stats['k']}/{stats['a']}/{stats['d']}"
    
    emb = discord.Embed(title=f"👤 DOSSIER: {member.name.upper()}", color=0x3498db)
    emb.set_thumbnail(url=member.display_avatar.url)
    
    emb.add_field(name="🏆 RANK", value=f"`{rank}`\nELO: **{u['elo']}**", inline=True)
    emb.add_field(name="💰 FINANCE", value=f"Cash: **{u['money']}$**\nBank: **{u['bank']}$**", inline=True)
    emb.add_field(name="⚔️ COMBAT", value=f"KDA: `{kda}`\nWins: `{stats['w']}`", inline=True)
    
    emb.add_field(name=f"⚡ LEVEL {u['lvl']}", value=f"`{bar}` {u['xp']}/{needed}", inline=False)
    
    await ctx.send(embed=emb)

# ==============================================================================
# [10] ПОМОЩЬ И АДМИНКА
# ==============================================================================
@bot.command()
async def help(ctx):
    emb = discord.Embed(title="💠 TITAN OS HELP", description="Ver 20.0 | Full Access", color=0x2b2d31)
    
    emb.add_field(name="🎮 MAIN", value="`!profile` `!result` `!top`", inline=True)
    emb.add_field(name="💵 MONEY", value="`!work` `!crime` `!daily` `!transfer`", inline=True)
    emb.add_field(name="🎰 FUN", value="`!slots` `!shop` `!buy` `!inventory`", inline=True)
    
    if ctx.author.guild_permissions.administrator:
        emb.add_field(name="👑 ADMIN", value="`!give_money @user [val]`\n`!set_elo @user [val]`", inline=False)
    
    await ctx.send(embed=emb)

@bot.command()
@commands.has_permissions(administrator=True)
async def give_money(ctx, member: discord.Member, amount: int):
    u = db.get(member.id)
    u['money'] += amount
    db.save()
    await ctx.send(f"✅ Выдано **{amount}$** пользователю {member.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def set_elo(ctx, member: discord.Member, amount: int):
    u = db.get(member.id)
    u['elo'] = amount
    db.save()
    await check_roles(member, amount)
    await ctx.send(f"✅ ELO пользователя {member.mention} установлено на **{amount}**")

# ==============================================================================
# [11] ОБРАБОТЧИК ОШИБОК (АНТИ-БАГ)
# ==============================================================================
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ **Cooldown:** {round(error.retry_after, 1)} сек.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ **Доступ запрещен.**")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ **Ошибка:** Не указаны аргументы команды.")
    else:
        print(f"ERROR: {error}") # Лог в консоль, чтобы не спамить в чат

# ==============================================================================
# ЗАПУСК
# ==============================================================================
@bot.event
async def on_ready():
    print(f"""
    ╔═══════════════════════════════════════╗
    ║      EVOLUTION TITAN CORE v20         ║
    ║      STATUS: ONLINE & READY           ║
    ║      LOGGED AS: {bot.user}      ║
    ╚═══════════════════════════════════════╝
    """)
    stay_active.start()

@tasks.loop(minutes=5)
async def stay_active():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="!help | Evolution"))

if __name__ == "__main__":
    keep_alive()
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"CRITICAL STARTUP ERROR: {e}")
