import random
import time
import hashlib
import telebot
from telebot import types

# Твой реальный токен
TOKEN = "6939016085:AAEfmOkRXKdw0_leniUt_jf5NKSM51IgI6c"
bot = telebot.TeleBot(TOKEN)

# База данных пользователей и раунда
users_db = {}
current_round_bets = {}
is_round_active = False
round_end_time = 0
current_game_hash = ""
current_secret_result = None  # Секретный результат текущего раунда для инсайда


def get_user(user_id, username="Игрок"):
    if user_id not in users_db:
        users_db[user_id] = {
            "name": username,
            "balance": 100000,
            "last_bonus": 0,
            "last_secret_bonus": 0
        }
    return users_db[user_id]


def parse_amount(amount_str):
    """Конвертирует строку ставки вроде '100к', '1.5кк', '5000' в число MB"""
    amount_str = amount_str.lower().strip()
    try:
        if 'кк' in amount_str:
            num = float(amount_str.replace('кк', '').replace(',', '.'))
            return int(num * 1_000_000)
        elif 'к' in amount_str or 'k' in amount_str:
            num = float(amount_str.replace('к', '').replace('k', '').replace(',', '.'))
            return int(num * 1_000)
        else:
            return int(amount_str)
    except ValueError:
        return 0


def get_emoji(multiplier):
    if multiplier == 2:
        return "🔵"
    elif multiplier == 3:
        return "🟡"
    elif multiplier == 5:
        return "🔴"
    elif multiplier == 50:
        return "🟢"
    return "⚪"


def generate_prediction():
    multipliers = [2, 3, 5, 50]
    weights = [0.47, 0.35, 0.17, 0.01]
    return random.choices(multipliers, weights=weights, k=1)[0]


def get_reply_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🔮 Вывести предикт"),
        types.KeyboardButton("💼 Кошелек"),
        types.KeyboardButton("🏦 Банк раунда"),
        types.KeyboardButton("📊 Лидеры"),
        types.KeyboardButton("🎁 Бонус 50к")
    )
    return markup


@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    user = get_user(message.from_user.id, message.from_user.first_name)
    bot.send_message(
        message.chat.id,
        f"🦍 **BOT GORILLA | СИМУЛЯТОР**\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Твой баланс: **{user['balance']:,} MB**\n\n"
        f"📌 **Как играть:**\n"
        f"• Сделать ставку: `ставка 3 100к`\n"
        f"• Сменить ник (10,000 MB): `.ник ТвоеИмя`\n"
        f"• Проверить банк: кнопка ниже 👇",
        parse_mode="Markdown",
        reply_markup=get_reply_keyboard()
    )


# Секретная команда инсайда в ЛС
@bot.message_handler(
    func=lambda message: message.chat.type == "private" and message.text.lower() in [".инсайд", "чтодаст", "инсайд"])
def secret_inside_info(message):
    global is_round_active, current_secret_result

    if not is_round_active or current_secret_result is None:
        bot.reply_to(message, "⏳ Сейчас нет активного раунда. Запусти раунд в беседе, чтобы узнать инсайд!")
        return

    emoji = get_emoji(current_secret_result)
    bot.reply_to(
        message,
        f"🤫 **ИНСАЙДЕРСКАЯ ИНФОРМАЦИЯ**\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"В текущем раунде выпадет: {emoji} **x{current_secret_result}**\n"
        f"_Используй с умом!_",
        parse_mode="Markdown"
    )


# Таблица лидеров
@bot.message_handler(func=lambda message: message.text in ["📊 Лидеры", "лидеры", "/leaders"])
def show_leaders(message):
    if not users_db:
        bot.reply_to(message, "📊 Список лидеров пока пуст.", reply_markup=get_reply_keyboard())
        return

    sorted_users = sorted(users_db.values(), key=lambda x: x["balance"], reverse=True)

    leaders_lines = []
    medals = ["🥇", "🥈", "🥉"]

    for idx, u_data in enumerate(sorted_users[:10]):
        place_sign = medals[idx] if idx < 3 else f"🔹 **{idx + 1}.**"
        leaders_lines.append(f"{place_sign} {u_data['name']} — **{u_data['balance']:,} MB**")

    leaders_text = "\n".join(leaders_lines)
    response = (
        f"📊 **ТАБЛИЦА ЛИДЕРОВ**\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"{leaders_text}"
    )

    bot.reply_to(message, response, parse_mode="Markdown", reply_markup=get_reply_keyboard())


# Смена ника
@bot.message_handler(func=lambda message: message.text.lower().startswith(".ник"))
def change_nickname(message):
    user_id = message.from_user.id
    user = get_user(user_id, message.from_user.first_name)

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ Укажи новый ник! Пример: `.ник Монах`", parse_mode="Markdown")
        return

    new_name = parts[1].strip()
    if len(new_name) > 20:
        bot.reply_to(message, "⚠️ Ник слишком длинный (максимум 20 символов).")
        return

    cost = 10000
    if user["balance"] < cost:
        bot.reply_to(message, f"❌ Смена ника стоит **{cost:,} MB**! У тебя недостаточно средств.",
                     parse_mode="Markdown")
        return

    user["balance"] -= cost
    user["name"] = new_name

    bot.reply_to(
        message,
        f"✅ **НИК УСПЕШНО ИЗМЕНЕН**\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Новый ник: **{new_name}**\n"
        f"💸 Списано: **{cost:,} MB**\n"
        f"💰 Баланс: **{user['balance']:,} MB**",
        parse_mode="Markdown",
        reply_markup=get_reply_keyboard()
    )


