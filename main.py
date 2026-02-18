import discord
from discord.ext import commands, tasks
import os, random, datetime, time, json, asyncio, logging
from flask import Flask
from threading import Thread

# ==========================================
# [1] СЕРВЕР ДЛЯ RENDER (24/7)
# ==========================================
app = Flask('')
@app.route('/')
def home(): return "Evolution Engine v11: Operational"
def run_web(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run_web, daemon=True).start()

# ==========================================
# [2] НАСТРОЙКА ЛОГИРОВАНИЯ
# ==========================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger('Evolution')

# ==========================================
# [3] УПРАВЛЕНИЕ ДАННЫМИ (JSON ENGINE)
# ==========================================
class Database:
    def __init__(self, path="main_db.json"):
        self.path = path
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"DB Load Error: {e}")
                return {}
        return {}

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"DB Save Error: {e}")

    def get_user(self, uid):
        uid = str(uid)
        if uid not in self.data:
            self.data[uid] = {
                "name": "Unknown",
                "elo": 1000, "money": 5000,
                "xp": 0, "lvl": 1,
                "k": 0, "a": 0, "d": 0,
                "w": 0, "l": 0,
                "last_work": 0, "last_daily": 0,
                "clan": None, "inv": []
            }
            self.save()
        return self.data[uid]

db = Database()

# ==========================================
# [4] КОНФИГУРАЦИЯ И ПЕРЕМЕННЫЕ
# ==========================================
TOKEN = os.getenv("DISCORD_TOKEN")
HUB_ID = os.getenv("HUB_ID")
PREFIX = "!"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# Настройки рангов
RANK_MAP = {
    "🌑 Bronze": 0,
    "🥈 Silver": 1200,
    "🔱 Gold": 1550,
    "💎 Platinum": 1900,
    "👑 Diamond": 2300,
    "🔥 Immortal": 2800
}

SHOP_ITEMS = {
    "V.I.P": 50000,
    "Premium": 150000,
    "Legend": 500000
}

# ==========================================
# [5] УТИЛИТЫ И ВИЗУАЛ
# ==========================================
def get_xp_needed(lvl):
    return lvl * 500

async def add_xp(uid, amount):
    u = db.get_user(uid)
    u['xp'] += amount
    needed = get_xp_needed(u['lvl'])
    if u['xp'] >= needed:
        u['xp'] -= needed
        u['lvl'] += 1
        db.save()
        return True
    db.save()
    return False

async def sync_roles(member, elo):
    if not member or isinstance(member, discord.User): return
    target = "🌑 Bronze"
    for r, v in RANK_MAP.items():
        if elo >= v: target = r
    
    role = discord.utils.get(member.guild.roles, name=target)
    if role and role not in member.roles:
        to_rem = [r for r in member.roles if r.name in RANK_MAP]
        await member.remove_roles(*to_rem)
        await member.add_roles(role)

# ==========================================
# [6] КРАСИВЫЙ ИНТЕРФЕЙС HELP
# ==========================================
@bot.command()
async def help(ctx):
    emb = discord.Embed(title="💠 EVOLUTION ULTIMATE CORE v11", color=0x2b2d31)
    emb.set_thumbnail(url=bot.user.display_avatar.url)
    
    emb.description = (
        "```fix\nСИСТЕМА СЕРВЕРА АКТИВНА\n```\n"
        "**🎮 OPERATIONS**\n"
        "• `!result K A D win/loss` — Отправить отчет\n"
        "• `!profile [@user]` — Личная статистика\n"
        "• `!top` — Глобальный лидерборд\n\n"
        "**💰 ECONOMY**\n"
        "• `!work` — Начать смену\n"
        "• `!daily` — Ежедневная награда\n"
        "• `!casino [sum]` — Азартные игры\n"
        "• `!shop` — Магазин ролей\n\n"
        "**🛠️ ADMIN**\n"
        "• `!set_elo` • `!set_money` • `!clear`"
    )
    
    emb.set_footer(text=f"User: {ctx.author.name} | Latency: {round(bot.latency*1000)}ms")
    await ctx.send(embed=emb)

# ==========================================
# [7] ИГРОВАЯ ЛОГИКА (RESULT & HUB)
# ==========================================
@bot.command()
async def result(ctx, k: int, a: int, d: int, res: str = "win"):
    if not ctx.message.attachments:
        return await ctx.send("❌ **ОШИБКА:** Скриншот обязателен!")

    chan = bot.get_channel(int(HUB_ID))
    if not chan: return await ctx.send("❌ HUB не найден.")

    diff = 25 if res.lower() == "win" else -20
    color = 0x2ecc71 if res.lower() == "win" else 0xe74c3c

    emb = discord.Embed(title="⚔️ НОВАЯ ЗАПИСЬ МАТЧА", color=color)
    emb.add_field(name="👤 АГЕНТ", value=ctx.author.mention, inline=True)
    emb.add_field(name="🏆 ИТОГ", value=res.upper(), inline=True)
    emb.add_field(name="📊 СТАТИСТИКА", value=f"```\nKDR: {k}/{a}/{d}\nELO: {diff}\n```", inline=False)
    emb.set_image(url=ctx.message.attachments[0].url)
    emb.set_footer(text=f"PAYLOAD:{ctx.author.id}|{diff}|{k}|{a}|{d}")

    m = await chan.send(embed=emb)
    await m.add_reaction("✅")
    await m.add_reaction("❌")
    await ctx.send("📡 **ДАННЫЕ ПЕРЕДАНЫ В HUB.**")

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or str(reaction.message.channel.id) != str(HUB_ID): return
    if not user.guild_permissions.manage_messages: return

    emb = reaction.message.embeds[0]
    try:
        data = emb.footer.text.split(":")[1].split("|")
        uid, elo_ch, k, a, d = int(data[0]), int(data[1]), int(data[2]), int(data[3]), int(data[4])
    except: return

    u = db.get_user(uid)
    if str(reaction.emoji) == "✅":
        u['elo'] += elo_ch
        u['k'] += k; u['a'] += a; u['d'] += d
        if elo_ch > 0: u['w'] += 1
        else: u['l'] += 1
        
        db.save()
        lvl_up = await add_xp(uid, 200)
        
        member = reaction.message.guild.get_member(uid)
        if member: await sync_roles(member, u['elo'])
        
        await reaction.message.channel.send(f"✅ **ОДОБРЕНО:** <@{uid}> ({u['elo']} ELO) {' + LEVEL UP!' if lvl_up else ''}")
        await reaction.message.delete()

