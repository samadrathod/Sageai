"""
voice_assistant.py — Continuous voice recognition and Text-to-Speech loop.
"""

from __future__ import annotations

import logging
import time
import threading
import json
import re
import requests
import speech_recognition as sr
import pyttsx3
import winsound

logger = logging.getLogger("sage-agent")

API_BASE = "http://localhost:5000/api"

# Helper for cyber chimes on Windows
def play_chime():
    try:
        winsound.Beep(900, 80)
        winsound.Beep(1300, 100)
    except Exception as e:
        logger.debug(f"Could not play win chime: {e}")


def play_confirm_chime():
    try:
        winsound.Beep(1200, 60)
        winsound.Beep(1500, 80)
    except Exception as e:
        logger.debug(f"Could not play win chime: {e}")


def speak_text(text: str):
    """Speak text using Windows SAPI5 TTS offline."""
    logger.info(f"TTS: {text}")
    try:
        engine = pyttsx3.init()
        engine.setProperty("rate", 190)
        voices = engine.getProperty("voices")
        for voice in voices:
            if "en" in voice.languages or "english" in voice.name.lower():
                engine.setProperty("voice", voice.id)
                break
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        logger.error(f"TTS Engine error: {e}")


def speak_to_gemini(message: str):
    """Sends the voice query to the Express backend and speaks the result."""
    try:
        # 1. Fetch conversations to find active session
        res = requests.get(f"{API_BASE}/gemini/conversations", timeout=4)
        convo_id = None
        if res.status_code == 200:
            convos = res.json()
            if convos:
                convo_id = convos[0]["id"]

        # Create one if missing
        if convo_id is None:
            res = requests.post(
                f"{API_BASE}/gemini/conversations",
                json={"title": "Voice Session"},
                timeout=4
            )
            if res.status_code == 201:
                convo_id = res.json()["id"]
            else:
                speak_text("I failed to initiate a new dialogue session.")
                return

        # 2. Post the message and parse streamed chunks
        url = f"{API_BASE}/gemini/conversations/{convo_id}/messages"
        payload = {"content": message}
        headers = {"Content-Type": "application/json"}

        logger.info(f"Relaying voice query to Gemini via Express (Session {convo_id})...")
        response_text = ""

        with requests.post(url, json=payload, headers=headers, stream=True, timeout=20) as r:
            if r.status_code != 200:
                speak_text("The SAGE core server returned an error.")
                return

            for line in r.iter_lines():
                if line:
                    decoded = line.decode("utf-8").strip()
                    if decoded.startswith("data: "):
                        data_str = decoded[6:]
                        try:
                            data = json.loads(data_str)
                            if data.get("done"):
                                break
                            if data.get("content"):
                                response_text += data["content"]
                        except json.JSONDecodeError:
                            pass

        if response_text:
            # Clean markdown artifacts from speech text
            clean_speech = response_text.replace("*", "").replace("`", "").strip()
            speak_text(clean_speech)
        else:
            speak_text("I received no response from the SAGE model.")

    except requests.exceptions.ConnectionError:
        logger.error("Could not connect to SAGE Express server.")
        speak_text("I cannot connect to the SAGE core API server. Please verify it is running on port 5000.")
    except Exception as e:
        logger.error(f"Voice query relay failed: {e}")
        speak_text("An error occurred while communicating with the assistant core.")


def save_message_to_db(user_msg: str, assistant_res: str):
    """Saves the user command and assistant response in the active conversation DB."""
    try:
        # Fetch conversations to find active session
        res = requests.get(f"{API_BASE}/gemini/conversations", timeout=4)
        convo_id = None
        if res.status_code == 200:
            convos = res.json()
            if convos:
                convo_id = convos[0]["id"]

        # Create one if missing
        if convo_id is None:
            res = requests.post(
                f"{API_BASE}/gemini/conversations",
                json={"title": "Voice Session"},
                timeout=4
            )
            if res.status_code == 201:
                convo_id = res.json()["id"]

        if convo_id is not None:
            url = f"{API_BASE}/gemini/conversations/{convo_id}/messages"
            payload = {
                "content": user_msg,
                "localResponse": assistant_res
            }
            headers = {"Content-Type": "application/json"}
            requests.post(url, json=payload, timeout=4)
    except Exception as e:
        logger.warning(f"Failed to persist local voice command: {e}")


def process_command(raw_text: str):
    """Extract commands from wake word strings and execute them."""
    logger.info(f"Heard: '{raw_text}'")

    # Clean the wake word and anything preceding it (e.g. 'Hey SAGE, open...' -> 'open...')
    command = re.sub(r"^.*?\b(hey\s+)?sage\b", "", raw_text, flags=re.I).strip()

    command = command.lstrip(",.!? ")
    if not command:
        play_chime()
        speak_text("Yes? How can I help you?")
        return

    # Trigger action chime
    play_confirm_chime()

    # Route to intent detector
    from intent_detector import detect
    from tool_router import route

    intent = detect(command)
    if intent is not None:
        logger.info(f"Local intent detected: {intent.intent} for target: {intent.target}")
        # Destructive action check
        res = route(intent, confirmed=False)
        if res.get("requires_confirm"):
            speak_text(f"To execute {intent.intent}, please confirm the action on your SAGE dashboard.")
            return

        speak_text(res["response"])
        save_message_to_db(command, res["response"])
        return

    # Fallback to Gemini
    speak_to_gemini(command)


def listen_loop():
    """Main voice loop running in a background thread."""
    r = sr.Recognizer()
    mic = sr.Microphone()

    # Setup sensitivity
    r.dynamic_energy_threshold = True
    r.pause_threshold = 0.8

    logger.info("Calibrating microphone ambient noise...")
    try:
        with mic as source:
            r.adjust_for_ambient_noise(source, duration=1.0)
        logger.info("Microphone calibration complete.")
    except Exception as e:
        logger.error(f"Failed to access microphone: {e}")
        return

    import main  # Dynamic import to fetch main.voice_enabled

    while True:
        if not main.voice_enabled:
            time.sleep(1.0)
            continue

        try:
            logger.debug("Listening for wake word...")
            with mic as source:
                # Capture audio phrase
                audio = r.listen(source, timeout=3.0, phrase_time_limit=8.0)

            # Recognize audio using Google Web STT
            recognized_text = r.recognize_google(audio)
            text_lower = recognized_text.lower()

            # Check for wake word using word boundaries regex to avoid matching substrings (e.g., 'passage')
            if re.search(r"\b(hey\s+)?sage\b", text_lower):
                # Process the spoken wake word
                process_command(recognized_text)

        except sr.WaitTimeoutError:
            # Silence, continue listening
            pass
        except sr.UnknownValueError:
            # Unrecognized audio, continue listening
            pass
        except Exception as e:
            logger.error(f"Voice loop error: {e}")
            time.sleep(1.0)


def start_voice_assistant():
    """Starts the continuous voice listening loop in a background thread."""
    voice_thread = threading.Thread(target=listen_loop, daemon=True)
    voice_thread.start()
    logger.info("SAGE Voice Assistant thread launched.")
