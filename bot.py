import asyncio
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from config import *
from db import cur, conn

# ===== CUSTOM DEVICE INFO =====
DEVICE_NAME = "𝗗𝗲𝘃 —🇮🇳 @iscxm"
APP_VERSION = "—Dev"
SYSTEM_VERSION = "Sex Randi Version 2.0 Join — @TechBotss"

# ===== BOT CLIENT =====
bot = TelegramClient(
    "bot",
    API_ID,
    API_HASH,
    device_model=DEVICE_NAME,
    system_version=SYSTEM_VERSION,
    app_version=APP_VERSION,
    lang_code="en"
).start(bot_token=BOT_TOKEN)

tasks = {}

# ===== HELPERS =====
def approved(uid):
    cur.execute("SELECT approved FROM users WHERE user_id=?", (uid,))
    r = cur.fetchone()
    return r and r[0] == 1


# ===== INLINE BUTTONS =====
MAIN_BTNS = [
    [Button.inline("➕ Add Account", b"add"), Button.inline("✏️ Set Message", b"set")],
    [Button.inline("⏱ Set Delay", b"time"), Button.inline("📋 Accounts", b"list")],
    [Button.inline("🚀 Start Ads", b"send"), Button.inline("🛑 Stop Ads", b"stop")],
    [Button.inline("👤 Profile", b"profile"), Button.inline("❓ Help", b"help")]
]

# ===== START =====
@bot.on(events.NewMessage(pattern="/start"))
async def start(e):
    uid = e.sender_id
    cur.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (uid,))
    conn.commit()

    if not approved(uid):
        return await e.reply(
            "❌ **You are not authorised**\n\nContact admin to get access.",
            buttons=[[Button.url("👤 Contact Admin", f"https://t.me/{ADMIN_USERNAME}")]]
        )

    await bot.send_file(
        uid,
        "start.jpg",  # 📸 photo must be in root
        caption=(
            "🔥 **Userbot Ready**\n\n"
            "Manage accounts, set ads & start broadcasting easily.\n\n"
            "👇 Use buttons below"
        ),
        buttons=MAIN_BTNS
    )

# ===== INLINE HANDLER =====
@bot.on(events.CallbackQuery)
async def callbacks(e):
    data = e.data.decode()
    await e.answer()

    cmd_map = {
        "add": "/add",
        "set": "/set",
        "time": "/time",
        "list": "/list",
        "send": "/send",
        "stop": "/stop",
        "profile": "/profile",
        "help": "/help"
    }

    if data in cmd_map:
        await bot.send_message(e.sender_id, cmd_map[data])


# ===== APPROVE (UNCHANGED) =====
@bot.on(events.NewMessage(pattern="/approve"))
async def approve_cmd(e):
    if e.sender_id != ADMIN_ID:
        return
    try:
        uid = int(e.text.split()[1])
    except:
        return await e.reply("Usage: /approve user_id")

    cur.execute("INSERT OR IGNORE INTO users(user_id, approved) VALUES(?,1)", (uid,))
    cur.execute("UPDATE users SET approved=1 WHERE user_id=?", (uid,))
    conn.commit()
    await e.reply("✅ User approved")


# ===== ADD ACCOUNT =====
@bot.on(events.NewMessage(pattern="/add"))
async def add_account(e):
    uid = e.sender_id
    if not approved(uid):
        return

    async with bot.conversation(uid, timeout=300) as conv:
        await conv.send_message("📱 Send phone number (with country code)")
        phone = (await conv.get_response()).text.strip()

        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        await client.send_code_request(phone)

        await conv.send_message("🔐 Send OTP like: `1 2 3 4 5`")
        otp = (await conv.get_response()).text.strip()

        try:
            await client.sign_in(phone=phone, code=otp)
        except SessionPasswordNeededError:
            await conv.send_message("🔑 2FA password?")
            pwd = (await conv.get_response()).text.strip()
            await client.sign_in(password=pwd)

        session = client.session.save()
        cur.execute(
            "INSERT INTO accounts(owner, phone, session) VALUES(?,?,?)",
            (uid, phone, session)
        )
        conn.commit()

        await conv.send_message(f"✅ Account added:\n`{phone}`")


