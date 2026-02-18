import discord
from discord.ext import commands, tasks
import os, json, random, datetime, time, asyncio, logging, math, re
from flask import Flask
from threading import Thread

# ==========================================
# [1] СЕРВЕР ЖИЗНЕОБЕСПЕЧЕНИЯ (FLASK)
# ==========================================
app = Flask('')
@app.route('/')
def home(): return "<h1>Evolution Overlord v50: SYSTEM ACTIVE</h1>"
def run_web(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run_web, daemon=True).start()

# ==========================================
# [2] ГЛОБАЛЬНОЕ ЛОГИРОВАНИЕ
# ==========================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('EvolutionCore')

# ==========================================
# [3] МОЩНОЕ ЯДРО БАЗЫ ДАННЫХ
# ==========================================
class DataEngine:
    def __init__(self, db_file="overlord_v50.json"):
        self.db_file = db_file
        self.data = self._load_db()

    def _load_db(self):
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"DB Load Error: {e}")
                return {"users": {}, "clans": {}, "global": {"total_matches": 0}}
        return {"users": {}, "clans": {}, "global": {"total_matches": 0}}

    def save(self):
        try:
            with open(self.db_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"DB Save Error: {e}")

    def get_u(self, uid):
        uid = str(uid)
        if uid not in self.data["users"]:
            self.data["users"][uid] = {
                "name": "Unknown", "elo": 1000, "money": 5000, "bank": 0,
                "lvl": 1, "xp": 0, "k": 0, "a": 0, "d": 0, "w": 0, "l": 0,
                "inv": [], "gpu": 0, "rep": 0, "clan": None,
                "t_work": 0, "t_daily": 0, "t_mine": 0, "t_crime": 0
            }
            self.save()
        return self.data["users"][uid]

db = DataEngine()

# ==========================================
# [4] КОНФИГУРАЦИЯ И ПЕРЕМЕННЫЕ
# ==========================================
TOKEN = os.getenv("DISCORD_TOKEN")
HUB_ID = os.getenv("HUB_ID")
PREFIX = "!"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

RANK_MAP = {
    "Bronze": 0, "Silver": 1200, "Gold": 1600,
    "Platinum": 2100, "Diamond": 2650, "Immortal": 3300
}

# ==========================================
# [5] ВСПОМОГАТЕЛЬНАЯ ЛОГИКА (AI & MATH)
# ==========================================
def xp_to_next(lvl): return int(1000 * (lvl ** 1.35))

async def award_xp(uid, amount, channel=None):
    u = db.get_u(uid)
    u['xp'] += amount
    req = xp_to_next(u['lvl'])
    if u['xp'] >= req:
        u['xp'] -= req
        u['lvl'] += 1
        bonus = u['lvl'] * 1500
        u['money'] += bonus
        db.save()
        if channel:
            e = discord.Embed(title="🚀 НОВЫЙ УРОВЕНЬ!", description=f"Боец <@{uid}> достиг уровня **{u['lvl']}**!\nНаграда: **{bonus}$**", color=0x00ff00)
            await channel.send(embed=e)

async def auto_sync_roles(member, elo):
    if not member or not hasattr(member, 'guild'): return
    target = "Bronze"
    for r, v in RANK_MAP.items():
        if elo >= v: target = r
    role = discord.utils.get(member.guild.roles, name=target)
    if role and role not in member.roles:
        old = [r for r in member.roles if r.name in RANK_MAP]
        try:
            if old: await member.remove_roles(*old)
            await member.add_roles(role)
        except: pass

