import discord
from discord.ext import commands, tasks
import os, random, datetime, time
from flask import Flask
from threading import Thread

# --- [ 1. ANTI-SLEEP ] ---
app = Flask('')
@app.route('/')
def home(): return "Evolution System: v5.0 God Mode Active"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- [ 2. CONFIG ] ---
TOKEN = os.getenv("DISCORD_TOKEN")
MOD_ID = os.getenv("HUB_ID") 

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

db = {}

def get_u(uid):
    uid = str(uid)
    if uid not in db:
        db[uid] = {
            "elo": 1000, "wins": 0, "losses": 0, "k": 0, "a": 0, "d": 0, 
            "money": 1000, "last_work": 0
        }
    return db[uid]

# --- [ 3. СИСТЕМА АВТО-РОЛЕЙ ] ---
RANKS = {
    "Bronze": 1000,
    "Silver": 1300,
    "Gold": 1600,
    "Platinum": 1900,
    "Diamond": 2200
}

async def update_roles(member, elo):
    new_role_name = "Bronze"
    for role_name, threshold in RANKS.items():
        if elo >= threshold:
            new_role_name = role_name
    
    # Ищем роль на сервере
    role = discord.utils.get(member.guild.roles, name=new_role_name)
    if role and role not in member.roles:
        # Снимаем старые ранговые роли
        to_remove = [r for r in member.roles if r.name in RANKS.keys()]
        await member.remove_roles(*to_remove)
        # Выдаем новую
        await member.add_roles(role)

# --- [ 4. КРАСИВЕЙШИЙ HELP ] ---
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="💠 EVOLUTION ULTIMATE MENU", color=0x2b2d31)
    embed.description = "Система авто-рангов и управления активирована.\n━━━━━━━━━━━━━━━━━━━━"
    
    embed.add_field(name="⚔️ ИГРОКИ", value="`!result` • Отчет матча\n`!profile` • Стата и ранг\n`!top` • Лидеры", inline=False)
    embed.add_field(name="💰 ЭКОНОМИКА", value="`!work` • Работа (КД 5-10м)\n`!casino` • Рискнуть\n`!shop` • Магазин", inline=False)
    
    if ctx.author.guild_permissions.administrator:
        embed.add_field(name="👑 АДМИН ПАНЕЛЬ", value="`!set_elo [@user] [число]`\n`!set_money [@user] [число]`\n`!clear [число]`\n`!reset [@user]`", inline=False)
    
    embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=embed)

# --- [ 5. WORK С КД ] ---
@bot.command()
async def work(ctx):
    u = get_u(ctx.author.id)
    now = int(time.time())
    if now < u['last_work']:
        rem = u['last_work'] - now
        bar = "🟦" * (10 - rem // 60) + "⬜" * (rem // 60)
        return await ctx.send(f"⏳ **Отдых:** {bar}\nДоступно через: **{rem // 60}м {rem % 60}с**")

    gain = random.randint(600, 1600)
    u['money'] += gain
    u['last_work'] = now + random.randint(300, 600)
    await ctx.send(embed=discord.Embed(description=f"✅ {ctx.author.mention}, заработано **{gain}$**", color=0x43b581))

# --- [ 6. HUB & AUTO-ROLES ] ---
@bot.command()
async def result(ctx, k: int, a: int, d: int, res: str = "win"):
    if not ctx.message.attachments: return await ctx.send("❌ Прикрепи скрин!")
    m_chan = bot.get_channel(int(MOD_ID))
    elo_ch = 25 if res.lower() == "win" else -20
    
    emb = discord.Embed(title="⚔️ ПРОВЕРКА МАТЧА", color=0x5865f2)
    emb.add_field(name="👤 Игрок", value=ctx.author.mention)
    emb.add_field(name="📊 Стата", value=f"`KDA: {k}/{a}/{d}`")
    emb.set_image(url=ctx.message.attachments[0].url)
    emb.set_footer(text=f"ID:{ctx.author.id}|ELO:{elo_ch}|K:{k}|A:{a}|D:{d}")
    
    msg = await m_chan.send(embed=emb)
    for r in ["✅", "❌"]: await msg.add_reaction(r)
    await ctx.send("📡 Отправлено в HUB!")

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or str(reaction.message.channel.id) != MOD_ID: return
    emb = reaction.message.embeds[0]
    data = dict(item.split(":") for item in emb.footer.text.split("|"))
    u = get_u(data['ID'])
    member = reaction.message.guild.get_member(int(data['ID']))

    if str(reaction.emoji) == "✅":
        u['elo'] += int(data['ELO'])
        u['k'] += int(data['K']); u['a'] += int(data['A']); u['d'] += int(data['D'])
        if member: await update_roles(member, u['elo'])
        await reaction.message.channel.send(f"✅ Одобрено для <@{data['ID']}>")
    await reaction.message.delete()

# --- [ 7. АДМИН КОМАНДЫ ] ---
@bot.command()
@commands.has_permissions(administrator=True)
async def set_elo(ctx, m: discord.Member, val: int):
    u = get_u(m.id)
    u['elo'] = val
    await update_roles(m, val)
    await ctx.send(f"✅ Установлено **{val} ELO** для {m.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def set_money(ctx, m: discord.Member, val: int):
    get_u(m.id)['money'] = val
    await ctx.send(f"✅ Баланс {m.mention} изменен на **{val}$**")

@bot.command()
@commands.has_permissions(administrator=True)
async def reset(ctx, m: discord.Member):
    if str(m.id) in db: del db[str(m.id)]
    await ctx.send(f"🧹 Данные {m.mention} полностью сброшены.")

# --- [ 8. PROFILE & OTHER ] ---
@bot.command()
async def profile(ctx, m: discord.Member = None):
    m = m or ctx.author; u = get_u(m.id)
    e = discord.Embed(title=f"👤 ПРОФИЛЬ: {m.name}", color=0x00ffcc)
    e.add_field(name="📈 ELO", value=f"**{u['elo']}**", inline=True)
    e.add_field(name="💰 Деньги", value=f"**{u['money']}$**", inline=True)
    e.add_field(name="⚔️ KDA", value=f"`{u['k']}/{u['a']}/{u['d']}`")
    e.set_thumbnail(url=m.display_avatar.url)
    await ctx.send(embed=e)

@bot.command()
async def casino(ctx, bet: int):
    u = get_u(ctx.author.id)
    if bet > u['money'] or bet <= 0: return await ctx.send("❌ Нет денег!")
    if random.random() > 0.55:
        u['money'] += bet
        await ctx.send(f"🎰 **ПОБЕДА!** Баланс: {u['money']}$")
    else:
        u['money'] -= bet
        await ctx.send(f"📉 **ЛУЗ.** Баланс: {u['money']}$")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 10):
    await ctx.channel.purge(limit=amount + 1)

@bot.event
async def on_ready():
    print(f"🔥 Evolution v5.0 Online!")
    stay_active.start()

@tasks.loop(minutes=2)
async def stay_active():
    await bot.change_presence(activity=discord.Streaming(name="!help | Evolution", url="https://twitch.tv/discord"))

keep_alive()
bot.run(TOKEN)
