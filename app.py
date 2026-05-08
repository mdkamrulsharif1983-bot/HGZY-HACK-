import os
import requests
import collections
import math
import time
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

API_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (Linux; Android 12)"}

def get_size(num): return "BIG" if num >= 5 else "SMALL"

# আপনার মেইন ইঞ্জিন থেকে নেওয়া হুবহু লজিক
def analyze_engine(history):
    nums = [int(i['number']) for i in history[:30]]
    freq = collections.Counter(nums)
    hot = [n for n, _ in freq.most_common(3)]
    
    changes = [abs(nums[i] - nums[i+1]) for i in range(len(nums)-1)]
    vol = sum(changes) / len(changes) if changes else 0
    momentum = sum(nums[:5]) - sum(nums[5:10])
    
    mean = sum(nums[:10]) / 10
    variance = sum((x - mean) ** 2 for x in nums[:10]) / 10
    std_dev = math.sqrt(variance)
    stability = max(0, min(100, 100 - (vol * 6) - (std_dev * 3)))
    
    # স্ট্রেংথ ও অন্যান্য ফ্যাক্টর
    big_ratio = sum(1 for n in nums[:12] if n >= 5) / 12 * 100
    streak = len(nums) >= 3 and len(set(nums[:3])) == 1
    zigzag = len(nums) >= 4 and (nums[0] < nums[1] > nums[2] < nums[3])

    return hot, vol, momentum, stability, streak, zigzag, big_ratio

@app.route('/predict', methods=['GET'])
def predict():
    try:
        response = requests.get(f"{API_URL}?ts={int(time.time()*1000)}", headers=HEADERS, timeout=5)
        data = response.json().get('data', {}).get('list', [])
        if not data: return jsonify({"status": "error"}), 500

        # অরিজিনাল ইঞ্জিন কল
        hot, vol, mom, stab, streak, zigzag, strength = analyze_engine(data)
        avg = sum(int(i['number']) for i in data[:10]) / 10
        last_num = int(data[0]['number'])
        last_col = data[0]['color'].upper()

        # আপনার অরিজিনাল ডিসিশন মেকিং লজিক
        score = 0
        if streak: size, color, score = get_size(last_num), last_col, 30
        elif zigzag: size, color, score = ("BIG" if last_num < 5 else "SMALL"), ("GREEN" if last_col == "RED" else "RED"), 20
        else: size, color = ("SMALL" if avg >= 4.6 else "BIG"), ("GREEN" if last_col == "RED" else "RED")

        confidence = max(5, min(98, (55 + abs(avg - 4.5) * 10 + score - vol * 2 + (stab - 50) * 0.3 + mom * 0.1)))

        return jsonify({
            "status": "success",
            "issue": int(data[0]['issueNumber']) + 1,
            "prediction": {
                "size": size,
                "color": color,
                "hot": hot[0],
                "confidence": round(confidence, 1),
                "volatility": round(vol, 2),
                "stability": round(stab, 1)
            }
        })
    except:
        return jsonify({"status": "error"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
