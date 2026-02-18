import discord
from discord.ext import commands, tasks
import os, random, datetime, time, json, asyncio, logging
from flask import Flask
from threading import Thread

# ==========================================
# 1. ЛОГИРОВАНИЕ (ДЛЯ ОТЛАДКИ В RENDER)
# ==========================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('EvolutionBot')

# ==========================================
# 2. ВЕБ-СЕРВЕР (KEEP ALIVE)
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "Evolution Engine Status: OPERATIONAL"

def run_web_server():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()

# ==========================================
# 3. СИСТЕМА БАЗЫ ДАННЫХ (JSON PERSISTENCE)
# ==========================================
class PersistentDB:
    def __init__(self, path="database.json"):
        self.path = path
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Ошибка загрузки БД: {e}")
                return {}
        return {}

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Ошибка сохранения БД: {e}")

    def get_user(self, uid):
        uid = str(uid)
        if uid not in self.data:
            self.data[uid] = {
                "elo": 1000,
                "money": 500,
                "stats": {"k": 0, "a": 0, "d": 0, "w": 0, "l": 0},
                "level": 1,
                "xp": 0,
                "last_work": 0,
                "inventory": []
            }
            self.save()
        return self.data[uid]

db = PersistentDB()

# ==========================================
# 4. НАСТРОЙКИ БОТА
# ==========================================
TOKEN = os.getenv("DISCORD_TOKEN")
MOD_CHANNEL_ID = os.getenv("HUB_ID") # Канал, куда летят скрины

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Названия ролей и пороги ELO
RANK_ROLES = {
    "🌑 Bronze": 0,
    "🥈 Silver": 1200,
    "🔱 Gold": 1500,
    "💎 Platinum": 1850,
    "👑 Diamond": 2200,
    "🔥 Immortal": 2600
}

# ==========================================
# 5. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================================
async def update_member_roles(member, current_elo):
    """Автоматически обновляет роль игрока в зависимости от его ELO"""
    if not member or not hasattr(member, 'guild'):
        return

    # Определяем, какая роль должна быть
    target_role_name = "🌑 Bronze"
    for r_name, threshold in RANK_ROLES.items():
        if current_elo >= threshold:
            target_role_name = r_name

    guild = member.guild
    # Проверяем, существует ли такая роль на сервере, если нет - создаем (опционально)
    target_role = discord.utils.get(guild.roles, name=target_role_name)
    
    if not target_role:
        logger.warning(f"Роль {target_role_name} не найдена на сервере {guild.name}")
        return

    # Если у игрока уже есть эта роль, ничего не делаем
    if target_role in member.roles:
        return

    # Список всех ранговых ролей для удаления
    all_rank_role_names = list(RANK_ROLES.keys())
    roles_to_remove = [r for r in member.roles if r.name in all_rank_role_names]

    try:
        if roles_to_remove:
            await member.remove_roles(*roles_to_remove)
        await member.add_roles(target_role)
        logger.info(f"Обновлена роль для {member.name}: {target_role_name}")
    except discord.Forbidden:
        logger.error(f"Нет прав на изменение ролей для {member.name}. Поднимите роль бота выше!")

# ==========================================
# 6. КРАСИВЕЙШЕЕ МЕНЮ HELP (EMBED)
# ==========================================
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="🌟 ЦЕНТР УПРАВЛЕНИЯ EVOLUTION",
        description=(
            "Добро пожаловать в элитную систему мониторинга матчей и экономики.\n"
            "Ниже приведен список доступных модулей и их функций.\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=0x2b2d31,
        timestamp=datetime.datetime.now()
    )

    embed.add_field(
        name="🎮 ГЕЙМИНГ & РЕЙТИНГ",
        value=(
            "`!result K A D win/loss` — Отправить отчет матча (обязательно скрин)\n"
            "`!profile [@user]` — Просмотр карточки игрока и ELO\n"
            "`!top` — Топ-10 лучших игроков сервера"
        ),
        inline=False
    )

    embed.add_field(
        name="💰 ЭКОНОМИКА & ФАН",
        value=(
            "`!work` — Пойти на смену (КД 5-10 минут)\n"
            "`!casino [сумма]` — Испытать удачу (шанс 45%)\n"
            "`!daily` — Ежедневный бонус валюты"
        ),
        inline=False
    )

    if ctx.author.guild_permissions.administrator:
        embed.add_field(
            name="🛠️ АДМИНИСТРАЦИЯ",
            value=(
                "`!set_elo @user [v]` — Установить рейтинг вручную\n"
                "`!add_money @user [v]` — Выдать валюту игроку\n"
                "`!clear [кол-во]` — Быстрая очистка чата"
            ),
            inline=False
        )

    embed.set_thumbnail(url=bot.user.display_avatar.url)
    embed.set_footer(text=f"Запросил: {ctx.author.name} • Версия 10.4.2", icon_url=ctx.author.display_avatar.url)
    
    await ctx.send(embed=embed)

