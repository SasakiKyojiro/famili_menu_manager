from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from mealie.db.models.recipe.ingredient import IngredientFoodModel, IngredientUnitModel
from mealie.db.models.recipe.recipe import RecipeModel
from mealie.schema.user import PrivateUser


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def require_household(model, user: PrivateUser):
    if model is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "resource not found")
    if str(model.household_id) != str(user.household_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "resource not found")
    return model


def require_group_food(session: Session, food_id: UUID | str, user: PrivateUser) -> IngredientFoodModel:
    food = session.get(IngredientFoodModel, food_id)
    if food is None or str(food.group_id) != str(user.group_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "food not found")
    return food


def require_group_unit(session: Session, unit_id: UUID | str | None, user: PrivateUser) -> IngredientUnitModel | None:
    if unit_id is None:
        return None
    unit = session.get(IngredientUnitModel, unit_id)
    if unit is None or str(unit.group_id) != str(user.group_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unit not found")
    return unit


def require_group_recipe(session: Session, recipe_id: UUID | str, user: PrivateUser) -> RecipeModel:
    recipe = session.get(RecipeModel, recipe_id)
    if recipe is None or str(recipe.group_id) != str(user.group_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "recipe not found")
    return recipe
