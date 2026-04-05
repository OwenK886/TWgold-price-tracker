import requests
import json
import os
import re

def get_gold_price():
    url = "https://rate.bot.com.tw/gold?Lang=zh-TW"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    try:
        print("開始連線台銀 (精準鎖定 1公克 模式)...")
        response = requests.get(url, headers=headers, timeout=10)
        html = response.text
        
        # 1. 抓取掛牌時間 (尋找 2026/01/09 19:50 格式)
        official_time = ""
        time_match = re.search(r'\d{4}/\d{2}/\d{2}\s\d{2}:\d{2}', html)
        if time_match:
            official_time = time_match.group()

        # 2. 精準抓取價格：鎖定包含「1公克」的表格列 (<tr>...</tr>)
        buy_price = None
        sell_price = None
        
        row_match = re.search(r'(<tr[^>]*>.*?1公克.*?</tr>)', html, re.DOTALL)
        if row_match:
            row_html = row_match.group(1)
            # 清除所有 HTML 標籤，只保留純文字
            clean_text = re.sub(r'<[^>]+>', ' ', row_html)
            # 移除千分位逗號，並找出所有 4 位數以上的數字
            clean_text = clean_text.replace(',', '')
            numbers = re.findall(r'(?<!\d)(\d{4,}(?:\.\d+)?)(?!\d)', clean_text)
            
            # 通常第一、第二個符合條件的數字就是買進與賣出價
            if len(numbers) >= 2:
                p1 = float(numbers[0])
                p2 = float(numbers[1])
                # 確保賣出價大於買進價
                buy_price = min(p1, p2)
                sell_price = max(p1, p2)

        if buy_price and sell_price and official_time:
            print(f"成功！掛牌時間：{official_time}，買進：{buy_price}，賣出：{sell_price}")
            save_to_json(official_time, buy_price, sell_price)
        else:
            print(f"解析失敗。時間:{official_time}, 找到的數字:{numbers if 'numbers' in locals() else '無'}")

    except Exception as e:
        print(f"程式異常: {e}")

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

    # 加入 currency 欄位
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
