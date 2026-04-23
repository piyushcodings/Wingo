import requests
import asyncio
import time
import random
import re
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# CONFIG
api_id = 23907288
api_hash = "f9a47570ed19aebf8eb0f0a5ec1111e5"
bot_token = "8670925766:AAEXImOGX5KSYraU2Bob99U-6_-70L0f26g"
app = Client("wingo-ultra", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

API_MAP = {
    "30s": "30S",
    "1m": "1M",
    "3m": "3M",
    "5m": "5M"
}

# STATE
last_period = None
last_prediction = None
wins = 0
losses = 0

current_prediction_text = ""
current_result_text = ""

# FETCH DATA
def fetch_data(mode):
    try:
        url = f"https://draw.ar-lottery01.com/WinGo/WinGo_{API_MAP[mode]}/GetHistoryIssuePage.json?page=1&size=50"
        return requests.get(url, timeout=5).json()["data"]["list"]
    except:
        return []

# TIME API
def get_time_data(mode):
    try:
        url = f"https://draw.ar-lottery01.com/WinGo/WinGo_{API_MAP[mode]}.json"
        return requests.get(url, timeout=5).json()
    except:
        return None

# BS
def to_bs(n): return "BIG" if n >= 5 else "SMALL"

# 🧠 LOGIC ENGINE
def advanced_logic(data):
    nums = [int(i["number"]) for i in data[:30]]
    score = {"BIG":0,"SMALL":0}

    b = sum(1 for n in nums if n >= 5)
    s = len(nums) - b

    if b > s:
        score["BIG"] += 3
    else:
        score["SMALL"] += 3

    last5 = [to_bs(n) for n in nums[:5]]

    if len(set(last5)) == 1:
        flip = "BIG" if last5[0] == "SMALL" else "SMALL"
        score[flip] += 3

    score[last5[0]] += 2

    final = max(score, key=score.get)
    conf = int((score[final] / sum(score.values())) * 100)

    return final, conf

# 🤖 AI FULL JSON
def ask_ai(data):
    try:
        prompt = f"""
Analyze Wingo data deeply:

{data}

Return STRICT:
Prediction: BIG or SMALL
Confidence: number
Number: best guess 0-9
"""

        url = "https://apis.prexzyvilla.site/ai/copilot-think?text=" + requests.utils.quote(prompt)
        res = requests.get(url, timeout=10).json()
        text = res.get("text", "")

        pred = "SKIP"
        conf = 50
        number = random.randint(0,9)

        # prediction
        if "Prediction:" in text:
            line = [l for l in text.split("\n") if "Prediction:" in l][0]
            if "BIG" in line.upper():
                pred = "BIG"
            elif "SMALL" in line.upper():
                pred = "SMALL"

        # confidence
        m = re.search(r"Confidence[: ]+(\d+)", text)
        if m:
            conf = int(m.group(1))

        # number
        n = re.search(r"Number[: ]+(\d)", text)
        if n:
            number = int(n.group(1))

        return pred, conf, number, text

    except:
        return "SKIP", 50, random.randint(0,9), "AI error"

# 🎯 NUMBER LOGIC
def number_logic(data, pred):
    nums = [int(i["number"]) for i in data[:20]]

    if pred == "BIG":
        pool = [5,6,7,8,9]
    else:
        pool = [0,1,2,3,4]

    # frequency bias
    freq = {n: nums.count(n) for n in pool}
    best = max(freq, key=freq.get)

    # randomness mix
    if random.random() < 0.3:
        best = random.choice(pool)

    return best

# MENU
def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("30s","m_30s"),
         InlineKeyboardButton("1m","m_1m")],
        [InlineKeyboardButton("3m","m_3m"),
         InlineKeyboardButton("5m","m_5m")]
    ])

@app.on_message(filters.command("start"))
def start(c,m):
    m.reply("Select Mode", reply_markup=menu())

@app.on_callback_query(filters.regex("m_"))
async def start_loop(c,q):
    mode = q.data.split("_")[1]
    msg = await q.message.edit_text("Starting...")
    await loop(msg, mode)

# 🔥 MAIN LOOP
async def loop(msg, mode):
    global last_period, last_prediction, wins, losses
    global current_prediction_text, current_result_text

    while True:
        t = get_time_data(mode)
        if not t:
            await msg.edit_text("API Error")
            return

        current = t["current"]["issueNumber"]
        end = t["current"]["endTime"]

        now = int(time.time()*1000)
        left = (end-now)//1000
        timer = f"{left//60:02}:{left%60:02}"

        if current != last_period:
            last_period = current
            data = fetch_data(mode)

            # RESULT
            result_text = ""
            if last_prediction:
                actual = to_bs(int(data[0]["number"]))

                if actual == last_prediction:
                    wins += 1
                    result_text = f"🏁 {actual} ✅"
                else:
                    losses += 1
                    result_text = f"🏁 {actual} ❌"

            current_result_text = result_text

            total = wins + losses
            acc = int((wins/total)*100) if total else 0

            # LOGIC
            bs_res, bs_conf = advanced_logic(data)

            # AI
            ai_pred, ai_conf, ai_num, ai_text = ask_ai(data)

            # MERGE
            final_pred = ai_pred
            final_conf = int((ai_conf*0.75)+(bs_conf*0.25))

            if ai_pred == "SKIP":
                final_pred = bs_res
                final_conf = bs_conf

            if ai_pred != bs_res:
                final_conf -= 10

            if final_conf < 55:
                final_pred = "SKIP"

            # NUMBER
            num = number_logic(data, final_pred)

            last_prediction = final_pred

            current_prediction_text = f"""
📊 {final_pred} ({final_conf}%)
🔢 Number: {num}

🤖 AI: {ai_pred} ({ai_conf}%)
🧠 Logic: {bs_res} ({bs_conf}%)

🎯 Accuracy: {acc}%
"""

        text = f"""
🆔 {current}

{current_prediction_text}

⏱ {timer}

{current_result_text}
"""

        try:
            await msg.edit_text(text)
        except:
            pass

        await asyncio.sleep(1)

app.run()
