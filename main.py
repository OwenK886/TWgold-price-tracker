import requests
from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime

def get_gold_price():
    url = "https://rate.bot.com.tw/gold?Lang=zh-TW"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    try:
        print("開始連線台銀...")
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # --- 精準抓取掛牌時間 ---
        official_time = ""
        # 1. 嘗試找特定的 span
        time_tag = soup.find("span", class_="time")
        if time_tag:
            official_time = time_tag.get_text().strip().replace("牌價最後更新時間：", "")
        
        # 2. 如果沒抓到，用正則表達式掃描整個網頁找日期格式 (例如 2026/01/09 19:50)
        if not official_time:
            match = re.search(r'\d{4}/\d{2}/\d{2}\s\d{2}:\d{2}', response.text)
            if match:
                official_time = match.group()
        
        # --- 抓取價格 ---
        buy_price = None
        sell_price = None
        
        # 找到所有表格列
        rows = soup.find_all('tr')
        for row in rows:
            if "黃金存摺" in row.text and "新台幣" in row.text:
                # 抓取該列中屬性為 data-table="本行買進" 和 "本行賣出" 的 td
                td_buy = row.find("td", {"data-table": "本行買進"})
                td_sell = row.find("td", {"data-table": "本行賣出"})
                if td_buy and td_sell:
                    buy_price = float(td_buy.text.strip().replace(',', ''))
                    sell_price = float(td_sell.text.strip().replace(',', ''))
                    break

        if buy_price and sell_price and official_time:
            print(f"成功！掛牌時間：{official_time}，買進：{buy_price}，賣出：{sell_price}")
            save_to_json(official_time, buy_price, sell_price)
        else:
            print(f"抓取失敗。時間:{official_time}, 買:{buy_price}, 賣:{sell_price}")

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

    # 週末測試期間，我們允許重複寫入以便看到成果
    history.append({"time": time_str, "buy": buy, "sell": sell})
    
    # 限制紀錄數量
    if len(history) > 100: history = history[-100:]
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=4)
    print(f"資料已寫入 data.json。目前總筆數: {len(history)}")

if __name__ == "__main__":
    get_gold_price()
