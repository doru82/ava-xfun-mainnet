import os
import re
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ========================================
# CONFIGURATION
# ========================================

XAI_API_KEY = os.getenv("XAI_API_KEY", "")
TYPEFULLY_API_KEY = os.getenv("TYPEFULLY_API_KEY", "")

# Social set ID for @AvaxLauncher
SOCIAL_SET_ID = "276434"

# Hard safety buffer for X weighted length (emoji/newlines can count weird)
X_SAFE_MAX_CHARS = 240

# ========================================
# FETCH AVAX NEWS & DATA
# ========================================

def get_avax_data():
    """Get AVAX price and market data."""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=avalanche-2&vs_currencies=usd&include_24hr_change=true"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json().get("avalanche-2", {})
            price = data.get("usd", 0)
            change = data.get("usd_24h_change", 0)
            return price, change
        return 0, 0
    except Exception as e:
        print(f"Error fetching AVAX data: {e}")
        return 0, 0


def get_crypto_news():
    """Fetch latest crypto news."""
    try:
        url = "https://cryptopanic.com/api/free/v1/posts/?public=true&filter=important"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            news = []
            for item in data.get("results", [])[:5]:
                news.append(item.get("title", ""))
            return news
        return []
    except Exception as e:
        print(f"Error fetching news: {e}")
        return []


# ========================================
# POST FORMATTING & LIMITS
# ========================================

def enforce_x_limit(text: str, max_len: int = X_SAFE_MAX_CHARS) -> str:
    """
    Hard truncation by Python length. We use a safety buffer (default 240)
    because X uses weighted length for some characters.
    """
    text = text.strip()
    if len(text) <= max_len:
        return text

    truncated = text[:max_len].rstrip()
    if " " in truncated:
        truncated = truncated.rsplit(" ", 1)[0].rstrip()
    return truncated


def force_4_paragraphs(text: str) -> str:
    """
    Ensure EXACTLY 4 short paragraphs, separated by ONE blank line.
    If model returns one block, split by sentences. If still not enough,
    split by commas, then pad with short CTA/footer.
    """
    text = text.replace("\r\n", "\n").strip()

    # split on blank lines first
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    # if only one paragraph, split by sentences
    if len(parts) == 1:
        sentences = re.split(r"(?<=[.!?])\s+", parts[0])
        parts = [s.strip() for s in sentences if s.strip()]

    # if still too few, try splitting long chunks by commas
    def split_by_comma_once(p: str):
        if "," in p:
            a, b = p.split(",", 1)
            return [a.strip(), b.strip()]
        return [p]

    i = 0
    while len(parts) < 4 and i < len(parts):
        if len(parts[i]) > 60 and "," in parts[i]:
            new_parts = split_by_comma_once(parts[i])
            parts = parts[:i] + [x for x in new_parts if x] + parts[i + 1:]
        i += 1

    # take first 4
    parts = [p for p in parts if p][:4]

    # pad if needed (keep it short + required constraints)
    while len(parts) < 4:
        if len(parts) == 0:
            parts.append("GM AVAX.")
        elif len(parts) == 1:
            parts.append("Launch a meme on @avax for 0.15 AVAX.")
        elif len(parts) == 2:
            parts.append("Auto-liquidity on @pangolindex.")
        else:
            parts.append("Try it, avaxfun.net")

    # make sure each paragraph is single-line (compact)
    parts = [re.sub(r"\s+", " ", p).strip() for p in parts]

    return "\n\n".join(parts[:4])


def ensure_required_tokens(text: str) -> str:
    """
    Ensure avaxfun.net and @avax exist at least once.
    Keep additions minimal to avoid breaking the limit.
    """
    out = text

    if "avaxfun.net" not in out.lower():
        out = out + " avaxfun.net"

    # very basic check for @avax tag
    if "@avax" not in out:
        out = out.replace("avaxfun.net", "@avax avaxfun.net", 1)

    return out


# ========================================
# GENERATE POST WITH GROK
# ========================================

