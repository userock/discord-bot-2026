import discord
from discord.ext import commands, tasks
import os, json, random, datetime, time, re, asyncio
import requests
from PIL import Image, ImageOps, ImageEnhance
import pytesseract
from io import BytesIO
from flask import Flask
from threading import Thread

# ==========================================
# [1] VISION & AI PERSONA CORE
# ==========================================
# Укажи свой путь к Tesseract!
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class AI_Engine:
    @staticmethod
    async def extract_kda(url):
        try:
            res = requests.get(url)
            img = Image.open(BytesIO(res.content)).convert('L')
            img = ImageEnhance.Contrast(img).enhance(2.5)
            text = pytesseract.image_to_string(img, config='--oem 3 --psm 6')
            
            match = re.findall(r'(\d+)[\s/|-]+(\d+)[\s/|-]+(\d+)', text)
            if match: return int(match[0][0]), int(match[0][2]), int(match[0][1]) # K, D, A
            
            nums = re.findall(r'\d+', text)
            if len(nums) >= 3: return int(nums[0]), int(nums[1]), int(nums[2])
            return None
        except Exception as e:
            print(f"[VISION ERROR]: {e}")
            return None

    @staticmethod
    def generate_comment(k, a, d, is_win):
        kda = (k + a) / d if d > 0 else k + a
        if is_win:
            if kda >= 3: return "🔥 Анализ: Абсолютная доминация. Система зафиксировала киберспортивный уровень."
            elif kda >= 1.5: return "✅ Анализ: Достойная победа. Сработал четко, как алгоритм."
            else: return "⚠️ Анализ: Команда вытащила тебя на своих плечах. Но победа есть победа."
        else:
            if kda >= 2: return "💔 Анализ: Система соболезнует. Ты старался, но тиммейты потянули на дно."
            else: return "📉 Анализ: Критический сбой навыков. Рекомендую экстренную тренировку аима."

# ==========================================
# [2] DATABASE CORE
# ==========================================
class NeuralDB:
    def __init__(self):
        self.file = "overlord_v100_data.json"
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.file):
            try:
                with open(self.file, "r", encoding="utf-8") as f: return json.load(f)
            except: pass
        return {"users": {}, "clans": {}}

    def save(self):
        with open(self.file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    def get_user(self, uid):
        uid = str(uid)
        if uid not in self.data["users"]:
            self.data["users"][uid] = {
                "elo": 1000, "money": 5000, "k": 0, "a": 0, "d": 0, 
                "w": 0, "l": 0, "gpu": 0, "clan": None, "t_work": 0
            }
            self.save()
        return self.data["users"][uid]

db = NeuralDB()

# ==========================================
# [3] BOT CONFIGURATION
# ==========================================
TOKEN = "ТВОЙ_ТОКЕН"
HUB_ID = 123456789012345678  # ВСТАВЬ ID ХАБА (БЕЗ КОВЫЧЕК!)
PREFIX = "!"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)
RANKS = {"Bronze": 0, "Silver": 1200, "Gold": 1600, "Platinum": 2100, "Diamond": 2700, "Immortal": 3500}

# ==========================================
# [4] УМНЫЙ !RESULT С ИИ-ХАРАКТЕРОМ
# ==========================================
@bot.command()
async def result(ctx, status: str = "win"):
    if not ctx.message.attachments:
        return await ctx.send("❌ **AI:** Эй, а где скриншот? Я не умею читать мысли.")

    status = status.lower()
    is_win = status in ["win", "победа", "w"]
    
    msg = await ctx.send("🌀 **AI VISION:** Загружаю скриншот в нейросеть. Анализирую пиксели...")
    stats = await AI_Engine.extract_kda(ctx.message.attachments[0].url)

    if not stats:
        return await msg.edit(content="❌ **AI VISION:** Изображение размыто или формат не распознан. Мои оптические сенсоры сдались.")

    k, a, d = stats
    elo_delta = 25 if is_win else -20
    ai_comment = AI_Engine.generate_comment(k, a, d, is_win)
    
    await msg.delete()
    
    emb = discord.Embed(title="🤖 ИИ-АНАЛИЗ ЗАВЕРШЕН", color=0x2ecc71 if is_win else 0xe74c3c)
    emb.add_field(name="Распознано", value=f"```fix\nK: {k} | A: {a} | D: {d}\n```", inline=False)
    emb.add_field(name="Исход", value="ПОБЕДА" if is_win else "ПОРАЖЕНИЕ", inline=True)
    emb.add_field(name="Прогноз ELO", value=f"{'+' if elo_delta>0 else ''}{elo_delta}", inline=True)
    emb.add_field(name="Вердикт Системы", value=f"_{ai_comment}_", inline=False)
    emb.set_image(url=ctx.message.attachments[0].url)
    emb.set_footer(text=f"PAYLOAD:{ctx.author.id}|{elo_delta}|{k}|{a}|{d}")

    confirm = await ctx.send(content="**Подтверди отправку в HUB:**", embed=emb)
    await confirm.add_reaction("✅")
    await confirm.add_reaction("❌")

    def check(r, u): return u == ctx.author and str(r.emoji) in ["✅", "❌"]

    try:
        r, u = await bot.wait_for('reaction_add', timeout=60.0, check=check)
        if str(r.emoji) == "✅":
            hub = bot.get_channel(HUB_ID)
            if hub:
                await hub.send(content=f"📡 **ВХОДЯЩИЙ ОТЧЕТ | <@{ctx.author.id}>**", embed=emb)
                await ctx.send("✅ Данные улетели в Хаб. Ожидай верификации.")
            else: await ctx.send("❌ Критическая ошибка: Канал HUB не найден.")
        else: await ctx.send("❌ Отмена. Я удаляю это из кэша.")
    except asyncio.TimeoutError:
        await ctx.send("⏳ Ты слишком долго думал. Тайм-аут.")

