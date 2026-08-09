from fastapi.testclient import TestClient

from mealie.schema.recipe.recipe_ingredient import SaveIngredientFood, SaveIngredientUnit
from tests.utils.factories import random_string
from tests.utils.fixture_schemas import TestUser


def _food_and_gram(user: TestUser):
    food = user.repos.ingredient_foods.create(SaveIngredientFood(name=random_string(12), group_id=user.group_id))
    unit = user.repos.ingredient_units.create(
        SaveIngredientUnit(name=f"gram-{random_string(6)}", group_id=user.group_id, standard_quantity=1, standard_unit="gram")
    )
    return food, unit


def test_inventory_ledger_low_stock(api_client: TestClient, unique_user_fn_scoped: TestUser):
    user = unique_user_fn_scoped
    food, unit = _food_and_gram(user)

    location = api_client.post(
        "/api/fmp/inventory/locations",
        headers=user.token,
        json={"name": "Test fridge", "type": "FRIDGE"},
    )
    assert location.status_code == 201

    lot = api_client.post(
        "/api/fmp/inventory/lots",
        headers=user.token,
        json={
            "foodId": str(food.id),
            "locationId": location.json()["id"],
            "quantity": 100,
            "unitId": str(unit.id),
        },
    )
    assert lot.status_code == 201

    consumed = api_client.post(
        f"/api/fmp/inventory/lots/{lot.json()['id']}/consume",
        headers=user.token,
        json={"quantity": 30, "unitId": str(unit.id)},
    )
    assert consumed.status_code == 200

    current = api_client.get(f"/api/fmp/inventory/lots/{lot.json()['id']}", headers=user.token)
    assert current.status_code == 200
    assert current.json()["quantity"] == 70

    target = api_client.put(
        f"/api/fmp/inventory/targets/{food.id}",
        headers=user.token,
        json={"foodId": str(food.id), "minimumQuantity": 80, "targetQuantity": 100, "unitId": str(unit.id)},
    )
    assert target.status_code == 200

    low = api_client.get("/api/fmp/inventory/low-stock", headers=user.token)
    assert low.status_code == 200
    item = next(x for x in low.json() if x["foodId"] == str(food.id))
    assert item["currentQuantity"] == 70
    assert item["missingQuantity"] == 30

    txs = api_client.get(f"/api/fmp/inventory/transactions?lot_id={lot.json()['id']}", headers=user.token)
    assert txs.status_code == 200
    assert [tx["type"] for tx in txs.json()] == ["CONSUME", "PURCHASE"]
