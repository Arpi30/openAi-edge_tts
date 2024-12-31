import json
import os
import requests
from dotenv import load_dotenv

# .env fájl betöltése
load_dotenv()

# Környezeti változók beolvasása
TOM_API = os.getenv("TOM_API")
HA_URL = os.getenv("HA_URL")

#JSON fájl beolvasása
with open("commands.json", "r", encoding="utf-8") as com:
  commands = json.load(com)

def get_nested_value(data, path):
    keys = path.split(".")
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key)
        else:
            return None  # Ha nem létezik az útvonal
    return data



def control_device(command):
    if command in commands:
        action_data = commands[command]
        entity_id = action_data["entity_id"]
        action = action_data["action"]
        data = action_data.get("data", {})  # Alapértelmezett üres adat, ha nincs megadva
        message = action_data.get("message", "A művelet végrehajtva.")  # Alapértelmezett üzenet
        method = action_data["method"]
        additional_data_list = action_data.get("additional_data", [])

        # REST API URL összeállítása
        api_url = f"{HA_URL}/api/services/{entity_id.split('.')[0]}/{action}"
        headers = {
            "Authorization": f"Bearer {TOM_API}",
            "Content-Type": "application/json"
        }
        payload = {"entity_id": entity_id, **data}

       
        try:
            # Get beágyazott kérésekre
            for additional_data in additional_data_list:
                if additional_data.get("type") == "get":
                    additional_url = f"{HA_URL}{additional_data['url']}"
                    get_response = requests.get(additional_url, headers=headers)
                    if get_response.status_code == 200:
                        # A JSON válaszból az adatok kinyerése
                        get_data = get_response.json()
                        keys = additional_data["data_keys"]
                        dynamic_data = {
                            key: get_nested_value(get_data, path)
                            for key, path in keys.items()
                        }
                        # Az üzenet bővítése a válasz adataival
                        message += additional_data["message_template"].format(**dynamic_data)
                    else:
                        error_message = f"Hiba történt a GET kérésnél: {get_response.status_code}, {get_response.text}"
                        print(error_message)
                        message += f"\n[Hiba a GET kéréssel: {error_message}]"

            # HTTP metódus validálása és meghívása
            allowed_methods = ["get", "post", "put", "delete", "patch"]
            if method.lower() not in allowed_methods:
                raise ValueError(f"Ismeretlen vagy nem támogatott HTTP metódus: {method}")

            # API hívás dinamikusan a megfelelő HTTP metódus szerint
            # POST metódus végrehajtása
            # A requests modul megfelelő metódusának meghívása (pl. post, get, stb.)
            request_method = getattr(requests, method.lower(), None)
            if request_method is None:
                raise ValueError(f"Ismeretlen HTTP metódus: {method}")

            response = request_method(api_url, headers=headers, json=payload)
            if response.status_code == 200:
                print(f"A(z) '{command}' parancs sikeresen végrehajtva.")
                response_data = response.json()  # JSON választ objektummá alakítjuk
                print(f"Válasz: {response_data}")
                return message
            else:
                error_message = f"Hiba történt: {response.status_code}, {response.text}"
                print(error_message)
                return f"Hiba történt a(z) '{command}' parancs végrehajtásakor: {error_message}"
        except Exception as e:
            print(f"API hívás sikertelen: {e}")
    else:
        print(f"Ismeretlen parancs: {command}")

#parancsok kilistázása
#print("Elérhető parancsok:", list(commands.keys()))