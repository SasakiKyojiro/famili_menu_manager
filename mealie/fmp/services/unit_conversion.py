from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from mealie.db.models.recipe.ingredient import IngredientUnitModel

from ..models import FoodUnitConversion


class UnitConversionService:
    MASS_TO_GRAMS = {
        "gram": 1.0, "grams": 1.0, "g": 1.0,
        "kilogram": 1000.0, "kilograms": 1000.0, "kg": 1000.0,
        "milligram": 0.001, "milligrams": 0.001, "mg": 0.001,
        "ounce": 28.349523125, "ounces": 28.349523125, "oz": 28.349523125,
        "pound": 453.59237, "pounds": 453.59237, "lb": 453.59237,
    }
    VOLUME_TO_ML = {
        "milliliter": 1.0, "milliliters": 1.0, "ml": 1.0,
        "liter": 1000.0, "liters": 1000.0, "l": 1000.0,
        "cup": 236.5882365, "cups": 236.5882365,
        "fluid-ounce": 29.5735295625, "fluid_ounce": 29.5735295625, "fluid ounce": 29.5735295625,
        "tablespoon": 14.78676478125, "tbsp": 14.78676478125,
        "teaspoon": 4.92892159375, "tsp": 4.92892159375,
        "pint": 473.176473, "quart": 946.352946, "gallon": 3785.411784,
    }

    def __init__(self, session: Session):
        self.session = session

    def _food_grams_per_unit(self, food_id, unit_id) -> float | None:
        if unit_id is None:
            return 1.0
        conv = self.session.scalar(select(FoodUnitConversion).where(
            FoodUnitConversion.food_id == food_id, FoodUnitConversion.unit_id == unit_id
        ))
        return conv.grams / conv.quantity if conv else None

    def _unit(self, unit_id) -> IngredientUnitModel | None:
        return self.session.get(IngredientUnitModel, unit_id) if unit_id is not None else None

    @staticmethod
    def _key(unit: IngredientUnitModel) -> str:
        return (unit.standard_unit or unit.name or "").strip().lower().replace("_", "-")

    def _standard_base(self, unit_id) -> tuple[str, float] | None:
        if unit_id is None:
            return "mass", 1.0
        unit = self._unit(unit_id)
        if not unit:
            return None
        key = self._key(unit)
        multiplier = unit.standard_quantity or 1.0
        if key in self.MASS_TO_GRAMS:
            return "mass", multiplier * self.MASS_TO_GRAMS[key]
        if key in self.VOLUME_TO_ML:
            return "volume", multiplier * self.VOLUME_TO_ML[key]
        # Fall back to display name for custom units that mirror a known unit.
        name = (unit.name or "").strip().lower()
        if name in self.MASS_TO_GRAMS:
            return "mass", self.MASS_TO_GRAMS[name]
        if name in self.VOLUME_TO_ML:
            return "volume", self.VOLUME_TO_ML[name]
        return None

    def _grams_per_unit(self, food_id, unit_id) -> float:
        specific = self._food_grams_per_unit(food_id, unit_id)
        if specific is not None:
            return specific
        standard = self._standard_base(unit_id)
        if standard and standard[0] == "mass":
            return standard[1]
        unit = self._unit(unit_id)
        label = unit.name if unit else "unitless"
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"unit '{label}' has no mass conversion for this food; create a FoodUnitConversion",
        )

    def convert(self, food_id, quantity: float, from_unit_id, to_unit_id) -> float:
        if from_unit_id == to_unit_id:
            return quantity
        # First use mass / food-specific conversion. This also handles count<->mass when both sides are resolvable.
        try:
            grams = quantity * self._grams_per_unit(food_id, from_unit_id)
            return grams / self._grams_per_unit(food_id, to_unit_id)
        except HTTPException:
            pass
        # If mass conversion is impossible, preserve dimensional volume conversion for stock operations.
        source = self._standard_base(from_unit_id)
        target = self._standard_base(to_unit_id)
        if source and target and source[0] == target[0]:
            return quantity * source[1] / target[1]
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "units are not convertible for this food")

    def to_grams(self, food_id, quantity: float, unit_id) -> float:
        return quantity * self._grams_per_unit(food_id, unit_id)
