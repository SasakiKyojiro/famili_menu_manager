from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from mealie.schema.user import PrivateUser

from ..enums import FoodDataProvider, NutritionSource
from ..integrations import OpenFoodFactsClient, USDAFoodDataCentralClient
from ..models import FoodExternalReference
from .common import require_group_food, utcnow_naive
from .nutrition import NutritionService


class ExternalFoodService:
    def __init__(self, session: Session, user: PrivateUser):
        self.session, self.user = session, user
        self.off = OpenFoodFactsClient()
        self.usda = USDAFoodDataCentralClient()

    async def search(self, provider: FoodDataProvider, query: str, limit: int = 20):
        if provider == FoodDataProvider.OPEN_FOOD_FACTS:
            return await self.off.search(query, limit)
        if provider == FoodDataProvider.USDA_FDC:
            return await self.usda.search(query, limit)
        return []

    async def barcode(self, barcode: str):
        return await self.off.barcode(barcode)

    async def resolve(self, provider: FoodDataProvider, external_id: str):
        if provider == FoodDataProvider.OPEN_FOOD_FACTS:
            return await self.off.barcode(external_id)
        if provider == FoodDataProvider.USDA_FDC:
            return await self.usda.get_food(external_id)
        return None

    async def link_and_import(self, food_id, provider: FoodDataProvider, external_id: str, barcode: str | None = None):
        require_group_food(self.session, food_id, self.user)
        result = await self.resolve(provider, external_id)
        raw = result.raw if result else None
        if result and not barcode:
            barcode = result.barcode
        ref = self.session.scalar(select(FoodExternalReference).where(
            FoodExternalReference.food_id == food_id,
            FoodExternalReference.provider == provider,
            FoodExternalReference.external_id == external_id,
        ))
        if ref is None:
            ref = FoodExternalReference(food_id=food_id, provider=provider, external_id=external_id)
            self.session.add(ref)
        ref.barcode = barcode; ref.raw_metadata = raw; ref.last_synced_at = utcnow_naive(); ref.confidence = 1.0
        self.session.flush()
        if result:
            source = NutritionSource.USDA if provider == FoodDataProvider.USDA_FDC else NutritionSource.OPEN_FOOD_FACTS
            NutritionService(self.session, self.user).import_external_nutrients(food_id, result, source)
        else:
            self.session.commit()
        self.session.refresh(ref)
        return ref
