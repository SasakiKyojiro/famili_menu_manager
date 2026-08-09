from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mealie.schema._mealie import MealieModel

from .enums import *


class FmpOut(MealieModel):
    model_config = ConfigDict(from_attributes=True)


class LocationCreate(MealieModel):
    name: str = Field(min_length=1, max_length=255)
    type: InventoryLocationType = InventoryLocationType.OTHER
    parent_id: UUID | None = None


class LocationUpdate(MealieModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    type: InventoryLocationType | None = None
    parent_id: UUID | None = None


class LocationOut(FmpOut):
    id: UUID
    household_id: UUID
    name: str
    type: InventoryLocationType
    parent_id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class StockLotCreate(MealieModel):
    food_id: UUID | None = None
    prepared_batch_id: UUID | None = None
    location_id: UUID | None = None
    quantity: float = Field(gt=0)
    unit_id: UUID | None = None
    purchased_at: datetime | None = None
    produced_at: datetime | None = None
    opened_at: datetime | None = None
    best_before: date | None = None
    expires_at: date | None = None
    price: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    barcode: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def validate_source(self):
        if (self.food_id is None) == (self.prepared_batch_id is None):
            raise ValueError("exactly one of food_id or prepared_batch_id is required")
        return self


class StockLotUpdate(MealieModel):
    location_id: UUID | None = None
    best_before: date | None = None
    expires_at: date | None = None
    opened_at: datetime | None = None
    price: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    barcode: str | None = Field(default=None, max_length=64)


class StockLotOut(FmpOut):
    id: UUID
    household_id: UUID
    food_id: UUID | None = None
    prepared_batch_id: UUID | None = None
    location_id: UUID | None = None
    quantity: float
    unit_id: UUID | None = None
    purchased_at: datetime | None = None
    produced_at: datetime | None = None
    opened_at: datetime | None = None
    best_before: date | None = None
    expires_at: date | None = None
    price: float | None = None
    currency: str | None = None
    status: StockLotStatus
    barcode: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class StockAction(MealieModel):
    quantity: float = Field(gt=0)
    unit_id: UUID | None = None
    note: str | None = None


class StockAdjust(MealieModel):
    new_quantity: float = Field(ge=0)
    note: str | None = None


class StockTransfer(MealieModel):
    location_id: UUID | None = None
    note: str | None = None


class StockConsumeFood(MealieModel):
    food_id: UUID
    quantity: float = Field(gt=0)
    unit_id: UUID | None = None
    allow_partial: bool = False
    note: str | None = None


class InventoryTargetUpsert(MealieModel):
    food_id: UUID
    minimum_quantity: float = Field(default=0, ge=0)
    target_quantity: float | None = Field(default=None, ge=0)
    unit_id: UUID | None = None


class InventoryTargetOut(FmpOut):
    id: UUID
    household_id: UUID
    food_id: UUID
    minimum_quantity: float
    target_quantity: float | None = None
    unit_id: UUID | None = None


class LowStockItem(MealieModel):
    food_id: UUID
    current_quantity: float
    minimum_quantity: float
    target_quantity: float | None = None
    missing_quantity: float
    unit_id: UUID | None = None


class StockTransactionOut(FmpOut):
    id: UUID
    household_id: UUID
    stock_lot_id: UUID
    type: StockTransactionType
    quantity: float
    unit_id: UUID | None = None
    user_id: UUID | None = None
    source_type: str | None = None
    source_id: str | None = None
    note: str | None = None
    created_at: datetime | None = None


class ConsumptionResult(MealieModel):
    requested_quantity: float
    consumed_quantity: float
    unit_id: UUID | None = None
    transactions: list[StockTransactionOut]


class FoodExternalReferenceCreate(MealieModel):
    food_id: UUID
    provider: FoodDataProvider
    external_id: str
    barcode: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    raw_metadata: dict | None = None


class FoodExternalReferenceOut(FmpOut):
    id: UUID
    food_id: UUID
    provider: FoodDataProvider
    external_id: str
    barcode: str | None = None
    confidence: float | None = None
    last_synced_at: datetime | None = None
    raw_metadata: dict | None = None


class FoodUnitConversionCreate(MealieModel):
    food_id: UUID
    unit_id: UUID
    quantity: float = Field(gt=0)
    grams: float = Field(gt=0)
    source: FoodDataProvider = FoodDataProvider.USER
    confidence: float | None = Field(default=None, ge=0, le=1)


class FoodUnitConversionOut(FmpOut):
    id: UUID
    food_id: UUID
    unit_id: UUID
    quantity: float
    grams: float
    source: FoodDataProvider
    confidence: float | None = None


class NutrientCreate(MealieModel):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=255)
    unit: str = Field(min_length=1, max_length=32)
    category: NutrientCategory = NutrientCategory.OTHER
    external_ids: dict | None = None


