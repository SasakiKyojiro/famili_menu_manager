from __future__ import annotations

from collections import defaultdict

from fastapi import HTTPException, status
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from mealie.db.models.recipe.nutrition import Nutrition
from mealie.db.models.recipe.recipe import RecipeModel
from mealie.schema.user import PrivateUser

from ..enums import CalculationType, CookingMethod, NutritionSource, NutrientCategory
from ..models import (
    CookingRetentionRule,
    FoodNutrientValue,
    Nutrient,
    NutritionProfile,
    NutritionProfileValue,
)
from ..schemas import NutritionProfileOut, NutritionProfileValueOut
from .common import require_group_food, require_group_recipe
from .unit_conversion import UnitConversionService

SOURCE_PRIORITY = {
    NutritionSource.USER: 4,
    NutritionSource.USDA: 3,
    NutritionSource.OPEN_FOOD_FACTS: 2,
    NutritionSource.ESTIMATED: 1,
    NutritionSource.CALCULATED: 0,
}

CANONICAL_NUTRIENTS = {
    "energy": ("ENERGY_KCAL", "Energy", "kcal", NutrientCategory.ENERGY),
    "energy-kcal": ("ENERGY_KCAL", "Energy", "kcal", NutrientCategory.ENERGY),
    "calories": ("ENERGY_KCAL", "Energy", "kcal", NutrientCategory.ENERGY),
    "protein": ("PROTEIN", "Protein", "g", NutrientCategory.MACRO),
    "fat": ("FAT", "Fat", "g", NutrientCategory.MACRO),
    "total lipid (fat)": ("FAT", "Fat", "g", NutrientCategory.MACRO),
    "carbohydrates": ("CARBOHYDRATE", "Carbohydrate", "g", NutrientCategory.MACRO),
    "carbohydrate": ("CARBOHYDRATE", "Carbohydrate", "g", NutrientCategory.MACRO),
    "carbohydrate, by difference": ("CARBOHYDRATE", "Carbohydrate", "g", NutrientCategory.MACRO),
    "fiber": ("FIBER", "Fiber", "g", NutrientCategory.MACRO),
    "fiber, total dietary": ("FIBER", "Fiber", "g", NutrientCategory.MACRO),
    "sugars": ("SUGAR", "Sugars", "g", NutrientCategory.MACRO),
    "sugars, total including nlea": ("SUGAR", "Sugars", "g", NutrientCategory.MACRO),
    "sodium": ("SODIUM", "Sodium", "mg", NutrientCategory.MINERAL),
    "iron": ("IRON", "Iron", "mg", NutrientCategory.MINERAL),
    "calcium": ("CALCIUM", "Calcium", "mg", NutrientCategory.MINERAL),
    "magnesium": ("MAGNESIUM", "Magnesium", "mg", NutrientCategory.MINERAL),
    "zinc": ("ZINC", "Zinc", "mg", NutrientCategory.MINERAL),
    "vitamin c": ("VITAMIN_C", "Vitamin C", "mg", NutrientCategory.VITAMIN),
    "vitamin c, total ascorbic acid": ("VITAMIN_C", "Vitamin C", "mg", NutrientCategory.VITAMIN),
    "vitamin b-12": ("VITAMIN_B12", "Vitamin B12", "ug", NutrientCategory.VITAMIN),
}