# ==========================================
# [6] ЯДРО HUB: ФИКС КОМАНДЫ RESULT
# ==========================================
@bot.command()
async def result(ctx, k: int = None, a: int = None, d: int = None, outcome: str = "win"):
    # Проверка на наличие аргументов
    if k is None or a is None or d is None:
        e = discord.Embed(title="❌ ОШИБКА ВВОДА", description="**Используй:** `!result [K] [A] [D] [win/loss]`", color=0xff0000)
        return await ctx.send(embed=e)

    # Жесткая проверка скриншота
    if not ctx.message.attachments:
        e = discord.Embed(title="❌ НЕТ СКРИНШОТА", description="Для подтверждения результата **необходимо** прикрепить скриншот таблицы!", color=0xff0000)
        return await ctx.send(embed=e)

    if not HUB_ID: return await ctx.send("❌ HUB не настроен!")
    hub_chan = bot.get_channel(int(HUB_ID))
    
    is_win = outcome.lower() in ["win", "победа", "w", "🏆"]
    elo_ch = 25 if is_win else -20
    color = 0x2ecc71 if is_win else 0xe74c3c

    emb = discord.Embed(title="⚔️ НОВЫЙ МАТЧ НА ВЕРИФИКАЦИЮ", color=color, timestamp=datetime.datetime.now())
    emb.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
    emb.add_field(name="👤 АГЕНТ", value=ctx.author.mention, inline=True)
    emb.add_field(name="🏆 ИТОГ", value=outcome.upper(), inline=True)
    emb.add_field(name="📊 СТАТИСТИКА", value=f"```fix\nK: {k} | A: {a} | D: {d}\nELO: {'+' if elo_ch > 0 else ''}{elo_ch}\n```", inline=False)
    emb.set_image(url=ctx.message.attachments[0].url)
    
    # Payload Security (Защищенная строка данных)
    emb.set_footer(text=f"PAYLOAD_ID:{ctx.author.id}|E:{elo_ch}|K:{k}|A:{a}|D:{d}")

    msg = await hub_chan.send(embed=emb)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    
    await ctx.send("📡 **ДАННЫЕ ПЕРЕДАНЫ:** Отчет отправлен в HUB. Ожидайте проверки модератором.")

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or str(reaction.message.channel.id) != str(HUB_ID): return
    if not user.guild_permissions.manage_messages: return
    if not reaction.message.embeds: return

    emb = reaction.message.embeds[0]
    if not emb.footer.text or "PAYLOAD_ID:" not in emb.footer.text: return

    try:
        raw = emb.footer.text.replace("PAYLOAD_ID:", "").replace("E:", "").replace("K:", "").replace("A:", "").replace("D:", "")
        data = raw.split("|")
        uid, elo_add, k, a, d = int(data[0]), int(data[1]), int(data[2]), int(data[3]), int(data[4])
    except: return

    u = db.get_u(uid)
    guild = reaction.message.guild
    member = guild.get_member(uid)

    if str(reaction.emoji) == "✅":
        u['elo'] += elo_add
        u['k'] += k; u['a'] += a; u['d'] += d
        if elo_add > 0: u['w'] += 1
        else: u['l'] += 1
        db.save()
        await award_xp(uid, 350, reaction.message.channel)
        if member: await auto_sync_roles(member, u['elo'])
        await reaction.message.channel.send(f"✅ **ОДОБРЕНО:** Боец <@{uid}> получил `{elo_add} ELO`. Текущий рейтинг: **{u['elo']}**")
        await reaction.message.delete()
        
    elif str(reaction.emoji) == "❌":
        await reaction.message.channel.send(f"❌ **ОТКЛОНЕНО:** Отчет <@{uid}> признан недействительным.")
        await reaction.message.delete()

# ==========================================
# [7] ЭКОНОМИКА: РАБОТА, МАЙНИНГ, КРИМИНАЛ
# ==========================================
@bot.command()
async def work(ctx):
    u = db.get_u(ctx.author.id)
    now = time.time()
    if now < u['t_work']:
        rem = int(u['t_work'] - now)
        return await ctx.send(f"⏳ **ОТКАЗ:** Твой контракт еще не обновлен. Жди `{rem//60}м {rem%60}с`.")

    gain = random.randint(1500, 4500) * u['lvl']
    u['money'] += gain
    u['t_work'] = now + 900
    db.save()
    await award_xp(ctx.author.id, 100, ctx.channel)
    await ctx.send(embed=discord.Embed(description=f"💰 **РАБОТА:** Ты выполнил задание и заработал **{gain}$**", color=0x2ecc71))

@bot.command()
async def crime(ctx):
    u = db.get_u(ctx.author.id)
    if time.time() < u['t_crime']: return await ctx.send("⏳ Полиция ищет тебя. Заляг на дно.")

    if random.random() < 0.48:
        win = random.randint(6000, 15000)
        u['money'] += win
        res = f"💣 **УСПЕХ!** Ты взломал сейф и вынес **{win}$**"
        color = 0x000000
    else:
        loss = random.randint(3000, 7000)
        u['money'] -= loss
        res = f"🚓 **ПРОВАЛ!** Тебя задержали. Штраф за адвоката: **{loss}$**"
        color = 0xff0000
    
    u['t_crime'] = time.time() + 1800
    db.save()
    await ctx.send(embed=discord.Embed(description=res, color=color))

@bot.command()
async def mine(ctx):
    u = db.get_u(ctx.author.id)
    if u['gpu'] <= 0: return await ctx.send("❌ У тебя нет видеокарт! Купи их в `!shop`.")
    if time.time() < u['t_mine']: return await ctx.send("⏳ Ферма еще охлаждается.")

    profit = u['gpu'] * random.randint(1000, 2500)
    u['money'] += profit
    u['t_mine'] = time.time() + 3600
    db.save()
    await ctx.send(f"💎 **МАЙНИНГ:** Твои {u['gpu']} видеокарт добыли **{profit}$**")

# ==========================================
# [8] ИНВЕНТАРЬ И МАГАЗИН
# ==========================================
@bot.command()
async def shop(ctx):
    e = discord.Embed(title="🛒 BLACK MARKET", color=0x2b2d31)
    e.add_field(name="📟 RTX 5090 GPU", value="Цена: `30,000$`\nДает доход в `!mine`", inline=False)
    e.add_field(name="📦 ELITE LOOTBOX", value="Цена: `7,000$`\nШанс выиграть до 30к", inline=False)
    e.add_field(name="🛡️ CLAN LICENSE", value="Цена: `150,000$`\nПраво создать свой клан", inline=False)
    e.set_footer(text="Купить: !buy [название]")
    await ctx.send(embed=e)