# ==========================================
# [5] HUB MODERATION
# ==========================================
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or reaction.message.channel.id != HUB_ID: return
    if not user.guild_permissions.manage_messages: return

    if str(reaction.emoji) == "✅" and reaction.message.embeds:
        emb = reaction.message.embeds[0]
        try:
            data = emb.footer.text.split("PAYLOAD:")[1].split("|")
            uid, elo_add, k, a, d = int(data[0]), int(data[1]), int(data[2]), int(data[3]), int(data[4])
            
            u = db.get_user(uid)
            u['elo'] += elo_add; u['k'] += k; u['a'] += a; u['d'] += d
            if elo_add > 0: u['w'] += 1
            else: u['l'] += 1
            db.save()
            
            await reaction.message.channel.send(f"🏆 **ПРИНЯТО:** <@{uid}> обновлен. Текущий ELO: **{u['elo']}**")
            await reaction.message.delete()
        except Exception as e: print(f"Hub Error: {e}")

# ==========================================
# [6] CLAN SYSTEM & RPG
# ==========================================
@bot.command()
async def clan_create(ctx, *, name: str):
    u = db.get_user(ctx.author.id)
    if u['money'] < 10000: return await ctx.send("❌ Создание клана стоит 10,000$. У тебя нет таких денег.")
    if u['clan']: return await ctx.send("❌ Ты уже состоишь в клане.")
    if name in db.data["clans"]: return await ctx.send("❌ Это имя уже занято.")

    u['money'] -= 10000
    u['clan'] = name
    db.data["clans"][name] = {"owner": ctx.author.id, "members": [ctx.author.id], "elo": u['elo']}
    db.save()
    await ctx.send(f"🛡️ Клан **{name}** успешно зарегистрирован в системе!")

@bot.command()
async def profile(ctx, member: discord.Member = None):
    member = member or ctx.author
    u = db.get_user(member.id)
    rank = next((r for r, v in reversed(RANKS.items()) if u['elo'] >= v), "Bronze")

    emb = discord.Embed(title=f"📁 ПАСПОРТ: {member.name.upper()}", color=0x3498db)
    emb.add_field(name="Ранг", value=f"`{rank}` (ELO: {u['elo']})")
    emb.add_field(name="Баланс", value=f"`{u['money']}$` | GPU: `{u['gpu']}`")
    emb.add_field(name="Клан", value=f"`{u['clan'] or 'Одиночка'}`")
    emb.add_field(name="Статистика", value=f"K/A/D: `{u['k']}/{u['a']}/{u['d']}`\nПобеды/Поражения: `{u['w']}/{u['l']}`", inline=False)
    await ctx.send(embed=emb)

# ==========================================
# [7] ERROR HANDLER & KEEP ALIVE
# ==========================================
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound): return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("⚠️ **AI:** Ты забыл указать аргументы. Напиши `!help`.")
    else:
        print(f"Global Error: {error}")

app = Flask('')
@app.route('/')
def home(): return "V100 Active"
def keep_alive(): Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()

@bot.event
async def on_ready():
    print(f"--- NEURAL OVERLORD V100 ONLINE ---")
    keep_alive()

bot.run(TOKEN)
