import os
import requests
import collections
import math
import time
import threading
from flask import Flask, jsonify
from flask_cors import CORS

# --- প্রো-লেভেল কনফিগারেশন ---
app = Flask(__name__)
CORS(app)

API_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (Linux; Android 12)"}

# গ্লোবাল স্টেট ম্যানেজমেন্ট (ইঞ্জিন মেমোরি)
engine_memory = {
    "last_prediction": None,
    "consecutive_wins": 0,
    "consecutive_losses": 0,
    "market_status": "STABLE"
}

def get_size(num): return "BIG" if num >= 5 else "SMALL"

# --- আল্ট্রা কোর ইঞ্জিন লজিক ---
def deep_market_analysis(history):
    if not history: return None
    
    nums = [int(i['number']) for i in history]
    # ১. ফ্রিকোয়েন্সি এনালাইসিস
    freq = collections.Counter(nums)
    hot_numbers = [n for n, _ in freq.most_common(3)]
    
    # ২. ভolatিলিটি ও মোমেন্টাম
    changes = [abs(nums[i] - nums[i+1]) for i in range(len(nums)-1)]
    volatility = sum(changes) / len(changes) if changes else 0
    momentum = sum(nums[:5]) - sum(nums[5:10])
    
    # ৩. স্ট্যাবিলিটি ও স্ট্যান্ডার্ড ডেভিয়েশন
    mean = sum(nums[:10]) / 10
    variance = sum((x - mean) ** 2 for x in nums[:10]) / 10
    std_dev = math.sqrt(variance)
    stability = max(0, min(100, 100 - (volatility * 6) - (std_dev * 3)))
    
    # ৪. প্যাটার্ন রিকগনিশন (Streak & Zigzag)
    streak = len(nums) >= 3 and len(set(nums[:3])) == 1
    zigzag = len(nums) >= 4 and (nums[0] < nums[1] > nums[2] < nums[3])
    
    # ৫. রেশিও এনালাইসিস
    big_count = sum(1 for n in nums[:12] if n >= 5)
    big_ratio = (big_count / 12) * 100
    
    return {
        "hot": hot_numbers[0],
        "vol": volatility,
        "mom": momentum,
        "stab": stability,
        "streak": streak,
        "zigzag": zigzag,
        "ratio": big_ratio,
        "avg": mean
    }

@app.route('/predict', methods=['GET'])
def predict_endpoint():
    try:
        res = requests.get(f"{API_URL}?ts={int(time.time()*1000)}", headers=HEADERS, timeout=5)
        raw_data = res.json().get('data', {}).get('list', [])
        if not raw_data: return jsonify({"status": "offline"}), 503

        # ইঞ্জিন প্রসেসিং
        analysis = deep_market_analysis(raw_data)
        last_num = int(raw_data[0]['number'])
        last_col = raw_data[0]['color'].upper()
        
        # ডিসিশন ম্যাট্রিক্স
        score = 0
        if analysis['streak']:
            size, color, score = get_size(last_num), last_col, 30
        elif analysis['zigzag']:
            size, color, score = ("BIG" if last_num < 5 else "SMALL"), ("GREEN" if last_col == "RED" else "RED"), 20
        else:
            size, color = ("SMALL" if analysis['avg'] >= 4.6 else "BIG"), ("GREEN" if last_col == "RED" else "RED")

        # কনফিডেন্স অ্যালগরিদম
        conf = max(10, min(99, (58 + abs(analysis['avg'] - 4.5) * 12 + score - analysis['vol'] * 2.5 + (analysis['stab'] - 50) * 0.4)))

        return jsonify({
            "status": "success",
            "server_time": time.time(),
            "issue": int(raw_data[0]['issueNumber']) + 1,
            "data": {
                "prediction": {"size": size, "color": color, "confidence": round(conf, 1)},
                "analytics": {
                    "volatility": round(analysis['vol'], 2),
                    "stability": round(analysis['stab'], 1),
                    "momentum": round(analysis['mom'], 2),
                    "jackpot": analysis['hot']
                }
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
    