class NutrientOut(FmpOut):
    id: UUID
    code: str
    name: str
    unit: str
    category: NutrientCategory
    external_ids: dict | None = None


class FoodNutrientValueUpsert(MealieModel):
    food_id: UUID
    nutrient_id: UUID
    amount: float
    basis_amount: float = Field(default=100.0, gt=0)
    basis_unit: str = "g"
    min_amount: float | None = None
    max_amount: float | None = None
    source: NutritionSource
    source_reference: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class FoodNutrientValueOut(FmpOut):
    id: UUID
    food_id: UUID
    nutrient_id: UUID
    amount: float
    basis_amount: float
    basis_unit: str
    min_amount: float | None = None
    max_amount: float | None = None
    source: NutritionSource
    source_reference: str | None = None
    confidence: float | None = None


class CookingRetentionRuleCreate(MealieModel):
    food_id: UUID | None = None
    food_category: str | None = None
    cooking_method: CookingMethod
    nutrient_id: UUID
    retention_factor: float = Field(ge=0)
    temperature_min: float | None = None
    temperature_max: float | None = None
    duration_min: float | None = Field(default=None, ge=0)
    duration_max: float | None = Field(default=None, ge=0)
    source: str | None = None
    evidence_level: EvidenceLevel = EvidenceLevel.MODERATE


class RecipeCookingStepProfileUpsert(MealieModel):
    method: CookingMethod = CookingMethod.OTHER
    temperature_c: float | None = None
    duration_minutes: float | None = Field(default=None, ge=0)
    water_contact: bool = False
    pressure: bool = False
    yield_factor: float | None = Field(default=None, gt=0)


class NutritionProfileValueOut(FmpOut):
    id: UUID
    nutrient_id: UUID
    amount: float
    min_amount: float | None = None
    max_amount: float | None = None


class NutritionProfileOut(FmpOut):
    id: UUID
    household_id: UUID | None = None
    food_id: UUID | None = None
    recipe_id: UUID | None = None
    prepared_batch_id: UUID | None = None
    basis_amount: float
    basis_unit: str
    calculation_type: CalculationType
    algorithm_version: str
    confidence: float | None = None
    values: list[NutritionProfileValueOut] = []
    created_at: datetime | None = None


class RecipeNutritionCalculate(MealieModel):
    cooking_method: CookingMethod | None = None
    persist: bool = True


class CookingSessionCreate(MealieModel):
    recipe_id: UUID
    recipe_scale: float = Field(default=1.0, gt=0)
    planned_servings: float | None = Field(default=None, gt=0)


class CookingSessionOut(FmpOut):
    id: UUID
    household_id: UUID
    recipe_id: UUID
    user_id: UUID | None = None
    recipe_scale: float
    planned_servings: float | None = None
    status: CookingSessionStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    current_step: int | None = None
    created_at: datetime | None = None


class CookingIngredientOut(FmpOut):
    id: UUID
    session_id: UUID
    recipe_ingredient_id: int | None = None
    food_id: UUID | None = None
    required_quantity: float | None = None
    required_unit_id: UUID | None = None
    consumed_quantity: float
    consumed_unit_id: UUID | None = None
    original_text: str | None = None


class CookingStepOut(FmpOut):
    id: UUID
    session_id: UUID
    instruction_id: UUID | None = None
    position: int
    status: CookingStepStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None


class CookingIngredientConsume(MealieModel):
    quantity: float | None = Field(default=None, gt=0)
    allow_partial: bool = False


class PreparedBatchCreate(MealieModel):
    name: str = Field(min_length=1, max_length=255)
    quantity: float = Field(gt=0)
    unit_id: UUID | None = None
    portions: float | None = Field(default=None, gt=0)
    best_before: date | None = None
    location_id: UUID | None = None


class PreparedBatchOut(FmpOut):
    id: UUID
    household_id: UUID
    cooking_session_id: UUID | None = None
    recipe_id: UUID | None = None
    completed_instruction_id: UUID | None = None
    name: str
    quantity: float
    unit_id: UUID | None = None
    portions: float | None = None
    prepared_at: datetime
    best_before: date | None = None
    nutrition_profile_id: UUID | None = None


class CookingComplete(MealieModel):
    output: PreparedBatchCreate
    consume_remaining: bool = True


class CookingCancel(MealieModel):
    preserve_as_batch: PreparedBatchCreate | None = None


class PersonCreate(MealieModel):
    user_id: UUID | None = None
    name: str = Field(min_length=1, max_length=255)
    birth_date: date | None = None
    sex: Sex | None = None
    height_cm: float | None = Field(default=None, gt=0)
    weight_kg: float | None = Field(default=None, gt=0)
    enabled: bool = True


