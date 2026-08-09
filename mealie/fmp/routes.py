from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import Depends, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from mealie.core.dependencies import get_current_user
from mealie.db.db_setup import generate_session
from mealie.db.models.recipe.instruction import RecipeInstruction
from mealie.db.models.recipe.recipe import RecipeModel
from mealie.routes._base.routers import UserAPIRouter
from mealie.schema.user import PrivateUser

from .enums import FoodDataProvider, StockTransactionType
from .models import (
    BioavailabilityRule,
    CookingRetentionRule,
    FoodExternalReference,
    FoodUnitConversion,
    InventoryLocation,
    InventoryTarget,
    MealPlanServing,
    Nutrient,
    NutrientReferenceValue,
    PersonAllergen,
    PersonDietaryRestriction,
    PersonFoodPreference,
    PersonNutrientTarget,
    PreparedFoodBatch,
    RecipeCookingStepProfile,
    StockLot,
)
from .schemas import *
from .services.bioavailability import BioavailabilityService
from .services.common import require_group_food, require_group_recipe, require_group_unit, require_household
from .services.cooking import CookingService
from .services.external_food import ExternalFoodService
from .services.inventory import InventoryService
from .services.nutrition import NutritionService
from .services.people import PeopleService
from .services.planning import PlanningService

router = UserAPIRouter(prefix="/fmp", tags=["Family Meal Planner"])


def require_manage(user: PrivateUser):
    if not (user.admin or user.can_manage):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "manage permission required")


def require_admin(user: PrivateUser):
    if not user.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "admin permission required")


@router.get("/capabilities")
def capabilities():
    return {
        "inventory": True,
        "fefo": True,
        "nutrition": True,
        "externalFood": ["OPEN_FOOD_FACTS", "USDA_FDC"],
        "cookingSessions": True,
        "preparedBatches": True,
        "people": True,
        "bioavailability": True,
        "mealPlanning": True,
        "ui": "integrated-mealie-fmp",
    }


