import asyncio
import edge_tts
from openai import OpenAI, RateLimitError
import os
from dotenv import load_dotenv
import speech_recognition as sr
from pydub import AudioSegment
from pydub.playback import play
from pydub.generators import Sine
from command import control_device
import sys

# Betölti a `.env` fájl tartalmát környezeti változóként
load_dotenv()

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

VOICES = ['hu-HU-NoemiNeural', 'hu-HU-TamasNeural']
output_file = "response.mp3"

# Hangjelzés generálása hangerő-szabályozással
def play_beep(volume_db: int = 0):
    """
    Beep hang generálása és lejátszása.
    :param volume_db: Hangerő dB-ben, alapértelmezett 0 dB (nincs változtatás).
                      Pozitív érték növeli a hangerőt, negatív csökkenti.
    """
    beep = Sine(1000).to_audio_segment(duration=300)  # 300 ms hosszúságú, 1000 Hz-es hang
    beep = beep + volume_db  # Hangerő módosítása
    play(beep)

# (1) Mikrofon hang rögzítése és ébresztő szó keresése
async def listen_for_wake_word(wake_words: dict) -> str:
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Várok az ébresztőszóra...")
        recognizer.adjust_for_ambient_noise(source)
        try:
            audio = recognizer.listen(source, timeout=60)  # 10 másodperc timeout
            text = recognizer.recognize_google(audio, language="hu-HU")
            print(f"Felismert szöveg: {text}")
            
            # Ellenőrzés minden ébresztőszóra
            for wake_word in wake_words.keys():
                if wake_word.lower() in text.lower():
                    play_beep(volume_db=-30)  # Beep hang lejátszása
                    return wake_word  # Visszaadja az illeszkedő ébresztő szót
            return ""  # Ha egyik sem illeszkedik
        except sr.UnknownValueError:
            print("Nem sikerült felismerni a beszédet.")
            return ""
        except sr.RequestError as e:
            print(f"API hiba történt: {e}")
            return ""
        except sr.WaitTimeoutError:
            print("Időtúllépés az ébresztőszóra várakozás közben.")
            return ""

# (6) ChatGPT kérdés-válasz lekérdezése
def get_chatgpt_response(prompt: str) -> str:
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()
    except RateLimitError as e:
        print("Rate limit error: ", e)
        return "Az API kvótája kimerült. Kérjük, ellenőrizze a fiókját."

# Mikrofon hang rögzítése
def get_audio_input() -> str:
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Beszélj most...")
        try:
            audio = recognizer.listen(source, timeout=60)  # 10 másodperces timeout
            return recognizer.recognize_google(audio, language="hu-HU")
        except sr.UnknownValueError:
            print("Nem sikerült felismerni a beszédet.")
            return ""
        except sr.RequestError as e:
            print(f"API hiba történt: {e}")
            return ""
        except sr.WaitTimeoutError:
            print("Időtúllépés beszéd rögzítés közben.")
            return ""

# (4) TTS generálása és MP3 fájl mentése
async def generate_speech_from_text_to_file(text: str, voice: str, output_file: str):
    communicate = edge_tts.Communicate(text, voice)
    print("Hang generálása folyamatban...")

    await communicate.save(output_file)
    print(f"Saved {output_file}")

# (5) Szöveg átalakítása hanggá és lejátszása
async def handle_audio_response(response_text):
    try:
        await generate_speech_from_text_to_file(response_text, VOICES[1], output_file)
        
        # MP3 fájl betöltése
        audio = AudioSegment.from_file(output_file)
        try:
            # Lejátszás
            play(audio)
        finally:
            if os.path.exists(output_file):
                # mp3 fájl törlése
                os.remove(output_file)
                print(f"A '{output_file}' fájl törölve lett.")
    except TypeError as e:
        print(f"Hiba: A szöveg típusa nem megfelelő ({e}).")
    except Exception as e:
        print(f"Ismeretlen hiba történt a hanggenerálás során: {e}")

# (3) Eszközvezérlés feldolgozása
async def handle_device_command():
    print("Kérem, mondja el az eszközhöz kapcsolódó parancsot...")
    device_command = get_audio_input()
    if not device_command:
        print("Nem sikerült felismerni az eszközparancsot.")
        return

    try:
        HA_response = control_device(device_command)
        await handle_audio_response(HA_response)
    except Exception as e:
        print(f"Hiba történt az eszköz vezérlése közben: {e}")
        await handle_audio_response("Hiba történt a parancs végrehajtása közben.")

# (2) ChatGPT kérdés feldolgozása
async def handle_gpt_question():
    print("Kérem, mondja el a kérdést a GPT számára...")
    gpt_question = get_audio_input()
    if not gpt_question:
        print("Nem sikerült felismerni a kérdést.")
        return

    try:
        chatgpt_response = get_chatgpt_response(gpt_question)
        print(f"ChatGPT válasz: {chatgpt_response}")
        await handle_audio_response(chatgpt_response)
    except Exception as e:
        print(f"Hiba történt a kérdés feldolgozása közben: {e}")
        await handle_audio_response("Hiba történt a kérdés feldolgozása közben.")

# (7) Fő program
async def main():
    # Ébresztőszavak és a hozzájuk tartozó logika
    wake_words = {
        "Eszköz": handle_device_command,
        "Kérdés": handle_gpt_question,
        "Kilépés": lambda: sys.exit()
    }

    while True:
        # (1) Várakozás az ébresztőszóra
        wake_word = await listen_for_wake_word(wake_words)
        if wake_word:
            print(f"Parancsszó '{wake_word}' felismerve!")
            # Meghívja a megfelelő handler függvényt
            await wake_words[wake_word]()

if __name__ == "__main__":
    asyncio.run(main())
