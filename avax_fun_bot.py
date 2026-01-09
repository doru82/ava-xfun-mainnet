import os
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
# GENERATE POST WITH GROK
# ========================================

def generate_avax_fun_post():
    """Generate post using Grok API."""
    
    if not XAI_API_KEY:
        raise ValueError("XAI_API_KEY not found!")
    
    # Get current context
    now = datetime.now()
    day_name = now.strftime("%A")
    
    # Get AVAX data
    avax_price, avax_change = get_avax_data()
    news = get_crypto_news()
    news_summary = "\n".join(news[:3]) if news else "No major news today"
    
    prompt = f"""You are the social media manager for AVAX Fun (@AvaxLauncher), a permissionless memecoin launcher on Avalanche.

ABOUT AVAX FUN:
- Permissionless memecoin launcher on Avalanche
- Only 0.15 AVAX per launch (very cheap!)
- Auto-liquidity on Pangolin DEX (@pangolindex)
- Verified factory contract
- Website: avaxfun.net
- Built on @avax (Avalanche blockchain)

YOUR TASK:
Write an engaging daily post that attracts the AVAX community. The post should:

STYLE RULES:
- Professional but friendly tone (not too corporate, not too casual)
- Educational and informative
- Highlight benefits of launching on AVAX Fun
- Create FOMO or excitement about memecoins
- Ask questions to encourage engagement
- Use some emojis but don't overdo it (3-5 max)
- Include a call-to-action
- LENGTH: 4-6 sentences, medium length post
- ALWAYS mention the website: avaxfun.net
- ALWAYS tag @avax somewhere in the post
- Can mention @pangolindex when talking about liquidity

POST THEMES TO ROTATE (pick one):
1. Why launch your memecoin on Avalanche vs other chains (speed, low fees)
2. How easy it is to launch (only 0.15 AVAX, takes seconds)
3. The power of auto-liquidity on Pangolin
4. Memecoin culture and community building
5. Success stories / potential of memecoins
6. Tutorial-style: "Did you know you can..."
7. Market commentary + how AVAX Fun fits in
8. Community questions: "What memecoin would you launch?"

CURRENT CONTEXT:
- Today is: {day_name}
- Date: {now.strftime("%B %d, %Y")}
- AVAX Price: ${avax_price:.2f} ({avax_change:+.1f}% 24h)
- Recent crypto news: {news_summary}

Write ONE engaging post. Output ONLY the post text, nothing else. No quotes around it."""

    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "grok-2-1212",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 400,
        "temperature": 0.8
    }
    
    try:
        response = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            post = data["choices"][0]["message"]["content"].strip()
            # Clean up any quotes if AI added them
            post = post.strip('"').strip("'")
            print(f"✅ Generated post:\n{post}")
            return post
        else:
            print(f"❌ Grok error: {response.status_code} - {response.text}")
            return None
            
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
        else:
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
    
    # 1. Generate post
    print("📝 Generating post with Grok...")
    post = generate_avax_fun_post()
    
    if not post:
        print("❌ Failed to generate post")
        return
    
    # 2. Post to X
    print("\n📤 Posting to X (@AvaxLauncher)...")
    print(f"Post:\n{post}\n")
    
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
