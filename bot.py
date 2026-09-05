# -*- coding: utf-8 -*-
"""
Diamond Squad - Bot Telegram pou top-up Free Fire (VERSION 2)
Estil GamexBulk/EpinBy: meni pèsistan anba a + sistèm Wallet (kont/balans)

Flux Wallet:
  Client ajoute lajan (peye NatCash/MonCash, voye prèv) -> Admin apwouve
  -> Balans kredite -> Client achte dyaman ENSTANTANEMAN ak balans li
  (pa bezwen voye prèv chak fwa li achte)

Pa gen sit web ki nesesè - tout bagay pase sou Telegram.
"""

import sqlite3
import logging
import os
import threading
from datetime import datetime

import requests
import telebot
from telebot import types
from flask import Flask

# ============================================================
# KONFIGIRASYON - CHANJE VALÈ SA YO ANVAN OU DEPLOYE
# ============================================================
BOT_TOKEN = "8636770943:AAGazL45aqH3uzb21Ak6xp_pUx0SNReacs4"
ADMIN_CHAT_ID = 8313303472                          # ID Telegram pa ou

NATCASH_NUMBER = "+509 32596064"
MONCASH_NUMBER = "+509 31766988"
ACCOUNT_NAME = "Lafleur Rodosky"                    # non ki sou kont NatCash/MonCash la

# API pou jwenn non kont Free Fire otomatikman selon ID (twazyèm pati, pa ofisyèl)
FREEFIRE_API_BASE = "http://siambhau69.eu.cc/freefireinfo/bhau"
FREEFIRE_API_KEY = "diamondsquadbot:FFINFO:7CL"
FREEFIRE_REGIONS_TO_TRY = ["BR", "SAC", "NA", "US", "ME"]  # eseye plizyè rejyon

# Pri yo (an Goud/HTG) - selon flyer Diamond Squad la
PACKAGES = {
    "pkg_1": {"label": "💎 100 + 20 Bonus Dyaman", "price": 175},
    "pkg_2": {"label": "💎 200 + 40 Bonus Dyaman", "price": 300},
    "pkg_3": {"label": "💎 310 + 32 Bonus Dyaman", "price": 500},
    "pkg_4": {"label": "💎 520 + 52 Bonus Dyaman", "price": 700},
    "pkg_5": {"label": "💎 1000 + 166 Bonus Dyaman", "price": 1500},
    "pkg_6": {"label": "💎 2000 + 398 Bonus Dyaman", "price": 3000},
    "pkg_7": {"label": "💎 5000 + 1160 Bonus Dyaman", "price": 8750},
    "pkg_8": {"label": "🎫 Booyah Pass", "price": 750},
    "pkg_9": {"label": "📅 Abonnement Mensuel", "price": 1750},
    "pkg_10": {"label": "📆 Hebdomadaire", "price": 150},
    "pkg_11": {"label": "📆 Abonnement Hebdomadaire", "price": 500},
}

# Kantite lajan pwopoze pou "Ajoute Lajan" (an HTG)
TOPUP_AMOUNTS = [250, 500, 1000, 2500, 5000]

