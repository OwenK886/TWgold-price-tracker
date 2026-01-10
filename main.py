import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

def get_gold_price():
    url = "https://rate.bot.com.tw/gold?Lang=zh-TW"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. 抓取掛牌時間
        # 台銀網頁上會有一個「牌價最後更新時間：2026/01/10 12:00」
        time_element = soup.find("span", {"class": "time"})
        official_time = time_element.text.strip() if time_element else datetime.now().strftime("%Y/%m/%d %H:%M")

        # 2. 抓取買進與賣出價
        buy_price = None
        sell_price = None
        
        # 尋找第一組新台幣計價的買進與賣出
        buy_td = soup.find("td", {"data-table": "本行買進", "class": "text-right"})
        sell_td = soup.find("td", {"data-table": "本行賣出", "class": "text-right"})
        
        if buy_td and sell_td:
            buy_price = float(buy_td.text.strip().replace(',', ''))
            sell_price = float(sell_td.text.strip().replace(',', ''))
            print(f"抓取成功: 掛牌時間={official_time}, 買進={buy_price}, 賣出={sell_price}")
            
            save_to_json(official_time, buy_price, sell_price)
        else:
            print("找不到價格標籤，請檢查網頁結構。")

    except Exception as e:
        print(f"執行出錯: {e}")

def save_to_json(time_str, buy, sell):
    filename = 'data.json'
    history = []
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            try:
                history = json.load(f)
            except: history = []
    
    # 檢查是否重複（如果掛牌時間跟上一筆一樣，就不重複存）
    if history and history[-1]['time'] == time_str:
        print("資料已存在，跳過儲存。")
        return

    history.append({
        "time": time_str,
        "buy": buy,
        "sell": sell
    })
    
    # 保持最近 200 筆
    if len(history) > 200: history = history[-200:]
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=4)
