import requests
import asyncio
import time
import random
import re
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# 🔑 CONFIG
api_id = 23907288
api_hash = "f9a47570ed19aebf8eb0f0a5ec1111e5"
bot_token = "8670925766:AAEXImOGX5KSYraU2Bob99U-6_-70L0f26g"


app = Client("wingo-ai-final", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

API_MAP = {
    "30s": "30S",
    "1m": "1M",
    "3m": "3M",
    "5m": "5M"
}

# 🔥 GLOBAL STATE
last_period = None
last_prediction = None
wins = 0
losses = 0

current_prediction_text = ""
current_result_text = ""

# 📊 FETCH DATA
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

# 🔄 BIG/SMALL
def to_bs(n): return "BIG" if n >= 5 else "SMALL"

# 🧠 LOCAL LOGIC
def advanced_logic(data):
    nums = [int(i["number"]) for i in data[:30]]
    score = {"BIG":0,"SMALL":0}
    reasons = []

    b = sum(1 for n in nums if n >= 5)
    s = len(nums) - b

    if b > s:
        score["BIG"] += 3
        reasons.append("Trend BIG")
    else:
        score["SMALL"] += 3
        reasons.append("Trend SMALL")

    last5 = [to_bs(n) for n in nums[:5]]

    if len(set(last5)) == 1:
        flip = "BIG" if last5[0] == "SMALL" else "SMALL"
        score[flip] += 3
        reasons.append("Streak Break")

    score[last5[0]] += 2
    reasons.append("Momentum")

    final = max(score, key=score.get)
    conf = int((score[final] / sum(score.values())) * 100)

    return final, conf, reasons

# 🤖 AI FULL JSON
def ask_ai_full(data):
    try:
        prompt = f"""
Analyze this Wingo JSON deeply:

{data}

Return:
Prediction: BIG/SMALL
Confidence: number
Reason: short
"""

        url = "https://apis.prexzyvilla.site/ai/copilot-think?text=" + requests.utils.quote(prompt)
        res = requests.get(url, timeout=10).json()
        text = res.get("text", "")

        pred = "SKIP"
        conf = 50

        if "BIG" in text.upper():
            pred = "BIG"
        elif "SMALL" in text.upper():
            pred = "SMALL"

        nums = re.findall(r"\d+", text)
        if nums:
            conf = int(nums[0])

        return pred, conf, text

    except:
        return "SKIP", 50, "AI error"

# 🎛 MENU
def mode_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("30s","mode_30s"),
         InlineKeyboardButton("1m","mode_1m")],
        [InlineKeyboardButton("3m","mode_3m"),
         InlineKeyboardButton("5m","mode_5m")]
    ])

# ▶️ START
@app.on_message(filters.command("start"))
def start(c,m):
    m.reply("Select Mode:", reply_markup=mode_menu())

# 🎯 MODE
@app.on_callback_query(filters.regex("mode_"))
async def mode_select(c,q):
    mode = q.data.split("_")[1]
    msg = await q.message.edit_text("🚀 Starting AI Engine...")
    await live_loop(msg, mode)

# 🔥 MAIN LOOP
async def live_loop(msg, mode):
    global last_period, last_prediction, wins, losses
    global current_prediction_text, current_result_text

    while True:
        tdata = get_time_data(mode)
        if not tdata:
            await msg.edit_text("❌ API Error")
            return

        current = tdata["current"]["issueNumber"]
        end = tdata["current"]["endTime"]

        now = int(time.time()*1000)
        left = (end - now)//1000
        timer = f"{left//60:02}:{left%60:02}"

        # 🆕 NEW ROUND
        if current != last_period:
            last_period = current

            data = fetch_data(mode)

            # 🏁 RESULT CHECK
            result_text = ""
            if last_prediction:
                actual = to_bs(int(data[0]["number"]))

                if actual == last_prediction:
                    wins += 1
                    result_text = f"🏁 {actual} ✅ WIN"
                else:
                    losses += 1
                    result_text = f"🏁 {actual} ❌ LOSS"

            current_result_text = result_text

            total = wins + losses
            acc = int((wins/total)*100) if total else 0

            # 🧠 LOGIC
            bs_res, bs_conf, reasons = advanced_logic(data)

            # 🤖 AI
            ai_pred, ai_conf, ai_text = ask_ai_full(data)

            # 🔥 MERGE (AI DOMINANT)
            final_pred = ai_pred
            final_conf = int((ai_conf * 0.75) + (bs_conf * 0.25))

            if ai_pred == "SKIP":
                final_pred = bs_res
                final_conf = bs_conf

            elif ai_pred != bs_res:
                final_conf -= 10

            if final_conf < 55:
                final_pred = "SKIP"

            last_prediction = final_pred

            # 🔒 STORE (IMPORTANT FIX)
            current_prediction_text = f"""
📊 FINAL: {final_pred} ({final_conf}%)

🤖 AI: {ai_pred} ({ai_conf}%)
🧠 LOGIC: {bs_res} ({bs_conf}%)

🧾 {', '.join(reasons)}

🤖 AI:
{ai_text[:150]}
"""

        # 🔄 TIMER UPDATE (NO OVERWRITE)
        text = f"""
🆔 {current}

{current_prediction_text}

⏱ {timer}

{current_result_text}
🎯 Accuracy: {int((wins/(wins+losses))*100) if (wins+losses)>0 else 0}%
"""

        try:
            await msg.edit_text(text)
        except:
            pass

        await asyncio.sleep(1)

# ▶️ RUN
app.run()
