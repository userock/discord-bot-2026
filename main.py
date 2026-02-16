import discord
from discord.ext import commands
import os
import requests
import random
from flask import Flask
from threading import Thread

# --- ЖИЗНЕОБЕСПЕЧЕНИЕ (чтобы Render не спал) ---
app = Flask('')
@app.route('/')
def home(): return "Project Evolution: AI Vision Engine Online"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.getenv("DISCORD_TOKEN")
MOD_CHANNEL_ID = os.getenv("MOD_CHANNEL_ID")
OCR_API_KEY = os.getenv("OCR_API_KEY")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# База данных (в памяти)
# {user_id: {"elo": 1000, "wins": 0, "streak": 0}}
db = {}

def get_rank(elo):
    if elo >= 2000: return "💎 Легенда"
    if elo >= 1500: return "🏆 Мастер"
    if elo >= 1200: return "🥇 Элита"
    if elo >= 1000: return "🥈 Игрок"
    return "🥉 Новичок"

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="Анализирую скрины... !help"))
    print(f"✅ Система Evolution AI готова. Бот: {bot.user}")

# --- КОМАНДА ОТПРАВКИ СКРИНШОТА ---
@bot.command()
async def result(ctx):
    if not ctx.message.attachments:
        return await ctx.send("❌ Прикрепи скриншот результата матча!")

    loading_msg = await ctx.send("🔍 **ИИ анализирует скриншот...** Подожди немного.")
    img_url = ctx.message.attachments[0].url

    try:
        # Запрос к OCR API (распознавание текста)
        ocr_url = f"https://api.ocr.space/parse/imageurl?apikey={OCR_API_KEY}&url={img_url}&language=eng&isOverlayRequired=false"
        res = requests.get(ocr_url).json()
        
        parsed_text = ""
        if res.get("ParsedResults"):
            parsed_text = res["ParsedResults"][0]["ParsedText"].lower()
        
        # ЛОГИКА ОПРЕДЕЛЕНИЯ ПОБЕДЫ
        elo_change = 0
        outcome = "НЕОПРЕДЕЛЕНО"
        win_keywords = ["victory", "win", "победа", "winner", "match won"]
        lose_keywords = ["defeat", "lose", "поражение", "match lost"]

        if any(word in parsed_text for word in win_keywords):
            outcome = "ПОБЕДА"
            elo_change = random.randint(25, 35) # Базовое ЭЛО за победу
        elif any(word in parsed_text for word in lose_keywords):
            outcome = "ПОРАЖЕНИЕ"
            elo_change = random.randint(-20, -15) # Снятие за поражение
        else:
            outcome = "НУЖЕН ОСМОТР"
            elo_change = 0

        # ПАНЕЛЬ ДЛЯ МОДЕРАТОРА
        mod_channel = bot.get_channel(int(MOD_CHANNEL_ID))
        embed = discord.Embed(title="🤖 Анализ матча от ИИ", color=0x00ffcc)
        embed.add_field(name="Игрок", value=ctx.author.mention, inline=True)
        embed.add_field(name="Вердикт ИИ", value=f"**{outcome}**", inline=True)
        embed.add_field(name="Расчетное ELO", value=f"`{elo_change if elo_change != 0 else '??'}`", inline=True)
        embed.add_field(name="Текст со скрина (фрагмент)", value=f"```{parsed_text[:300] if parsed_text else 'Текст не найден'}```", inline=False)
        embed.set_image(url=img_url)
        embed.set_footer(text=f"ID:{ctx.author.id}|ELO:{elo_change}")

        msg = await mod_channel.send(embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        
        await loading_msg.edit(content=f"✅ **{ctx.author.name}**, твой скрин отправлен на проверку. Ожидай вердикта модераторов!")

    except Exception as e:
        await ctx.send("⚠️ Ошибка при чтении скрина. Убедись, что ссылка на фото прямая или попробуй еще раз.")
        print(f"Ошибка OCR: {e}")

# --- ПОДТВЕРЖДЕНИЕ МОДЕРАТОРОМ ---
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot: return
    if str(reaction.message.channel.id) != MOD_CHANNEL_ID: return
    if not user.guild_permissions.manage_messages: return

    msg = reaction.message
    embed = msg.embeds[0]
    
    # Достаем данные из футера
    footer_data = embed.footer.text.split("|")
    p_id = int(footer_data[0].replace("ID:", ""))
    elo_to_add = int(footer_data[1].replace("ELO:", ""))
    
    player = await bot.fetch_user(p_id)

    if str(reaction.emoji) == "✅":
        if p_id not in db: db[p_id] = {"elo": 1000, "wins": 0, "streak": 0}
        
        # Логика винстрика
        if elo_to_add > 0:
            db[p_id]["wins"] += 1
            db[p_id]["streak"] += 1
            if db[p_id]["streak"] >= 3: # Бонус за серию от 3 побед
                elo_to_add += 10
                bonus_msg = " + 🔥 Бонус за стрик!"
            else: bonus_msg = ""
        else:
            db[p_id]["streak"] = 0 # Сброс стрика при поражении
            bonus_msg = ""

        db[p_id]["elo"] += elo_to_add
        
        await msg.channel.send(f"🟢 **Подтверждено:** {player.mention} | Изменение: `{elo_to_add}` ELO {bonus_msg}")
        await player.send(f"🎮 Твой результат проверен! Изменение ELO: `{elo_to_add}`. Твой текущий ранг: **{get_rank(db[p_id]['elo'])}**")
        await msg.delete()

    elif str(reaction.emoji) == "❌":
        await msg.channel.send(f"🔴 **Отклонено:** Результат игрока {player.mention} не засчитан.")
        await msg.delete()

# --- ПРОФИЛЬ И ТОП ---
@bot.command()
async def profile(ctx, member: discord.Member = None):
    member = member or ctx.author
    u = db.get(member.id, {"elo": 1000, "wins": 0, "streak": 0})
    
    embed = discord.Embed(title=f"💳 Профиль: {member.name}", color=0xff5500)
    embed.add_field(name="📈 ELO", value=f"`{u['elo']}`", inline=True)
    embed.add_field(name="🏆 Победы", value=f"`{u['wins']}`", inline=True)
    embed.add_field(name="🔥 Стрик", value=f"`{u['streak']}`", inline=True)
    embed.add_field(name="🎖️ Ранг", value=get_rank(u['elo']), inline=False)
    embed.set_thumbnail(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def top(ctx):
    if not db: return await ctx.send("📊 Список пуст.")
    sorted_db = sorted(db.items(), key=lambda x: x[1]['elo'], reverse=True)
    leaderboard = "🏆 **ТОП ИГРОКОВ EVOLUTION**\n"
    for i, (p_id, p_info) in enumerate(sorted_db[:10], 1):
        leaderboard += f"**{i}.** <@{p_id}> — `{p_info['elo']}` ELO | `{p_info['wins']}` побед\n"
    await ctx.send(leaderboard)

keep_alive()
bot.run(TOKEN)
