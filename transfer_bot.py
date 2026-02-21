import requests
import json
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Hämtar nycklar
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
SHEET_URL = os.environ["SHEET_URL"]
HISTORY_FILE = "sent.json"

def normalize_name(name):
    """Specialtecken så att matchningen blir exakt"""
    if not name:
        return ""
    
    name = name.lower()
    
    replacements = {
        'ø': 'o', 'ö': 'o', 'ó': 'o', 'ò': 'o', 'ô': 'o',
        'å': 'a', 'ä': 'a', 'á': 'a', 'à': 'a', 'â': 'a', 'æ': 'ae',
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'í': 'i', 'ì': 'i', 'î': 'i',
        'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
        'ñ': 'n', 'ç': 'c',
        '-': ' ',
        "'": "",  
        "´": "",
        "`": ""
    }
    
    for key, value in replacements.items():
        name = name.replace(key, value)
        
    return name.strip()


def get_watchlist():
    """Hämtar spelare från sheet"""
    print("Hämtar bevakningslista")
    try:
        response = requests.get(SHEET_URL)
        return [normalize_name(line) for line in response.text.splitlines() if line.strip()]
    except Exception as e:
        print(f"Fel vid hämtning av lista: {e}")
        return []


def format_fee(fee_value, is_fee = False):
    """Formaterar siffror till snygga valutor, eller returnerar texten om det är ett lån/gratis"""
    if isinstance(fee_value, (int, float)):
        # Formaterar med mellanslag som tusentalsavskiljare
        formatted_number = "{:,}".format(fee_value).replace(",", " ")
        return f"€ {formatted_number}"
    # Om de är en "on loan" eller "free transfer"
    elif is_fee and isinstance(fee_value, str):
        translations = {
            "on loan": "On loan",
            "free transfer": "Free transfer",
            "fee": "Undisclosed fee"
        }
        return translations.get(fee_value.lower(), fee_value.capitalize())
    
    return "Unknown"


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
            raw_fee = t.get("fee")

            if raw_fee:
                raw_value = raw_fee.get("value") or raw_fee.get("feeText", "Unknown fee")
            else:
                raw_value = "Unknown fee"

            raw_market_value = t.get("marketValue")

            clean_transfers.append({
                "search_name": normalize_name(t.get("name", "")),
                "display_name": t.get("name", ""), 
                "from": t.get("fromClub", "Unknown"),
                "to": t.get("toClub", "Unknown"),
                "fee": format_fee(raw_value, is_fee = True),
                "market_value": format_fee(raw_market_value) if raw_market_value else "Unknown"
            })
        return clean_transfers
    except Exception as e:
        print(f"Kunde inte hämta transfers - {e}")
        return []


def send_telegram(t):
    """Skickar notisen t telegram"""
    msg = (
        f"🚨 <b>TRANSFER!</b> 🚨 \n\n"
        f"⚽ <b>{t['display_name']}</b>\n"
        f"➡️ From: {t['from']}\n"
        f"⬅️ To: {t['to']}\n"
        f"💰 {t['fee']}\n"
        f"📈 Market Value: {t['market_value']}"
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
        if t["search_name"] in watchlist:
            #kollar både namn och ny klubb
            unique_id = f"{t['search_name']}-{t['to']}"
            
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