"""
automation_commands.py — Automation routine execution handlers.
"""

from __future__ import annotations
import os
import subprocess
import threading
import time
import sqlite3
import requests
import psutil
import logging
import app_launcher
import automation_manager
from voice_assistant import speak_text

logger = logging.getLogger("sage-agent")
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "memory.db")

def load_env_vars():
    agent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root_dir = os.path.abspath(os.path.join(agent_dir, "..", ".."))
    env_path = os.path.join(root_dir, ".env")
    vars = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    vars[k.strip()] = v.strip()
    return vars


def handle_coding_setup(target: str | None, extra: dict) -> str:
    """
    Executes the Coding Setup routine:
    1. Opens VS Code
    2. Opens GitHub
    3. Opens project folder
    4. Starts local development server in a visible cmd window
    """
    speak_text("Initializing your coding setup.")
    
    # Paths resolved dynamically
    agent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root_dir = os.path.abspath(os.path.join(agent_dir, "..", ".."))
    sage_dir = os.path.abspath(os.path.join(agent_dir, "..", "sage"))
    
    # 1. VS Code
    try:
        app_launcher.launch_app("code")
    except Exception:
        pass

    # 2. GitHub
    try:
        app_launcher.open_path("https://github.com")
    except Exception:
        pass

    # 3. Project folder
    try:
        app_launcher.open_path(root_dir)
    except Exception:
        pass

    # 4. Start local development server
    try:
        if os.path.exists(sage_dir):
            subprocess.Popen(
                ["cmd.exe", "/c", "start", "cmd.exe", "/k", "pnpm run dev"],
                cwd=sage_dir,
                shell=False
            )
    except Exception:
        pass

    return "VS Code, GitHub, and project folder opened; frontend dev server started."


def handle_study_mode(target: str | None, extra: dict) -> str:
    """
    Executes the Study Mode routine:
    1. Suppress notifications (Focus Assist)
    2. Opens local notes page
    3. Starts a 25-minute study timer
    """
    speak_text("Activating study mode. Opening notes, starting timer, and suppressing notifications.")
    
    # 1. Focus Assist
    automation_manager.toggle_focus_assist(True)
    
    # 2. Notes page
    try:
        app_launcher.open_path("http://localhost:5173/notes")
    except Exception:
        pass
        
    # 3. Pomodoro timer (25 minutes)
    automation_manager.start_study_timer(25)
    
    return "Study Mode activated. Focus Assist enabled, notes page opened, and Pomodoro timer set for 25 minutes."


def handle_gaming_mode(target: str | None, extra: dict) -> str:
    """
    Executes the Gaming Mode routine:
    1. Closes resource-heavy work apps (VS Code)
    2. Opens Spotify
    3. Enables Focus Assist to block alerts
    """
    speak_text("Activating gaming mode. Launching Spotify, closing VS Code, and suppressing alerts.")
    
    # 1. Close VS Code processes
    from local_commands.app_commands import handle_close_app
    try:
        handle_close_app("Code.exe", {"display_name": "VS Code"})
    except Exception:
        pass
        
    # 2. Open Spotify
    try:
        app_launcher.launch_app("spotify")
    except Exception:
        pass
        
    # 3. Focus Assist
    automation_manager.toggle_focus_assist(True)
    
    return "Gaming Mode activated. VS Code closed, Spotify opened, and Focus Assist enabled."


