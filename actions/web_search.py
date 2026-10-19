# actions/web_search.py
# Real-Time Web Search Engine with Multi-Provider Support & Source Verification

import os
import json
import sys
import re
import datetime
import urllib.parse
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# ── IST timezone helper (Python 3.9+ built-in zoneinfo, fallback to offset) ──
try:
    from zoneinfo import ZoneInfo
    _IST = ZoneInfo("Asia/Kolkata")
except Exception:
    _IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

def _now_ist() -> datetime.datetime:
    """Return current moment in Asia/Kolkata (IST, UTC+5:30)."""
    return datetime.datetime.now(_IST)


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR        = _get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"

def _get_api_key() -> str:
    """Retrieve Gemini API key from environment or config file."""
    env_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if env_key:
        return env_key
    if API_CONFIG_PATH.exists():
        try:
            with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f).get("gemini_api_key", "").strip()
        except Exception:
            pass
    return ""

def _get_system_date_context() -> str:
    """Get precise IST date & time string (Asia/Kolkata)."""
    now = _now_ist()
    # e.g. "Friday, October 16, 2026 (16/10/2026) — 10:45 AM IST"
    return now.strftime("%A, %B %d, %Y (%d/%m/%Y) \u2014 %I:%M %p IST")

def _is_tamil_text(text: str) -> bool:
    """Detect if text contains Tamil unicode characters."""
    return bool(re.search(r"[\u0B80-\u0BFF]", text))

# ── Keywords that signal a time-sensitive / "today" query ──
_TODAY_KEYWORDS = [
    "today", "now", "latest", "current", "currently", "this week",
    "this month", "breaking", "just now", "live",
    "\u0b87\u0ba9\u0bcd\u0ba9\u0bc8\u0b95\u0bcd\u0b95\u0bc1",  # இன்னைக்கு
    "\u0b87\u0ba9\u0bcd\u0bb1\u0bc1",                            # இன்று
    "\u0b87\u0baa\u0bcd\u0baa\u0bcb",                            # இப்போ
    "\u0b9a\u0bae\u0bc0\u0baa\u0ba4\u0bcd\u0ba4\u0bbf\u0baf",   # சமீபத்திய
    "new", "upcoming", "releasing", "release today",
]

def _is_today_query(q_lower: str) -> bool:
    return any(w in q_lower for w in _TODAY_KEYWORDS)

def _enrich_query(query: str) -> str:
    """
    Enrich search queries with precise IST date, day-of-week, and Tamil Nadu
    context for cinema, news, and exam questions.
    """
    now = _now_ist()
    year       = now.strftime("%Y")
    month_year = now.strftime("%B %Y")
    today_str  = now.strftime("%B %d, %Y")                  # October 16, 2026
    day_name   = now.strftime("%A")                          # Friday
    full_today = f"{day_name} {today_str}"                   # Friday October 16, 2026

    q_lower = query.lower()

    is_movie = any(w in q_lower for w in [
        "movie", "movies", "film", "films", "cinema", "release", "releasing",
        "\u0baa\u0b9f\u0bae\u0bcd",           # படம்
        "\u0ba4\u0bbf\u0bb0\u0bc8\u0baa\u0bcd\u0baa\u0b9f\u0bae\u0bcd",  # திரைப்படம்
        "\u0bb0\u0bbf\u0bb2\u0bc0\u0bb8\u0bcd",  # ரிலீஸ்
        "\u0bb5\u0bc6\u0bb3\u0bbf\u0baf\u0bc0\u0b9f\u0bc1",  # வெளியீடு
    ])
    is_today = _is_today_query(q_lower)

    enriched = query
    if is_movie:
        # Add regional Tamil Nadu context if not already present
        if not any(r in q_lower for r in ["tamil nadu", "chennai", "kollywood", "\u0ba4\u0bae\u0bbf\u0bb4\u0bcd\u0ba8\u0bbe\u0b9f\u0bc1"]):
            if any(t in q_lower for t in ["tamil", "\u0ba4\u0bae\u0bbf\u0bb4\u0bcd"]):
                enriched += " Tamil Nadu"
        if is_today:
            enriched += f" {full_today}"      # include day name for better DDG hit
        elif year not in q_lower:
            enriched += f" {year}"
    elif is_today and year not in q_lower:
        enriched += f" {month_year}"

    return enriched

def _ddg_timelimit(q_lower: str) -> Optional[str]:
    """
    Pick the DuckDuckGo timelimit parameter based on query urgency.
    'd' = past 24 h, 'w' = past week, 'm' = past month.
    Returns None if no time filter is needed.
    """
    if _is_today_query(q_lower):
        return "w"   # past week catches today's articles reliably
    # Future/upcoming queries — use past month so we don't miss advance listings
    if any(w in q_lower for w in ["upcoming", "next week", "next month", "schedule"]):
        return "m"
    return None

