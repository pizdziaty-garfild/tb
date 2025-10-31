# -*- coding: utf-8 -*-
"""
Simple rate limiter stub that allows all requests.
Replace later with token bucket implementation.
"""
import asyncio

class RateLimiter:
    def __init__(self, *args, **kwargs):
        pass
    async def allow_request(self, key) -> bool:
        return True
