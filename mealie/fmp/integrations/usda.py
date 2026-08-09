from __future__ import annotations

import os

import httpx

from mealie.fmp.enums import FoodDataProvider
from mealie.fmp.schemas import ExternalSearchResult


class USDAFoodDataCentralClient:
    BASE_URL = "https://api.nal.usda.gov/fdc/v1"

    def __init__(self, api_key: str | None = None, client: httpx.AsyncClient | None = None):
        self.api_key = api_key or os.getenv("FMP_USDA_API_KEY", "DEMO_KEY")
        self._client = client

    async def _request(self, method: str, path: str, *, params: dict | None = None, json: dict | None = None) -> dict:
        params = {**(params or {}), "api_key": self.api_key}
        if self._client is not None:
            response = await self._client.request(method, path, params=params, json=json)
            response.raise_for_status()
            return response.json()
        async with httpx.AsyncClient(base_url=self.BASE_URL, timeout=20.0) as client:
            response = await client.request(method, path, params=params, json=json)
            response.raise_for_status()
            return response.json()

    @staticmethod
    def _nutrients(food: dict) -> dict[str, float]:
        result: dict[str, float] = {}
        for item in food.get("foodNutrients") or []:
            nutrient = item.get("nutrient") or {}
            name = nutrient.get("name") or item.get("nutrientName")
            amount = item.get("amount") or item.get("value")
            if name and isinstance(amount, (int, float)):
                result[str(name)] = float(amount)
        return result

    @classmethod
    def _to_result(cls, food: dict) -> ExternalSearchResult:
        fdc_id = str(food.get("fdcId") or food.get("fdc_id") or "")
        return ExternalSearchResult(
            provider=FoodDataProvider.USDA_FDC,
            external_id=fdc_id,
            name=food.get("description") or food.get("lowercaseDescription") or fdc_id,
            barcode=food.get("gtinUpc"),
            nutrients=cls._nutrients(food),
            raw=food,
        )

    async def get_food(self, fdc_id: str) -> ExternalSearchResult:
        return self._to_result(await self._request("GET", f"/food/{fdc_id}"))

    async def search(self, query: str, limit: int = 20) -> list[ExternalSearchResult]:
        data = await self._request("POST", "/foods/search", json={"query": query, "pageSize": limit})
        return [self._to_result(food) for food in (data.get("foods") or [])[:limit]]
