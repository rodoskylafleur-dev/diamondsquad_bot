# -*- coding: utf-8 -*-
"""
Diamond Squad - Bot Telegram pou top-up Free Fire
Flux: Client chwazi pak -> antre ID FF -> chwazi peman -> voye referans/prèv
      -> Bot voye kòmand la BAY ADMIN -> Admin konfime -> Bot avize client
Pa gen sit web ki nesesè - tout bagay pase sou Telegram.
"""

import sqlite3
import logging
import os
import threading
from datetime import datetime

import telebot
from telebot import types
from flask import Flask

# ============================================================
# KONFIGIRASYON - CHANJE VALÈ SA YO ANVAN OU DEPLOYE
# ============================================================
BOT_TOKEN = "8636770943:AAGazL45aqH3uzb21Ak6xp_pUx0SNReacs4"
ADMIN_CHAT_ID = 8313303472                          # ID Telegram pa ou (wè enstriksyon anba a)

NATCASH_NUMBER = "+509 32596064"
MONCASH_NUMBER = "+509 31766988"
ACCOUNT_NAME = "Lafleur Rodosky"                    # non ki sou kont NatCash/MonCash la

# Pri yo (an Goud/HTG) - selon flyer Diamond Squad la
PACKAGES = {
    "pkg_1": {"label": "💎 100 + 20 Bonus Dyaman", "price": 175},
    "pkg_2": {"label": "💎 200 + 40 Bonus Dyaman", "price": 300},
    "pkg_3": {"label": "💎 310 + 32 Bonus Dyaman", "price": 500},
    "pkg_4": {"label": "💎 520 + 52 Bonus Dyaman", "price": 700},
    "pkg_5": {"label": "💎 1000 + 166 Bonus Dyaman", "price": 1500},
    "pkg_6": {"label": "💎 2000 + 398 Bonus Dyaman", "price": 3000},
    "pkg_7": {"label": "💎 5000 + 1160 Bonus Dyaman", "price": 8750},
}

