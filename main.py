import requests
from bs4 import BeautifulSoup
import json
import os
import re

def get_gold_price():
    url = "https://rate.bot.com.tw/gold?Lang=zh-TW"
    headers = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1'}
    
    try:
        print("開始連線台銀 (模擬行動裝置)...")
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. 抓取掛牌時間
        official_time = ""
        time_match = re.search(r'\d{4}/\d{2}/\d{2}\s\d{2}:\d{2}', response.text)
        if time_match:
            official_time = time_match.group()

        buy_price = None
        sell_price = None

        # 2. 針對你提供的響應式 HTML 結構進行抓取
        # 我們尋找所有的 'footable-row-detail-row' 區塊
        detail_rows = soup.find_all("div", class_="footable-row-detail-row")
        
        for row in detail_rows:
            row_text = row.get_text()
            # 尋找價格（排除表單內的其他數字）
            # 價格通常位在「1 公克:」之後，按鈕之前
            val_div = row.find("div", class_="footable-row-detail-value")
            if not val_div: continue
            
            # 提取純數字 (可能有換行符號)
            price_text = val_div.get_text(strip=True)
            # 使用正則只抓取數字部分
            price_match = re.search(r'(\d+)', price_text)
            
            if price_match:
                current_val = float(price_match.group(1))
                
                if "買進" in row_text:
                    sell_price = current_val  # 銀行標示買進按鈕，代表那是你的買入價(賣出價)
                elif "回售" in row_text:
                    buy_price = current_val   # 銀行標示回售按鈕，代表那是你的賣出價(買進價)

        if buy_price and sell_price and official_time:
            print(f"成功！掛牌時間：{official_time}，買進：{buy_price}，賣出：{sell_price}")
            save_to_json(official_time, buy_price, sell_price)
        else:
            print(f"解析失敗。時間:{official_time}, 買:{buy_price}, 賣:{sell_price}")
            # 備案：如果響應式抓不到，嘗試原本的桌機版抓法
            print("嘗試備案抓法...")
            buy_tag = soup.find("td", {"data-table": "本行買進"})
            sell_tag = soup.find("td", {"data-table": "本行賣出"})
            if buy_tag and sell_tag:
                save_to_json(official_time, float(buy_tag.text.strip().replace(',','')), float(sell_tag.text.strip().replace(',','')))

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

    history.append({"time": time_str, "buy": buy, "sell": sell})
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=4)
    print(f"資料已更新，總筆數: {len(history)}")

if __name__ == "__main__":
    get_gold_price()