@bot.command()
async def buy(ctx, *, item: str):
    u = db.get_u(ctx.author.id)
    item = item.lower()
    if "gpu" in item:
        if u['money'] < 30000: return await ctx.send("❌ Недостаточно средств.")
        u['money'] -= 30000
        u['gpu'] += 1
        await ctx.send("✅ Ты приобрел **RTX 5090**. Теперь доход в `!mine` вырос!")
    elif "lootbox" in item:
        if u['money'] < 7000: return await ctx.send("❌ Недостаточно средств.")
        u['money'] -= 7000
        win = random.randint(1000, 35000)
        u['money'] += win
        await ctx.send(f"📦 Ты открыл кейс и нашел в нем **{win}$**!")
    else:
        await ctx.send("❌ Предмет не найден.")
    db.save()

# ==========================================
# [9] ПРОФИЛЬ И AI-СТАТИСТИКА
# ==========================================
@bot.command()
async def profile(ctx, m: discord.Member = None):
    m = m or ctx.author
    u = db.get_u(m.id)
    
    cur_rank = "Bronze"
    for r, v in RANK_MAP.items():
        if u['elo'] >= v: cur_rank = r
        
    xp_req = xp_to_next(u['lvl'])
    bar = "🟩" * int((u['xp']/xp_req)*12) + "⬛" * (12 - int((u['xp']/xp_req)*12))

    e = discord.Embed(title=f"📁 DOSSIER: {m.display_name.upper()}", color=0x00d9ff)
    e.set_thumbnail(url=m.display_avatar.url)
    e.add_field(name="🏆 STATUS", value=f"Ранг: `{cur_rank}`\nELO: **{u['elo']}**", inline=True)
    e.add_field(name="💳 WALLET", value=f"Наличные: `{u['money']}$`\nВ банке: `{u['bank']}$`", inline=True)
    e.add_field(name="📊 COMBAT", value=f"```fix\nK/A/D: {u['k']}/{u['a']}/{u['d']}\nWins: {u['w']} | Losses: {u['l']}\n```", inline=False)
    e.add_field(name=f"🆙 LEVEL {u['lvl']}", value=f"{bar}\n`{u['xp']} / {xp_req} XP`", inline=False)
    
    # AI Logic (Анализ стиля игры)
    kda = (u['k']+u['a'])/u['d'] if u['d'] > 0 else u['k']
    style = "Новичок"
    if kda > 2.5: style = "Элитный Киллер"
    elif u['money'] > 500000: style = "Магнат"
    e.add_field(name="🤖 AI ANALYSIS", value=f"Тип бойца: **{style}**", inline=False)
    
    await ctx.send(embed=e)

# ==========================================
# [10] УТИЛИТЫ И ОБСЛУЖИВАНИЕ
# ==========================================
@bot.command()
async def help(ctx):
    e = discord.Embed(title="📜 OVERLORD COMMAND LIST", color=0x2b2d31)
    e.add_field(name="⚔️ МАТЧИ", value="`!result`, `!profile`, `!top`", inline=True)
    e.add_field(name="💰 ДЕНЬГИ", value="`!work`, `!crime`, `!mine`, `!daily`", inline=True)
    e.add_field(name="🏪 РЫНОК", value="`!shop`, `!buy`, `!inv`", inline=True)
    e.add_field(name="🏦 БАНК", value="`!dep`, `!pay`", inline=True)
    e.set_footer(text="Версия 50.0.1 Platinum | 1000+ Lines Code")
    await ctx.send(embed=e)

@bot.command()
@commands.has_permissions(administrator=True)
async def set_elo(ctx, m: discord.Member, val: int):
    u = db.get_u(m.id)
    u['elo'] = val
    db.save()
    await auto_sync_roles(m, val)
    await ctx.send(f"✅ Рейтинг {m.mention} изменен на **{val}**")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Кулдаун! Попробуй через {round(error.retry_after, 1)} сек.")
    else: logger.error(f"Error in {ctx.command}: {error}")

# ==========================================
# [11] ЗАПУСК СИСТЕМЫ
# ==========================================
@bot.event
async def on_ready():
    logger.info(f"TITAN CONNECTED: {bot.user}")
    if not bank_interest.is_running(): bank_interest.start()
    await bot.change_presence(activity=discord.Game(name="Evolution v50 | !help"))

@tasks.loop(hours=1)
async def bank_interest():
    for uid in db.data["users"]:
        user = db.data["users"][uid]
        if user["bank"] > 0:
            user["bank"] = int(user["bank"] * 1.01) # 1% в час
    db.save()
    logger.info("Bank interest processed.")

if __name__ == "__main__":
    keep_alive()
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"CRITICAL SHUTDOWN: {e}")
