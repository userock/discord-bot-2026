import discord
from discord.ext import commands, tasks
import os, random, datetime, time, json, asyncio, logging
from flask import Flask
from threading import Thread

# --- [ 1. ВЕБ-СЕРВЕР 24/7 ] ---
app = Flask('')
@app.route('/')
def home(): return "Evolution Engine v15: MAXIMUM OUTPUT"
def run_web(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run_web, daemon=True).start()

# --- [ 2. DATABASE ARCHITECTURE ] ---
class AdvancedDB:
    def __init__(self, file="titan_db.json"):
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

    def get_u(self, uid):
        uid = str(uid)
        if uid not in self.data["users"]:
            self.data["users"][uid] = {
                "name": "Unknown", "elo": 1000, "money": 2000, "bank": 0,
                "lvl": 1, "xp": 0, "k": 0, "a": 0, "d": 0, "w": 0, "l": 0,
                "last_work": 0, "last_daily": 0, "clan": None, "inv": []
            }
            self.save()
        return self.data["users"][uid]

db = AdvancedDB()

# --- [ 3. CONFIG & INTENTS ] ---
TOKEN = os.getenv("DISCORD_TOKEN")
HUB_ID = os.getenv("HUB_ID")
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Названия ролей и пороги ELO
RANKS = {
    "🌑 Bronze": 0, "🥈 Silver": 1200, "🔱 Gold": 1500,
    "💎 Platinum": 1900, "👑 Diamond": 2300, "🔥 Immortal": 2800
}

# --- [ 4. ЛОГИКА XP И РАНГОВ ] ---
def get_need_xp(lvl): return int(1000 * (lvl ** 1.2))

async def add_xp(uid, amount, ctx):
    u = db.get_u(uid)
    u['xp'] += amount
    if u['xp'] >= get_need_xp(u['lvl']):
        u['xp'] -= get_need_xp(u['lvl'])
        u['lvl'] += 1
        db.save()
        e = discord.Embed(title="🚀 LEVEL UP!", description=f"<@{uid}> теперь **{u['lvl']}** уровня!", color=0x00ff00)
        await ctx.send(embed=e)

async def sync_roles(member, elo):
    if not member or isinstance(member, discord.User): return
    target = "🌑 Bronze"
    for r, v in RANKS.items():
        if elo >= v: target = r
    role = discord.utils.get(member.guild.roles, name=target)
    if role and role not in member.roles:
        to_rem = [r for r in member.roles if r.name in RANKS]
        await member.remove_roles(*to_rem)
        await member.add_roles(role)

