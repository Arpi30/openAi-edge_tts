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


def control_device(command):
    if command in commands:
        action_data = commands[command]
        entity_id = action_data["entity_id"]
        action = action_data["action"]
        data = action_data.get("data", {})  # Alapértelmezett üres adat, ha nincs megadva
        message = action_data.get("message", "A művelet végrehajtva.")  # Alapértelmezett üzenet

        # REST API URL összeállítása
        api_url = f"{HA_URL}/api/services/{entity_id.split('.')[0]}/{action}"
        headers = {
            "Authorization": f"Bearer {TOM_API}",
            "Content-Type": "application/json"
        }
        payload = {"entity_id": entity_id, **data}

        # API hívás
        response = requests.post(api_url, headers=headers, json=payload)
        if response.status_code == 200:
            print(f"A(z) '{command}' parancs sikeresen végrehajtva.")
            response_data = response.json()  # JSON választ objektummá alakítjuk
            print(f"Válasz: {response_data}")
            return message
        else:
            print(f"Hiba történt: {response.status_code}, {response.text}")
    else:
        print(f"Ismeretlen parancs: {command}")

#parancsok kilistázása
#print("Elérhető parancsok:", list(commands.keys()))


# Példa használatra
""" voice_command = "kapcsold be a klímát a dolgozó szobában"
control_device(voice_command) """
