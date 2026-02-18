import discord
from discord.ext import commands, tasks
import os, json, random, datetime, time, asyncio, logging
from flask import Flask
from threading import Thread

# --- [ СИСТЕМА ЖИЗНЕОБЕСПЕЧЕНИЯ ] ---
app = Flask('')
@app.route('/')
def home(): return "Evolution AI Core v30: ONLINE"
def run_web(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run_web, daemon=True).start()

# --- [ КОНФИГУРАЦИЯ ] ---
TOKEN = os.getenv("DISCORD_TOKEN")
HUB_ID = os.getenv("HUB_ID")
PREFIX = "!"

RANKS = {
    "Bronze": 0, "Silver": 1200, "Gold": 1600,
    "Platinum": 2000, "Diamond": 2500, "Immortal": 3000
}

# --- [ БАЗА ДАННЫХ ] ---
class TitanDB:
    def __init__(self, file="titan_v30.json"):
        self.file = file
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.file):
            with open(self.file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"users": {}, "clans": {}}

    def save(self):
        with open(self.file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    def get_u(self, uid):
        uid = str(uid)
        if uid not in self.data["users"]:
            self.data["users"][uid] = {
                "elo": 1000, "money": 5000, "lvl": 1, "xp": 0,
                "k": 0, "a": 0, "d": 0, "w": 0, "l": 0,
                "t_work": 0, "t_mine": 0, "clan": None, "gpu": 0
            }
            self.save()
        return self.data["users"][uid]

db = TitanDB()

# --- [ ИНИЦИАЛИЗАЦИЯ БОТА ] ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# --- [ AI ЛОГИКА ] ---
AI_PHRASES = [
    "Анализ данных завершен. Твой потенциал растет.",
    "Система зафиксировала твою активность. Продолжай в том же духе.",
    "Внимание: уровень ELO критически важен для доминирования.",
    "Обнаружено новое достижение в секторе экономики."
]

# --- [ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ] ---
async def sync_roles(member, elo):
    current_rank = "Bronze"
    for r, v in RANKS.items():
        if elo >= v: current_rank = r
    role = discord.utils.get(member.guild.roles, name=current_rank)
    if role and role not in member.roles:
        await member.remove_roles(*[r for r in member.roles if r.name in RANKS])
        await member.add_roles(role)

# --- [ КОМАНДА RESULT (FIXED) ] ---
@bot.command()
async def result(ctx, k: int, a: int, d: int, status: str = "win"):
    if not ctx.message.attachments:
        return await ctx.send("❌ **ОШИБКА:** Ты не прикрепил скриншот! Команда не сработает без пруфа.")

    if not HUB_ID:
        return await ctx.send("❌ **ОШИБКА СИСТЕМЫ:** HUB_ID не настроен админом.")

    hub_channel = bot.get_channel(int(HUB_ID))
    if not hub_channel:
        return await ctx.send("❌ **ОШИБКА:** Канал модерации не найден.")

    res = status.lower()
    elo_diff = 25 if res == "win" else -20
    color = 0x2ecc71 if res == "win" else 0xe74c3c

    emb = discord.Embed(title="📊 НОВЫЙ ОТЧЕТ МАТЧА", color=color, timestamp=datetime.datetime.now())
    emb.add_field(name="👤 Игрок", value=ctx.author.mention, inline=True)
    emb.add_field(name="🏆 Итог", value=res.upper(), inline=True)
    emb.add_field(name="⚔️ KDA", value=f"`{k} / {a} / {d}`", inline=True)
    emb.set_image(url=ctx.message.attachments[0].url)
    emb.set_footer(text=f"PAYLOAD:{ctx.author.id}|{elo_diff}|{k}|{a}|{d}")

    msg = await hub_channel.send(embed=emb)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    
    # AI Comment
    ai_msg = random.choice(AI_PHRASES)
    await ctx.send(f"📡 **AI CORE:** {ai_msg}\n✅ Отчет отправлен в HUB.")

# --- [ ОБРАБОТКА РЕАКЦИЙ HUB ] ---
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or str(reaction.message.channel.id) != str(HUB_ID): return
    if not user.guild_permissions.manage_messages: return
    if not reaction.message.embeds: return

    emb = reaction.message.embeds[0]
    if "PAYLOAD:" not in str(emb.footer.text): return

    data = emb.footer.text.split(":")[1].split("|")
    uid, elo_add, k, a, d = int(data[0]), int(data[1]), int(data[2]), int(data[3]), int(data[4])
    
    u = db.get_u(uid)
    guild = reaction.message.guild
    member = guild.get_member(uid)

    if str(reaction.emoji) == "✅":
        u['elo'] += elo_add
        u['k'] += k; u['a'] += a; u['d'] += d
        if elo_add > 0: u['w'] += 1
        else: u['l'] += 1
        db.save()
        if member: await sync_roles(member, u['elo'])
        await reaction.message.channel.send(f"✅ **ОДОБРЕНО:** <@{uid}> получил {elo_add} ELO.")
        await reaction.message.delete()
    elif str(reaction.emoji) == "❌":
        await reaction.message.channel.send(f"❌ **ОТКЛОНЕНО:** Заявка <@{uid}> аннулирована.")
        await reaction.message.delete()

# --- [ НОВЫЕ КОМАНДЫ: ЭКОНОМИКА И МАЙНИНГ ] ---
@bot.command()
async def work(ctx):
    u = db.get_u(ctx.author.id)
    if time.time() < u['t_work']:
        rem = int(u['t_work'] - time.time())
        return await ctx.send(f"⏳ **AI:** Системе нужен отдых. Жди {rem} сек.")
    
    gain = random.randint(1000, 3000)
    u['money'] += gain
    u['t_work'] = time.time() + 600
    db.save()
    await ctx.send(f"💰 **РАБОТА:** Ты выполнил контракт и получил `{gain}$`")

@bot.command()
async def buy_gpu(ctx):
    u = db.get_u(ctx.author.id)
    cost = 15000
    if u['money'] < cost: return await ctx.send("❌ Недостаточно средств для покупки видеокарты (15к).")
    u['money'] -= cost
    u['gpu'] += 1
    db.save()
    await ctx.send(f"📟 **МАЙНИНГ:** Ты купил видеокарту! Теперь `!mine` дает больше.")

@bot.command()
async def mine(ctx):
    u = db.get_u(ctx.author.id)
    if u['gpu'] < 1: return await ctx.send("❌ У тебя нет видеокарт. Купи их: `!buy_gpu`.")
    if time.time() < u['t_mine']: return await ctx.send("⏳ Ферма перегрелась. Жди.")
    
    profit = u['gpu'] * random.randint(500, 1200)
    u['money'] += profit
    u['t_mine'] = time.time() + 1800
    db.save()
    await ctx.send(f"💎 **МАЙНИНГ:** Ферма принесла `{profit}$` прибыли.")

# --- [ КЛАНОВАЯ СИСТЕМА ] ---
@bot.command()
async def clan_create(ctx, name: str):
    u = db.get_u(ctx.author.id)
    if u['money'] < 50000: return await ctx.send("❌ Создание клана стоит 50,000$.")
    if name in db.data['clans']: return await ctx.send("❌ Такое имя клана уже занято.")
    
    u['money'] -= 50000
    u['clan'] = name
    db.data['clans'][name] = {"owner": ctx.author.id, "members": [ctx.author.id]}
    db.save()
    await ctx.send(f"🛡️ **КЛАН:** Клан `{name}` официально зарегистрирован!")

# --- [ ПРОФИЛЬ И ТОП ] ---
@bot.command()
async def profile(ctx, member: discord.Member = None):
    member = member or ctx.author
    u = db.get_u(member.id)
    
    emb = discord.Embed(title=f"👤 NEURAL DOSSIER: {member.name}", color=0x3498db)
    emb.set_thumbnail(url=member.display_avatar.url)
    emb.add_field(name="🏆 ELO / РАНГ", value=f"**{u['elo']}** | `{next((r for r, v in reversed(list(RANKS.items())) if u['elo'] >= v), 'Bronze')}`", inline=True)
    emb.add_field(name="💳 БАЛАНС", value=f"`{u['money']}$`", inline=True)
    emb.add_field(name="📊 СТАТЫ", value=f"KDA: `{u['k']}/{u['a']}/{u['d']}`\nПобеды: `{u['w']}`", inline=True)
    emb.add_field(name="📟 ФЕРМА", value=f"Карты: `{u['gpu']}` шт.", inline=True)
    if u['clan']: emb.add_field(name="🛡️ КЛАН", value=f"`{u['clan']}`", inline=True)
    
    await ctx.send(embed=emb)

@bot.command()
async def help(ctx):
    emb = discord.Embed(title="🌌 EVOLUTION AI HELP", color=0x2b2d31)
    emb.add_field(name="⚔️ MATCHES", value="`!result K A D win/loss`", inline=True)
    emb.add_field(name="💰 ECONOMY", value="`!work`, `!mine`, `!buy_gpu`, `!daily`", inline=True)
    emb.add_field(name="🛡️ CLANS", value="`!clan_create`, `!clan_info`", inline=True)
    emb.add_field(name="📊 STATS", value="`!profile`, `!top`, `!pay`", inline=True)
    await ctx.send(embed=emb)

# --- [ ЗАПУСК ] ---
@bot.event
async def on_ready():
    print(f"--- EVOLUTION AI CORE v30 READY ---")
    keep_alive()

bot.run(TOKEN)