class PersonUpdate(MealieModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    birth_date: date | None = None
    sex: Sex | None = None
    height_cm: float | None = Field(default=None, gt=0)
    weight_kg: float | None = Field(default=None, gt=0)
    enabled: bool | None = None


class PersonOut(FmpOut):
    id: UUID
    household_id: UUID
    user_id: UUID | None = None
    name: str
    birth_date: date | None = None
    sex: Sex | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    enabled: bool


class CodeTag(MealieModel):
    code: str = Field(min_length=1, max_length=128)
    label: str | None = None


class AllergenCreate(CodeTag):
    severity: str | None = None


class PersonAllergenOut(FmpOut):
    id: UUID
    person_id: UUID
    code: str
    label: str | None = None
    severity: str | None = None


class PersonRestrictionOut(FmpOut):
    id: UUID
    person_id: UUID
    code: str
    label: str | None = None


class PersonPreferenceOut(FmpOut):
    id: UUID
    person_id: UUID
    food_id: UUID
    score: float


class NutrientReferenceValueCreate(MealieModel):
    nutrient_id: UUID
    sex: Sex | None = None
    age_from_days: int | None = Field(default=None, ge=0)
    age_to_days: int | None = Field(default=None, ge=0)
    pregnancy: bool | None = None
    lactation: bool | None = None
    minimum: float | None = None
    target: float | None = None
    maximum: float | None = None
    period: NutrientTargetPeriod = NutrientTargetPeriod.DAY
    source: str
    source_version: str | None = None


class NutrientReferenceValueOut(FmpOut):
    id: UUID
    nutrient_id: UUID
    sex: Sex | None = None
    age_from_days: int | None = None
    age_to_days: int | None = None
    pregnancy: bool | None = None
    lactation: bool | None = None
    minimum: float | None = None
    target: float | None = None
    maximum: float | None = None
    period: NutrientTargetPeriod
    source: str
    source_version: str | None = None


class ApplyReferenceValuesRequest(MealieModel):
    overwrite: bool = False


class NutrientTargetUpsert(MealieModel):
    nutrient_id: UUID
    minimum: float | None = None
    target: float | None = None
    maximum: float | None = None
    period: NutrientTargetPeriod = NutrientTargetPeriod.DAY
    source: str | None = None


class NutrientTargetOut(FmpOut):
    id: UUID
    person_id: UUID
    nutrient_id: UUID
    minimum: float | None = None
    target: float | None = None
    maximum: float | None = None
    period: NutrientTargetPeriod
    source: str | None = None


class PreferenceUpsert(MealieModel):
    food_id: UUID
    score: float = Field(ge=-1, le=1)


class MealPlanServingUpsert(MealieModel):
    person_id: UUID
    servings: float = Field(gt=0)


class RecommendationRequest(MealieModel):
    person_ids: list[UUID] = []
    limit: int = Field(default=10, ge=1, le=100)
    pantry_weight: float = 1.0
    expiry_weight: float = 1.5
    preference_weight: float = 0.5


class RecipeRecommendation(MealieModel):
    recipe_id: UUID
    name: str
    score: float
    pantry_coverage: float
    expiring_ingredients: int
    missing_food_ids: list[UUID]
    reasons: list[str]


class GenerateMealPlanRequest(RecommendationRequest):
    start_date: date
    days: int = Field(default=7, ge=1, le=31)
    entry_type: str = "dinner"
    create_entries: bool = False


class GeneratedMealPlanItem(MealieModel):
    date: date
    recipe_id: UUID
    recipe_name: str
    score: float
    meal_plan_id: int | None = None


class BioavailabilityRuleCreate(MealieModel):
    nutrient_id: UUID
    trigger_type: BioavailabilityTriggerType
    trigger_code: str
    factor_min: float = Field(gt=0)
    factor_max: float = Field(gt=0)
    timing_before_minutes: int | None = Field(default=None, ge=0)
    timing_after_minutes: int | None = Field(default=None, ge=0)
    evidence_level: EvidenceLevel = EvidenceLevel.MODERATE
    source: str | None = None

    @model_validator(mode="after")
    def factors_ordered(self):
        if self.factor_min > self.factor_max:
            raise ValueError("factor_min must be <= factor_max")
        return self


class BioavailabilityEvaluate(MealieModel):
    nutrient_amounts: dict[str, float]
    trigger_codes: list[str] = []


class BioavailabilityResult(MealieModel):
    nutrient_code: str
    original_amount: float
    effective_min: float
    effective_max: float
    applied_rules: int


class ExternalSearchResult(MealieModel):
    provider: FoodDataProvider
    external_id: str
    name: str
    barcode: str | None = None
    nutrients: dict[str, float] = {}
    raw: dict = {}
