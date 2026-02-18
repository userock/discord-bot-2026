import discord
from discord.ext import commands, tasks
import os, json, random, datetime, time, asyncio, logging
from flask import Flask
from threading import Thread

# ==========================================
# [1] ЖИЗНЕОБЕСПЕЧЕНИЕ (FLASK)
# ==========================================
app = Flask('')
@app.route('/')
def home(): return "Evolution Overlord v60: NEURAL CORE ACTIVE"
def run_web(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run_web, daemon=True).start()

# ==========================================
# [2] NEURAL DATA ENGINE (DATABASE)
# ==========================================
class NeuralDB:
    def __init__(self, file="neural_overlord.json"):
        self.file = file
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.file):
            try:
                with open(self.file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: return {"users": {}, "clans": {}, "market": []}
        return {"users": {}, "clans": {}, "market": []}

    def save(self):
        with open(self.file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    def get_user(self, uid):
        uid = str(uid)
        if uid not in self.data["users"]:
            self.data["users"][uid] = {
                "elo": 1000, "money": 5000, "bank": 0,
                "lvl": 1, "xp": 0, "k": 0, "a": 0, "d": 0,
                "w": 0, "l": 0, "inv": [], "gpu": 0,
                "timers": {"work": 0, "crime": 0, "mine": 0}
            }
            self.save()
        return self.data["users"][uid]

db = NeuralDB()

# ==========================================
# [3] CONFIGURATION & INTENTS
# ==========================================
TOKEN = os.getenv("DISCORD_TOKEN")
HUB_ID = os.getenv("HUB_ID")
PREFIX = "!"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

RANKS = {
    "Bronze": 0, "Silver": 1200, "Gold": 1600,
    "Platinum": 2100, "Diamond": 2700, "Immortal": 3500
}

# ==========================================
# [4] AI NEURAL LOGIC (АНАЛИЗАТОР)
# ==========================================
class NeuralAI:
    @staticmethod
    def analyze_performance(u):
        kda = (u['k'] + u['a']) / u['d'] if u['d'] > 0 else u['k']
        if kda > 3.0: return "Твоя эффективность пугает. Система видит в тебе доминанта."
        if kda < 1.0: return "Твои показатели ниже нормы. Рекомендую сменить тактику."
        return "Стабильные результаты. Продолжай калибровку навыков."

    @staticmethod
    def get_market_tip():
        tips = [
            "Инвестируй в видеокарты. Пассивный доход — путь к власти.",
            "Не держи деньги в кармане, банки защищают от инфляции.",
            "Кланы — это не просто тег, это твоя армия."
        ]
        return random.choice(tips)

# ==========================================
# [5] ФУНКЦИИ ПРОГРЕССИИ
# ==========================================
def get_xp_req(lvl): return int(1000 * (lvl ** 1.4))

async def add_xp(uid, amount, channel=None):
    u = db.get_user(uid)
    u['xp'] += amount
    req = get_xp_req(u['lvl'])
    if u['xp'] >= req:
        u['xp'] -= req
        u['lvl'] += 1
        reward = u['lvl'] * 2000
        u['money'] += reward
        db.save()
        if channel:
            emb = discord.Embed(title="🧠 NEURAL LEVEL UP", description=f"<@{uid}> достиг уровня **{u['lvl']}**\nНаграда: **{reward}$**", color=0x00ffff)
            await channel.send(embed=emb)

async def update_member_rank(member, elo):
    if not member or isinstance(member, discord.User): return
    target_rank = "Bronze"
    for r, v in RANKS.items():
        if elo >= v: target_rank = r
    
    role = discord.utils.get(member.guild.roles, name=target_rank)
    if role and role not in member.roles:
        to_remove = [r for r in member.roles if r.name in RANKS]
        try:
            await member.remove_roles(*to_remove)
            await member.add_roles(role)
        except Exception as e:
            print(f"Role Error: {e}")

# ==========================================
# [6] FIXED !RESULT COMMAND (HUB CORE)
# ==========================================
@bot.command()
async def result(ctx, k: int = None, a: int = None, d: int = None, status: str = "win"):
    # 1. Проверка аргументов
    if k is None or a is None or d is None:
        return await ctx.send("❌ **ОШИБКА:** Формат: `!result [Киллы] [Ассисты] [Смерти] [win/loss]`")

    # 2. Проверка вложений (Главный фикс)
    if not ctx.message.attachments:
        emb = discord.Embed(title="⚠️ ПРОВЕРКА ДАННЫХ", description="Для регистрации матча **ОБЯЗАТЕЛЬНО** прикрепи скриншот результата!", color=0xffa500)
        return await ctx.send(embed=emb)

    # 3. Проверка HUB канала
    if not HUB_ID: return await ctx.send("❌ HUB_ID не настроен в переменных!")
    hub_chan = bot.get_channel(int(HUB_ID))
    if not hub_chan: return await ctx.send("❌ Не могу найти канал HUB. Проверь ID.")

    # 4. Логика расчета
    is_win = status.lower() in ["win", "победа", "w", "win"]
    delta = 25 if is_win else -20
    color = 0x2ecc71 if is_win else 0xe74c3c

    # 5. Генерация Эмбеда
    emb = discord.Embed(title="🛰️ ПЕРЕДАЧА ДАННЫХ МАТЧА", color=color, timestamp=datetime.datetime.now())
    emb.set_author(name=f"Оперативник: {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
    emb.add_field(name="📊 СТАТИСТИКА", value=f"```fix\nK: {k} | A: {a} | D: {d}\nELO: {'+' if delta > 0 else ''}{delta}\n```", inline=False)
    emb.add_field(name="🏆 ИТОГ", value=f"**{status.upper()}**", inline=True)
    emb.set_image(url=ctx.message.attachments[0].url)
    
    # Скрытый Payload для AI-обработки
    emb.set_footer(text=f"PAYLOAD:{ctx.author.id}|{delta}|{k}|{a}|{d}")

    # 6. Отправка и Реакции
    try:
        msg = await hub_chan.send(embed=emb)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        await ctx.send(f"📡 **AI CORE:** Данные получены. Ожидайте верификации в <#{HUB_ID}>")
    except Exception as e:
        await ctx.send(f"❌ Ошибка при отправке: {e}")

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or str(reaction.message.channel.id) != str(HUB_ID): return
    if not user.guild_permissions.manage_messages: return
    if not reaction.message.embeds: return

    emb = reaction.message.embeds[0]
    if not emb.footer.text or "PAYLOAD:" not in emb.footer.text: return

    try:
        raw = emb.footer.text.split("PAYLOAD:")[1].split("|")
        uid, elo_add, k, a, d = int(raw[0]), int(raw[1]), int(raw[2]), int(raw[3]), int(raw[4])
    except: return

    u = db.get_user(uid)
    guild = reaction.message.guild
    member = guild.get_member(uid)

    if str(reaction.emoji) == "✅":
        u['elo'] += elo_add
        u['k'] += k; u['a'] += a; u['d'] += d
        if elo_add > 0: u['w'] += 1
        else: u['l'] += 1
        db.save()
        await add_xp(uid, 400, reaction.message.channel)
        if member: await update_member_rank(member, u['elo'])
        await reaction.message.channel.send(f"✅ **СИСТЕМА:** Данные <@{uid}> синхронизированы. Текущий ELO: `{u['elo']}`")
        await reaction.message.delete()
    
    elif str(reaction.emoji) == "❌":
        await reaction.message.channel.send(f"❌ **ОТКАЗ:** Отчет <@{uid}> отклонен модератором.")
        await reaction.message.delete()

# ==========================================
# [7] ЭКОНОМИКА И ИНТЕЛЛЕКТУАЛЬНЫЕ КОМАНДЫ
# ==========================================
@bot.command()
async def work(ctx):
    u = db.get_user(ctx.author.id)
    if time.time() < u['timers']['work']:
        rem = int(u['timers']['work'] - time.time())
        return await ctx.send(f"⏳ **AI:** Твои нейроны перегружены. Жди `{rem//60}м {rem%60}с`.")

    reward = random.randint(2000, 5000) * u['lvl']
    u['money'] += reward
    u['timers']['work'] = time.time() + 900
    db.save()
    await add_xp(ctx.author.id, 150, ctx.channel)
    await ctx.send(embed=discord.Embed(description=f"💼 **РАБОТА:** Выполнен контракт. Получено **{reward}$**", color=0x2ecc71))

@bot.command()
async def mine(ctx):
    u = db.get_user(ctx.author.id)
    if u['gpu'] == 0: return await ctx.send("❌ **AI:** У тебя нет вычислительных мощностей. Купи GPU в `!shop`.")
    if time.time() < u['timers']['mine']: return await ctx.send("⏳ **AI:** Ферма перегрета. Охлаждение...")

    profit = u['gpu'] * random.randint(1500, 3000)
    u['money'] += profit
    u['timers']['mine'] = time.time() + 3600
    db.save()
    await ctx.send(f"💎 **МАЙНИНГ:** Твои {u['gpu']} GPU добыли криптовалюту на **{profit}$**")

# ==========================================
# [8] НЕЙРОННЫЙ ПРОФИЛЬ (КАК У МЕНЯ)
# ==========================================
@bot.command()
async def profile(ctx, m: discord.Member = None):
    m = m or ctx.author
    u = db.get_u_data = db.get_user(m.id)
    
    rank = "Bronze"
    for r, v in RANKS.items():
        if u['elo'] >= v: rank = r
    
    xp_req = get_xp_req(u['lvl'])
    bar = "🟦" * int((u['xp']/xp_req)*10) + "⬜" * (10 - int((u['xp']/xp_req)*10))

    emb = discord.Embed(title=f"🧠 NEURAL INTERFACE: {m.name.upper()}", color=0x3498db)
    emb.set_thumbnail(url=m.display_avatar.url)
    
    emb.add_field(name="📡 STATUS", value=f"Rank: `{rank}`\nELO: **{u['elo']}**", inline=True)
    emb.add_field(name="💳 CAPITAL", value=f"Нал: `{u['money']}$`\nБанк: `{u['bank']}$`", inline=True)
    
    comb = f"```fix\nKDA: {u['k']}/{u['a']}/{u['d']}\nSeries: {u['w']}W / {u['l']}L\n```"
    emb.add_field(name="📊 COMBAT DATA", value=comb, inline=False)
    emb.add_field(name=f"🆙 LEVEL {u['lvl']}", value=f"{bar} `{u['xp']}/{xp_req}`", inline=False)
    
    # AI Вставка
    ai_analysis = NeuralAI.analyze_performance(u)
    ai_tip = NeuralAI.get_market_tip()
    emb.add_field(name="🤖 AI INSIGHTS", value=f"_{ai_analysis}_\n\n**Совет:** {ai_tip}", inline=False)
    
    await ctx.send(embed=emb)

# ==========================================
# [9] МАГАЗИН И ПОМОЩЬ
# ==========================================
@bot.command()
async def shop(ctx):
    e = discord.Embed(title="🏬 NEURAL MARKET", color=0x2b2d31)
    e.add_field(name="📟 GPU NVIDIA H100", value="Цена: `40,000$`\nДает мощный доход в `!mine`", inline=False)
    e.add_field(name="🎲 NEURAL CASE", value="Цена: `8,000$`\nШанс выиграть до 50,000$", inline=False)
    await ctx.send(embed=e)

@bot.command()
async def buy(ctx, *, item: str):
    u = db.get_user(ctx.author.id)
    item = item.lower()
    if "gpu" in item:
        if u['money'] < 40000: return await ctx.send("❌ Недостаточно средств.")
        u['money'] -= 40000
        u['gpu'] += 1
        db.save()
        await ctx.send("✅ GPU установлена. Твой хешрейт вырос.")
    elif "case" in item:
        if u['money'] < 8000: return await ctx.send("❌ Недостаточно средств.")
        u['money'] -= 8000
        win = random.randint(1000, 50000)
        u['money'] += win
        db.save()
        await ctx.send(f"🎲 Кейс открыт! Выигрыш: **{win}$**")
    else:
        await ctx.send("❌ Предмет не найден.")

@bot.command()
async def help(ctx):
    emb = discord.Embed(title="🛰️ OVERLORD CONTROL PANEL", color=0x2b2d31)
    emb.add_field(name="⚔️ СЕКТОР БОЯ", value="`!result`, `!profile`, `!top`")
    emb.add_field(name="💰 СЕКТОР ЭКОНОМИКИ", value="`!work`, `!mine`, `!shop`, `!buy`")
    emb.add_field(name="⚙️ СЕРВИС", value="`!dep`, `!pay`, `!daily`")
    emb.set_footer(text="Evolution Overlord v60.4 Platinum Edition")
    await ctx.send(embed=emb)

# ==========================================
# ЗАПУСК СИСТЕМЫ
# ==========================================
@bot.event
async def on_ready():
    print(f"--- NEURAL OVERLORD v60 ONLINE ---")
    stay_active.start()

@tasks.loop(minutes=5)
async def stay_active():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="за матрицей | !help"))

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