# --- [ 5. МЕГА-ДИЗАЙНЕРСКИЙ HELP ] ---
@bot.command()
async def help(ctx):
    e = discord.Embed(title="💠 EVOLUTION TITAN INTERFACE", color=0x2b2d31)
    e.set_thumbnail(url=bot.user.display_avatar.url)
    e.description = "```fix\nSYSTEM: ONLINE | SECURITY: GRANTED\n```"
    
    e.add_field(name="⚔️ БОЕВОЙ СЕКТОР", value=(
        "`!result K A D win/loss` — Отчет матча\n"
        "`!profile [@user]` — Личное досье\n"
        "`!top` — Список элиты"
    ), inline=False)
    
    e.add_field(name="💰 ЭКОНОМИЧЕСКИЙ СЕКТОР", value=(
        "`!work` — Работа\n`!daily` — Ежедневка\n"
        "`!casino [сумма]` — Кости\n`!shop` — Магазин"
    ), inline=False)
    
    e.add_field(name="🛡️ УПРАВЛЕНИЕ", value=(
        "`!clan_create [имя]` — Создать клан (10k)\n"
        "`!set_elo @user [число]` — Админ-команда"
    ), inline=False)
    
    e.set_footer(text=f"Request by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=e)

# --- [ 6. HUB & MATCH SYSTEM ] ---
@bot.command()
async def result(ctx, k: int, a: int, d: int, status: str = "win"):
    if not ctx.message.attachments:
        return await ctx.send("❌ **ОШИБКА:** Скриншот обязателен!")
    
    chan = bot.get_channel(int(HUB_ID))
    if not chan: return await ctx.send("❌ Канал HUB не найден.")

    diff = 25 if status.lower() == "win" else -20
    emb = discord.Embed(title="⚔️ ВХОДЯЩИЕ ДАННЫЕ МАТЧА", color=0x5865f2)
    emb.add_field(name="👤 АГЕНТ", value=ctx.author.mention, inline=True)
    emb.add_field(name="🏆 РЕЗУЛЬТАТ", value=status.upper(), inline=True)
    emb.add_field(name="📊 СТАТИСТИКА", value=f"```\nK/A/D: {k}/{a}/{d}\nELO: {'+' if diff > 0 else ''}{diff}\n```", inline=False)
    emb.set_image(url=ctx.message.attachments[0].url)
    emb.set_footer(text=f"DATA:{ctx.author.id}|{diff}|{k}|{a}|{d}")

    msg = await chan.send(embed=emb)
    for r in ["✅", "❌"]: await msg.add_reaction(r)
    await ctx.send("📡 **ДАННЫЕ ОТПРАВЛЕНЫ В HUB.**")

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or str(reaction.message.channel.id) != str(HUB_ID): return
    if not user.guild_permissions.manage_messages: return

    emb = reaction.message.embeds[0]
    try:
        data = emb.footer.text.split(":")[1].split("|")
        uid, elo_ch, k, a, d = int(data[0]), int(data[1]), int(data[2]), int(data[3]), int(data[4])
    except: return

    u = db.get_u(uid)
    if str(reaction.emoji) == "✅":
        u['elo'] += elo_ch
        u['k'] += k; u['a'] += a; u['d'] += d
        if elo_ch > 0: u['w'] += 1
        else: u['l'] += 1
        db.save()
        await add_xp(uid, 250, reaction.message.channel)
        member = reaction.message.guild.get_member(uid)
        if member: await sync_roles(member, u['elo'])
        await reaction.message.channel.send(f"✅ **ПРИНЯТО:** <@{uid}> ({u['elo']} ELO)")
        await reaction.message.delete()
    elif str(reaction.emoji) == "❌":
        await reaction.message.channel.send(f"❌ **ОТКЛОНЕНО:** <@{uid}>")
        await reaction.message.delete()

# --- [ 7. ПРОФИЛЬ (ДИЗАЙНЕРСКАЯ КАРТОЧКА) ] ---
@bot.command()
async def profile(ctx, m: discord.Member = None):
    m = m or ctx.author
    u = db.get_u(m.id)
    rank = "🌑 Bronze"
    for r, v in RANKS.items():
        if u['elo'] >= v: rank = r

    emb = discord.Embed(title=f"📁 ДОСЬЕ: {m.display_name.upper()}", color=0x00d9ff)
    emb.set_thumbnail(url=m.display_avatar.url)
    
    xp_needed = get_need_xp(u['lvl'])
    bar = "🟦" * int(u['xp']/xp_needed*10) + "⬜" * (10 - int(u['xp']/xp_needed*10))

    emb.add_field(name="🏆 РАНГ", value=f"**{rank}**\nELO: `{u['elo']}`", inline=True)
    emb.add_field(name="💰 ФИНАНСЫ", value=f"Нал: `{u['money']}$`\nБанк: `{u['bank']}$`", inline=True)
    emb.add_field(name="⚔️ БОЕВАЯ СТАТИСТИКА", value=f"```\nK/A/D: {u['k']}/{u['a']}/{u['d']}\nВинрейт: {u['w']}W / {u['l']}L\n```", inline=False)
    emb.add_field(name=f"🆙 УРОВЕНЬ: {u['lvl']}", value=f"{bar} ({u['xp']}/{xp_needed} XP)", inline=False)
    
    if u['clan']: emb.add_field(name="🛡️ КЛАН", value=f"**{u['clan']}**", inline=True)

    emb.set_footer(text="EVOLUTION TITAN v15.0")
    await ctx.send(embed=emb)

# --- [ 8. ЭКОНОМИКА (WORK, CASINO, TOP) ] ---
@bot.command()
async def work(ctx):
    u = db.get_u(ctx.author.id)
    if time.time() < u['last_work']:
        rem = int(u['last_work'] - time.time())
        return await ctx.send(f"⏳ **ОТКАЗ.** Доступ через {rem//60}м {rem%60}с.")
    
    gain = random.randint(800, 2500)
    u['money'] += gain
    u['last_work'] = time.time() + 600
    db.save()
    await add_xp(ctx.author.id, 100, ctx)
    await ctx.send(f"💰 **РАБОТА:** Заработано `{gain}$` и `100 XP`")

@bot.command()
async def casino(ctx, amount: int):
    u = db.get_u(ctx.author.id)
    if amount > u['money'] or amount <= 0: return await ctx.send("❌ Недостаточно средств!")
    if random.random() < 0.47:
        u['money'] += amount
        res = f"🎰 **ПОБЕДА!** Баланс: `{u['money']}$`"
    else:
        u['money'] -= amount
        res = f"📉 **ПРОИГРЫШ.** Баланс: `{u['money']}$`"
    db.save()
    await ctx.send(res)

@bot.command()
async def top(ctx):
    top_list = sorted(db.data["users"].items(), key=lambda x: x[1]['elo'], reverse=True)[:10]
    res = ""
    for i, (uid, data) in enumerate(top_list, 1):
        res += f"**{i}.** <@{uid}> — `{data['elo']} ELO`\n"
    e = discord.Embed(title="🏆 ТОП-10 ОПЕРАТИВНИКОВ", description=res, color=0xf1c40f)
    await ctx.send(embed=e)

# --- [ 9. АДМИНИСТРАТОРЫ ] ---
@bot.command()
@commands.has_permissions(administrator=True)
async def set_elo(ctx, m: discord.Member, val: int):
    u = db.get_u(m.id)
    u['elo'] = val
    db.save()
    await sync_roles(m, val)
    await ctx.send(f"✅ **СИСТЕМА:** {m.mention} установлен ELO: `{val}`")

# --- [ 10. ЗАПУСК ] ---
@bot.event
async def on_ready():
    print(f"--- EVOLUTION V15 LOADED ---")
    stay_active.start()

@tasks.loop(minutes=2)
async def stay_active():
    await bot.change_presence(activity=discord.Streaming(name="!help | Titan Engine", url="https://twitch.tv/discord"))

keep_alive()
bot.run(TOKEN)