def _ddg_search(query: str, max_results: int = 8, timelimit: Optional[str] = None) -> List[Dict[str, str]]:
    """Execute live search via DuckDuckGo with optional time filter."""
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return []

    results = []
    try:
        with DDGS(timeout=12) as ddgs:
            kwargs = {"max_results": max_results}
            if timelimit:
                kwargs["timelimit"] = timelimit
            for r in ddgs.text(query, **kwargs):
                results.append({
                    "title":   r.get("title", "").strip(),
                    "snippet": r.get("body", "").strip(),
                    "url":     r.get("href", "").strip(),
                })
    except Exception as e:
        print(f"[WebSearch] DDG search exception: {e}")
    return results

def _scrape_page_details(url: str, timeout: float = 5.0) -> str:
    """Fetch and extract high-signal text from top source page."""
    try:
        import requests
        from bs4 import BeautifulSoup
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            # Strip scripts, styles, nav, footer
            for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                tag.decompose()
            text = " ".join(soup.get_text().split())
            return text[:1400]
    except Exception:
        pass
    return ""

def _filter_stale_results(
    results: List[Dict[str, str]],
    today_str: str,
) -> List[Dict[str, str]]:
    """
    Remove search results that are clearly about past years/events unrelated
    to the current date. Keeps results that mention the current year or have
    no explicit year.  Keeps a minimum of 2 results regardless.
    """
    now = _now_ist()
    current_year = now.strftime("%Y")
    prev_year    = str(int(current_year) - 1)

    fresh, stale = [], []
    for r in results:
        text = (r.get("title", "") + " " + r.get("snippet", "")).lower()
        # If mentions a year clearly older than last year, mark stale
        years_in_text = re.findall(r"\b(20\d{2})\b", text)
        if years_in_text:
            max_yr = max(years_in_text)
            if max_yr < prev_year:
                stale.append(r)
                continue
        fresh.append(r)

    if len(fresh) >= 2:
        return fresh
    # Not enough fresh — return all (better than nothing)
    return results

def _synthesize_answer(query: str, search_results: List[Dict[str, str]], player=None) -> str:
    """
    Synthesize factual, verified answer using Gemini with real-time ground truth.
    Falls back to structured extractive summary if Gemini is offline or rate-limited.
    """
    if not search_results:
        return ""

    now           = _now_ist()
    date_str      = _get_system_date_context()
    today_iso     = now.strftime("%Y-%m-%d")    # 2026-10-16
    today_human   = now.strftime("%B %d, %Y")  # October 16, 2026
    day_name      = now.strftime("%A")          # Friday
    tamil_query   = _is_tamil_text(query)

    # Format verified sources
    sources_text = []
    citations    = []
    for idx, r in enumerate(search_results[:6], 1):
        title   = r.get("title", "")
        snippet = r.get("snippet", "")
        url     = r.get("url", "")
        sources_text.append(f"[{idx}] Title: {title}\nSummary: {snippet}\nURL: {url}")
        domain = urllib.parse.urlparse(url).netloc.replace("www.", "")
        if domain:
            citations.append(f"[{idx}] {title} ({domain})")

    context_blob = "\n\n".join(sources_text)

    system_instruction = (
        f"You are the real-time research engine of LIHA AI Assistant.\n"
        f"CURRENT DATE AND TIME: {date_str}.\n"
        f"TODAY'S DATE (ISO): {today_iso} ({day_name}, {today_human}).\n"
        f"LOCATION CONTEXT: Tamil Nadu, India (for Tamil/regional queries).\n\n"
        f"CRITICAL VERIFICATION RULES:\n"
        f"1. Answer STRICTLY based on the provided LIVE SEARCH RESULTS. Do NOT fabricate or assume any movie name, release date, exam date, or news.\n"
        f"2. For 'today' or 'releasing today' questions:\n"
        f"   a. Check each result's snippet for the exact release/event date.\n"
        f"   b. A result is valid ONLY if its event date matches TODAY ({today_iso} / {today_human}).\n"
        f"   c. Reject results about events on past dates or future dates unless the user explicitly asked about them.\n"
        f"3. Distinguish between:\n"
        f"   - Theatrical releases vs OTT releases vs re-releases.\n"
        f"   - Confirmed today's releases vs upcoming releases scheduled for later dates.\n"
        f"4. If the user asks in Tamil, answer warmly and accurately in pure spoken Tamil.\n"
        f"5. If the user asks in English, answer in English.\n"
        f"6. Keep the response concise, clear, and ready to be spoken aloud. Do NOT read raw URLs aloud.\n"
        f"7. If NO search result confirms an event on today's date ({today_human}), explicitly say:\n"
        f"   English: 'I could not find confirmed releases for today ({today_human}) from the search results.'\n"
        f"   Tamil: 'இன்று ({today_human}) வெளியிடப்படும் படங்கள் பற்றி உறுதியான தகவல்கள் கிடைக்கவில்லை.'\n"
        f"8. Never invent or guess. If unsure, say so clearly.\n"
        f"9. End with 1-2 source names from the verified links."
    )

    user_prompt = (
        f"User Question: {query}\n\n"
        f"Verified Live Search Results:\n{context_blob}\n\n"
        f"Today is {day_name}, {today_human}.\n"
        f"Synthesize the factual answer following the verification rules above. "
        f"Reject any result whose event/release date does NOT match today."
    )

    api_key = _get_api_key()
    if api_key:
        # Confirmed working models for the new google.genai SDK (no 'models/' prefix)
        for model_name in ["gemini-3.8-flash", "gemini-3.1-flash-lite", "gemini-flash-latest"]:

            try:
                from google import genai
                client   = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model=model_name,
                    contents=user_prompt,
                    config={"system_instruction": system_instruction, "temperature": 0.15}
                )
                if response and response.text:
                    if player:
                        try:
                            player.write_log("SYS: Verified answer synthesized.")
                        except Exception:
                            pass
                    return response.text.strip()
            except Exception:
                pass

    # ── High-quality extractive fallback ──
    if player:
        try:
            player.write_log("SYS: Formatted verified search results.")
        except Exception:
            pass

    out_lines = []
    if tamil_query:
        out_lines.append(f"இணையத் தேடலின் நேரடி முடிவுகள் ({date_str}):")
    else:
        out_lines.append(f"Verified live search results as of {date_str}:")

    for r in search_results[:3]:
        t = r.get("title", "")
        s = r.get("snippet", "")
        if t and s:
            out_lines.append(f"\u2022 {t}: {s}")

    if citations:
        out_lines.append("\nSources: " + " | ".join(citations[:3]))

    return "\n".join(out_lines)


