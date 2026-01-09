import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

def get_gold_price():
    url = "https://rate.bot.com.tw/gold?Lang=zh-TW"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 抓取台銀金存摺賣出價 (這只是一個範例選取器，具體需視網頁結構調整)
    price = soup.find("td", {"data-table": "本行賣出"}).text.strip()
    
    data = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "price": price
    }
    
    # 將結果存入 json 檔
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"成功抓取價格: {price}")

if __name__ == "__main__":
    get_gold_price()
