import random
from typing import Dict

# Browser Fingerprint profiles (Chrome, Firefox, Edge, Safari)
BROWSER_USER_AGENTS = [
    # Chrome 120 - Windows
    {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "sec_ch_ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "platform": '"Windows"',
        "mobile": "?0"
    },
    # Chrome 121 - macOS
    {
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "sec_ch_ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
        "platform": '"macOS"',
        "mobile": "?0"
    },
    # Firefox 121 - Windows
    {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "sec_ch_ua": None,
        "platform": None,
        "mobile": None
    },
    # Edge 120 - Windows
    {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "sec_ch_ua": '"Not_A Brand";v="8", "Chromium";v="120", "Microsoft Edge";v="120"',
        "platform": '"Windows"',
        "mobile": "?0"
    },
    # Safari 17 - macOS
    {
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "sec_ch_ua": None,
        "platform": None,
        "mobile": None
    }
]

ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9,en-US;q=0.8",
    "en-US,en;q=0.8,de;q=0.6",
    "en-US,en;q=0.9,fr;q=0.7"
]

def get_random_stealth_headers(custom_accept: str = None) -> Dict[str, str]:
    """Generates realistic, synchronized browser HTTP headers for stealth scraping."""
    profile = random.choice(BROWSER_USER_AGENTS)
    headers = {
        "User-Agent": profile["user_agent"],
        "Accept": custom_accept or "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": random.choice(ACCEPT_LANGUAGES),
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1"
    }

    if profile["sec_ch_ua"]:
        headers["Sec-Ch-Ua"] = profile["sec_ch_ua"]
        headers["Sec-Ch-Ua-Mobile"] = profile["mobile"]
        headers["Sec-Ch-Ua-Platform"] = profile["platform"]

    return headers
