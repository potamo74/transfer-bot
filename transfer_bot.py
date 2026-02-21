import requests
import json
import os

# Hämtar nycklar
TELEGRAM_TOKEN = os.environ["8569602675:AAF6K9rh7Vo01zAp_o1iaKWWtJw-NIkbSYw"]
CHAT_ID = os.environ["8205152248"]
SHEET_URL = os.environ["https://docs.google.com/spreadsheets/d/e/2PACX-1vS3uIgzCqha10nuHln-lgZ3kHw33mtQCV4lSM_Ga_0Woex-82PXkf-1wmbYzex_tUgL2_MI0CVVefm7/pub?gid=0&single=true&output=csv"]
HISTORY_FILE = "sent.json"

def get_watchlist():
    """Hämtar spelare från sheet"""
    print("Hämtar bevakningslista")
    try:
        response = requests.get(SHEET_URL)
        return [line.strip().lower() for line in response.text.splitlines() if line.strip()]
    except Exception as e:
        print(f"Fel vid hämtning av lista: {e}")
        return []


def get_transfers():
    """Hämtar transfers från Fotmob"""
    print("Hämtar senaste transfers")
    url = "https://www.fotmob.com/api/transfers?lang=en"
    try:
        response = requests.get(url)
        data = response.json()
        
        raw_list = data.get("transfers", [])
        
        clean_transfers = []
        for t in raw_list:
            #Lägger till spelare i listan.
            clean_transfers.append({
                "name": t.get("name", "").lower(),
                "display_name": t.get("name", ""), 
                "from": t.get("fromClub", "Okänd"),
                "to": t.get("toClub", "Okänd"),
                "fee": t.get("fee", {}).get("value", "Okänt pris")
            })
        return clean_transfers
    except Exception as e:
        print(f"Kunde inte hämta transfers - {e}")
        return []


def send_telegram(t):
    """Skickar notisen t telegram"""
    msg = (
        f"🚨 <b>TRANSFER!</b>\n\n"
        f"⚽ <b>{t['display_name']}</b>\n"
        f"➡️ Från: {t['from']}\n"
        f"⬅️ Till: {t['to']}\n"
        f"💰 {t['fee']}"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})

def main():
    #Ladda historik
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            sent_players = json.load(f)
    else:
        sent_players = []

    #Hämta data
    watchlist = get_watchlist()
    transfers = get_transfers() 

    print(f"Bevakar {len(watchlist)} spelare. Hittade {len(transfers)} transfers totalt.")

    new_sent = sent_players.copy()

    #Jämför
    for t in transfers:
        if t["name"] in watchlist:
            #kollar både namn och ny klubb
            unique_id = f"{t['name']}-{t['to']}"
            
            if unique_id not in sent_players:
                print(f"TRÄFF! Skickar notis om {t['display_name']}")
                send_telegram(t)
                new_sent.append(unique_id)
            else:
                print(f"Redan skickat för {t['display_name']}")

    #Spara historik
    with open(HISTORY_FILE, "w") as f:
        json.dump(new_sent, f)

if __name__ == "__main__":
    main()