
import os
import json
import time
import asyncio
import aiohttp
import sys




_tokens = None
_rate_limiters = {}


class RateLimiter:
    def __init__(self, max_calls, period):
        self.max_calls = max_calls
        self.period = period
        self.calls = []
        self.lock = asyncio.Lock()

    async def acquire(self):
        async with self.lock:
            now = time.monotonic()
            # Nettoyer les appels trop anciens
            self.calls = [t for t in self.calls if now - t < self.period]
            if len(self.calls) >= self.max_calls:
                sleep_time = self.period - (now - self.calls[0])
                await asyncio.sleep(sleep_time)
                now = time.monotonic()
                self.calls = [t for t in self.calls if now - t < self.period]
            self.calls.append(now)



def load_tokens():
    global _tokens, _rate_limiters
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
    tokens_file = os.path.join(base_dir, 'tokens.json')
    with open(tokens_file, 'r', encoding='utf-8') as f:
        _tokens = json.load(f)
    # Créer un rate limiter pour chaque token
    for key in _tokens.keys():
        _rate_limiters[key] = RateLimiter(max_calls=2, period=1.0)



def get_access_token(token_index=0):
    global _tokens
    if _tokens is None:
        load_tokens()
    token_keys = list(_tokens.keys())
    selected_key = token_keys[token_index % len(token_keys)]
    return _tokens[selected_key], selected_key

