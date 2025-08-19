import httpx, asyncio, random, time
from typing import List, Dict, Any
from .config import LC_GRAPHQL

_recent_q = """
query recent($username: String!, $limit: Int!) {
  recentAcSubmissionList(username: $username, limit: $limit) {
    id
    title
    titleSlug
    timestamp
  }
}
"""

_problem_q = """
query bySlug($slug: String!) {
  question(titleSlug: $slug) { title difficulty }
}
"""

class LCClient:
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://leetcode.com",
                "Content-Type": "application/json",
            },
        )

    async def recent_ac(self, username:str, limit:int=12) -> List[Dict[str,Any]]:
        r = await self.client.post(LC_GRAPHQL, json={"query": _recent_q, "variables": {"username": username, "limit": limit}})
        r.raise_for_status()
        data = r.json()["data"]["recentAcSubmissionList"] or []
        # normalize ints
        for d in data:
            d["timestamp"] = int(d["timestamp"])
        return data

    async def problem_meta(self, slug:str) -> Dict[str,str]:
        r = await self.client.post(LC_GRAPHQL, json={"query": _problem_q, "variables": {"slug": slug}})
        r.raise_for_status()
        q = r.json()["data"]["question"]
        return {"title": q["title"], "difficulty": q["difficulty"]}

    async def close(self):
        await self.client.aclose()
