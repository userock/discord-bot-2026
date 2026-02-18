import discord
from discord.ext import commands, tasks
import os, random, datetime, time, json, asyncio
from flask import Flask
from threading import Thread

# --- [ 1. ВЕБ-СЕРВЕР ДЛЯ ПОДДЕРЖКИ ЖИЗНИ ] ---
app = Flask('')

@app.route('/')
def home():
    return "Evolution System v7.0: Heavy Engine Online"

def run_server():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_server)
    t.start()

# --- [ 2. СИСТЕМА ХРАНЕНИЯ ДАННЫХ ] ---
class Database:
    def __init__(self, filename="database.json"):
        self.filename = filename
        self.data = self.load()

    def load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[ERROR] Ошибка загрузки БД: {e}")
                return {}
        return {}

    def save(self):
        try:
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"[ERROR] Ошибка сохранения БД: {e}")

    def get_user(self, uid):
        uid = str(uid)
        if uid not in self.data:
            self.data[uid] = {
                "elo": 1000, "wins": 0, "losses": 0,
                "k": 0, "a": 0, "d": 0,
                "money": 1000, "lvl": 1, "xp": 0,
                "last_work": 0, "inventory": []
            }
            self.save()
        return self.data[uid]

db = Database()

# --- [ 3. КОНФИГУРАЦИЯ БОТА ] ---
TOKEN = os.getenv("DISCORD_TOKEN")
MOD_ID = os.getenv("HUB_ID")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

RANKS = {
    "Bronze": 1000,
    "Silver": 1300,
    "Gold": 1600,
    "Platinum": 1900,
    "Diamond": 2200
}

# --- [ 4. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ] ---
async def manage_roles(member, elo):
    """Автоматическая смена ролей в зависимости от ELO"""
    target_role_name = "Bronze"
    for r_name, val in RANKS.items():
        if elo >= val:
            target_role_name = r_name
    
    # Находим нужную роль на сервере
    new_role = discord.utils.get(member.guild.roles, name=target_role_name)
    if not new_role:
        print(f"[WARN] Роль {target_role_name} не найдена на сервере!")
        return

    # Если роль уже есть — ничего не делаем
    if new_role in member.roles:
        return

    # Удаляем все старые ранговые роли
    roles_to_remove = [r for r in member.roles if r.name in RANKS.keys()]
    
    try:
        if roles_to_remove:
            await member.remove_roles(*roles_to_remove, reason="Смена ранга ELO")
        await member.add_roles(new_role, reason="Достижение нового порога ELO")
    except discord.Forbidden:
        print("[ERROR] Недостаточно прав для смены ролей! Перетяни роль бота выше всех.")
    except Exception as e:
        print(f"[ERROR] Ошибка при выдаче роли: {e}")

# --- [ 5. ОСНОВНЫЕ КОМАНДЫ (ГЕЙМИНГ) ] ---
@bot.command()
async def result(ctx, k: int, a: int, d: int, status: str = "win"):
    """
    Отправка результата матча.
    Использование: !result [K] [A] [D] [win/loss] + Скриншот
    """
    # 1. Проверка на вложения
    if not ctx.message.attachments:
        emb = discord.Embed(description="❌ **Ошибка:** Вы должны прикрепить скриншот с результатами матча.", color=0xff4444)
        return await ctx.send(embed=emb)

    # 2. Проверка канала модерации
    if not MOD_ID:
        return await ctx.send("❌ **Критическая ошибка:** Переменная HUB_ID не настроена в Render.")
    
    hub_channel = bot.get_channel(int(MOD_ID))
    if not hub_channel:
        return await ctx.send("❌ **Ошибка:** Бот не видит канал HUB. Проверьте ID и права доступа.")

    # 3. Подготовка данных
    res_type = status.lower()
    elo_change = 25 if res_type == "win" else -20
    color = 0x44ff44 if res_type == "win" else 0xff4444

    # 4. Создание заявки для HUB
    hub_emb = discord.Embed(title="⚔️ НОВАЯ ЗАЯВКА НА ПРОВЕРКУ", color=color, timestamp=datetime.datetime.now())
    hub_emb.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
    
    hub_emb.add_field(name="👤 Игрок", value=ctx.author.mention, inline=True)
    hub_emb.add_field(name="🏆 Результат", value=res_type.upper(), inline=True)
    hub_emb.add_field(name="📊 Боевая статистика", value=f"```Убийства: {k}\nПомощь:    {a}\nСмерти:    {d}\nKDR:      {round(k/d, 2) if d > 0 else k}```", inline=False)
    
    hub_emb.set_image(url=ctx.message.attachments[0].url)
    
    # Payload для обработки реакции (скрыт в футере)
    hub_emb.set_footer(text=f"UID:{ctx.author.id} | ELO:{elo_change} | K:{k} | A:{a} | D:{d} | T:{res_type}")

    try:
        hub_msg = await hub_channel.send(embed=hub_emb)
        await hub_msg.add_reaction("✅")
        await hub_msg.add_reaction("❌")
        
        # Ответ пользователю
        confirm = discord.Embed(description=f"📡 **Данные отправлены!**\nВаша статистика `{k}/{a}/{d}` передана судьям в HUB.", color=0x5865f2)
        await ctx.send(embed=confirm)
    except Exception as e:
        await ctx.send(f"❌ Ошибка отправки в HUB: `{e}`")

