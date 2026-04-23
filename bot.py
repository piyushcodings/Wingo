import asyncio
import requests
import random
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
api_id = 23907288
api_hash = "f9a47570ed19aebf8eb0f0a5ec1111e5"
bot_token = "8670925766:AAEXImOGX5KSYraU2Bob99U-6_-70L0f26g"

app = Client("wingo-ai-bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)


# ===== GLOBAL =====
last_prediction = None
last_period = None

# ===== FETCH =====
def fetch_history(mode):
    url = f"https://draw.ar-lottery01.com/WinGo/WinGo_{mode}/GetHistoryIssuePage.json?page=1&size=50"
    return requests.get(url).json()["data"]["list"]

def fetch_timer(mode):
    url = f"https://draw.ar-lottery01.com/WinGo/WinGo_{mode}.json"
    return requests.get(url).json()

def to_bs(n):
    return "BIG" if int(n) >= 5 else "SMALL"

# ===== PHASE DETECTION =====
def detect_phase(data):
    nums = [int(i["number"]) for i in data[:10]]
    bs = ["B" if n >= 5 else "S" for n in nums]

    if bs.count("B") >= 7 or bs.count("S") >= 7:
        return "TREND"

    pattern = "".join(bs[:6])
    if pattern in ["BSBSBS", "SBSBSB"]:
        return "ZIGZAG"

    return "RANDOM"

# ===== AI =====
def ask_ai(data):
    try:
        payload = [i["number"] for i in data[:15]]
        res = requests.get(f"https://apis.prexzyvilla.site/ai/copilot-think?text={payload}")
        text = res.json()["text"].lower()

        if "big" in text:
            return "BIG", 70
        elif "small" in text:
            return "SMALL", 70
    except:
        pass

    return random.choice(["BIG","SMALL"]), 50

# ===== PREDICT =====
def predict(data):

    nums = [int(i["number"]) for i in data[:20]]
    bs = [to_bs(n) for n in nums]

    phase = detect_phase(data)

    # ===== PHASE BASED =====
    if phase == "TREND":
        last = bs[0]
        final_bs = "BIG" if last == "SMALL" else "SMALL"

    elif phase == "ZIGZAG":
        last = bs[0]
        final_bs = "BIG" if last == "SMALL" else "SMALL"

    else:
        final_bs = random.choice(["BIG","SMALL"])

    # ===== ANTI SPAM =====
    last4 = bs[:4]
    if last4.count(last4[0]) == 4:
        final_bs = "BIG" if last4[0]=="SMALL" else "SMALL"

    # ===== AI MERGE =====
    ai_pred, ai_conf = ask_ai(data)

    if ai_pred == final_bs:
        conf = int((ai_conf * 0.7) + 20)
    else:
        conf = int((ai_conf * 0.5) + 10)

    # ===== SKIP =====
    if conf < 55:
        return "SKIP", "-", "-", conf, phase

    # ===== NUMBER =====
    pool = [5,6,7,8,9] if final_bs=="BIG" else [0,1,2,3,4]

    freq = {n: nums.count(n) for n in pool}
    final_num = max(freq, key=freq.get) if sum(freq.values()) else random.choice(pool)

    # avoid repeat
    if final_num == nums[0]:
        final_num = random.choice(pool)

    # ===== COLOR =====
    color_map = {
        0:"RED",1:"GREEN",2:"RED",3:"GREEN",4:"RED",
        5:"GREEN/VIOLET",6:"RED",7:"GREEN",8:"RED",9:"GREEN"
    }

    final_color = color_map[final_num]

    return final_bs, final_num, final_color, conf, phase

# ===== INLINE =====
keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("30s", callback_data="30S"),
     InlineKeyboardButton("1min", callback_data="1M")],
    [InlineKeyboardButton("3min", callback_data="3M"),
     InlineKeyboardButton("5min", callback_data="5M")]
])

@app.on_message(filters.command("start"))
async def start(_, msg):
    await msg.reply("Select Mode 👇", reply_markup=keyboard)

# ===== MAIN LOOP =====
@app.on_callback_query()
async def callback(_, query):
    mode = query.data
    message = await query.message.edit("Starting...")

    global last_prediction, last_period

    saved_prediction = None

    while True:
        try:
            timer = fetch_timer(mode)
            history = fetch_history(mode)

            current = timer["current"]
            period = current["issueNumber"]
            end_time = current["endTime"]

            remain = int((end_time - time.time()*1000)/1000)
            remain = max(remain, 0)

            # 🔥 NEW PERIOD → NEW PREDICTION
            if period != last_period:
                saved_prediction = predict(history)
                last_period = period

            pred_bs, pred_num, pred_color, conf, phase = saved_prediction

            text = f"""
🆔 {period}

🎯 {pred_bs}
🔢 {pred_num}
🎨 {pred_color}

📊 {conf}%
🧠 Phase: {phase}

⏱ {remain}s
"""

            await message.edit(text)

            await asyncio.sleep(1)

        except Exception as e:
            await message.edit(f"Error: {e}")
            break

app.run()
