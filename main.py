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

        # 1. 抓取掛牌時間 (精準定位法)
        official_time = None
        
        # 嘗試方法 A: 從特定的 time 標籤抓取 (通常格式為 2026/01/10 12:00)
        time_element = soup.find("span", {"class": "time"})
        if time_element:
            official_time = time_element.get_text().strip()
            # 去除可能存在的「牌價最後更新時間：」字樣
            official_time = official_time.replace("牌價最後更新時間：", "").strip()

        # 嘗試方法 B: 如果 A 失敗，從表格上方的文字抓取
        if not official_time:
            info_text = soup.find("div", {"class": "pull-left"})
            if info_text and "時間" in info_text.text:
                official_time = info_text.text.split("：")[-1].strip()

        # 如果都抓不到，才用系統時間當備案
        if not official_time:
            official_time = datetime.now().strftime("%Y/%m/%d %H:%M")

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
    
    # 修改這裡：加入 print 方便除錯
    if history and history[-1]['time'] == time_str:
        print(f"台銀掛牌時間仍為 {time_str}，資料重複，跳過不儲存。")
        return

    history.append({
        "time": time_str,
        "buy": buy,
        "sell": sell
    })
    
    # 儲存檔案
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=4)
    print(f"成功寫入一筆新資料：{time_str}")
    
    # 保持最近 500 筆
    if len(history) > 500: history = history[-500:]
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=4)