# Inventory locations
@router.get("/inventory/locations", response_model=list[LocationOut])
def list_locations(session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return InventoryService(session, user).list_locations()


@router.post("/inventory/locations", response_model=LocationOut, status_code=201)
def create_location(data: LocationCreate, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return InventoryService(session, user).create_location(data.name, data.type, data.parent_id)


@router.patch("/inventory/locations/{location_id}", response_model=LocationOut)
def update_location(location_id: UUID, data: LocationUpdate, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    model = require_household(session.get(InventoryLocation, location_id), user)
    if data.parent_id:
        parent = require_household(session.get(InventoryLocation, data.parent_id), user)
        if str(parent.id) == str(model.id):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "location cannot be its own parent")
    for key, value in data.model_dump(exclude_unset=True).items(): setattr(model, key, value)
    session.commit(); session.refresh(model); return model


@router.delete("/inventory/locations/{location_id}", status_code=204)
def delete_location(location_id: UUID, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    model = require_household(session.get(InventoryLocation, location_id), user)
    session.delete(model); session.commit()


# Stock lots / ledger
@router.get("/inventory/lots", response_model=list[StockLotOut])
def list_lots(food_id: UUID | None = None, active_only: bool = True, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return InventoryService(session, user).list_lots(food_id=food_id, active_only=active_only)


@router.get("/inventory/lots/expiring", response_model=list[StockLotOut])
def expiring_lots(days: int = Query(default=7, ge=0, le=3650), session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return InventoryService(session, user).expiring(days)


@router.post("/inventory/lots", response_model=StockLotOut, status_code=201)
def create_lot(data: StockLotCreate, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return InventoryService(session, user).create_lot(data)


@router.get("/inventory/lots/{lot_id}", response_model=StockLotOut)
def get_lot(lot_id: UUID, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return require_household(session.get(StockLot, lot_id), user)


@router.patch("/inventory/lots/{lot_id}", response_model=StockLotOut)
def update_lot(lot_id: UUID, data: StockLotUpdate, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    model = require_household(session.get(StockLot, lot_id), user)
    inv = InventoryService(session, user)
    if "location_id" in data.model_fields_set and data.location_id:
        inv._location(data.location_id)
    for key, value in data.model_dump(exclude_unset=True).items(): setattr(model, key, value)
    session.commit(); session.refresh(model); return model


@router.get("/inventory/targets", response_model=list[InventoryTargetOut])
def inventory_targets(session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return InventoryService(session, user).targets()


@router.put("/inventory/targets/{food_id}", response_model=InventoryTargetOut)
def upsert_inventory_target(food_id: UUID, data: InventoryTargetUpsert, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    if str(data.food_id) != str(food_id):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "path and body ids differ")
    return InventoryService(session, user).upsert_target(data)


@router.get("/inventory/low-stock", response_model=list[LowStockItem])
def low_stock(session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return InventoryService(session, user).low_stock()


@router.get("/inventory/transactions", response_model=list[StockTransactionOut])
def transactions(lot_id: UUID | None = None, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return InventoryService(session, user).transactions(lot_id)


@router.post("/inventory/lots/{lot_id}/consume", response_model=StockTransactionOut)
def consume_lot(lot_id: UUID, data: StockAction, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return InventoryService(session, user).consume_lot(lot_id, data.quantity, data.unit_id, note=data.note)


@router.post("/inventory/lots/{lot_id}/waste", response_model=StockTransactionOut)
def waste_lot(lot_id: UUID, data: StockAction, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return InventoryService(session, user).waste(lot_id, data.quantity, data.unit_id, data.note)


@router.post("/inventory/lots/{lot_id}/adjust", response_model=StockTransactionOut)
def adjust_lot(lot_id: UUID, data: StockAdjust, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return InventoryService(session, user).adjust(lot_id, data.new_quantity, data.note)


@router.post("/inventory/lots/{lot_id}/transfer", response_model=StockTransactionOut)
def transfer_lot(lot_id: UUID, data: StockTransfer, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return InventoryService(session, user).transfer(lot_id, data.location_id, data.note)


@router.post("/inventory/consume-food", response_model=ConsumptionResult)
def consume_food(data: StockConsumeFood, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    consumed, txs = InventoryService(session, user).consume_food(data.food_id, data.quantity, data.unit_id, allow_partial=data.allow_partial, note=data.note)
    return ConsumptionResult(requested_quantity=data.quantity, consumed_quantity=consumed, unit_id=data.unit_id, transactions=txs)


# Food mappings / conversions
@router.get("/foods/{food_id}/external-references", response_model=list[FoodExternalReferenceOut])
def external_refs(food_id: UUID, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    require_group_food(session, food_id, user)
    return list(session.scalars(select(FoodExternalReference).where(FoodExternalReference.food_id == food_id)))


@router.get("/foods/{food_id}/unit-conversions", response_model=list[FoodUnitConversionOut])
def food_conversions(food_id: UUID, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    require_group_food(session, food_id, user)
    return list(session.scalars(select(FoodUnitConversion).where(FoodUnitConversion.food_id == food_id)))


@router.put("/foods/{food_id}/unit-conversions/{unit_id}", response_model=FoodUnitConversionOut)
def upsert_food_conversion(food_id: UUID, unit_id: UUID, data: FoodUnitConversionCreate, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    if str(data.food_id) != str(food_id) or str(data.unit_id) != str(unit_id):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "path and body ids differ")
    require_group_food(session, food_id, user); require_group_unit(session, unit_id, user)
    model = session.scalar(select(FoodUnitConversion).where(FoodUnitConversion.food_id == food_id, FoodUnitConversion.unit_id == unit_id))
    if model is None:
        model = FoodUnitConversion(**data.model_dump()); session.add(model)
    else:
        for key,value in data.model_dump().items(): setattr(model,key,value)
    session.commit(); session.refresh(model); return model


# External data
@router.get("/external-food/search", response_model=list[ExternalSearchResult])
async def external_search(provider: FoodDataProvider, q: str, limit: int = Query(default=20, ge=1, le=50), session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return await ExternalFoodService(session, user).search(provider, q, limit)


@router.get("/external-food/barcode/{barcode}", response_model=ExternalSearchResult | None)
async def external_barcode(barcode: str, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return await ExternalFoodService(session, user).barcode(barcode)


@router.post("/foods/{food_id}/external/{provider}/{external_id}", response_model=FoodExternalReferenceOut)
async def link_external(food_id: UUID, provider: FoodDataProvider, external_id: str, barcode: str | None = None, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return await ExternalFoodService(session, user).link_and_import(food_id, provider, external_id, barcode)


# Nutrients
@router.get("/nutrition/nutrients", response_model=list[NutrientOut])
def nutrients(session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return NutritionService(session, user).list_nutrients()


@router.post("/nutrition/nutrients/seed", response_model=list[NutrientOut])
def seed_nutrients(session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    require_admin(user)
    return NutritionService(session, user).seed_canonical_nutrients()


@router.post("/nutrition/nutrients", response_model=NutrientOut, status_code=201)
def create_nutrient(data: NutrientCreate, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    require_admin(user)
    if session.scalar(select(Nutrient).where(Nutrient.code == data.code)):
        raise HTTPException(status.HTTP_409_CONFLICT, "nutrient code exists")
    model=Nutrient(**data.model_dump()); session.add(model); session.commit(); session.refresh(model); return model


@router.get("/nutrition/foods/{food_id}", response_model=list[FoodNutrientValueOut])
def food_nutrition(food_id: UUID, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return NutritionService(session, user).food_values(food_id)


@router.put("/nutrition/foods/{food_id}/values/{nutrient_id}", response_model=FoodNutrientValueOut)
def upsert_food_nutrient(food_id: UUID, nutrient_id: UUID, data: FoodNutrientValueUpsert, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    if str(data.food_id)!=str(food_id) or str(data.nutrient_id)!=str(nutrient_id):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,"path and body ids differ")
    return NutritionService(session,user).upsert_food_value(data)


@router.post("/nutrition/recipes/{recipe_id}/calculate", response_model=NutritionProfileOut)
def calculate_recipe_nutrition(recipe_id: UUID, data: RecipeNutritionCalculate, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return NutritionService(session,user).calculate_recipe(recipe_id,data.cooking_method,data.persist)


@router.get("/nutrition/recipes/{recipe_id}", response_model=NutritionProfileOut)
def latest_recipe_nutrition(recipe_id: UUID, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return NutritionService(session,user).latest_recipe_profile(recipe_id)


@router.post("/nutrition/retention-rules", status_code=201)
def create_retention_rule(data: CookingRetentionRuleCreate, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    if data.food_id is None:
        require_admin(user)
    else:
        require_manage(user)
        require_group_food(session, data.food_id, user)
    if not session.get(Nutrient, data.nutrient_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "nutrient not found")
    model = CookingRetentionRule(**data.model_dump())
    session.add(model)
    session.commit()
    session.refresh(model)
    return model


@router.put("/recipes/instructions/{instruction_id}/cooking-profile")
def upsert_cooking_step_profile(instruction_id: UUID, data: RecipeCookingStepProfileUpsert, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    instruction=session.get(RecipeInstruction,instruction_id)
    if not instruction:
        raise HTTPException(status.HTTP_404_NOT_FOUND,"instruction not found")
    require_group_recipe(session,instruction.recipe_id,user)
    model=session.scalar(select(RecipeCookingStepProfile).where(RecipeCookingStepProfile.instruction_id==instruction_id))
    if model is None:
        model=RecipeCookingStepProfile(instruction_id=instruction_id,**data.model_dump()); session.add(model)
    else:
        for k,v in data.model_dump().items(): setattr(model,k,v)
    session.commit(); session.refresh(model); return model

# Cooking sessions
@router.get("/cooking/sessions", response_model=list[CookingSessionOut])
def list_cooking_sessions(active_only: bool = False, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return CookingService(session,user).list(active_only)


@router.post("/cooking/sessions", response_model=CookingSessionOut, status_code=201)
def create_cooking_session(data: CookingSessionCreate, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return CookingService(session,user).create(data.recipe_id,data.recipe_scale,data.planned_servings)


@router.get("/cooking/sessions/{session_id}", response_model=CookingSessionOut)
def get_cooking_session(session_id: UUID, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return CookingService(session,user)._session(session_id)


@router.get("/cooking/sessions/{session_id}/ingredients", response_model=list[CookingIngredientOut])
def cooking_ingredients(session_id: UUID, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return CookingService(session,user).ingredients(session_id)


@router.get("/cooking/sessions/{session_id}/steps", response_model=list[CookingStepOut])
def cooking_steps(session_id: UUID, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return CookingService(session,user).steps(session_id)


@router.post("/cooking/sessions/{session_id}/start", response_model=CookingSessionOut)
def start_cooking(session_id: UUID, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return CookingService(session,user).start(session_id)


@router.post("/cooking/sessions/{session_id}/pause", response_model=CookingSessionOut)
def pause_cooking(session_id: UUID, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return CookingService(session,user).pause(session_id)


@router.post("/cooking/sessions/{session_id}/steps/{step_id}/complete", response_model=CookingStepOut)
def complete_cooking_step(session_id: UUID, step_id: UUID, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return CookingService(session,user).complete_step(session_id,step_id)


@router.post("/cooking/sessions/{session_id}/ingredients/{ingredient_id}/consume", response_model=CookingIngredientOut)
def consume_cooking_ingredient(session_id: UUID, ingredient_id: UUID, data: CookingIngredientConsume, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    ingredient,_=CookingService(session,user).consume_ingredient(session_id,ingredient_id,data.quantity,data.allow_partial)
    return ingredient


@router.post("/cooking/sessions/{session_id}/complete", response_model=PreparedBatchOut)
def complete_cooking(session_id: UUID, data: CookingComplete, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return CookingService(session,user).complete(session_id,data.output,data.consume_remaining)


@router.post("/cooking/sessions/{session_id}/cancel")
def cancel_cooking(session_id: UUID, data: CookingCancel, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    cooking,batch=CookingService(session,user).cancel(session_id,data.preserve_as_batch)
    return {"session": CookingSessionOut.model_validate(cooking), "preparedBatch": PreparedBatchOut.model_validate(batch) if batch else None}


@router.get("/prepared-batches", response_model=list[PreparedBatchOut])
def prepared_batches(session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return list(session.scalars(select(PreparedFoodBatch).where(PreparedFoodBatch.household_id==user.household_id).order_by(PreparedFoodBatch.prepared_at.desc())))


@router.get("/nutrition/reference-values", response_model=list[NutrientReferenceValueOut])
def nutrient_reference_values(session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return list(session.scalars(select(NutrientReferenceValue).order_by(NutrientReferenceValue.nutrient_id)))


@router.post("/nutrition/reference-values", response_model=NutrientReferenceValueOut, status_code=201)
def create_nutrient_reference_value(data: NutrientReferenceValueCreate, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    require_admin(user)
    if not session.get(Nutrient, data.nutrient_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "nutrient not found")
    model = NutrientReferenceValue(**data.model_dump()); session.add(model); session.commit(); session.refresh(model); return model


# People
@router.get("/people", response_model=list[PersonOut])
def people(session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return PeopleService(session,user).list()


@router.post("/people", response_model=PersonOut, status_code=201)
def create_person(data: PersonCreate, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return PeopleService(session,user).create(data)


@router.patch("/people/{person_id}", response_model=PersonOut)
def update_person(person_id: UUID, data: PersonUpdate, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return PeopleService(session,user).update(person_id,data)


@router.delete("/people/{person_id}", status_code=204)
def delete_person(person_id: UUID, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    PeopleService(session,user).delete(person_id)


@router.get("/people/{person_id}/allergens", response_model=list[PersonAllergenOut])
def person_allergens(person_id: UUID, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return PeopleService(session,user).allergens(person_id)


@router.put("/people/{person_id}/allergens/{code}", response_model=PersonAllergenOut)
def upsert_allergen(person_id: UUID, code: str, data: AllergenCreate, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    if data.code != code: raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,"path and body codes differ")
    return PeopleService(session,user).add_allergen(person_id,data)


@router.get("/people/{person_id}/restrictions", response_model=list[PersonRestrictionOut])
def person_restrictions(person_id: UUID, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return PeopleService(session,user).restrictions(person_id)


@router.put("/people/{person_id}/restrictions/{code}", response_model=PersonRestrictionOut)
def upsert_restriction(person_id: UUID, code: str, data: CodeTag, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    if data.code != code: raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,"path and body codes differ")
    return PeopleService(session,user).add_restriction(person_id,data)


@router.get("/people/{person_id}/preferences", response_model=list[PersonPreferenceOut])
def person_preferences(person_id: UUID, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return PeopleService(session,user).preferences(person_id)


@router.put("/people/{person_id}/preferences/{food_id}", response_model=PersonPreferenceOut)
def upsert_preference(person_id: UUID, food_id: UUID, data: PreferenceUpsert, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    if str(data.food_id)!=str(food_id): raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,"path and body ids differ")
    return PeopleService(session,user).preference(person_id,data)


@router.get("/people/{person_id}/reference-values", response_model=list[NutrientReferenceValueOut])
def person_reference_values(person_id: UUID, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return PeopleService(session,user).reference_values(person_id)


@router.post("/people/{person_id}/nutrient-targets/apply-reference-values", response_model=list[NutrientTargetOut])
def apply_person_reference_values(person_id: UUID, data: ApplyReferenceValuesRequest, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return PeopleService(session, user).apply_reference_values(person_id, data.overwrite)


@router.get("/people/{person_id}/nutrient-targets", response_model=list[NutrientTargetOut])
def person_targets(person_id: UUID, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return PeopleService(session,user).targets(person_id)


@router.put("/people/{person_id}/nutrient-targets/{nutrient_id}", response_model=NutrientTargetOut)
def upsert_target(person_id: UUID, nutrient_id: UUID, data: NutrientTargetUpsert, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    if str(data.nutrient_id)!=str(nutrient_id): raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,"path and body ids differ")
    return PeopleService(session,user).target(person_id,data)


# Bioavailability
@router.get("/bioavailability/rules")
def bioavailability_rules(session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return list(session.scalars(select(BioavailabilityRule)))


@router.post("/bioavailability/rules", status_code=201)
def create_bioavailability_rule(data: BioavailabilityRuleCreate, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    require_admin(user)
    if not session.get(Nutrient,data.nutrient_id): raise HTTPException(status.HTTP_404_NOT_FOUND,"nutrient not found")
    model=BioavailabilityRule(**data.model_dump()); session.add(model); session.commit(); session.refresh(model); return model


@router.post("/bioavailability/evaluate", response_model=list[BioavailabilityResult])
def evaluate_bioavailability(data: BioavailabilityEvaluate, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return BioavailabilityService(session).evaluate(data.nutrient_amounts,data.trigger_codes)


# Planning
@router.post("/recommendations/recipes", response_model=list[RecipeRecommendation])
def recommend_recipes(data: RecommendationRequest, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return PlanningService(session,user).recommend(data)


@router.post("/recommendations/meal-plan", response_model=list[GeneratedMealPlanItem])
def generate_meal_plan(data: GenerateMealPlanRequest, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    return PlanningService(session,user).generate(data)


@router.put("/meal-plans/{meal_plan_id}/servings/{person_id}")
def upsert_meal_plan_serving(meal_plan_id: int, person_id: UUID, data: MealPlanServingUpsert, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    if str(data.person_id)!=str(person_id): raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,"path and body ids differ")
    PeopleService(session,user)._person(person_id)
    # Ensure meal plan belongs to the current household through its owner.
    from mealie.db.models.household.mealplan import GroupMealPlan
    from mealie.db.models.users.users import User
    meal = session.scalar(select(GroupMealPlan).join(User, GroupMealPlan.user_id == User.id).where(
        GroupMealPlan.id == meal_plan_id,
        User.household_id == user.household_id,
    ))
    if meal is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND,"meal plan not found")
    model=session.scalar(select(MealPlanServing).where(MealPlanServing.meal_plan_id==meal_plan_id,MealPlanServing.person_id==person_id))
    if model is None:
        model=MealPlanServing(meal_plan_id=meal_plan_id,person_id=person_id,servings=data.servings); session.add(model)
    else: model.servings=data.servings
    session.commit(); session.refresh(model); return model

# Maintenance / delete endpoints are intentionally explicit; ledger transactions are never mutable/deletable.
@router.delete("/inventory/targets/{food_id}", status_code=204)
def delete_inventory_target(food_id: UUID, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    model = session.scalar(select(InventoryTarget).where(InventoryTarget.household_id == user.household_id, InventoryTarget.food_id == food_id))
    if model is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "inventory target not found")
    session.delete(model); session.commit()


@router.delete("/foods/{food_id}/unit-conversions/{unit_id}", status_code=204)
def delete_food_conversion(food_id: UUID, unit_id: UUID, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    require_group_food(session, food_id, user)
    model = session.scalar(select(FoodUnitConversion).where(FoodUnitConversion.food_id == food_id, FoodUnitConversion.unit_id == unit_id))
    if model is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "conversion not found")
    session.delete(model); session.commit()


@router.delete("/foods/{food_id}/external-references/{reference_id}", status_code=204)
def delete_external_reference(food_id: UUID, reference_id: UUID, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    require_group_food(session, food_id, user)
    model = session.get(FoodExternalReference, reference_id)
    if model is None or str(model.food_id) != str(food_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "external reference not found")
    session.delete(model); session.commit()


@router.get("/nutrition/retention-rules")
def list_retention_rules(session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    from mealie.db.models.recipe.ingredient import IngredientFoodModel
    group_food_ids = select(IngredientFoodModel.id).where(IngredientFoodModel.group_id == user.group_id)
    stmt = select(CookingRetentionRule).where(
        (CookingRetentionRule.food_id.is_(None)) | (CookingRetentionRule.food_id.in_(group_food_ids))
    ).order_by(CookingRetentionRule.cooking_method, CookingRetentionRule.nutrient_id)
    return list(session.scalars(stmt))


@router.delete("/nutrition/retention-rules/{rule_id}", status_code=204)
def delete_retention_rule(rule_id: UUID, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    model = session.get(CookingRetentionRule, rule_id)
    if model is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "retention rule not found")
    if model.food_id is None:
        require_admin(user)
    else:
        require_manage(user)
        require_group_food(session, model.food_id, user)
    session.delete(model)
    session.commit()


@router.get("/recipes/instructions/{instruction_id}/cooking-profile")
def get_cooking_step_profile(instruction_id: UUID, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    instruction = session.get(RecipeInstruction, instruction_id)
    if instruction is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "instruction not found")
    require_group_recipe(session, instruction.recipe_id, user)
    model = session.scalar(select(RecipeCookingStepProfile).where(RecipeCookingStepProfile.instruction_id == instruction_id))
    if model is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "cooking profile not found")
    return model


@router.delete("/people/{person_id}/allergens/{code}", status_code=204)
def delete_person_allergen(person_id: UUID, code: str, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    PeopleService(session, user)._person(person_id)
    model = session.scalar(select(PersonAllergen).where(PersonAllergen.person_id == person_id, PersonAllergen.code == code))
    if model is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "allergen not found")
    session.delete(model); session.commit()


@router.delete("/people/{person_id}/restrictions/{code}", status_code=204)
def delete_person_restriction(person_id: UUID, code: str, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    PeopleService(session, user)._person(person_id)
    model = session.scalar(select(PersonDietaryRestriction).where(PersonDietaryRestriction.person_id == person_id, PersonDietaryRestriction.code == code))
    if model is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "restriction not found")
    session.delete(model); session.commit()


@router.delete("/people/{person_id}/preferences/{food_id}", status_code=204)
def delete_person_preference(person_id: UUID, food_id: UUID, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    PeopleService(session, user)._person(person_id)
    model = session.scalar(select(PersonFoodPreference).where(PersonFoodPreference.person_id == person_id, PersonFoodPreference.food_id == food_id))
    if model is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "preference not found")
    session.delete(model); session.commit()


@router.delete("/people/{person_id}/nutrient-targets/{nutrient_id}", status_code=204)
def delete_person_target(person_id: UUID, nutrient_id: UUID, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    PeopleService(session, user)._person(person_id)
    models = list(session.scalars(select(PersonNutrientTarget).where(PersonNutrientTarget.person_id == person_id, PersonNutrientTarget.nutrient_id == nutrient_id)))
    if not models:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "target not found")
    for model in models:
        session.delete(model)
    session.commit()


@router.delete("/bioavailability/rules/{rule_id}", status_code=204)
def delete_bioavailability_rule(rule_id: UUID, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    require_admin(user)
    model = session.get(BioavailabilityRule, rule_id)
    if model is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bioavailability rule not found")
    session.delete(model); session.commit()


@router.get("/meal-plans/{meal_plan_id}/servings")
def meal_plan_servings(meal_plan_id: int, session: Session = Depends(generate_session), user: PrivateUser = Depends(get_current_user)):
    from mealie.db.models.household.mealplan import GroupMealPlan
    from mealie.db.models.users.users import User
    meal = session.scalar(select(GroupMealPlan).join(User, GroupMealPlan.user_id == User.id).where(
        GroupMealPlan.id == meal_plan_id, User.household_id == user.household_id
    ))
    if meal is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "meal plan not found")
    return list(session.scalars(select(MealPlanServing).where(MealPlanServing.meal_plan_id == meal_plan_id)))
