import asyncio
import json
from typing import Dict, Tuple

import aiohttp


class StreamElementsGambleAPI:
    def __init__(self, account_id: str, jwt_token: str):
        self.account_id = account_id
        self.jwt_token = jwt_token
        self.lock = asyncio.Lock()
        self.url_route = "https://api.streamelements.com/kappa/v2"

    async def set_luck(self, luck: int) -> Tuple[str, int]:
        data = {"roulette": {"luck": luck}}
        return await self.request("put", data)

    async def set_user_cooldown(self, user_cooldown: int) -> Tuple[str, int]:
        data = {"roulette": {"cooldown": {"user": user_cooldown}}}
        return await self.request("put", data)

    async def request(self, method: str, data: Dict) -> Tuple[str, int]:
        url = f"{self.url_route}/bot/modules/{self.account_id}/roulette"
        headers = {"Authorization": f"Bearer {self.jwt_token}", "Content-Type": "application/json"}
        async with self.lock:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.request(method, url, data=json.dumps(data)) as response:
                    text = await response.text()
                    return text, response.status
