import requests
import json
import os
import re
import sys
from bs4 import BeautifulSoup

def get_gold_price():
    url = "https://rate.bot.com.tw/gold?Lang=zh-TW"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }
    
    try:
        print("開始連線台銀 (純文字錨點萃取模式)...")
        response = requests.get(url, headers=headers, timeout=10)
        html = response.text
        
        # 1. 抓取掛牌時間
        soup = BeautifulSoup(html, 'html.parser')
        
        # 魔法指令：把所有 HTML 標籤 (div, form, button) 全部脫掉，只留純文字，並用空格隔開
        text = soup.get_text(separator=' ')
        # 把多餘的換行、連續空白全部壓平成單一空格
        text = re.sub(r'\s+', ' ', text)

        official_time = ""
        time_match = re.search(r'\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}', text)
        if time_match:
            official_time = time_match.group()

        # 2. 抓取價格
        buy_price = None
        sell_price = None
        
        # 在純文字中尋找 "1 公克" 或是 "1公克"
        match = re.search(r'1\s*公克', text)
        if match:
            # 找到 "1公克" 後，擷取它後方的 150 個字元 (這絕對包含著買賣報價)
            start_idx = match.end()
            sub_text = text[start_idx:start_idx+150]
            
            # 從這段文字中，利用正則找出所有的「數字」 (包含千分位逗號，例如 4,818)
            raw_numbers = re.findall(r'(?<![\d.])(\d{1,3}(?:,\d{3})+|\d{4,})(?![\d.])', sub_text)
            
            valid_prices = []
            for n in raw_numbers:
                val = float(n.replace(',', ''))
                # 黃金 1公克 價格目前約在 4000 多，設定 2000~15000 作為合理範圍，過濾掉雜訊
                if 2000 < val < 15000:
                    valid_prices.append(val)
            
            if len(valid_prices) >= 2:
                # 確保買進與賣出價格正確 (銀行賣出價一定比較高)
                buy_price = min(valid_prices[0], valid_prices[1])
                sell_price = max(valid_prices[0], valid_prices[1])
        
        if buy_price and sell_price and official_time:
            print(f"🎉 成功！掛牌時間：{official_time}，買進：{buy_price}，賣出：{sell_price}")
            save_to_json(official_time, buy_price, sell_price)
        else:
            print(f"❌ 解析失敗。時間:{official_time}")
            print(f"擷取到的文字區塊: {sub_text if 'sub_text' in locals() else '找不到1公克'}")
            sys.exit(1)

    except Exception as e:
        print(f"💥 程式異常: {e}")
        sys.exit(1)

def save_to_json(time_str, buy, sell):
    filename = 'data.json'
    history = []
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except: history = []

    if history and history[-1]['time'] == time_str:
        print(f"資料重複 ({time_str})，不再儲存。")
        return

    history.append({
        "time": time_str, 
        "buy": buy, 
        "sell": sell,
        "currency": "TWD"
    })
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=4)
    print(f"資料已更新 (TWD)，目前總筆數: {len(history)}")

if __name__ == "__main__":
    get_gold_price()