def generate_avax_fun_post():
    """Generate post using Grok API."""

    if not XAI_API_KEY:
        raise ValueError("XAI_API_KEY not found!")

    now = datetime.now()
    day_name = now.strftime("%A")

    avax_price, avax_change = get_avax_data()
    news = get_crypto_news()
    news_summary = "\n".join(news[:3]) if news else "No major news today"

    prompt = f"""You are the social media manager for AVAX Fun (@AvaxLauncher), a permissionless memecoin launcher on Avalanche.

ABOUT AVAX FUN:
- Permissionless memecoin launcher on Avalanche
- Only 0.15 AVAX per launch
- Auto-liquidity on Pangolin DEX (@pangolindex)
- Verified factory contract
- Website: avaxfun.net
- Built on @avax

YOUR TASK:
Write ONE engaging daily post.

STYLE RULES:
- Professional but friendly
- Educational + a bit of FOMO
- Ask 1 question
- 1–3 emojis max
- Include a call-to-action
- FORMAT: EXACTLY 4 very short paragraphs (1 sentence each). Separate paragraphs with ONE blank line.
- Keep it SHORT (X non-premium)
- NEVER use em dash (—) or en dash (–)
- MUST include: avaxfun.net
- MUST include: @avax
- Optional: mention @pangolindex when talking liquidity

CONTEXT:
- Today: {day_name}
- Date: {now.strftime("%B %d, %Y")}
- AVAX: ${avax_price:.2f} ({avax_change:+.1f}% 24h)
- News:
{news_summary}

Output ONLY the post text, nothing else. No quotes.
"""

    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "grok-3",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 250,
        "temperature": 0.8
    }

    try:
        response = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code != 200:
            print(f"❌ Grok error: {response.status_code} - {response.text}")
            return None

        data = response.json()
        post = data["choices"][0]["message"]["content"].strip()

        # basic cleanup
        post = post.strip('"').strip("'")
        post = post.replace("—", ",").replace("–", ",")
        post = post.replace("\t", " ").strip()

        # Normalize to paragraphs, then enforce 4-paragraph format
        post = force_4_paragraphs(post)

        # Ensure required tokens (may add a few chars)
        post = ensure_required_tokens(post)

        # Final hard limit (buffered)
        post = enforce_x_limit(post, X_SAFE_MAX_CHARS)

        # If required tokens got trimmed off by enforce, re-add minimally and re-trim
        if "avaxfun.net" not in post.lower() or "@avax" not in post:
            post = ensure_required_tokens(post)
            post = enforce_x_limit(post, X_SAFE_MAX_CHARS)

        print(f"✅ Generated post ({len(post)} chars):\n{post}")
        return post

    except Exception as e:
        print(f"❌ Exception: {e}")
        return None


# ========================================
# TYPEFULLY API
# ========================================

def post_to_typefully(post_text: str) -> bool:
    """Post via Typefully API to @AvaxLauncher account."""

    if not TYPEFULLY_API_KEY:
        raise ValueError("TYPEFULLY_API_KEY not found!")

    headers = {
        "Authorization": f"Bearer {TYPEFULLY_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "platforms": {
            "x": {
                "enabled": True,
                "posts": [{"text": post_text}]
            }
        },
        "publish_at": "now"
    }

    url = f"https://api.typefully.com/v2/social-sets/{SOCIAL_SET_ID}/drafts"

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)

        if response.status_code in [200, 201]:
            print("✅ Post published successfully!")
            return True

        print(f"❌ Error: {response.status_code} - {response.text}")
        return False

    except Exception as e:
        print(f"❌ Exception: {e}")
        return False


# ========================================
# MAIN
# ========================================

def run_avax_fun_bot():
    """Main function."""
    print(f"🔺 AVAX Fun Bot starting at {datetime.now()}\n")

    print("📝 Generating post with Grok...")
    post = generate_avax_fun_post()

    if not post:
        print("❌ Failed to generate post")
        return

    # Extra safety: enforce again right before sending
    post = enforce_x_limit(post, X_SAFE_MAX_CHARS)

    print("\n📤 Posting to X (@AvaxLauncher)...")
    print(f"Post ({len(post)} chars):\n{post}\n")

    success = post_to_typefully(post)

    if success:
        print(f"\n🎉 Post published successfully at {datetime.now()}")
    else:
        print("\n❌ Failed to post")


if __name__ == "__main__":
    if not XAI_API_KEY:
        print("❌ XAI_API_KEY not found!")
        exit(1)
    if not TYPEFULLY_API_KEY:
        print("❌ TYPEFULLY_API_KEY not found!")
        exit(1)

    run_avax_fun_bot()