# ============================================================
logging.basicConfig(level=logging.INFO)
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# ------------------ BAZ DÒNE (SQLite) ------------------
conn = sqlite3.connect("orders.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    chat_id INTEGER PRIMARY KEY,
    username TEXT,
    balance REAL DEFAULT 0
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_chat_id INTEGER,
    client_username TEXT,
    package_label TEXT,
    price INTEGER,
    ff_id TEXT,
    ff_name TEXT,
    status TEXT DEFAULT 'PANN',
    created_at TEXT
)
""")
# Ajoute kolòn ff_name si baz done a te deja egziste san li (migrasyon dous)
try:
    cur.execute("ALTER TABLE orders ADD COLUMN ff_name TEXT")
    conn.commit()
except sqlite3.OperationalError:
    pass  # kolòn nan deja egziste

cur.execute("""
CREATE TABLE IF NOT EXISTS deposits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_chat_id INTEGER,
    client_username TEXT,
    amount REAL,
    payment_method TEXT,
    reference TEXT,
    status TEXT DEFAULT 'PANN',
    created_at TEXT
)
""")
conn.commit()

# Estoke eta konvèsasyon chak client an memwa
user_state = {}

# ============================================================
# Ti fonksyon pou jere itilizatè ak balans
# ============================================================
def ensure_user(chat_id, username):
    cur.execute("SELECT chat_id FROM users WHERE chat_id=?", (chat_id,))
    if not cur.fetchone():
        cur.execute("INSERT INTO users (chat_id, username, balance) VALUES (?, ?, 0)",
                    (chat_id, username))
        conn.commit()
    else:
        cur.execute("UPDATE users SET username=? WHERE chat_id=?", (username, chat_id))
        conn.commit()

def get_balance(chat_id):
    cur.execute("SELECT balance FROM users WHERE chat_id=?", (chat_id,))
    row = cur.fetchone()
    return row[0] if row else 0

def add_balance(chat_id, amount):
    cur.execute("UPDATE users SET balance = balance + ? WHERE chat_id=?", (amount, chat_id))
    conn.commit()

def deduct_balance(chat_id, amount):
    cur.execute("UPDATE users SET balance = balance - ? WHERE chat_id=?", (amount, chat_id))
    conn.commit()

def lookup_ff_nickname(ff_id):
    """
    Eseye jwenn non kont Free Fire a otomatikman selon ID a.
    Eseye plizyè rejyon youn apre lòt. Retounen non an si jwenn,
    oswa None si pa jwenn (bot la ap kontinye san erè nan ka sa a).
    """
    for region in FREEFIRE_REGIONS_TO_TRY:
        try:
            resp = requests.get(
                FREEFIRE_API_BASE,
                params={"uid": ff_id, "region": region, "key": FREEFIRE_API_KEY},
                timeout=6
            )
            data = resp.json()
            nickname = data.get("basicInfo", {}).get("nickname")
            if nickname:
                return nickname
        except Exception as e:
            logging.info(f"FF lookup echwe pou rejyon {region}: {e}")
            continue
    return None

# ============================================================
# Meni pèsistan (anba a, tankou GamexBulk/EpinBy)
# ============================================================
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("💎 Achte Dyaman"),
        types.KeyboardButton("💰 Kont Mwen"),
    )
    markup.add(
        types.KeyboardButton("➕ Ajoute Lajan"),
        types.KeyboardButton("📦 Kòmand Mwen"),
    )
    markup.add(types.KeyboardButton("🆘 Sipò"))
    return markup

# ============================================================
# /start - Antre nan bot la
# ============================================================
@bot.message_handler(commands=["start"])
def start(message):
    chat_id = message.chat.id
    username = message.from_user.username or message.from_user.first_name
    ensure_user(chat_id, username)
    user_state[chat_id] = {}
    bot.send_message(
        chat_id,
        f"👋 Byenveni nan <b>Diamond Squad</b> 💎\n\n"
        f"Itilize meni anba a pou navige:",
        reply_markup=main_menu()
    )

# ============================================================
# Meni: 💎 Achte Dyaman
# ============================================================
@bot.message_handler(func=lambda m: m.text == "💎 Achte Dyaman")
def menu_buy(message):
    chat_id = message.chat.id
    balance = get_balance(chat_id)
    markup = types.InlineKeyboardMarkup(row_width=1)
    for key, pkg in PACKAGES.items():
        markup.add(types.InlineKeyboardButton(
            f"{pkg['label']} — {pkg['price']} HTG ✅ 📦", callback_data=f"buy_{key}"
        ))
    bot.send_message(
        chat_id,
        f"💰 Balans ou: <b>{balance:.0f} HTG</b>\n\n"
        "Chwazi pak dyaman ou vle achte a:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_pkg_"))
def choose_package(call):
    chat_id = call.message.chat.id
    key = call.data.replace("buy_", "")
    pkg = PACKAGES[key]
    balance = get_balance(chat_id)

    bot.answer_callback_query(call.id)

    if balance < pkg["price"]:
        manke = pkg["price"] - balance
        bot.send_message(
            chat_id,
            f"⚠️ Balans ou pa sifi pou pak sa a.\n\n"
            f"💰 Balans aktyèl: {balance:.0f} HTG\n"
            f"💎 Pri pak la: {pkg['price']} HTG\n"
            f"📉 Manke: {manke:.0f} HTG\n\n"
            f"Klike <b>➕ Ajoute Lajan</b> nan meni an pou rechaje kont ou.",
            reply_markup=main_menu()
        )
        return

    user_state[chat_id] = {"package": pkg}
    bot.send_message(
        chat_id,
        f"Ou chwazi: <b>{pkg['label']}</b> — {pkg['price']} HTG\n\n"
        "📌 Tanpri antre <b>ID Free Fire</b> ou (nimewo kont lan):"
    )
    bot.register_next_step_handler(call.message, receive_ff_id)

def receive_ff_id(message):
    chat_id = message.chat.id
    ff_id = message.text.strip() if message.content_type == "text" else None
    state = user_state.get(chat_id)

    if not state or "package" not in state or not ff_id or not ff_id.isdigit():
        bot.send_message(chat_id, "⚠️ ID Free Fire dwe sèlman chif. Tanpri kòmanse ankò ak 💎 Achte Dyaman",
                          reply_markup=main_menu())
        return

    pkg = state["package"]
    balance = get_balance(chat_id)

    if balance < pkg["price"]:
        bot.send_message(chat_id, "⚠️ Balans ou chanje, li pa sifi ankò. Tanpri ajoute lajan.",
                          reply_markup=main_menu())
        return

    wait_msg = bot.send_message(chat_id, "🔍 M ap chèche kont lan, tann yon segond...")
    nickname = lookup_ff_nickname(ff_id)
    try:
        bot.delete_message(chat_id, wait_msg.message_id)
    except Exception:
        pass

    user_state[chat_id]["ff_id"] = ff_id
    user_state[chat_id]["ff_name"] = nickname  # ka None si pa jwenn

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Wi, se kòrèk", callback_data="ffconfirm_yes"),
        types.InlineKeyboardButton("❌ Non, chanje ID", callback_data="ffconfirm_no"),
    )

    if nickname:
        bot.send_message(
            chat_id,
            f"✅ <b>Kont Jwenn!</b>\n\n"
            f"👤 Non: <b>{nickname}</b>\n"
            f"🆔 ID: <code>{ff_id}</code>\n\n"
            f"💎 Pak: {pkg['label']}\n"
            f"💵 Pri: {pkg['price']} HTG\n\n"
            f"Èske enfo yo kòrèk?",
            reply_markup=markup
        )
    else:
        bot.send_message(
            chat_id,
            f"⚠️ Nou pa t ka jwenn non kont lan otomatikman, men ou ka kontinye.\n\n"
            f"🆔 ID: <code>{ff_id}</code>\n"
            f"💎 Pak: {pkg['label']}\n"
            f"💵 Pri: {pkg['price']} HTG\n\n"
            f"Èske ID a kòrèk?",
            reply_markup=markup
        )

@bot.callback_query_handler(func=lambda call: call.data in ["ffconfirm_yes", "ffconfirm_no"])
def confirm_ff_account(call):
    chat_id = call.message.chat.id
    state = user_state.get(chat_id)
    bot.answer_callback_query(call.id)

    if not state or "ff_id" not in state:
        bot.send_message(chat_id, "Tanpri kòmanse ankò ak 💎 Achte Dyaman", reply_markup=main_menu())
        return

    if call.data == "ffconfirm_no":
        bot.send_message(chat_id, "📌 Tanpri antre <b>ID Free Fire</b> ou ankò:")
        bot.register_next_step_handler(call.message, receive_ff_id)
        return

    # Konfime -> finalize acha a
    pkg = state["package"]
    ff_id = state["ff_id"]
    ff_name = state.get("ff_name")
    balance = get_balance(chat_id)

    if balance < pkg["price"]:
        bot.send_message(chat_id, "⚠️ Balans ou chanje, li pa sifi ankò. Tanpri ajoute lajan.",
                          reply_markup=main_menu())
        user_state.pop(chat_id, None)
        return

    username = call.from_user.username or call.from_user.first_name

    deduct_balance(chat_id, pkg["price"])
    cur.execute("""
        INSERT INTO orders (client_chat_id, client_username, package_label, price, ff_id, ff_name, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'PANN', ?)
    """, (chat_id, username, pkg["label"], pkg["price"], ff_id, ff_name,
          datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    order_id = cur.lastrowid

    new_balance = get_balance(chat_id)
    nom_ligne = f"👤 Non: {ff_name}\n" if ff_name else ""
    bot.send_message(
        chat_id,
        f"✅ Acha ou fèt ak siksè!\n\n"
        f"💎 {pkg['label']}\n"
        f"{nom_ligne}"
        f"🆔 ID: {ff_id}\n"
        f"💰 Nouvo balans: {new_balance:.0f} HTG\n\n"
        f"Nou pral livre dyaman yo talè konsa. Mèsi! 💎",
        reply_markup=main_menu()
    )

    admin_markup = types.InlineKeyboardMarkup(row_width=2)
    admin_markup.add(
        types.InlineKeyboardButton("✅ Konplete", callback_data=f"orderdone_{order_id}"),
        types.InlineKeyboardButton("❌ Anile", callback_data=f"ordercancel_{order_id}"),
    )
    nom_admin_ligne = f"👤 Non FF: <b>{ff_name}</b>\n" if ff_name else "👤 Non FF: <i>pa jwenn otomatikman</i>\n"
    bot.send_message(
        ADMIN_CHAT_ID,
        f"🆕 <b>NOUVO KÒMAND #{order_id}</b> (peye ak Wallet)\n\n"
        f"👤 Client Telegram: @{username} (chat_id: {chat_id})\n"
        f"{nom_admin_ligne}"
        f"🆔 ID Free Fire: <code>{ff_id}</code>\n"
        f"💎 Pak: {pkg['label']}\n"
        f"💵 Pri: {pkg['price']} HTG",
        reply_markup=admin_markup
    )

    user_state.pop(chat_id, None)

# ============================================================
# Aksyon Admin pou KÒMAND (Konplete / Anile)
# ============================================================
@bot.callback_query_handler(func=lambda call: call.data.startswith(("orderdone_", "ordercancel_")))
def admin_order_action(call):
    if call.message.chat.id != ADMIN_CHAT_ID:
        bot.answer_callback_query(call.id, "Ou pa otorize.")
        return

    action, order_id = call.data.split("_")
    order_id = int(order_id)

    cur.execute("SELECT client_chat_id, package_label, price FROM orders WHERE id=?", (order_id,))
    row = cur.fetchone()
    if not row:
        bot.answer_callback_query(call.id, "Kòmand pa jwenn.")
        return
    client_chat_id, pkg_label, price = row

    if action == "orderdone":
        cur.execute("UPDATE orders SET status='KONPLETE' WHERE id=?", (order_id,))
        conn.commit()
        bot.send_message(client_chat_id, f"🎉 Dyaman yo ({pkg_label}) delivre! Mèsi anpil, tounen vin achte ankò!")
        bot.answer_callback_query(call.id, "Kòmand konplete ✅")
    else:
        # Anile -> remèt lajan nan wallet client la
        cur.execute("UPDATE orders SET status='ANILE' WHERE id=?", (order_id,))
        conn.commit()
        add_balance(client_chat_id, price)
        bot.send_message(client_chat_id,
                          f"⚠️ Kòmand ou pou {pkg_label} anile. {price} HTG remèt nan balans ou.")
        bot.answer_callback_query(call.id, "Kòmand anile, lajan remèt ❌")

    try:
        bot.edit_message_reply_markup(ADMIN_CHAT_ID, call.message.message_id, reply_markup=None)
    except Exception:
        pass

# ============================================================
# Meni: 💰 Kont Mwen
# ============================================================
@bot.message_handler(func=lambda m: m.text == "💰 Kont Mwen")
def menu_wallet(message):
    chat_id = message.chat.id
    balance = get_balance(chat_id)
    bot.send_message(
        chat_id,
        f"💰 <b>Balans kont ou:</b> {balance:.0f} HTG\n\n"
        "Klike ➕ Ajoute Lajan pou rechaje kont ou.",
        reply_markup=main_menu()
    )

# ============================================================
# Meni: ➕ Ajoute Lajan
# ============================================================
@bot.message_handler(func=lambda m: m.text == "➕ Ajoute Lajan")
def menu_topup(message):
    chat_id = message.chat.id
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [types.InlineKeyboardButton(f"{a} HTG", callback_data=f"topup_{a}") for a in TOPUP_AMOUNTS]
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton("Lòt montan", callback_data="topup_custom"))
    bot.send_message(chat_id, "💵 Chwazi konbyen ou vle ajoute nan kont ou:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("topup_"))
def choose_topup_amount(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)

    if call.data == "topup_custom":
        bot.send_message(chat_id, "✍️ Ekri montan (an HTG) ou vle ajoute a:")
        bot.register_next_step_handler(call.message, receive_custom_amount)
        return

    amount = float(call.data.replace("topup_", ""))
    ask_topup_payment_method(chat_id, amount)

def receive_custom_amount(message):
    chat_id = message.chat.id
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            raise ValueError
    except (ValueError, AttributeError):
        bot.send_message(chat_id, "⚠️ Tanpri antre yon nimewo valid.", reply_markup=main_menu())
        return
    ask_topup_payment_method(chat_id, amount)

def ask_topup_payment_method(chat_id, amount):
    user_state[chat_id] = {"topup_amount": amount}
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("NatCash", callback_data="topuppay_natcash"),
        types.InlineKeyboardButton("MonCash", callback_data="topuppay_moncash"),
    )
    bot.send_message(chat_id, f"💵 Ou pral ajoute <b>{amount:.0f} HTG</b>.\n\nChwazi metòd peman:",
                      reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["topuppay_natcash", "topuppay_moncash"])
def topup_choose_payment(call):
    chat_id = call.message.chat.id
    state = user_state.get(chat_id)
    if not state or "topup_amount" not in state:
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "Tanpri kòmanse ankò ak ➕ Ajoute Lajan", reply_markup=main_menu())
        return

    method = "NatCash" if call.data == "topuppay_natcash" else "MonCash"
    number = NATCASH_NUMBER if method == "NatCash" else MONCASH_NUMBER
    amount = state["topup_amount"]
    user_state[chat_id]["topup_method"] = method

    bot.answer_callback_query(call.id)
    bot.send_message(
        chat_id,
        f"💰 Voye <b>{amount:.0f} Goud</b> sou {method}: <code>{number}</code>\n"
        f"👤 Non kont lan: <b>{ACCOUNT_NAME}</b>\n\n"
        "Apre ou fin voye, voye <b>referans tranzaksyon an</b> "
        "(oswa yon screenshot) isit la:"
    )
    bot.register_next_step_handler(call.message, receive_topup_proof)

def receive_topup_proof(message):
    chat_id = message.chat.id
    state = user_state.get(chat_id)
    if not state or "topup_method" not in state:
        bot.send_message(chat_id, "Tanpri kòmanse ankò ak ➕ Ajoute Lajan", reply_markup=main_menu())
        return

    photo_file_id = None
    if message.content_type == "photo":
        photo_file_id = message.photo[-1].file_id
        reference = "📷 Screenshot (gade foto anba a)"
    elif message.content_type == "text":
        reference = message.text.strip()
    else:
        reference = "Pa gen referans/foto valid"

    amount = state["topup_amount"]
    method = state["topup_method"]
    username = message.from_user.username or message.from_user.first_name

    cur.execute("""
        INSERT INTO deposits (client_chat_id, client_username, amount, payment_method, reference, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'PANN', ?)
    """, (chat_id, username, amount, method, reference, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    deposit_id = cur.lastrowid

    bot.send_message(
        chat_id,
        "✅ Demann ou anrejistre! N ap konfime peman an epi kredite kont ou talè konsa.",
        reply_markup=main_menu()
    )

    admin_markup = types.InlineKeyboardMarkup(row_width=2)
    admin_markup.add(
        types.InlineKeyboardButton("✅ Aksepte", callback_data=f"depapprove_{deposit_id}"),
        types.InlineKeyboardButton("❌ Refize", callback_data=f"depreject_{deposit_id}"),
    )
    caption = (
        f"💰 <b>NOUVO DEPO #{deposit_id}</b>\n\n"
        f"👤 Client: @{username} (chat_id: {chat_id})\n"
        f"💵 Montan: {amount:.0f} HTG\n"
        f"💳 Metòd: {method}\n"
        f"🧾 Referans: {reference}"
    )
    if photo_file_id:
        bot.send_photo(ADMIN_CHAT_ID, photo_file_id, caption=caption, reply_markup=admin_markup)
    else:
        bot.send_message(ADMIN_CHAT_ID, caption, reply_markup=admin_markup)

    user_state.pop(chat_id, None)

# ============================================================
# Aksyon Admin pou DEPO (Aksepte / Refize)
# ============================================================
@bot.callback_query_handler(func=lambda call: call.data.startswith(("depapprove_", "depreject_")))
def admin_deposit_action(call):
    if call.message.chat.id != ADMIN_CHAT_ID:
        bot.answer_callback_query(call.id, "Ou pa otorize.")
        return

    action, dep_id = call.data.split("_")
    dep_id = int(dep_id)

    cur.execute("SELECT client_chat_id, amount FROM deposits WHERE id=?", (dep_id,))
    row = cur.fetchone()
    if not row:
        bot.answer_callback_query(call.id, "Depo pa jwenn.")
        return
    client_chat_id, amount = row

    if action == "depapprove":
        cur.execute("UPDATE deposits SET status='APWOUVE' WHERE id=?", (dep_id,))
        conn.commit()
        add_balance(client_chat_id, amount)
        new_balance = get_balance(client_chat_id)
        bot.send_message(client_chat_id,
                          f"✅ {amount:.0f} HTG kredite nan kont ou!\n💰 Nouvo balans: {new_balance:.0f} HTG")
        bot.answer_callback_query(call.id, "Depo apwouve ✅")
    else:
        cur.execute("UPDATE deposits SET status='REFIZE' WHERE id=?", (dep_id,))
        conn.commit()
        bot.send_message(client_chat_id, "❌ Depo ou refize. Kontakte sipò si ou panse gen erè.")
        bot.answer_callback_query(call.id, "Depo refize ❌")

    try:
        bot.edit_message_reply_markup(ADMIN_CHAT_ID, call.message.message_id, reply_markup=None)
    except Exception:
        pass

# ============================================================
# Meni: 📦 Kòmand Mwen
# ============================================================
@bot.message_handler(func=lambda m: m.text == "📦 Kòmand Mwen")
def menu_orders(message):
    chat_id = message.chat.id
    cur.execute("""
        SELECT package_label, price, status, created_at FROM orders
        WHERE client_chat_id=? ORDER BY id DESC LIMIT 10
    """, (chat_id,))
    rows = cur.fetchall()
    if not rows:
        bot.send_message(chat_id, "Ou poko fè okenn kòmand.", reply_markup=main_menu())
        return

    status_icon = {"PANN": "⏳", "KONPLETE": "✅", "ANILE": "❌"}
    text = "📦 <b>10 dènye kòmand ou yo:</b>\n\n"
    for pkg_label, price, status, created_at in rows:
        icon = status_icon.get(status, "•")
        text += f"{icon} {pkg_label} — {price:.0f} HTG ({created_at})\n"
    bot.send_message(chat_id, text, reply_markup=main_menu())

# ============================================================
# Meni: 🆘 Sipò
# ============================================================
@bot.message_handler(func=lambda m: m.text == "🆘 Sipò")
def menu_support(message):
    bot.send_message(
        message.chat.id,
        "🆘 <b>Sipò Diamond Squad</b>\n\n"
        f"📱 NatCash/MonCash: {NATCASH_NUMBER}\n"
        "Ekri nou dirèkteman isit la si ou gen yon pwoblèm, "
        "n ap reponn ou pi vit posib.",
        reply_markup=main_menu()
    )

# ============================================================
# Kòmand admin: /pending (kòmand ak depo ki poko trete)
# ============================================================
@bot.message_handler(commands=["pending"])
def pending_all(message):
    if message.chat.id != ADMIN_CHAT_ID:
        return

    cur.execute("SELECT id, client_username, package_label, price FROM orders WHERE status='PANN'")
    orders = cur.fetchall()
    cur.execute("SELECT id, client_username, amount FROM deposits WHERE status='PANN'")
    deposits = cur.fetchall()

    text = "📋 <b>Kòmand ki poko trete:</b>\n"
    text += "\n".join(f"#{r[0]} - @{r[1]} - {r[2]} - {r[3]} HTG" for r in orders) or "Okenn"
    text += "\n\n💰 <b>Depo ki poko trete:</b>\n"
    text += "\n".join(f"#{r[0]} - @{r[1]} - {r[2]:.0f} HTG" for r in deposits) or "Okenn"

    bot.send_message(ADMIN_CHAT_ID, text)

# ============================================================
if __name__ == "__main__":
    web = Flask(__name__)

    @web.route("/")
    def home():
        return "Diamond Squad bot ap kouri! 💎"

    def run_bot():
        print("Bot ap kouri...")
        bot.infinity_polling()

    threading.Thread(target=run_bot).start()

    port = int(os.environ.get("PORT", 5000))
    web.run(host="0.0.0.0", port=port)
