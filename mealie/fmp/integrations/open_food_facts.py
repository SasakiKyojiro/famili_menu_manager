from __future__ import annotations

import httpx

from mealie.fmp.enums import FoodDataProvider
from mealie.fmp.schemas import ExternalSearchResult


class OpenFoodFactsClient:
    BASE_URL = "https://world.openfoodfacts.org"

    def __init__(self, client: httpx.AsyncClient | None = None):
        self._client = client

    async def _get(self, path: str, params: dict | None = None) -> dict:
        if self._client is not None:
            response = await self._client.get(path, params=params)
            response.raise_for_status()
            return response.json()
        async with httpx.AsyncClient(base_url=self.BASE_URL, timeout=20.0, headers={"User-Agent": "Mealie-FMP/1.0"}) as client:
            response = await client.get(path, params=params)
            response.raise_for_status()
            return response.json()

    @staticmethod
    def _to_result(product: dict) -> ExternalSearchResult:
        nutriments = product.get("nutriments") or {}
        nutrients = {
            key.removesuffix("_100g"): float(value)
            for key, value in nutriments.items()
            if key.endswith("_100g") and isinstance(value, (int, float))
        }
        return ExternalSearchResult(
            provider=FoodDataProvider.OPEN_FOOD_FACTS,
            external_id=str(product.get("code") or product.get("_id") or ""),
            barcode=product.get("code"),
            name=product.get("product_name") or product.get("generic_name") or product.get("code") or "Unknown product",
            nutrients=nutrients,
            raw=product,
        )

    async def barcode(self, barcode: str) -> ExternalSearchResult | None:
        data = await self._get(f"/api/v2/product/{barcode}.json")
        if data.get("status") != 1 or not data.get("product"):
            return None
        return self._to_result(data["product"])

    async def search(self, query: str, limit: int = 20) -> list[ExternalSearchResult]:
        data = await self._get(
            "/cgi/search.pl",
            params={"search_terms": query, "search_simple": 1, "action": "process", "json": 1, "page_size": limit},
        )
        return [self._to_result(p) for p in data.get("products", [])[:limit]]
