import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

def get_gold_price():
    url = "https://rate.bot.com.tw/gold?Lang=zh-TW"
    try:
        # 加入 User-Agent 模擬真人瀏覽器，避免被阻擋
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 尋找台銀黃金存摺「賣出價」的第一筆數據 (通常是新台幣)
        price_element = soup.find("td", {"class": "text-right", "data-table": "本行賣出"})
        if not price_element:
            print("找不到價格標籤")
            return
            
        price = float(price_element.text.strip().replace(',', '')) # 移除逗號並轉為數字
        now_time = datetime.now().strftime("%Y-%m-%d %H:%M")

        # --- 處理歷史數據累加 ---
        filename = 'data.json'
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
        else:
            history_data = []

        # 加入新數據
        history_data.append({"time": now_time, "price": price})

        # 只保留最近 100 筆數據 (避免檔案過大)
        if len(history_data) > 100:
            history_data = history_data[-100:]

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, ensure_ascii=False, indent=4)
            
        print(f"成功更新！當前價格: {price}")

    except Exception as e:
        print(f"發生錯誤: {e}")

if __name__ == "__main__":
    get_gold_price()