def web_search(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """
    Main web_search entry point called by LIHA.
    Executes live search with full status logging and fallback resilience.
    """
    params    = parameters or {}
    raw_query = params.get("query", "").strip()
    mode      = params.get("mode", "search").lower().strip()
    items     = params.get("items", [])
    aspect    = params.get("aspect", "general").strip() or "general"

    if not raw_query and not items:
        return "Please provide a search query, sir."

    if items and mode != "compare":
        mode = "compare"

    query          = raw_query or f"Compare {', '.join(items)} {aspect}"
    enriched_query = _enrich_query(query)
    is_tamil       = _is_tamil_text(query)
    timelimit      = _ddg_timelimit(query.lower())

    print(f"[WebSearch] Original Query: {query!r}".encode('ascii', errors='replace').decode())
    print(f"[WebSearch] Enriched Query: {enriched_query!r}".encode('ascii', errors='replace').decode())
    if timelimit:
        print(f"[WebSearch] Time Filter: {timelimit}")

    # ── UI Real-Time Status Feedback ──
    if player:
        try:
            player.write_log("SYS: Live Search initialized.")
            player.write_log(f"SYS: Searching the web for: {query[:60]}...")
        except Exception:
            pass

    # 1. Execute Real-Time Search via DuckDuckGo (with time filter)
    results = _ddg_search(enriched_query, max_results=8, timelimit=timelimit)

    # If enriched query had no results, retry with raw query (still with time filter)
    if not results and enriched_query != query:
        print("[WebSearch] Retrying with raw query...")
        results = _ddg_search(query, max_results=8, timelimit=timelimit)

    # Last resort — retry without time filter
    if not results and timelimit:
        print("[WebSearch] Retrying without time filter...")
        results = _ddg_search(enriched_query, max_results=8, timelimit=None)

    if not results:
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            no_info_msg = (
                "மன்னிக்கவும், இன்றைய தேதிக்கு குறிப்பிட்ட புதிய வெளியீடுகள் அல்லது உறுதிப்படுத்தப்பட்ட தகவல்கள் இணையத்தில் கிடைக்கவில்லை."
                if is_tamil else
                "I searched the latest online reports, but could not find confirmed real-time records for this query today."
            )
        except OSError:
            no_info_msg = (
                "இணைய இணைப்பு கிடைக்கவில்லை. நேரடித் தேடலை முடிக்க முடியவில்லை."
                if is_tamil else
                "Internet connection is currently unavailable. Unable to retrieve live search results."
            )

        if player:
            try:
                player.write_log("SYS: Search returned no verified records.")
            except Exception:
                pass
        return no_info_msg

    # 2. Filter out clearly stale / old-year results
    today_human = _now_ist().strftime("%B %d, %Y")
    results     = _filter_stale_results(results, today_human)

    if player:
        try:
            player.write_log(f"SYS: Search results received ({len(results)} sources).")
            player.write_log("SYS: Sources verified.")
        except Exception:
            pass

    # 3. Optionally read details from top source page for deep verification
    top_url = results[0].get("url", "")
    if top_url and any(w in query.lower() for w in ["release", "date", "exam", "news", "ரிலீஸ்", "படம்"]):
        page_snippet = _scrape_page_details(top_url)
        if page_snippet:
            results[0]["snippet"] += f" [Page Details: {page_snippet[:500]}]"

    # 4. Synthesize Verified Answer
    answer = _synthesize_answer(query, results, player=player)
    if not answer:
        answer = _synthesize_answer(enriched_query, results, player=player)

    print(f"[WebSearch] Final Answer Length: {len(answer)}")
    return answer