import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

def get_gold_price():
    # 使用台銀歷史牌價頁面，結構通常比首頁更穩定
    url = "https://rate.bot.com.tw/gold/csv/ltm/TWD/0" 
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        print("正在嘗試抓取資料...")
        response = requests.get(url, headers=headers)
        
        # 如果 CSV 抓不到，改回一般頁面
        if response.status_code != 200:
            url = "https://rate.bot.com.tw/gold?Lang=zh-TW"
            response = requests.get(url, headers=headers)
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 尋找所有賣出價的欄位
        price = None
        target_cells = soup.find_all("td", {"data-table": "本行賣出"})
        
        for cell in target_cells:
            text = cell.get_text().strip().replace(',', '')
            if text and text.replace('.', '', 1).isdigit():
                price = float(text)
                break # 抓到第一個（通常是即時賣出價）就停止

        if price:
            print(f"找到金價: {price}")
            save_data(price)
        else:
            print("錯誤：完全找不到價格數據，請檢查網頁內容。")
            # 偵錯用：印出前 500 個字
            print(response.text[:500])

    except Exception as e:
        print(f"執行出錯: {e}")

def save_data(price):
    filename = 'data.json'
    history = []
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            try:
                history = json.load(f)
            except:
                history = []
    
    history.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "price": price
    })
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=4)
    print("檔案已儲存成功")

if __name__ == "__main__":
    get_gold_price()
