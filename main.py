import requests
import json
import os
import re
import sys
from bs4 import BeautifulSoup

def get_gold_price():
    url = "https://rate.bot.com.tw/gold?Lang=zh-TW"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    try:
        print("開始連線台銀 (BeautifulSoup 專業解析模式)...")
        response = requests.get(url, headers=headers, timeout=10)
        html = response.text
        
        # 1. 抓取掛牌時間
        official_time = ""
        time_match = re.search(r'\d{4}/\d{2}/\d{2}\s\d{2}:\d{2}', html)
        if time_match:
            official_time = time_match.group()

        # 2. 使用 BeautifulSoup 鎖定表格
        soup = BeautifulSoup(html, 'html.parser')
        
        buy_price = None
        sell_price = None
        
        # 尋找網頁中所有的表格列 (tr)
        rows = soup.find_all('tr')
        for row in rows:
            # 將整列轉成純文字
            row_text = row.get_text(separator=' ', strip=True)
            
            # 條件：如果這列的文字包含「1公克」與「黃金」(過濾掉空格干擾)
            if '1公克' in row_text.replace(' ', '') and '黃金' in row_text:
                print(f"成功找到目標列: {row_text}")
                
                # 移除千分位逗號，並找出裡面的所有 4 位數以上的數字
                clean_text = row_text.replace(',', '')
                numbers = re.findall(r'(?<!\d)(\d{4,}(?:\.\d+)?)(?!\d)', clean_text)
                
                if len(numbers) >= 2:
                    p1 = float(numbers[0])
                    p2 = float(numbers[1])
                    buy_price = min(p1, p2)
                    sell_price = max(p1, p2)
                
                # 找到就跳出迴圈
                break

        if buy_price and sell_price and official_time:
            print(f"成功！掛牌時間：{official_time}，買進：{buy_price}，賣出：{sell_price}")
            save_to_json(official_time, buy_price, sell_price)
        else:
            print(f"解析失敗。時間:{official_time}, 找不到包含 1公克 的黃金報價。")
            sys.exit(1) # 主動報錯

    except Exception as e:
        print(f"程式異常: {e}")
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
