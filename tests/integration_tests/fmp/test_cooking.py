from fastapi.testclient import TestClient

from mealie.schema.recipe.recipe import Recipe
from mealie.schema.recipe.recipe_ingredient import RecipeIngredient, SaveIngredientFood, SaveIngredientUnit
from mealie.schema.recipe.recipe_step import RecipeStep
from tests.utils.factories import random_string
from tests.utils.fixture_schemas import TestUser


def test_cooking_consumes_stock_and_produces_batch(api_client: TestClient, unique_user_fn_scoped: TestUser):
    user = unique_user_fn_scoped
    food = user.repos.ingredient_foods.create(SaveIngredientFood(name=random_string(12), group_id=user.group_id))
    unit = user.repos.ingredient_units.create(
        SaveIngredientUnit(name=f"gram-{random_string(6)}", group_id=user.group_id, standard_quantity=1, standard_unit="gram")
    )
    recipe = user.repos.recipes.create(
        Recipe(
            user_id=user.user_id,
            group_id=user.group_id,
            name=random_string(12),
            recipe_ingredient=[RecipeIngredient(quantity=20, unit=unit, food=food)],
            recipe_instructions=[RecipeStep(text="Cook")],
        )
    )

    lot = api_client.post(
        "/api/fmp/inventory/lots",
        headers=user.token,
        json={"foodId": str(food.id), "quantity": 100, "unitId": str(unit.id)},
    )
    assert lot.status_code == 201

    cooking = api_client.post(
        "/api/fmp/cooking/sessions",
        headers=user.token,
        json={"recipeId": str(recipe.id), "recipeScale": 1},
    )
    assert cooking.status_code == 201
    session_id = cooking.json()["id"]
    assert api_client.post(f"/api/fmp/cooking/sessions/{session_id}/start", headers=user.token).status_code == 200

    ingredients = api_client.get(f"/api/fmp/cooking/sessions/{session_id}/ingredients", headers=user.token).json()
    assert len(ingredients) == 1
    response = api_client.post(
        f"/api/fmp/cooking/sessions/{session_id}/ingredients/{ingredients[0]['id']}/consume",
        headers=user.token,
        json={},
    )
    assert response.status_code == 200
    assert response.json()["consumedQuantity"] == 20

    finished = api_client.post(
        f"/api/fmp/cooking/sessions/{session_id}/complete",
        headers=user.token,
        json={
            "consumeRemaining": False,
            "output": {"name": "Prepared test food", "quantity": 80, "unitId": str(unit.id)},
        },
    )
    assert finished.status_code == 200

    source_lot = api_client.get(f"/api/fmp/inventory/lots/{lot.json()['id']}", headers=user.token).json()
    assert source_lot["quantity"] == 80

    prepared = api_client.get("/api/fmp/prepared-batches", headers=user.token)
    assert prepared.status_code == 200
    assert any(x["id"] == finished.json()["id"] for x in prepared.json())

    lots = api_client.get("/api/fmp/inventory/lots", headers=user.token).json()
    assert any(x["preparedBatchId"] == finished.json()["id"] for x in lots)