def handle_global_news_briefing(target: str | None, extra: dict) -> str:
    """
    Executes the Global News Briefing:
    1. Reads user interests from sqlite memories.
    2. Fetches headlines from saurav.tech or falls back to BBC RSS feed.
    3. Deduplicates headlines.
    4. Calls Ollama (or Cloud Fallback) to summarize the headlines into a news-anchor style briefing.
    5. Stores the context in sqlite memories under 'last_news_briefing' for follow-up questions.
    """
    import xml.etree.ElementTree as ET
    from datetime import datetime
    
    speak_text("Gathering the latest headlines for your briefing.")
    
    # 1. Load user interests from SQLite memories
    categories = ["general", "technology", "business", "science", "sports"]
    interests = []
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM memories")
        rows = cursor.fetchall()
        conn.close()
        
        for key, val in rows:
            content = (str(key) + " " + str(val)).lower()
            if "tech" in content or "coding" in content or "programming" in content:
                interests.append("technology")
            if "business" in content or "finance" in content or "stocks" in content:
                interests.append("business")
            if "science" in content or "space" in content or "physics" in content:
                interests.append("science")
            if "sports" in content or "football" in content or "cricket" in content:
                interests.append("sports")
            if "health" in content or "medicine" in content:
                interests.append("health")
            if "entertainment" in content or "movie" in content or "music" in content:
                interests.append("entertainment")
        
        # Deduplicate
        interests = list(dict.fromkeys(interests))
        if interests:
            # Reorder categories: personalized ones first, general always at index 0
            if "general" not in interests:
                interests = ["general"] + interests
            # Add other default categories not covered
            for cat in categories:
                if cat not in interests:
                    interests.append(cat)
            categories = interests
    except Exception as e:
        logger.error(f"Error loading interests from memories: {e}")

    # 2. Fetch news from saurav.tech
    headlines_by_cat = {}
    
    # helper to check if a category is tech, general, science, sports, business, health, entertainment
    saurav_valid_categories = {"general", "technology", "business", "science", "sports", "health", "entertainment"}
    
    for cat in categories:
        if cat not in saurav_valid_categories:
            continue
        try:
            url = f"https://saurav.tech/NewsAPI/top-headlines/category/{cat}/us.json"
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                articles = data.get("articles", [])
                titles = []
                for a in articles[:5]: # Take top 5
                    title = a.get("title")
                    if title and title not in titles:
                        titles.append(title)
                if titles:
                    headlines_by_cat[cat] = titles
            else:
                logger.warning(f"Saurav API returned code {res.status_code} for {cat}")
        except Exception as e:
            logger.warning(f"Saurav API request failed for {cat}: {e}")

    # RSS Fallback if we failed to fetch headlines from saurav.tech or got no headlines
    if not headlines_by_cat:
        logger.info("Using RSS fallback for headlines...")
        try:
            res = requests.get("http://feeds.bbci.co.uk/news/world/rss.xml", timeout=6)
            if res.status_code == 200:
                root = ET.fromstring(res.content)
                titles = []
                for item in root.findall(".//item")[:15]:
                    title = item.find("title")
                    if title is not None and title.text:
                        titles.append(title.text.strip())
                if titles:
                    headlines_by_cat["general"] = titles
            else:
                logger.warning(f"BBC RSS returned status code {res.status_code}")
        except Exception as e:
            logger.error(f"RSS fallback failed: {e}")

    # If still empty, return offline message
    if not headlines_by_cat:
        speak_text("I cannot retrieve the news right now. Please verify your internet connection, Sam.")
        return "Offline. Failed to retrieve news headlines."

    # Format the headlines list for the LLM
    headlines_text = ""
    for cat, titles in headlines_by_cat.items():
        cat_name = cat.capitalize()
        headlines_text += f"\nCategory: {cat_name}\n"
        for t in titles:
            headlines_text += f"- {t}\n"

    # 3. Determine greeting based on local time
    hour = datetime.now().hour
    if hour < 12:
        greeting = "morning"
    elif hour < 18:
        greeting = "afternoon"
    else:
        greeting = "evening"

    # Construct the Prompt
    prompt = (
        "You are a personal news anchor. Summarize the following news headlines into a clean, spoken global briefing. "
        "Remove duplicates and group them by category. Do not speak like a search engine. Act as a premium personal developer assistant. "
        "Structure the output exactly like this:\n\n"
        f"Good {greeting}, Sam.\n\n"
        "Here is your global briefing.\n\n"
        "World:\n"
        "[summarized world news bullet points]\n\n"
        "Technology:\n"
        "[summarized technology news bullet points]\n\n"
        "Business:\n"
        "[summarized business news bullet points]\n\n"
        "[Include other active categories from below as needed]\n\n"
        "That concludes your briefing."
        "\n\nHere are the headlines to summarize:\n"
        f"{headlines_text}"
    )

    # 4. Invoke LLM: Try Local Ollama first
    summary = None
    env_vars = load_env_vars()
    
    # Check if Ollama is running
    ollama_running = False
    try:
        ollama_res = requests.get("http://localhost:11434/api/tags", timeout=2)
        ollama_running = (ollama_res.status_code == 200)
    except Exception:
        pass

    if ollama_running:
        try:
            logger.info("Summarizing news briefing locally using Ollama...")
            model = "qwen3:4b"
            # Get system info to check memory status
            try:
                mem = psutil.virtual_memory()
                free_gb = mem.available / 1e9
                if free_gb < 1.5:
                    model = "phi3:mini"
            except Exception:
                pass
                
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {
                    "keep_alive": "5m"
                }
            }
            res = requests.post("http://localhost:11434/api/chat", json=payload, timeout=30)
            if res.status_code == 200:
                summary = res.json().get("message", {}).get("content")
        except Exception as e:
            logger.error(f"Local Ollama news summarization failed: {e}")

    # 5. Cloud Fallback if local Ollama failed or not running
    if not summary:
        # Check Groq
        groq_api_key = env_vars.get("GROQ_API_KEY")
        if groq_api_key:
            try:
                logger.info("Summarizing news briefing using Groq Cloud API...")
                headers = {
                    "Authorization": f"Bearer {groq_api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "llama3-8b-8192",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.5
                }
                res = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=15)
                if res.status_code == 200:
                    summary = res.json().get("choices", [{}])[0].get("message", {}).get("content")
            except Exception as e:
                logger.error(f"Groq Cloud news summarization failed: {e}")

    if not summary:
        # Fallback to Gemini
        gemini_api_key = env_vars.get("GEMINI_API_KEY")
        if gemini_api_key:
            try:
                logger.info("Summarizing news briefing using Gemini Cloud API...")
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_api_key}"
                payload = {
                    "contents": [{
                        "parts": [{"text": prompt}]
                    }]
                }
                res = requests.post(url, json=payload, timeout=15)
                if res.status_code == 200:
                    summary = res.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text")
            except Exception as e:
                logger.error(f"Gemini Cloud news summarization failed: {e}")

    # Ultimate fallback if all LLMs failed
    if not summary:
        logger.warning("All LLM summarizations failed. Constructing basic summary.")
        summary = f"Good {greeting}, Sam.\n\nHere is your global briefing.\n"
        for cat, titles in headlines_by_cat.items():
            summary += f"\n{cat.capitalize()}:\n"
            for t in titles[:3]:
                summary += f"- {t}\n"
        summary += "\nThat concludes your briefing."

    # 6. Store news briefing context under key 'last_news_briefing' in sqlite memories
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO memories (key, value) VALUES (?, ?)",
            ("last_news_briefing", summary)
        )
        conn.commit()
        conn.close()
        logger.info("News briefing context saved to SQLite memories for follow-up.")
    except Exception as e:
        logger.error(f"Failed to save briefing context to SQLite: {e}")

    speak_text(summary)
    return summary