# ===== REMOVE (UNCHANGED) =====
@bot.on(events.NewMessage(pattern="/remove"))
async def remove_account(e):
    uid = e.sender_id
    if not approved(uid):
        return

    try:
        index = int(e.text.split()[1]) - 1
    except:
        return await e.reply("Usage: /remove {account number}")

    cur.execute("SELECT id, phone FROM accounts WHERE owner=? ORDER BY id", (uid,))
    rows = cur.fetchall()

    if index < 0 or index >= len(rows):
        return await e.reply("❌ Invalid account number")

    acc_id, phone = rows[index]
    cur.execute("DELETE FROM accounts WHERE id=?", (acc_id,))
    conn.commit()
    await e.reply(f"🗑 Removed: `{phone}`")


# ===== SET MESSAGE =====
@bot.on(events.NewMessage(pattern="/set"))
async def set_msg(e):
    uid = e.sender_id
    if not approved(uid):
        return

    async with bot.conversation(uid) as conv:
        await conv.send_message("✏️ Send ad message")
        msg = (await conv.get_response()).text
        cur.execute("UPDATE users SET message=? WHERE user_id=?", (msg, uid))
        conn.commit()
        await conv.send_message("✅ Message saved")


# ===== SET TIME =====
@bot.on(events.NewMessage(pattern="/time"))
async def set_time(e):
    uid = e.sender_id
    if not approved(uid):
        return
    try:
        t = int(e.text.split()[1])
    except:
        return await e.reply("Usage: /time 5")

    cur.execute("UPDATE users SET delay=? WHERE user_id=?", (t, uid))
    conn.commit()
    await e.reply(f"⏱ Delay set to {t}s")


# ===== LIST =====
@bot.on(events.NewMessage(pattern="/list"))
async def list_acc(e):
    uid = e.sender_id
    cur.execute("SELECT phone FROM accounts WHERE owner=?", (uid,))
    rows = cur.fetchall()
    if not rows:
        return await e.reply("No accounts added")

    await e.reply("\n".join(f"{i+1}. {r[0]}" for i, r in enumerate(rows)))


# ===== SEND =====
@bot.on(events.NewMessage(pattern="/send"))
async def start_ads(e):
    uid = e.sender_id
    if not approved(uid):
        return

    cur.execute("UPDATE users SET running=1 WHERE user_id=?", (uid,))
    conn.commit()

    if uid in tasks and not tasks[uid].done():
        return await e.reply("⚠️ Ads already running")

    tasks[uid] = asyncio.create_task(ads_loop(uid))
    await e.reply("🚀 **Ads started successfully**")


# ===== STOP =====
@bot.on(events.NewMessage(pattern="/stop"))
async def stop_ads(e):
    uid = e.sender_id
    cur.execute("UPDATE users SET running=0 WHERE user_id=?", (uid,))
    conn.commit()

    task = tasks.pop(uid, None)
    if task:
        task.cancel()

    await e.reply("🛑 Ads stopped completely")


# ===== PROFILE =====
@bot.on(events.NewMessage(pattern="/profile"))
async def profile_cmd(e):
    u = await e.get_sender()
    uid = e.sender_id

    cur.execute("SELECT sent_count FROM users WHERE user_id=?", (uid,))
    sent = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM accounts WHERE owner=?", (uid,))
    accs = cur.fetchone()[0]

    await e.reply(
        f"👤 **Profile**\n\n"
        f"Name: {u.first_name}\n"
        f"Username: @{u.username or 'N/A'}\n"
        f"ID: `{uid}`\n\n"
        f"📊 Accounts: {accs}\n"
        f"📨 Sent: {sent}"
    )


# ===== HELP =====
@bot.on(events.NewMessage(pattern="/help"))
async def help_cmd(e):
    await e.reply("👇 Use inline buttons from /start")

bot.run_until_disconnected()