# Банк раунда с визуальным прогресс-баром
@bot.message_handler(func=lambda message: message.text.lower() in ["банк", "🏦 банк раунда"])
def show_round_pool(message):
    global current_round_bets, is_round_active, round_end_time, current_game_hash

    if not is_round_active:
        bot.reply_to(message,
                     "🏦 Сейчас нет активного раунда. Сделайте ставку или нажмите «Вывести предикт», чтобы запустить новый раунд!",
                     reply_markup=get_reply_keyboard())
        return

    timeLeft = int(round_end_time - time.time())
    if timeLeft < 0: timeLeft = 0

    # Генерация красивого прогресс-бара (на 10 блоков)
    progress_blocks = int((60 - timeLeft) / 6)
    if progress_blocks > 10: progress_blocks = 10
    if progress_blocks < 0: progress_blocks = 0
    bar = "🟢" * progress_blocks + "⚪" * (10 - progress_blocks)

    user_id = message.from_user.id
    user_total_bet = 0
    lines_text = ""

    for mult in [2, 3, 5, 50]:
        bettors_for_mult = []
        for uid, data in current_round_bets.items():
            if mult in data["bets"] and data["bets"][mult] > 0:
                amount = data["bets"][mult]
                bettors_for_mult.append(f"• {data['name']} — <code>{amount:,} MB</code>")
                if uid == user_id: user_total_bet += amount
        if bettors_for_mult:
            lines_text += f"\n<b>🎯 Ставки на x{mult}:</b>\n" + "\n".join(bettors_for_mult) + "\n"

    current_user_name = get_user(user_id, message.from_user.first_name)["name"]
    response = (
        f"🏦 <b>БАНК ТЕКУЩЕГО РАУНДА</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Игрок: <b>{current_user_name}</b>\n"
        f"💎 Ваша ставка в банке: <b>{user_total_bet:,} MB</b>\n\n"
        f"⏳ Прогресс раунда:\n{bar} (осталось <b>{timeLeft} сек.</b>)\n\n"
        f"🔗 Хеш: <code>{current_game_hash[:16]}...</code>"
        f"{lines_text}"
    )
    bot.reply_to(message, response, parse_mode="HTML", reply_markup=get_reply_keyboard())


@bot.message_handler(func=lambda message: message.text.strip().lower() == "сюдабонус")
def secret_bonus(message):
    user = get_user(message.from_user.id, message.from_user.first_name)
    current_time = time.time()
    if current_time - user["last_secret_bonus"] < 300:
        left = int(300 - (current_time - user["last_secret_bonus"]))
        bot.reply_to(message, f"⏳ Перезарядка секретного бонуса: {left // 60} мин. {left % 60} сек.")
        return
    user["balance"] += 500000
    user["last_secret_bonus"] = current_time
    bot.reply_to(message, f"🤫 **ПРОМОКОД АКТИВИРОВАН!**\n🎁 +500 000 MB\n💰 Баланс: **{user['balance']:,} MB**",
                 parse_mode="Markdown", reply_markup=get_reply_keyboard())


@bot.message_handler(func=lambda message: message.text == "💼 Кошелек")
def show_wallet(message):
    user = get_user(message.from_user.id, message.from_user.first_name)
    bot.send_message(
        message.chat.id,
        f"💼 **ВАШ КОШЕЛЕК**\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Баланс: **{user['balance']:,} MB**",
        parse_mode="Markdown",
        reply_markup=get_reply_keyboard()
    )


@bot.message_handler(func=lambda message: message.text == "🎁 Бонус 50к")
def get_bonus(message):
    user = get_user(message.from_user.id, message.from_user.first_name)
    if time.time() - user["last_bonus"] < 3600:
        bot.reply_to(message, "⏳ Ежечасный бонус уже был получен! Загляните позже.")
        return
    user["balance"] += 50000
    user["last_bonus"] = time.time()
    bot.reply_to(message, f"🎁 **БОНУС УСПЕШНО ПОЛУЧЕН**\n🎉 +50,000 MB\n💰 Баланс: **{user['balance']:,} MB**",
                 parse_mode="Markdown", reply_markup=get_reply_keyboard())


