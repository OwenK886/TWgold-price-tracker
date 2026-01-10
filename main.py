import requests
import json
import os
import re

def get_gold_price():
    url = "https://rate.bot.com.tw/gold?Lang=zh-TW"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    try:
        print("開始連線台銀 (全域掃描模式)...")
        response = requests.get(url, headers=headers, timeout=10)
        html = response.text
        
        # 1. 抓取掛牌時間 (尋找 2026/01/09 19:50 格式)
        official_time = ""
        time_match = re.search(r'\d{4}/\d{2}/\d{2}\s\d{2}:\d{2}', html)
        if time_match:
            official_time = time_match.group()

        # 2. 抓取價格 (強力正則解析)
        # 我們尋找「數字」後面緊跟著「買進按鈕」或「回售按鈕」的模式
        # 模式說明：抓取數字，中間可能夾雜換行或空格，後面接著買進/回售按鈕文字
        buy_price = None  # 對應網頁的「回售」數字
        sell_price = None # 對應網頁的「買進」數字

        # 搜尋賣出價 (你要買，所以找買進按鈕)
        sell_match = re.search(r'(\d{4,5})\s*<[^>]*>\s*買進', html)
        # 搜尋買進價 (你要賣，所以找回售按鈕)
        buy_match = re.search(r'(\d{4,5})\s*<[^>]*>\s*回售', html)

        if sell_match:
            sell_price = float(sell_match.group(1))
        if buy_match:
            buy_price = float(buy_match.group(1))

        # --- 備案：如果正則失敗，直接找所有 4 位數數字 (針對台銀目前 45xx 的價格) ---
        if not buy_price or not sell_price:
            print("正則掃描失敗，啟動備案：尋找所有 4 位數數字...")
            prices = re.findall(r'>\s*(\d{4,5})\s*<', html)
            if len(prices) >= 2:
                # 根據台銀結構，通常第一筆是賣出，第二筆是買進 (或反之)
                # 這裡取前兩筆符合 4000 以上的數字
                filtered_prices = [float(p) for p in prices if float(p) > 3000]
                if len(filtered_prices) >= 2:
                    sell_price = filtered_prices[0]
                    buy_price = filtered_prices[1]

        if buy_price and sell_price and official_time:
            # 修正買賣價格邏輯：賣出價通常比買進價高
            real_sell = max(buy_price, sell_price)
            real_buy = min(buy_price, sell_price)
            print(f"成功！掛牌時間：{official_time}，買進：{real_buy}，賣出：{real_sell}")
            save_to_json(official_time, real_buy, real_sell)
        else:
            print(f"解析失敗。時間:{official_time}, 買:{buy_price}, 賣:{sell_price}")
            # 輸出部分原始碼供下次診斷
            idx = html.find("買進")
            if idx != -1:
                print("關鍵字附近原始碼：", html[idx-100:idx+100])

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
        "currency": "TWD" # 這裡標註幣別
    })
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=4)
    print(f"資料已更新 (TWD)，目前總筆數: {len(history)}")

if __name__ == "__main__":
    get_gold_price()