# ==========================================
# 7. СИСТЕМА ПРОВЕРКИ МАТЧЕЙ (CORE)
# ==========================================
@bot.command()
async def result(ctx, k: int, a: int, d: int, status: str = "win"):
    """Отправка результата в HUB на проверку"""
    if not ctx.message.attachments:
        return await ctx.send("❌ **Ошибка:** Вы должны прикрепить скриншот (доказательство) к сообщению!")

    if not MOD_CHANNEL_ID:
        return await ctx.send("❌ **Ошибка настройки:** Переменная `HUB_ID` не задана в Render.")

    mod_channel = bot.get_channel(int(MOD_CHANNEL_ID))
    if not mod_channel:
        return await ctx.send("❌ **Ошибка:** Бот не видит канал HUB. Проверьте права и ID.")

    res_status = status.lower()
    elo_gain = 25 if res_status == "win" else -20
    color = 0x2ecc71 if res_status == "win" else 0xe74c3c

    # Создаем Embed для модераторов
    hub_emb = discord.Embed(
        title="⚔️ НОВАЯ ЗАЯВКА НА ПРОВЕРКУ",
        description=f"Игрок {ctx.author.mention} подал заявку на обновление рейтинга.",
        color=color,
        timestamp=datetime.datetime.now()
    )
    hub_emb.add_field(name="🏆 Итог матча", value=f"**{res_status.upper()}**", inline=True)
    hub_emb.add_field(name="📊 Статистика", value=f"K: `{k}` | A: `{a}` | D: `{d}`", inline=True)
    hub_emb.add_field(name="📈 Ожидаемое ELO", value=f"**{elo_gain}**", inline=True)
    hub_emb.set_image(url=ctx.message.attachments[0].url)
    
    # Payload для обработки реакции (зашито в футер)
    hub_emb.set_footer(text=f"UID:{ctx.author.id} | E:{elo_gain} | K:{k} | A:{a} | D:{d} | S:{res_status}")

    try:
        msg = await mod_channel.send(embed=hub_emb)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        await ctx.send(f"📡 {ctx.author.mention}, твой результат отправлен на проверку в HUB!")
    except Exception as e:
        await ctx.send(f"❌ Произошла ошибка при отправке: {e}")

# ==========================================
# 8. ОБРАБОТЧИК РЕАКЦИЙ (HUB LOGIC)
# ==========================================
@bot.event
async def on_reaction_add(reaction, user):
    if user.bot: return
    if str(reaction.message.channel.id) != str(MOD_CHANNEL_ID): return
    if not reaction.message.embeds: return

    embed = reaction.message.embeds[0]
    if not embed.footer.text or "UID:" not in embed.footer.text: return

    # Только люди с правами модератора могут подтверждать
    if not user.guild_permissions.manage_messages:
        return

    # Парсим скрытые данные
    try:
        raw = embed.footer.text.replace(" ", "").split("|")
        payload = {i.split(":")[0]: i.split(":")[1] for i in raw}
        
        target_id = int(payload['UID'])
        elo_diff = int(payload['E'])
    except Exception as e:
        logger.error(f"Ошибка парсинга Payload: {e}")
        return

    target_user_data = db.get_user(target_id)
    guild = reaction.message.guild
    member = guild.get_member(target_id)

    if str(reaction.emoji) == "✅":
        # Обновляем статы
        target_user_data['elo'] += elo_diff
        target_user_data['stats']['k'] += int(payload['K'])
        target_user_data['stats']['a'] += int(payload['A'])
        target_user_data['stats']['d'] += int(payload['D'])
        
        if elo_diff > 0: target_user_data['stats']['w'] += 1
        else: target_user_data['stats']['l'] += 1
        
        db.save()
        
        if member:
            await update_member_roles(member, target_user_data['elo'])
        
        await reaction.message.channel.send(f"✅ Результат игрока <@{target_id}> одобрен администратором **{user.name}**", delete_after=5)
        await reaction.message.delete()

    elif str(reaction.emoji) == "❌":
        await reaction.message.channel.send(f"❌ Заявка игрока <@{target_id}> отклонена модератором **{user.name}**", delete_after=5)
        await reaction.message.delete()