class NutritionService:
    def __init__(self, session: Session, user: PrivateUser):
        self.session = session
        self.user = user
        self.converter = UnitConversionService(session)

    def list_nutrients(self):
        return list(self.session.scalars(select(Nutrient).order_by(Nutrient.category, Nutrient.name)))

    def seed_canonical_nutrients(self):
        seeded = []
        seen = set()
        for code, name, unit, category in CANONICAL_NUTRIENTS.values():
            if code in seen:
                continue
            seen.add(code)
            nutrient = self.session.scalar(select(Nutrient).where(Nutrient.code == code))
            if nutrient is None:
                nutrient = Nutrient(code=code, name=name, unit=unit, category=category)
                self.session.add(nutrient)
            seeded.append(nutrient)
        self.session.commit()
        return seeded

    def ensure_nutrient(self, raw_name: str, unit: str | None = None) -> Nutrient:
        key = raw_name.strip().lower().replace("_100g", "")
        definition = CANONICAL_NUTRIENTS.get(key)
        if definition:
            code, name, canonical_unit, category = definition
        else:
            code = "EXT_" + "_".join(part for part in "".join(ch if ch.isalnum() else " " for ch in raw_name.upper()).split())[:70]
            name, canonical_unit, category = raw_name, unit or "g", NutrientCategory.OTHER
        nutrient = self.session.scalar(select(Nutrient).where(Nutrient.code == code))
        if nutrient:
            return nutrient
        nutrient = Nutrient(code=code, name=name, unit=canonical_unit, category=category)
        self.session.add(nutrient); self.session.flush()
        return nutrient

    def food_values(self, food_id):
        require_group_food(self.session, food_id, self.user)
        return list(self.session.scalars(select(FoodNutrientValue).where(FoodNutrientValue.food_id == food_id)))

    def best_food_values(self, food_id) -> list[FoodNutrientValue]:
        values = self.food_values(food_id)
        best: dict[str, FoodNutrientValue] = {}
        for value in values:
            key = str(value.nutrient_id)
            if key not in best or SOURCE_PRIORITY.get(value.source, 0) > SOURCE_PRIORITY.get(best[key].source, 0):
                best[key] = value
        return list(best.values())

    def upsert_food_value(self, data):
        require_group_food(self.session, data.food_id, self.user)
        if not self.session.get(Nutrient, data.nutrient_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "nutrient not found")
        model = self.session.scalar(select(FoodNutrientValue).where(
            FoodNutrientValue.food_id == data.food_id,
            FoodNutrientValue.nutrient_id == data.nutrient_id,
            FoodNutrientValue.source == data.source,
        ))
        if model is None:
            model = FoodNutrientValue(**data.model_dump()); self.session.add(model)
        else:
            for key, value in data.model_dump().items(): setattr(model, key, value)
        self.session.commit(); self.session.refresh(model); return model

    def import_external_nutrients(self, food_id, result, source: NutritionSource):
        require_group_food(self.session, food_id, self.user)
        imported = []
        for raw_name, amount in result.nutrients.items():
            if not isinstance(amount, (int, float)):
                continue
            nutrient = self.ensure_nutrient(raw_name)
            value = self.session.scalar(select(FoodNutrientValue).where(
                FoodNutrientValue.food_id == food_id,
                FoodNutrientValue.nutrient_id == nutrient.id,
                FoodNutrientValue.source == source,
            ))
            if value is None:
                value = FoodNutrientValue(
                    food_id=food_id, nutrient_id=nutrient.id, amount=float(amount), basis_amount=100,
                    basis_unit="g", source=source, source_reference=result.external_id, confidence=0.9 if source == NutritionSource.USDA else 0.8,
                ); self.session.add(value)
            else:
                value.amount = float(amount); value.source_reference = result.external_id
            imported.append(value)
        self.session.commit()
        return imported

    def _retention_factor(self, food_id, nutrient_id, method: CookingMethod | None) -> float:
        if not method or method == CookingMethod.RAW:
            return 1.0
        rules = list(self.session.scalars(select(CookingRetentionRule).where(
            CookingRetentionRule.nutrient_id == nutrient_id,
            CookingRetentionRule.cooking_method == method,
            or_(CookingRetentionRule.food_id == food_id, CookingRetentionRule.food_id.is_(None)),
        ).order_by(CookingRetentionRule.food_id.desc())))
        return max(0.0, rules[0].retention_factor) if rules else 1.0

    def calculate_recipe(self, recipe_id, cooking_method: CookingMethod | None = None, persist=True) -> NutritionProfileOut:
        recipe = require_group_recipe(self.session, recipe_id, self.user)
        totals: dict[str, float] = defaultdict(float)
        mins: dict[str, float] = defaultdict(float)
        maxs: dict[str, float] = defaultdict(float)
        nutrient_models: dict[str, Nutrient] = {}
        resolved = 0
        eligible = 0
        for ingredient in recipe.recipe_ingredient:
            if not ingredient.food_id or ingredient.quantity is None:
                continue
            eligible += 1
            values = self.best_food_values(ingredient.food_id)
            if not values:
                continue
            try:
                grams = self.converter.to_grams(ingredient.food_id, ingredient.quantity, ingredient.unit_id)
            except HTTPException:
                continue
            resolved += 1
            for value in values:
                nutrient = self.session.get(Nutrient, value.nutrient_id)
                if not nutrient:
                    continue
                nutrient_models[str(nutrient.id)] = nutrient
                factor = grams / value.basis_amount if value.basis_unit.lower() in {"g", "gram", "grams"} else grams / 100.0
                retention = self._retention_factor(ingredient.food_id, value.nutrient_id, cooking_method)
                amount = value.amount * factor * retention
                totals[str(nutrient.id)] += amount
                mins[str(nutrient.id)] += (value.min_amount if value.min_amount is not None else value.amount) * factor * retention
                maxs[str(nutrient.id)] += (value.max_amount if value.max_amount is not None else value.amount) * factor * retention
        confidence = 1.0 if eligible == 0 else resolved / eligible
        profile = NutritionProfile(
            household_id=self.user.household_id, recipe_id=recipe.id, basis_amount=1, basis_unit="recipe",
            calculation_type=CalculationType.CALCULATED, algorithm_version="fmp-1", confidence=confidence,
        )
        self.session.add(profile); self.session.flush()
        profile_values = []
        for nutrient_id, amount in totals.items():
            pv = NutritionProfileValue(
                profile_id=profile.id, nutrient_id=nutrient_id, amount=amount,
                min_amount=mins[nutrient_id], max_amount=maxs[nutrient_id],
            )
            self.session.add(pv); profile_values.append(pv)
        if persist:
            self._sync_legacy_recipe_nutrition(recipe, nutrient_models, totals)
            self.session.commit()
        else:
            self.session.rollback()
            # Re-create DTO because rollback expires transient DB identities.
            return NutritionProfileOut(
                id=profile.id, household_id=self.user.household_id, recipe_id=recipe.id, basis_amount=1,
                basis_unit="recipe", calculation_type=CalculationType.CALCULATED, algorithm_version="fmp-1",
                confidence=confidence,
                values=[NutritionProfileValueOut(id=pv.id, nutrient_id=pv.nutrient_id, amount=pv.amount, min_amount=pv.min_amount, max_amount=pv.max_amount) for pv in profile_values],
            )
        return self.profile_out(profile)

    def _sync_legacy_recipe_nutrition(self, recipe: RecipeModel, nutrients: dict[str, Nutrient], totals: dict[str, float]):
        by_code = {nutrients[nid].code: (amount, nutrients[nid].unit) for nid, amount in totals.items() if nid in nutrients}
        legacy = recipe.nutrition
        if legacy is None:
            legacy = Nutrition(); legacy.recipe_id = recipe.id; self.session.add(legacy); recipe.nutrition = legacy
        mapping = {
            "ENERGY_KCAL": "calories", "PROTEIN": "protein_content", "FAT": "fat_content",
            "CARBOHYDRATE": "carbohydrate_content", "FIBER": "fiber_content", "SUGAR": "sugar_content", "SODIUM": "sodium_content",
        }
        for code, field in mapping.items():
            if code in by_code:
                amount, unit = by_code[code]
                setattr(legacy, field, f"{amount:.3g} {unit}")

    def latest_recipe_profile(self, recipe_id):
        require_group_recipe(self.session, recipe_id, self.user)
        profile = self.session.scalar(select(NutritionProfile).where(
            NutritionProfile.recipe_id == recipe_id,
            NutritionProfile.household_id == self.user.household_id,
        ).order_by(NutritionProfile.created_at.desc()))
        if not profile:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "nutrition profile not found")
        return self.profile_out(profile)

    def profile_out(self, profile: NutritionProfile) -> NutritionProfileOut:
        values = list(self.session.scalars(select(NutritionProfileValue).where(NutritionProfileValue.profile_id == profile.id)))
        return NutritionProfileOut.model_validate(profile).model_copy(update={"values": [NutritionProfileValueOut.model_validate(v) for v in values]})