# --- [ 6. ОБРАБОТЧИК РЕАКЦИЙ (ЯДРО ПРОВЕРКИ) ] ---
@bot.event
async def on_reaction_add(reaction, user):
    # Игнорируем бота и реакции вне канала HUB
    if user.bot: return
    if str(reaction.message.channel.id) != str(MOD_ID): return
    if not reaction.message.embeds: return

    embed = reaction.message.embeds[0]
    if not embed.footer.text or "UID:" not in embed.footer.text: return

    # Проверка прав (только админы могут одобрять)
    if not user.guild_permissions.manage_messages:
        return

    # Парсинг данных из Payload
    try:
        raw_data = embed.footer.text.replace(" ", "").split("|")
        p = {item.split(":")[0]: item.split(":")[1] for item in raw_data}
        
        target_uid = int(p['UID'])
        elo_diff = int(p['ELO'])
    except Exception as e:
        print(f"[ERROR] Ошибка парсинга Payloads: {e}")
        return

    u_data = db.get_user(target_uid)
    guild = reaction.message.guild
    target_member = guild.get_member(target_uid)

    if str(reaction.emoji) == "✅":
        # Начисляем статы
        u_data['elo'] += elo_diff
        u_data['k'] += int(p['K'])
        u_data['a'] += int(p['A'])
        u_data['d'] += int(p['D'])
        
        if elo_diff > 0: u_data['wins'] += 1
        else: u_data['losses'] += 1
        
        db.save()

        # Обновляем роль
        if target_member:
            await manage_roles(target_member, u_data['elo'])

        # Уведомление
        notification = f"✅ **Одобрено!** Игрок <@{target_uid}> получил **{elo_diff} ELO**. (Итого: {u_data['elo']})"
        await reaction.message.channel.send(notification, delete_after=10)
        await reaction.message.delete()

    elif str(reaction.emoji) == "❌":
        await reaction.message.channel.send(f"❌ **Отклонено!** Статистика <@{target_uid}> аннулирована.", delete_after=10)
        await reaction.message.delete()

# --- [ 7. ЭКОНОМИКА И ПРОФИЛЬ ] ---
@bot.command()
async def work(ctx):
    u = db.get_user(ctx.author.id)
    now = int(time.time())
    
    if now < u['last_work']:
        rem = u['last_work'] - now
        return await ctx.send(f"⏳ **Рано!** Твои руки ещё дрожат. Приходи через **{rem // 60}м {rem % 60}с**.")

    gain = random.randint(700, 1800)
    u['money'] += gain
    u['last_work'] = now + random.randint(300, 600) # КД 5-10 мин
    db.save()
    
    emb = discord.Embed(description=f"💰 **{ctx.author.name}**, ты выполнил контракт и получил **{gain}$**", color=0x43b581)
    await ctx.send(embed=emb)

@bot.command()
async def profile(ctx, member: discord.Member = None):
    member = member or ctx.author
    u = db.get_user(member.id)
    
    # Определение ранга текстом
    rank_name = "Bronze"
    for r, v in RANKS.items():
        if u['elo'] >= v: rank_name = r

    emb = discord.Embed(title=f"📊 ДОСЬЕ: {member.name}", color=0x00d9ff)
    emb.add_field(name="🏆 Ранг / ELO", value=f"**{rank_name}** ({u['elo']})", inline=True)
    emb.add_field(name="💰 Кошелек", value=f"**{u['money']}$**", inline=True)
    emb.add_field(name="⚔️ Стата K/A/D", value=f"`{u['k']} / {u['a']} / {u['d']}`", inline=False)
    emb.add_field(name="🎮 Матчи", value=f"Побед: {u['wins']} | Лузов: {u['losses']}", inline=True)
    
    emb.set_thumbnail(url=member.display_avatar.url)
    emb.set_footer(text="Evolution System Heavy Engine")
    await ctx.send(embed=emb)

# --- [ 8. КРАСИВЫЙ HELP ] ---
@bot.command()
async def help(ctx):
    emb = discord.Embed(title="💠 EVOLUTION ULTIMATE INTERFACE", color=0x2b2d31)
    emb.description = "Все модули активны. Выберите категорию команд.\n" + "─" * 25
    
    emb.add_field(name="🎮 **GAMEPLAY**", value="`!result` - Отправить скриншот\n`!profile` - Твоя статистика\n`!top` - Лидерборд", inline=False)
    emb.add_field(name="💸 **ECONOMY**", value="`!work` - Заработок (КД)\n`!casino` - Испытать удачу", inline=False)
    
    if ctx.author.guild_permissions.administrator:
        emb.add_field(name="👑 **ADMIN**", value="`!set_elo @user [v]`\n`!clear [n]`\n`!set_money @user [v]`", inline=False)
    
    emb.set_footer(text="Система работает на ядре Gemini Flash 3.0")
    await ctx.send(embed=emb)

# --- [ 9. АДМИНИСТРИРОВАНИЕ ] ---
@bot.command()
@commands.has_permissions(administrator=True)
async def set_elo(ctx, member: discord.Member, value: int):
    u = db.get_user(member.id)
    u['elo'] = value
    db.save()
    await manage_roles(member, value)
    await ctx.send(f"✅ Установлено **{value} ELO** для {member.mention}")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 10):
    await ctx.channel.purge(limit=amount + 1)

# --- [ 10. ЗАПУСК ] ---
@bot.event
async def on_ready():
    print(f"""
    #######################################
    # EVOLUTION SYSTEM LOADED SUCCESSFULLY #
    # Logged as: {bot.user.name}             #
    #######################################
    """)
    if not stay_active.is_running():
        stay_active.start()

@tasks.loop(minutes=2)
async def stay_active():
    await bot.change_presence(activity=discord.Streaming(name="!help | Evolution", url="https://twitch.tv/discord"))

if __name__ == "__main__":
    keep_alive()
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"Ошибка запуска: {e}")
