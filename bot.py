import requests
import asyncio
import time
import random
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# 🔑 CONFIG
api_id = 23907288
api_hash = "f9a47570ed19aebf8eb0f0a5ec1111e5"
bot_token = "8670925766:AAEXImOGX5KSYraU2Bob99U-6_-70L0f26g"

app = Client("wingo-ultra-final", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

API_MAP = {
    "30s": "30S",
    "1m": "1M",
    "3m": "3M",
    "5m": "5M"
}

last_period = None

# 📊 FETCH HISTORY
def fetch_data(mode):
    try:
        url = f"https://draw.ar-lottery01.com/WinGo/WinGo_{API_MAP[mode]}/GetHistoryIssuePage.json?page=1&size=50"
        return requests.get(url, timeout=5).json()["data"]["list"]
    except:
        return []

# ⏱ TIME API
def get_time_data(mode):
    try:
        url = f"https://draw.ar-lottery01.com/WinGo/WinGo_{API_MAP[mode]}.json"
        return requests.get(url, timeout=5).json()
    except:
        return None

# 🔄 BIG SMALL
def to_bs(n): return "B" if n >= 5 else "S"

# 🎨 COLOR
def get_color(c):
    if "red" in c: return "RED"
    if "green" in c: return "GREEN"
    return "VIOLET"

# 🧠 ADVANCED LOGIC ENGINE
def advanced_logic(data):
    nums = [int(i["number"]) for i in data[:30]]
    colors = [get_color(i["color"]) for i in data[:30]]

    score = {"B":0, "S":0}
    reasons = []

    # 🔥 trend
    b = sum(1 for n in nums if n >= 5)
    s = len(nums) - b
    if b > s:
        score["B"] += 3
        reasons.append("Trend BIG")
    else:
        score["S"] += 3
        reasons.append("Trend SMALL")

    # 🔥 streak
    last5 = [to_bs(n) for n in nums[:5]]
    if len(set(last5)) == 1:
        flip = "B" if last5[0] == "S" else "S"
        score[flip] += 3
        reasons.append("Streak break")

    # 🔥 momentum
    score[last5[0]] += 2
    reasons.append("Momentum")

    # 🔥 volatility
    diff = sum(abs(nums[i]-nums[i+1]) for i in range(len(nums)-1))
    if diff > 60:
        score[random.choice(["B","S"])] += 1
        reasons.append("Volatility")

    # 🔥 color influence
    g = colors.count("GREEN")
    r = colors.count("RED")
    if g > r:
        score["B"] += 1
    else:
        score["S"] += 1

    final = "B" if score["B"] > score["S"] else "S"
    conf = int((max(score.values()) / sum(score.values())) * 100)

    if conf < 55:
        return "SKIP", conf, reasons

    return ("BIG" if final=="B" else "SMALL"), conf, reasons

# 🎨 COLOR ENGINE
def color_logic(data):
    colors = [get_color(i["color"]) for i in data[:30]]

    score = {"RED":0,"GREEN":0}

    for c in colors[:20]:
        if c in score:
            score[c] += 1

    if len(set(colors[:4])) == 1:
        score[random.choice(["RED","GREEN"])] += 2

    final = max(score, key=score.get)
    conf = int(score[final] / sum(score.values()) * 100)

    return final, conf

# 🤖 AI FULL DATA
def ask_ai(data):
    try:
        nums = [int(i["number"]) for i in data[:30]]
        colors = [i["color"] for i in data[:30]]

        bs = ["BIG" if n>=5 else "SMALL" for n in nums]

        big_count = bs.count("BIG")
        small_count = bs.count("SMALL")

        prompt = f"""
Analyze Wingo deeply.

Numbers: {nums}
BIG/SMALL: {bs}
Colors: {colors}

Stats:
BIG={big_count}, SMALL={small_count}

Find trend, streak, pattern.
Predict next BIG/SMALL with confidence and reason.
"""

        url = "https://apis.prexzyvilla.site/ai/copilot-think?text=" + requests.utils.quote(prompt)
        res = requests.get(url, timeout=8).json()

        return res.get("text", "")
    except:
        return ""

# 🎛 UI
def mode_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("30s","mode_30s"),
         InlineKeyboardButton("1m","mode_1m")],
        [InlineKeyboardButton("3m","mode_3m"),
         InlineKeyboardButton("5m","mode_5m")]
    ])

def type_menu(mode):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("BIG/SMALL", f"type_bs_{mode}")],
        [InlineKeyboardButton("COLOR", f"type_color_{mode}")],
        [InlineKeyboardButton("BOTH", f"type_both_{mode}")]
    ])

# ▶️ START
@app.on_message(filters.command("start"))
def start(c,m):
    m.reply("🤖 Wingo Ultra AI Bot\n\nSelect Mode:", reply_markup=mode_menu())

# 🎯 MODE
@app.on_callback_query(filters.regex("mode_"))
def mode(c,q):
    m = q.data.split("_")[1]
    q.message.edit_text("Select Prediction Type:", reply_markup=type_menu(m))

# 🔥 LIVE LOOP
async def live_loop(msg, mode, ptype):
    global last_period

    while True:
        tdata = get_time_data(mode)
        if not tdata:
            await msg.edit_text("❌ API error")
            return

        current = tdata["current"]["issueNumber"]
        end = tdata["current"]["endTime"]

        now = int(time.time()*1000)
        left = (end - now)//1000
        timer = f"{left//60:02}:{left%60:02}"

        if current != last_period:
            last_period = current

            data = fetch_data(mode)

            bs_res, bs_conf, reasons = advanced_logic(data)
            col_res, col_conf = color_logic(data)
            ai_text = ask_ai(data)

            text = f"🆕 ROUND {current}\n\n"

            if ptype in ["bs","both"]:
                text += f"📊 {bs_res} ({bs_conf}%)\n"

            if ptype in ["color","both"]:
                text += f"🎨 {col_res} ({col_conf}%)\n"

            text += f"\n⏱ {timer}\n"
            text += f"\n🧠 {', '.join(reasons)}"

            if ai_text:
                text += f"\n\n🤖 AI:\n{ai_text}"

        else:
            text = f"🆔 {current}\n⏱ {timer}\n⌛ Waiting..."

        try:
            await msg.edit_text(text)
        except:
            pass

        await asyncio.sleep(1)

# 🎯 FINAL
@app.on_callback_query(filters.regex("type_"))
async def final(c,q):
    _,ptype,mode = q.data.split("_")

    msg = await q.message.edit_text("⏳ Starting...")
    await live_loop(msg, mode, ptype)

# ▶️ RUN
app.run()