# ============================================================
logging.basicConfig(level=logging.INFO)
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# ------------------ BAZ DÒNE (SQLite) ------------------
conn = sqlite3.connect("orders.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_chat_id INTEGER,
    client_username TEXT,
    package_label TEXT,
    price INTEGER,
    ff_id TEXT,
    payment_method TEXT,
    reference TEXT,
    status TEXT DEFAULT 'PANN',
    created_at TEXT
)
""")
conn.commit()

# Estoke eta konvèsasyon chak client an memwa (senp, pa bezwen redis pou volim sa a)
user_state = {}

# ============================================================
# /start - Meni prensipal
# ============================================================
@bot.message_handler(commands=["start"])
def start(message):
    chat_id = message.chat.id
    user_state[chat_id] = {}
    markup = types.InlineKeyboardMarkup(row_width=1)
    for key, pkg in PACKAGES.items():
        markup.add(types.InlineKeyboardButton(
            f"{pkg['label']} — {pkg['price']} HTG", callback_data=key
        ))
    bot.send_message(
        chat_id,
        "👋 Byenveni nan <b>Diamond Squad</b> 💎\n\n"
        "Chwazi pak dyaman ou vle achte a anba a:",
        reply_markup=markup
    )

# ============================================================
# Chwazi pak
# ============================================================
@bot.callback_query_handler(func=lambda call: call.data in PACKAGES)
def choose_package(call):
    chat_id = call.message.chat.id
    pkg = PACKAGES[call.data]
    user_state[chat_id] = {"package": pkg}
    bot.answer_callback_query(call.id)
    bot.send_message(
        chat_id,
        f"Ou chwazi: <b>{pkg['label']}</b> — {pkg['price']} HTG\n\n"
        "📌 Tanpri antre <b>ID Free Fire</b> ou (nimewo kont lan):"
    )
    bot.register_next_step_handler(call.message, receive_ff_id)

def receive_ff_id(message):
    chat_id = message.chat.id
    ff_id = message.text.strip()
    if chat_id not in user_state or "package" not in user_state[chat_id]:
        bot.send_message(chat_id, "Tanpri kòmanse ak /start")
        return
    user_state[chat_id]["ff_id"] = ff_id

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("NatCash", callback_data="pay_natcash"),
        types.InlineKeyboardButton("MonCash", callback_data="pay_moncash"),
    )
    bot.send_message(chat_id, "💳 Chwazi metòd peman ou:", reply_markup=markup)

# ============================================================
# Chwazi metòd peman
# ============================================================
@bot.callback_query_handler(func=lambda call: call.data in ["pay_natcash", "pay_moncash"])
def choose_payment(call):
    chat_id = call.message.chat.id
    if chat_id not in user_state or "ff_id" not in user_state[chat_id]:
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "Tanpri kòmanse ak /start")
        return

    method = "NatCash" if call.data == "pay_natcash" else "MonCash"
    number = NATCASH_NUMBER if method == "NatCash" else MONCASH_NUMBER
    user_state[chat_id]["payment_method"] = method

    bot.answer_callback_query(call.id)
    pkg = user_state[chat_id]["package"]
    bot.send_message(
        chat_id,
        f"💰 Voye <b>{pkg['price']} Goud</b> sou {method}: <code>{number}</code>\n"
        f"👤 Non kont lan: <b>{ACCOUNT_NAME}</b>\n\n"
        "Apre ou fin voye, tanpri kopye/kole <b>referans tranzaksyon an</b> "
        "(oswa screenshot la si ou pa gen referans) isit la:"
    )
    bot.register_next_step_handler(call.message, receive_reference)

def receive_reference(message):
    chat_id = message.chat.id
    state = user_state.get(chat_id)
    if not state or "payment_method" not in state:
        bot.send_message(chat_id, "Tanpri kòmanse ak /start")
        return

    # Client ka voye swa yon tèks (referans/ID tranzaksyon) swa yon foto (screenshot)
    photo_file_id = None
    if message.content_type == "photo":
        photo_file_id = message.photo[-1].file_id   # pi gwo rezolisyon an
        reference = "📷 Screenshot (gade foto anba a)"
    elif message.content_type == "text":
        reference = message.text.strip()
    else:
        reference = "Pa gen referans/foto valid"

    pkg = state["package"]
    ff_id = state["ff_id"]
    method = state["payment_method"]
    username = message.from_user.username or message.from_user.first_name

    # Anrejistre kòmand lan nan baz dòne a
    cur.execute("""
        INSERT INTO orders (client_chat_id, client_username, package_label, price,
                             ff_id, payment_method, reference, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'PANN', ?)
    """, (chat_id, username, pkg["label"], pkg["price"], ff_id, method, reference,
          datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    order_id = cur.lastrowid

    # Konfime bay client la
    bot.send_message(
        chat_id,
        "✅ Kòmand ou anrejistre! Nou pral konfime peman an epi "
        "livre dyaman yo talè konsa. Mèsi pou konfyans ou! 💎"
    )

    # Voye mesaj bay ADMIN (ou menm) ak boutons pou aksyon rapid
    admin_markup = types.InlineKeyboardMarkup(row_width=2)
    admin_markup.add(
        types.InlineKeyboardButton("✅ Konplete", callback_data=f"done_{order_id}"),
        types.InlineKeyboardButton("❌ Anile", callback_data=f"cancel_{order_id}"),
    )
    caption = (
        f"🆕 <b>NOUVO KÒMAND #{order_id}</b>\n\n"
        f"👤 Client: @{username} (chat_id: {chat_id})\n"
        f"💎 Pak: {pkg['label']}\n"
        f"💵 Pri: {pkg['price']} HTG\n"
        f"🎮 ID Free Fire: <code>{ff_id}</code>\n"
        f"💳 Metòd: {method}\n"
        f"🧾 Referans: {reference}"
    )

    if photo_file_id:
        # Voye vrè foto/screenshot la ak tout enfo kòmand la kòm kapsyon
        bot.send_photo(ADMIN_CHAT_ID, photo_file_id, caption=caption, reply_markup=admin_markup)
    else:
        bot.send_message(ADMIN_CHAT_ID, caption, reply_markup=admin_markup)

    user_state.pop(chat_id, None)

# ============================================================
# Aksyon Admin (Konplete / Anile)
# ============================================================
@bot.callback_query_handler(func=lambda call: call.data.startswith(("done_", "cancel_")))
def admin_action(call):
    if call.message.chat.id != ADMIN_CHAT_ID:
        bot.answer_callback_query(call.id, "Ou pa otorize.")
        return

    action, order_id = call.data.split("_")
    order_id = int(order_id)

    cur.execute("SELECT client_chat_id, package_label FROM orders WHERE id=?", (order_id,))
    row = cur.fetchone()
    if not row:
        bot.answer_callback_query(call.id, "Kòmand pa jwenn.")
        return
    client_chat_id, pkg_label = row

    if action == "done":
        cur.execute("UPDATE orders SET status='KONPLETE' WHERE id=?", (order_id,))
        conn.commit()
        bot.send_message(client_chat_id, f"🎉 Dyaman yo ({pkg_label}) delivre! Mèsi anpil, tounen vin achte ankò!")
        bot.answer_callback_query(call.id, "Kòmand make konplete ✅")
    else:
        cur.execute("UPDATE orders SET status='ANILE' WHERE id=?", (order_id,))
        conn.commit()
        bot.send_message(client_chat_id, f"⚠️ Kòmand ou pou {pkg_label} anile. Kontakte nou pou plis enfo.")
        bot.answer_callback_query(call.id, "Kòmand anile ❌")

    # Chanje mesaj admin an pou l montre se fini
    try:
        bot.edit_message_reply_markup(ADMIN_CHAT_ID, call.message.message_id, reply_markup=None)
    except Exception:
        pass

# ============================================================
# Kòmand /kòmand pou wè kòmand ki poko trete (admin sèlman)
# ============================================================
@bot.message_handler(commands=["pending"])
def pending_orders(message):
    if message.chat.id != ADMIN_CHAT_ID:
        return
    cur.execute("SELECT id, client_username, package_label, price FROM orders WHERE status='PANN'")
    rows = cur.fetchall()
    if not rows:
        bot.send_message(ADMIN_CHAT_ID, "Pa gen kòmand ki poko trete.")
        return
    text = "📋 <b>Kòmand ki poko trete:</b>\n\n"
    for r in rows:
        text += f"#{r[0]} - @{r[1]} - {r[2]} - {r[3]} HTG\n"
    bot.send_message(ADMIN_CHAT_ID, text)

# ============================================================
if __name__ == "__main__":
    # Ti sèvè web pou satisfè egzijans Render (Web Service bezwen reponn sou yon pò)
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
