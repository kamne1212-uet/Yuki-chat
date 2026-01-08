import time

USER_COOLDOWN = {}
COOLDOWN_SECONDS = 30

def check_rate_limit(user_id):
    now = time.time()
    last = USER_COOLDOWN.get(user_id, 0)

    if now - last < COOLDOWN_SECONDS:
        return False

    USER_COOLDOWN[user_id] = now
    return True
