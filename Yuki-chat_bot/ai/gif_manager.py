import random
import time

"""
Send GIFs based on keywords, then roll the probability
of sending that GIF to prevent GIF spam abuse.
"""

# ===== COOLDOWN =====
GIF_COOLDOWN = {}
GIF_COOLDOWN_SECONDS = 90

# ===== CONFIG =====
GIF_CONFIG = {
    "good night": {
        "priority": 6,
        "probability": 1.0,
        "keywords": ["good night", "sleep well", "sweet dreams"],
        "gifs": [
            "https://tenor.com/view/suou-yuki-roshidere-sister-suou-yuki-gif-9340525912127880634"
        ]
    },
    "good morning": {
        "priority": 7,
        "probability": 1.0,
        "keywords": ["good morning", "morning~"],
        "gifs": [
            "https://tenor.com/view/sealyx-alya-sometimes-hides-her-feelings-in-russian-roshidere-gif-6671162755924401044"
        ]
    },
    "wink": {
        "priority": 3,
        "probability": 0.5,
        "keywords": ["wink"],
        "gifs": [
            "https://tenor.com/view/%E9%84%B0%E5%BA%A7%E8%89%BE%E8%8E%89%E5%90%8C%E5%AD%B8-alya-sometimes-hides-her-feelings-in-russian-%E5%91%A8%E9%98%B2%E6%9C%89%E5%B8%8C-suou-yuki-tongue-gif-443975556508281009"
        ]
    },
    "tease": {
        "priority": 4,
        "probability": 0.5,
        "keywords": ["hehe", "fufu", "ara~", "you're cute", "teasing tone", "teasingly"],
        "gifs": [
            "https://tenor.com/view/yuki-gif-15563913965827340070"
        ]
    },
    "smug": {
        "priority": 5,
        "probability": 0.5,
        "keywords": ["smug", "hmph", "obviously", "smirks"],
        "gifs": [
            "https://tenor.com/view/suou-yuki-roshidere-sister-suou-yuki-gif-17357276135117632944",
            "https://tenor.com/view/suou-yuki-roshidere-sister-suou-yuki-gif-17192898929696458608",
            "https://tenor.com/view/alya-sometimes-hides-her-feelings-in-russian-roshidere-anime-girl-cute-gif-16228130656224382773",
            "https://tenor.com/view/suou-yuki-roshidere-sister-suou-yuki-gif-5671034940910266841"
        ]
    },
    "blush": {
        "priority": 2,
        "probability": 0.5,
        "keywords": ["blushing", "blushes slightly", "blushes"],
        "gifs": [
            "https://tenor.com/view/suou-yuki-roshidere-sister-suou-yuki-gif-8255471325517522898"
        ]
    },
    "excited": {
        "priority": 1,
        "probability": 0.5,
        "keywords": ["leans in closer", "excitedly","leans in curiously"],
        "gifs": [
            "https://tenor.com/view/%E8%89%BE%E8%8E%89%E5%90%8C%E5%AD%B8-alya-sometimes-hides-her-feelings-in-russian-suou-yuki-%E5%91%A8%E9%98%B2-%E6%9C%89%E5%B8%8C-%E8%B2%BC-gif-16589675791875980427",
            "https://tenor.com/view/suou-yuki-roshidere-sister-suou-yuki-gif-5671034940910266841"
        ]
    }
}



def can_send_gif(user_id: str) -> bool:
    now = time.time()
    last = GIF_COOLDOWN.get(user_id, 0)

    if now - last < GIF_COOLDOWN_SECONDS:
        return False

    GIF_COOLDOWN[user_id] = now
    return True


def pick_gif_from_reply(bot_reply: str) -> str | None:
    text = bot_reply.lower()
    matched = []

    for ctx, cfg in GIF_CONFIG.items():
        if any(k in text for k in cfg["keywords"]):
            matched.append((ctx, cfg))

    if not matched:
        return None

    # sort by priority DESC
    matched.sort(key=lambda x: x[1]["priority"], reverse=True)

    ctx, cfg = matched[0]

    # roll probability
    if random.random() > cfg["probability"]:
        return None

    return random.choice(cfg["gifs"])