# ==========================================
# 9. ЭКОНОМИКА (WORK, CASINO, PROFILE)
# ==========================================
@bot.command()
async def work(ctx):
    u = db.get_user(ctx.author.id)
    now = int(time.time())
    
    if now < u['last_work']:
        wait_sec = u['last_work'] - now
        return await ctx.send(f"⏳ {ctx.author.name}, ты слишком устал. Возвращайся через **{wait_sec // 60}м {wait_sec % 60}с**.")

    reward = random.randint(400, 1200)
    u['money'] += reward
    # КД от 5 до 10 минут
    u['last_work'] = now + random.randint(300, 600)
    db.save()

    emb = discord.Embed(
        description=f"💰 **Успешная работа!**\nВы заработали **{reward}$**.\nСледующая смена через { (u['last_work']-now)//60 } мин.",
        color=0x2ecc71
    )
    await ctx.send(embed=emb)

@bot.command()
async def profile(ctx, member: discord.Member = None):
    member = member or ctx.author
    u = db.get_user(member.id)
    
    # Вычисляем текущий ранг для отображения
    cur_rank = "🌑 Bronze"
    for r_name, threshold in RANK_ROLES.items():
        if u['elo'] >= threshold: cur_rank = r_name

    emb = discord.Embed(title=f"👤 КАРТОЧКА ИГРОКА: {member.name}", color=0x00d9ff)
    emb.add_field(name="🏆 Текущий Ранг", value=f"**{cur_rank}**", inline=True)
    emb.add_field(name="📈 Рейтинг ELO", value=f"**{u['elo']}**", inline=True)
    emb.add_field(name="💰 Баланс", value=f"**{u['money']}$**", inline=True)
    
    s = u['stats']
    kda_ratio = round((s['k'] + s['a']) / s['d'], 2) if s['d'] > 0 else (s['k'] + s['a'])
    emb.add_field(name="⚔️ Боевая статистика (K/A/D)", value=f"`{s['k']} / {s['a']} / {s['d']}` (KDA: {kda_ratio})", inline=False)
    emb.add_field(name="🏁 Матчи", value=f"Побед: {s['w']} | Поражений: {s['l']}", inline=True)
    
    emb.set_thumbnail(url=member.display_avatar.url)
    emb.set_footer(text="Evolution Ultimate • persistence system active")
    await ctx.send(embed=embed)

@bot.command()
async def casino(ctx, amount: int):
    u = db.get_user(ctx.author.id)
    if amount <= 0 or amount > u['money']:
        return await ctx.send("❌ У вас недостаточно средств или сумма некорректна!")

    if random.random() < 0.45: # 45% шанс выигрыша
        u['money'] += amount
        color, text = 0x2ecc71, f"🎰 **ВЫИГРЫШ!** Вы получили **{amount}$**"
    else:
        u['money'] -= amount
        color, text = 0xe74c3c, f"📉 **ПРОИГРЫШ.** Вы потеряли **{amount}$**"
    
    db.save()
    await ctx.send(embed=discord.Embed(description=text, color=color))

# ==========================================
# 10. АДМИН-КОМАНДЫ
# ==========================================
@bot.command()
@commands.has_permissions(administrator=True)
async def set_elo(ctx, member: discord.Member, value: int):
    u = db.get_user(member.id)
    u['elo'] = value
    db.save()
    await update_member_roles(member, value)
    await ctx.send(f"✅ Игроку {member.mention} установлен рейтинг **{value} ELO**.")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 10):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 Удалено **{amount}** сообщений.", delete_after=3)

# ==========================================
# 11. СОБЫТИЯ И ЗАПУСК
# ==========================================
@bot.event
async def on_ready():
    logger.info(f"--- Evolution Engine v10 запущен как {bot.user} ---")
    if not stay_active_loop.is_running():
        stay_active_loop.start()

@tasks.loop(minutes=2)
async def stay_active_loop():
    # Статус стриминга помогает обходить некоторые ограничения хостинга
    await bot.change_presence(activity=discord.Streaming(name="!help | Evolution Engine", url="https://twitch.tv/discord"))

if __name__ == "__main__":
    keep_alive() # Запуск Flask в потоке
    try:
        bot.run(TOKEN)
    except Exception as e:
        logger.critical(f"Критическая ошибка запуска: {e}")
