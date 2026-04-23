import asyncio
import requests
import random
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
api_id = 23907288
api_hash = "f9a47570ed19aebf8eb0f0a5ec1111e5"
bot_token = "8670925766:AAEXImOGX5KSYraU2Bob99U-6_-70L0f26g"

app = Client("wingo-ai-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ===== GLOBAL =====
last_prediction = None
last_period = None
wins = 0
losses = 0

strategy_stats = {
    "pattern": {"win":0,"loss":0},
    "zigzag": {"win":0,"loss":0},
    "trend": {"win":0,"loss":0}
}

# ===== FETCH =====
def fetch_history(mode):
    url = f"https://draw.ar-lottery01.com/WinGo/WinGo_{mode}/GetHistoryIssuePage.json?page=1&size=50"
    return requests.get(url).json()["data"]["list"]

def fetch_timer(mode):
    url = f"https://draw.ar-lottery01.com/WinGo/WinGo_{mode}.json"
    return requests.get(url).json()

def to_bs(n):
    return "BIG" if int(n) >= 5 else "SMALL"

# ===== LOGICS =====
def pattern(data):
    nums = [to_bs(i["number"]) for i in data[:10]]
    return "BIG" if nums.count("BIG") > nums.count("SMALL") else "SMALL"

def zigzag(data):
    nums = [to_bs(i["number"]) for i in data[:6]]
    if nums in [["BIG","SMALL"]*3, ["SMALL","BIG"]*3]:
        return "BIG" if nums[-1]=="SMALL" else "SMALL"
    return None

def trend(data):
    nums = [to_bs(i["number"]) for i in data[:20]]
    return "BIG" if nums.count("BIG") >= 10 else "SMALL"

# ===== WEIGHT =====
def get_weight(name):
    s = strategy_stats[name]
    total = s["win"] + s["loss"]
    if total == 0:
        return 1
    return s["win"] / total

# ===== AI =====
def ask_ai(data):
    try:
        payload = str(data[:20])
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
    scores = {"BIG":0,"SMALL":0}

    p = pattern(data)
    scores[p] += 2 * get_weight("pattern")

    z = zigzag(data)
    if z:
        scores[z] += 3 * get_weight("zigzag")

    t = trend(data)
    scores[t] += 2 * get_weight("trend")

    ai_pred, ai_conf = ask_ai(data)
    scores[ai_pred] += ai_conf / 50

    final_bs = max(scores, key=scores.get)

    nums = [int(i["number"]) for i in data[:20]]

    pool = [5,6,7,8,9] if final_bs=="BIG" else [0,1,2,3,4]

    freq = {n: nums.count(n) for n in pool}
    final_num = max(freq, key=freq.get) if sum(freq.values()) else random.choice(pool)

    # avoid repeat
    if final_num == nums[0]:
        final_num = random.choice(pool)

    color_map = {
        0:"RED",1:"GREEN",2:"RED",3:"GREEN",4:"RED",
        5:"GREEN/VIOLET",6:"RED",7:"GREEN",8:"RED",9:"GREEN"
    }

    final_color = color_map[final_num]

    conf = int((scores[final_bs] / (sum(scores.values())+1)) * 100)

    return final_bs, final_num, final_color, conf

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

    global last_prediction, last_period, wins, losses

    while True:
        try:
            timer = fetch_timer(mode)
            history = fetch_history(mode)

            current = timer["current"]
            period = current["issueNumber"]
            end_time = current["endTime"]

            remain = int((end_time - time.time()*1000)/1000)
            remain = max(remain, 0)

            pred_bs, pred_num, pred_color, conf = predict(history)

            # ===== RESULT CHECK =====
            if last_period and period != last_period:
                actual = to_bs(history[0]["number"])

                if last_prediction == actual:
                    wins += 1
                    result = "WIN ✅"
                else:
                    losses += 1
                    result = "LOSS ❌"
            else:
                result = "Waiting..."

            acc = int((wins/(wins+losses))*100) if (wins+losses)>0 else 0

            text = f"""
🆔 {period}

🎯 {pred_bs}
🔢 {pred_num}
🎨 {pred_color}

📊 {conf}%  
⏱ {remain}s

🏁 {result}
🎯 Accuracy: {acc}%
"""

            await message.edit(text)

            last_prediction = pred_bs
            last_period = period

            await asyncio.sleep(1)

        except Exception as e:
            await message.edit(f"Error: {e}")
            break

app.run()
