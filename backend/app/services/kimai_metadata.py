from typing import Optional
import time
import httpx
from pydantic import BaseModel
from app.connectors.base import TimeEntryNormalized

class MetadataCacheEntry(BaseModel):
    name: str
    timestamp: float

class KimaiMetadataService:
    """
    Service for resolving Kimai entity names by ID with in-memory caching (TTL 10 minutes).
    """
    TTL = 600  # 10 minutes in seconds

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip('/')
        self._client = httpx.AsyncClient(
            base_url=f"{self.base_url}/api",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0
        )
        self._caches = {
            'customers': {},
            'projects': {},
            'activities': {}
        }

    async def get_customer_name(self, customer_id: int) -> Optional[str]:
        """Get customer name by ID, with caching."""
        cache_key = customer_id
        if cache_key not in self._caches['customers'] or time.time() - self._caches['customers'][cache_key].timestamp > self.TTL:
            try:
                response = await self._client.get(f"/customers/{customer_id}")
                response.raise_for_status()
                data = response.json()
                self._caches['customers'][cache_key] = MetadataCacheEntry(
                    name=data['name'],
                    timestamp=time.time()
                )
            except httpx.HTTPError:
                return None
        return self._caches['customers'].get(cache_key, {}).name

    async def get_project_name(self, project_id: int) -> Optional[str]:
        """Get project name by ID, with caching."""
        cache_key = project_id
        if cache_key not in self._caches['projects'] or time.time() - self._caches['projects'][cache_key].timestamp > self.TTL:
            try:
                response = await self._client.get(f"/projects/{project_id}")
                response.raise_for_status()
                data = response.json()
                self._caches['projects'][cache_key] = MetadataCacheEntry(
                    name=data['name'],
                    timestamp=time.time()
                )
            except httpx.HTTPError:
                return None
        return self._caches['projects'].get(cache_key, {}).name

    async def get_activity_name(self, activity_id: int) -> Optional[str]:
        """Get activity name by ID, with caching."""
        cache_key = activity_id
        if cache_key not in self._caches['activities'] or time.time() - self._caches['activities'][cache_key].timestamp > self.TTL:
            try:
                response = await self._client.get(f"/activities/{activity_id}")
                response.raise_for_status()
                data = response.json()
                self._caches['activities'][cache_key] = MetadataCacheEntry(
                    name=data['name'],
                    timestamp=time.time()
                )
            except httpx.HTTPError:
                return None
        return self._caches['activities'].get(cache_key, {}).name

    async def enrich_normalized_entry(self, entry: TimeEntryNormalized) -> TimeEntryNormalized:
        """Enrich a normalized entry with names from IDs."""
        if entry.source != 'zammad':
            return entry  # Only enrich Zammad entries for sync to Kimai

        enriched = entry.model_copy(deep=True)
        if entry.customer_id:
            enriched.customer_name = await self.get_customer_name(entry.customer_id)
        if entry.project_id:
            enriched.project_name = await self.get_project_name(entry.project_id)
        if entry.activity_id:
            enriched.activity_name = await self.get_activity_name(entry.activity_id)
        return enriched

    async def close(self):
        await self._client.aclose()