def run_round_logic(chat_id):
    global is_round_active, current_round_bets, round_end_time, current_game_hash, current_secret_result
    is_round_active = True
    round_end_time = time.time() + 60
    current_game_hash = hashlib.sha256(str(time.time()).encode()).hexdigest()

    current_secret_result = generate_prediction()

    bot.send_message(
        chat_id,
        f"🦍 **BOT GORILLA | НОВЫЙ РАУНД**\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🎲 Прием ставок открыт!\n"
        f"⏳ Итоги через **60 секунд**\n\n"
        f"🔗 Хеш: `{current_game_hash[:16]}...`",
        parse_mode="Markdown",
        reply_markup=get_reply_keyboard()
    )

    time.sleep(60)

    result = current_secret_result
    emoji = get_emoji(result)
    is_round_active = False

    results_summary = []

    for uid, data in list(current_round_bets.items()):
        p_user = get_user(uid)
        p_name = data["name"]
        p_bets = data["bets"]

        player_lines = []
        total_payout = 0

        for mult, amount in p_bets.items():
            if result == mult:
                win_sum = amount * mult
                total_payout += win_sum
                player_lines.append(f"🟢 ставка x{mult} {amount:,} MB — **ВЫИГРАЛА (+{win_sum:,})**")
            else:
                player_lines.append(f"🔴 ставка x{mult} {amount:,} MB — проиграла")

        p_user["balance"] += total_payout

        bets_formatted = "\n".join(player_lines)
        results_summary.append(f"👤 **{p_name}**:\n{bets_formatted}")

    summary_text = "\n\n".join(results_summary) if results_summary else "💤 Никто не сделал ставок в этом раунде."
    current_round_bets.clear()
    current_secret_result = None

    photo_filename = f"x{result}.png"
    caption = (
        f"🎲 **ИТОГИ РАУНДА** 🎲\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Выпал множитель: {emoji} **x{result}**\n\n"
        f"{summary_text}"
    )

    try:
        with open(photo_filename, 'rb') as photo:
            bot.send_photo(chat_id, photo=photo, caption=caption, parse_mode="Markdown",
                           reply_markup=get_reply_keyboard())
    except FileNotFoundError:
        bot.send_message(chat_id, f"⚠️ Файл {photo_filename} не найден!\n\n{caption}", parse_mode="Markdown",
                         reply_markup=get_reply_keyboard())


@bot.message_handler(func=lambda message: message.text == "🔮 Вывести предикт")
def send_predict(message):
    result = generate_prediction()
    emoji = get_emoji(result)
    game_hash = hashlib.sha256(str(time.time()).encode()).hexdigest()

    caption_text = (
        f"🔮 **ПРЕДИКТ АЛГОРИТМА**\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Результат: {emoji} **x{result}**\n"
        f"🔗 Хеш: `{game_hash[:16]}...`"
    )

    photo_filename = f"x{result}.png"
    try:
        with open(photo_filename, 'rb') as photo:
            bot.send_photo(message.chat.id, photo=photo, caption=caption_text, parse_mode="Markdown",
                           reply_markup=get_reply_keyboard())
    except FileNotFoundError:
        bot.send_message(message.chat.id, f"⚠️ Файл {photo_filename} не найден!\n\n{caption_text}",
                         parse_mode="Markdown", reply_markup=get_reply_keyboard())


@bot.message_handler(func=lambda message: message.text.lower().startswith("ставка"))
def handle_bet(message):
    global current_round_bets, is_round_active
    user_id = message.from_user.id
    user_data = get_user(user_id, message.from_user.first_name)
    name = user_data["name"]

    parts = message.text.split()
    if len(parts) != 3:
        bot.reply_to(message, "⚠️ **Ошибка формата!**\nПример: `ставка 3 100к` или `ставка 2 50к`",
                     parse_mode="Markdown")
        return

    mult_str = parts[1].lower().replace('х', '').replace('x', '')
    if not mult_str.isdigit() or int(mult_str) not in [2, 3, 5, 50]:
        bot.reply_to(message, "⚠️ Ошибка коэффициента! Доступно: **2, 3, 5, 50**", parse_mode="Markdown")
        return

    target_mult = int(mult_str)

    bet_amount = parse_amount(parts[2])
    if bet_amount <= 0:
        bot.reply_to(message, "⚠️ Укажи корректную сумму ставки! Пример: `ставка 3 100к`", parse_mode="Markdown")
        return

    if bet_amount > user_data["balance"]:
        bot.reply_to(message, f"❌ Недостаточно средств!\n💰 Твой баланс: **{user_data['balance']:,} MB**",
                     parse_mode="Markdown")
        return

    user_data["balance"] -= bet_amount

    if user_id not in current_round_bets:
        current_round_bets[user_id] = {"name": name, "bets": {}}
    if target_mult in current_round_bets[user_id]["bets"]:
        current_round_bets[user_id]["bets"][target_mult] += bet_amount
    else:
        current_round_bets[user_id]["bets"][target_mult] = bet_amount

    if not is_round_active:
        bot.reply_to(message,
                     f"✅ Ставка принята: **{bet_amount:,} MB** на **x{target_mult}**.\n🚀 Запущен общий раунд на 60 секунд!",
                     parse_mode="Markdown", reply_markup=get_reply_keyboard())
        run_round_logic(message.chat.id)
    else:
        bot.reply_to(message,
                     f"✅ Ставка принята: **{bet_amount:,} MB** на **x{target_mult}** (добавлена в текущий раунд).",
                     parse_mode="Markdown", reply_markup=get_reply_keyboard())


if __name__ == "__main__":
    print("Бот успешно запущен и оформлен...")
    bot.infinity_polling()