# ==========================================
# [8] ЭКОНОМИКА (WORK, DAILY, CASINO)
# ==========================================
@bot.command()
async def work(ctx):
    u = db.get_user(ctx.author.id)
    now = int(time.time())
    if now < u['last_work']:
        rem = u['last_work'] - now
        return await ctx.send(f"⏳ **ОТКАЗ.** Доступ через `{rem//60}м {rem%60}с`.")

    money = random.randint(1000, 3000)
    u['money'] += money
    u['last_work'] = now + 600
    db.save()
    
    await add_xp(ctx.author.id, 50)
    
    emb = discord.Embed(description=f"💵 **СМЕНА ОКОНЧЕНА.** Вы получили `{money}$` и `50 XP`", color=0x2ecc71)
    await ctx.send(embed=emb)

@bot.command()
async def casino(ctx, amount: int):
    u = db.get_user(ctx.author.id)
    if amount > u['money'] or amount <= 0: return await ctx.send("❌ Недостаточно средств.")

    if random.random() < 0.46:
        u['money'] += amount
        msg = f"🎰 **ПОБЕДА!** Баланс: `{u['money']}$`"
    else:
        u['money'] -= amount
        msg = f"📉 **ПРОИГРЫШ.** Баланс: `{u['money']}$`"
    
    db.save()
    await ctx.send(msg)

# ==========================================
# [9] ПРОФИЛЬ (ДИЗАЙНЕРСКАЯ КАРТОЧКА)
# ==========================================
@bot.command()
async def profile(ctx, m: discord.Member = None):
    m = m or ctx.author
    u = db.get_user(m.id)
    
    rank = "Bronze"
    for r, v in RANK_MAP.items():
        if u['elo'] >= v: rank = r

    emb = discord.Embed(title=f"📁 DOSSIER: {m.display_name.upper()}", color=0x00d9ff)
    emb.set_thumbnail(url=m.display_avatar.url)
    
    xp_bar = "🟦" * (int(u['xp']/get_xp_needed(u['lvl'])*10)) + "⬜" * (10 - int(u['xp']/get_xp_needed(u['lvl'])*10))
    
    emb.description = (
        f"**🏆 RANK:** `{rank}`\n"
        f"**📊 ELO:** `{u['elo']}`\n"
        f"**🎖️ LEVEL:** `{u['lvl']}`\n"
        f"**✨ XP:** `{u['xp']}/{get_xp_needed(u['lvl'])}`\n`{xp_bar}`\n\n"
        f"**💰 WALLET:** `{u['money']}$`\n"
        f"**⚔️ K/A/D:** `{u['k']}/{u['a']}/{u['d']}`\n"
        f"**📈 WINRATE:** `{u['w']}W / {u['l']}L`"
    )
    
    emb.set_footer(text="EVOLUTION SECURITY SYSTEM v11.0.1")
    await ctx.send(embed=emb)

# ==========================================
# [10] МАГАЗИН И ТОП
# ==========================================
@bot.command()
async def shop(ctx):
    emb = discord.Embed(title="🛒 BLACK MARKET", color=0x2b2d31)
    for role, price in SHOP_ITEMS.items():
        emb.add_field(name=role, value=f"Цена: `{price}$`", inline=False)
    emb.set_footer(text="Для покупки: !buy [Название]")
    await ctx.send(embed=emb)

@bot.command()
async def top(ctx):
    sorted_db = sorted(db.data.items(), key=lambda x: x[1]['elo'], reverse=True)[:10]
    res = ""
    for i, (uid, data) in enumerate(sorted_db, 1):
        res += f"**{i}.** <@{uid}> — `{data['elo']} ELO`\n"
    
    emb = discord.Embed(title="🏆 GLOBAL LEADERBOARD", description=res, color=0xf1c40f)
    await ctx.send(embed=emb)

# ==========================================
# [11] АДМИНИСТРИРОВАНИЕ
# ==========================================
@bot.command()
@commands.has_permissions(administrator=True)
async def set_elo(ctx, m: discord.Member, val: int):
    u = db.get_user(m.id)
    u['elo'] = val
    db.save()
    await sync_roles(m, val)
    await ctx.send(f"✅ {m.mention} -> `{val} ELO`.")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 10):
    await ctx.channel.purge(limit=amount + 1)

# ==========================================
# [12] ИНИЦИАЛИЗАЦИЯ
# ==========================================
@bot.event
async def on_ready():
    logger.info(f"--- EVOLUTION v11 READY AS {bot.user} ---")
    if not stay_active.is_running(): stay_active.start()

@tasks.loop(minutes=2)
async def stay_active():
    await bot.change_presence(activity=discord.Streaming(name="!help | Evolution v11", url="https://twitch.tv/discord"))

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
