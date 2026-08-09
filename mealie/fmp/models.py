from __future__ import annotations

from datetime import date, datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from mealie.db.models._model_base import SqlAlchemyBase
from mealie.db.models._model_utils.datetime import NaiveDateTime
from mealie.db.models._model_utils.guid import GUID

from .enums import (
    BioavailabilityTriggerType,
    CalculationType,
    CookingMethod,
    CookingSessionStatus,
    CookingStepStatus,
    EvidenceLevel,
    FoodDataProvider,
    InventoryLocationType,
    NutrientCategory,
    NutrientTargetPeriod,
    NutritionSource,
    Sex,
    StockLotStatus,
    StockTransactionType,
)


def enum_col(enum_type, *, default=None, nullable=False):
    return mapped_column(sa.Enum(enum_type, native_enum=False, length=64), default=default, nullable=nullable)


class InventoryLocation(SqlAlchemyBase):
    __tablename__ = "fmp_inventory_locations"
    __table_args__ = (sa.UniqueConstraint("household_id", "parent_id", "name", name="uq_fmp_location_parent_name"),)
    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    household_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("households.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    type: Mapped[InventoryLocationType] = enum_col(InventoryLocationType, default=InventoryLocationType.OTHER)
    parent_id: Mapped[GUID | None] = mapped_column(GUID, sa.ForeignKey("fmp_inventory_locations.id", ondelete="SET NULL"), index=True)


class InventoryTarget(SqlAlchemyBase):
    __tablename__ = "fmp_inventory_targets"
    __table_args__ = (sa.UniqueConstraint("household_id", "food_id", name="uq_fmp_inventory_target_food"),)
    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    household_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("households.id", ondelete="CASCADE"), index=True)
    food_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("ingredient_foods.id", ondelete="CASCADE"), index=True)
    minimum_quantity: Mapped[float] = mapped_column(sa.Float, nullable=False, default=0.0)
    target_quantity: Mapped[float | None] = mapped_column(sa.Float)
    unit_id: Mapped[GUID | None] = mapped_column(GUID, sa.ForeignKey("ingredient_units.id", ondelete="SET NULL"))


class FoodExternalReference(SqlAlchemyBase):
    __tablename__ = "fmp_food_external_references"
    __table_args__ = (
        sa.UniqueConstraint("provider", "external_id", "food_id", name="uq_fmp_food_external_ref"),
        sa.Index("ix_fmp_food_external_barcode", "barcode"),
    )
    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    food_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("ingredient_foods.id", ondelete="CASCADE"), index=True)
    provider: Mapped[FoodDataProvider] = enum_col(FoodDataProvider)
    external_id: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    barcode: Mapped[str | None] = mapped_column(sa.String(64))
    confidence: Mapped[float | None] = mapped_column(sa.Float)
    last_synced_at: Mapped[datetime | None] = mapped_column(NaiveDateTime)
    raw_metadata: Mapped[dict | None] = mapped_column(sa.JSON)


class FoodUnitConversion(SqlAlchemyBase):
    __tablename__ = "fmp_food_unit_conversions"
    __table_args__ = (sa.UniqueConstraint("food_id", "unit_id", name="uq_fmp_food_unit_conversion"),)
    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    food_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("ingredient_foods.id", ondelete="CASCADE"), index=True)
    unit_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("ingredient_units.id", ondelete="CASCADE"), index=True)
    quantity: Mapped[float] = mapped_column(sa.Float, nullable=False, default=1.0)
    grams: Mapped[float] = mapped_column(sa.Float, nullable=False)
    source: Mapped[FoodDataProvider] = enum_col(FoodDataProvider, default=FoodDataProvider.USER)
    confidence: Mapped[float | None] = mapped_column(sa.Float)


class Nutrient(SqlAlchemyBase):
    __tablename__ = "fmp_nutrients"
    __table_args__ = (sa.UniqueConstraint("code", name="uq_fmp_nutrient_code"),)
    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    code: Mapped[str] = mapped_column(sa.String(80), nullable=False, index=True)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    unit: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    category: Mapped[NutrientCategory] = enum_col(NutrientCategory, default=NutrientCategory.OTHER)
    external_ids: Mapped[dict | None] = mapped_column(sa.JSON)


class FoodNutrientValue(SqlAlchemyBase):
    __tablename__ = "fmp_food_nutrient_values"
    __table_args__ = (sa.UniqueConstraint("food_id", "nutrient_id", "source", name="uq_fmp_food_nutrient_source"),)
    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    food_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("ingredient_foods.id", ondelete="CASCADE"), index=True)
    nutrient_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("fmp_nutrients.id", ondelete="CASCADE"), index=True)
    amount: Mapped[float] = mapped_column(sa.Float, nullable=False)
    basis_amount: Mapped[float] = mapped_column(sa.Float, nullable=False, default=100.0)
    basis_unit: Mapped[str] = mapped_column(sa.String(32), nullable=False, default="g")
    min_amount: Mapped[float | None] = mapped_column(sa.Float)
    max_amount: Mapped[float | None] = mapped_column(sa.Float)
    source: Mapped[NutritionSource] = enum_col(NutritionSource)
    source_reference: Mapped[str | None] = mapped_column(sa.String(255))
    confidence: Mapped[float | None] = mapped_column(sa.Float)


class CookingRetentionRule(SqlAlchemyBase):
    __tablename__ = "fmp_cooking_retention_rules"
    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    food_id: Mapped[GUID | None] = mapped_column(GUID, sa.ForeignKey("ingredient_foods.id", ondelete="CASCADE"), index=True)
    food_category: Mapped[str | None] = mapped_column(sa.String(128), index=True)
    cooking_method: Mapped[CookingMethod] = enum_col(CookingMethod)
    nutrient_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("fmp_nutrients.id", ondelete="CASCADE"), index=True)
    retention_factor: Mapped[float] = mapped_column(sa.Float, nullable=False)
    temperature_min: Mapped[float | None] = mapped_column(sa.Float)
    temperature_max: Mapped[float | None] = mapped_column(sa.Float)
    duration_min: Mapped[float | None] = mapped_column(sa.Float)
    duration_max: Mapped[float | None] = mapped_column(sa.Float)
    source: Mapped[str | None] = mapped_column(sa.String(255))
    evidence_level: Mapped[EvidenceLevel] = enum_col(EvidenceLevel, default=EvidenceLevel.MODERATE)


class RecipeCookingStepProfile(SqlAlchemyBase):
    __tablename__ = "fmp_recipe_cooking_step_profiles"
    __table_args__ = (sa.UniqueConstraint("instruction_id", name="uq_fmp_instruction_profile"),)
    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    instruction_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("recipe_instructions.id", ondelete="CASCADE"), index=True)
    method: Mapped[CookingMethod] = enum_col(CookingMethod, default=CookingMethod.OTHER)
    temperature_c: Mapped[float | None] = mapped_column(sa.Float)
    duration_minutes: Mapped[float | None] = mapped_column(sa.Float)
    water_contact: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    pressure: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    yield_factor: Mapped[float | None] = mapped_column(sa.Float)


class NutritionProfile(SqlAlchemyBase):
    __tablename__ = "fmp_nutrition_profiles"
    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    household_id: Mapped[GUID | None] = mapped_column(GUID, sa.ForeignKey("households.id", ondelete="CASCADE"), index=True)
    food_id: Mapped[GUID | None] = mapped_column(GUID, sa.ForeignKey("ingredient_foods.id", ondelete="CASCADE"), index=True)
    recipe_id: Mapped[GUID | None] = mapped_column(GUID, sa.ForeignKey("recipes.id", ondelete="CASCADE"), index=True)
    prepared_batch_id: Mapped[GUID | None] = mapped_column(GUID, index=True)
    basis_amount: Mapped[float] = mapped_column(sa.Float, nullable=False, default=100.0)
    basis_unit: Mapped[str] = mapped_column(sa.String(32), nullable=False, default="g")
    calculation_type: Mapped[CalculationType] = enum_col(CalculationType)
    algorithm_version: Mapped[str] = mapped_column(sa.String(64), nullable=False, default="fmp-1")
    confidence: Mapped[float | None] = mapped_column(sa.Float)


class NutritionProfileValue(SqlAlchemyBase):
    __tablename__ = "fmp_nutrition_profile_values"
    __table_args__ = (sa.UniqueConstraint("profile_id", "nutrient_id", name="uq_fmp_profile_nutrient"),)
    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    profile_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("fmp_nutrition_profiles.id", ondelete="CASCADE"), index=True)
    nutrient_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("fmp_nutrients.id", ondelete="CASCADE"), index=True)
    amount: Mapped[float] = mapped_column(sa.Float, nullable=False)
    min_amount: Mapped[float | None] = mapped_column(sa.Float)
    max_amount: Mapped[float | None] = mapped_column(sa.Float)


class CookingSession(SqlAlchemyBase):
    __tablename__ = "fmp_cooking_sessions"
    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    household_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("households.id", ondelete="CASCADE"), index=True)
    recipe_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("recipes.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[GUID | None] = mapped_column(GUID, sa.ForeignKey("users.id", ondelete="SET NULL"), index=True)
    recipe_scale: Mapped[float] = mapped_column(sa.Float, nullable=False, default=1.0)
    planned_servings: Mapped[float | None] = mapped_column(sa.Float)
    status: Mapped[CookingSessionStatus] = enum_col(CookingSessionStatus, default=CookingSessionStatus.CREATED)
    started_at: Mapped[datetime | None] = mapped_column(NaiveDateTime)
    completed_at: Mapped[datetime | None] = mapped_column(NaiveDateTime)
    cancelled_at: Mapped[datetime | None] = mapped_column(NaiveDateTime)
    current_step: Mapped[int | None] = mapped_column(sa.Integer)


class CookingSessionStep(SqlAlchemyBase):
    __tablename__ = "fmp_cooking_session_steps"
    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    session_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("fmp_cooking_sessions.id", ondelete="CASCADE"), index=True)
    instruction_id: Mapped[GUID | None] = mapped_column(GUID, sa.ForeignKey("recipe_instructions.id", ondelete="SET NULL"), index=True)
    position: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    status: Mapped[CookingStepStatus] = enum_col(CookingStepStatus, default=CookingStepStatus.PENDING)
    started_at: Mapped[datetime | None] = mapped_column(NaiveDateTime)
    completed_at: Mapped[datetime | None] = mapped_column(NaiveDateTime)


class CookingSessionIngredient(SqlAlchemyBase):
    __tablename__ = "fmp_cooking_session_ingredients"
    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    session_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("fmp_cooking_sessions.id", ondelete="CASCADE"), index=True)
    recipe_ingredient_id: Mapped[int | None] = mapped_column(sa.Integer, sa.ForeignKey("recipes_ingredients.id", ondelete="SET NULL"), index=True)
    food_id: Mapped[GUID | None] = mapped_column(GUID, sa.ForeignKey("ingredient_foods.id", ondelete="SET NULL"), index=True)
    required_quantity: Mapped[float | None] = mapped_column(sa.Float)
    required_unit_id: Mapped[GUID | None] = mapped_column(GUID, sa.ForeignKey("ingredient_units.id", ondelete="SET NULL"))
    consumed_quantity: Mapped[float] = mapped_column(sa.Float, nullable=False, default=0.0)
    consumed_unit_id: Mapped[GUID | None] = mapped_column(GUID, sa.ForeignKey("ingredient_units.id", ondelete="SET NULL"))
    original_text: Mapped[str | None] = mapped_column(sa.String)


class PreparedFoodBatch(SqlAlchemyBase):
    __tablename__ = "fmp_prepared_food_batches"
    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    household_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("households.id", ondelete="CASCADE"), index=True)
    cooking_session_id: Mapped[GUID | None] = mapped_column(GUID, sa.ForeignKey("fmp_cooking_sessions.id", ondelete="SET NULL"), index=True)
    recipe_id: Mapped[GUID | None] = mapped_column(GUID, sa.ForeignKey("recipes.id", ondelete="SET NULL"), index=True)
    completed_instruction_id: Mapped[GUID | None] = mapped_column(GUID, sa.ForeignKey("recipe_instructions.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    quantity: Mapped[float] = mapped_column(sa.Float, nullable=False)
    unit_id: Mapped[GUID | None] = mapped_column(GUID, sa.ForeignKey("ingredient_units.id", ondelete="SET NULL"))
    portions: Mapped[float | None] = mapped_column(sa.Float)
    prepared_at: Mapped[datetime] = mapped_column(NaiveDateTime, nullable=False)
    best_before: Mapped[date | None] = mapped_column(sa.Date)
    nutrition_profile_id: Mapped[GUID | None] = mapped_column(GUID, sa.ForeignKey("fmp_nutrition_profiles.id", ondelete="SET NULL"))


class StockLot(SqlAlchemyBase):
    __tablename__ = "fmp_stock_lots"
    __table_args__ = (
        sa.CheckConstraint("(food_id IS NOT NULL) <> (prepared_batch_id IS NOT NULL)", name="ck_fmp_stock_lot_source_xor"),
        sa.CheckConstraint("quantity >= 0", name="ck_fmp_stock_lot_quantity"),
    )
    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    household_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("households.id", ondelete="CASCADE"), index=True)
    food_id: Mapped[GUID | None] = mapped_column(GUID, sa.ForeignKey("ingredient_foods.id", ondelete="SET NULL"), index=True)
    prepared_batch_id: Mapped[GUID | None] = mapped_column(GUID, sa.ForeignKey("fmp_prepared_food_batches.id", ondelete="SET NULL"), index=True)
    location_id: Mapped[GUID | None] = mapped_column(GUID, sa.ForeignKey("fmp_inventory_locations.id", ondelete="SET NULL"), index=True)
    quantity: Mapped[float] = mapped_column(sa.Float, nullable=False)
    unit_id: Mapped[GUID | None] = mapped_column(GUID, sa.ForeignKey("ingredient_units.id", ondelete="SET NULL"), index=True)
    purchased_at: Mapped[datetime | None] = mapped_column(NaiveDateTime)
    produced_at: Mapped[datetime | None] = mapped_column(NaiveDateTime)
    opened_at: Mapped[datetime | None] = mapped_column(NaiveDateTime)
    best_before: Mapped[date | None] = mapped_column(sa.Date, index=True)
    expires_at: Mapped[date | None] = mapped_column(sa.Date, index=True)
    price: Mapped[float | None] = mapped_column(sa.Float)
    currency: Mapped[str | None] = mapped_column(sa.String(3))
    status: Mapped[StockLotStatus] = enum_col(StockLotStatus, default=StockLotStatus.ACTIVE)
    barcode: Mapped[str | None] = mapped_column(sa.String(64), index=True)


class StockTransaction(SqlAlchemyBase):
    __tablename__ = "fmp_stock_transactions"
    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    household_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("households.id", ondelete="CASCADE"), index=True)
    stock_lot_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("fmp_stock_lots.id", ondelete="CASCADE"), index=True)
    type: Mapped[StockTransactionType] = enum_col(StockTransactionType)
    quantity: Mapped[float] = mapped_column(sa.Float, nullable=False)
    unit_id: Mapped[GUID | None] = mapped_column(GUID, sa.ForeignKey("ingredient_units.id", ondelete="SET NULL"))
    user_id: Mapped[GUID | None] = mapped_column(GUID, sa.ForeignKey("users.id", ondelete="SET NULL"), index=True)
    source_type: Mapped[str | None] = mapped_column(sa.String(64))
    source_id: Mapped[str | None] = mapped_column(sa.String(64))
    note: Mapped[str | None] = mapped_column(sa.String)


class CookingConsumption(SqlAlchemyBase):
    __tablename__ = "fmp_cooking_consumptions"
    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    session_ingredient_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("fmp_cooking_session_ingredients.id", ondelete="CASCADE"), index=True)
    stock_lot_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("fmp_stock_lots.id", ondelete="RESTRICT"), index=True)
    stock_transaction_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("fmp_stock_transactions.id", ondelete="RESTRICT"), index=True)
    quantity: Mapped[float] = mapped_column(sa.Float, nullable=False)
    unit_id: Mapped[GUID | None] = mapped_column(GUID, sa.ForeignKey("ingredient_units.id", ondelete="SET NULL"))


class BioavailabilityRule(SqlAlchemyBase):
    __tablename__ = "fmp_bioavailability_rules"
    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    nutrient_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("fmp_nutrients.id", ondelete="CASCADE"), index=True)
    trigger_type: Mapped[BioavailabilityTriggerType] = enum_col(BioavailabilityTriggerType)
    trigger_code: Mapped[str] = mapped_column(sa.String(128), nullable=False, index=True)
    factor_min: Mapped[float] = mapped_column(sa.Float, nullable=False)
    factor_max: Mapped[float] = mapped_column(sa.Float, nullable=False)
    timing_before_minutes: Mapped[int | None] = mapped_column(sa.Integer)
    timing_after_minutes: Mapped[int | None] = mapped_column(sa.Integer)
    evidence_level: Mapped[EvidenceLevel] = enum_col(EvidenceLevel, default=EvidenceLevel.MODERATE)
    source: Mapped[str | None] = mapped_column(sa.String(512))


class PersonProfile(SqlAlchemyBase):
    __tablename__ = "fmp_person_profiles"
    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    household_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("households.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[GUID | None] = mapped_column(GUID, sa.ForeignKey("users.id", ondelete="SET NULL"), index=True)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    birth_date: Mapped[date | None] = mapped_column(sa.Date)
    sex: Mapped[Sex | None] = enum_col(Sex, nullable=True)
    height_cm: Mapped[float | None] = mapped_column(sa.Float)
    weight_kg: Mapped[float | None] = mapped_column(sa.Float)
    enabled: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)


class PersonAllergen(SqlAlchemyBase):
    __tablename__ = "fmp_person_allergens"
    __table_args__ = (sa.UniqueConstraint("person_id", "code", name="uq_fmp_person_allergen"),)
    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    person_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("fmp_person_profiles.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    label: Mapped[str | None] = mapped_column(sa.String(255))
    severity: Mapped[str | None] = mapped_column(sa.String(64))


class PersonDietaryRestriction(SqlAlchemyBase):
    __tablename__ = "fmp_person_dietary_restrictions"
    __table_args__ = (sa.UniqueConstraint("person_id", "code", name="uq_fmp_person_restriction"),)
    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    person_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("fmp_person_profiles.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    label: Mapped[str | None] = mapped_column(sa.String(255))


class PersonFoodPreference(SqlAlchemyBase):
    __tablename__ = "fmp_person_food_preferences"
    __table_args__ = (sa.UniqueConstraint("person_id", "food_id", name="uq_fmp_person_food_pref"),)
    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    person_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("fmp_person_profiles.id", ondelete="CASCADE"), index=True)
    food_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("ingredient_foods.id", ondelete="CASCADE"), index=True)
    score: Mapped[float] = mapped_column(sa.Float, nullable=False, default=0.0)


class NutrientReferenceValue(SqlAlchemyBase):
    __tablename__ = "fmp_nutrient_reference_values"
    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    nutrient_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("fmp_nutrients.id", ondelete="CASCADE"), index=True)
    sex: Mapped[Sex | None] = enum_col(Sex, nullable=True)
    age_from_days: Mapped[int | None] = mapped_column(sa.Integer)
    age_to_days: Mapped[int | None] = mapped_column(sa.Integer)
    pregnancy: Mapped[bool | None] = mapped_column(sa.Boolean)
    lactation: Mapped[bool | None] = mapped_column(sa.Boolean)
    minimum: Mapped[float | None] = mapped_column(sa.Float)
    target: Mapped[float | None] = mapped_column(sa.Float)
    maximum: Mapped[float | None] = mapped_column(sa.Float)
    period: Mapped[NutrientTargetPeriod] = enum_col(NutrientTargetPeriod, default=NutrientTargetPeriod.DAY)
    source: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    source_version: Mapped[str | None] = mapped_column(sa.String(128))


class PersonNutrientTarget(SqlAlchemyBase):
    __tablename__ = "fmp_person_nutrient_targets"
    __table_args__ = (sa.UniqueConstraint("person_id", "nutrient_id", "period", name="uq_fmp_person_nutrient_target"),)
    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    person_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("fmp_person_profiles.id", ondelete="CASCADE"), index=True)
    nutrient_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("fmp_nutrients.id", ondelete="CASCADE"), index=True)
    minimum: Mapped[float | None] = mapped_column(sa.Float)
    target: Mapped[float | None] = mapped_column(sa.Float)
    maximum: Mapped[float | None] = mapped_column(sa.Float)
    period: Mapped[NutrientTargetPeriod] = enum_col(NutrientTargetPeriod, default=NutrientTargetPeriod.DAY)
    source: Mapped[str | None] = mapped_column(sa.String(255))


class MealPlanServing(SqlAlchemyBase):
    __tablename__ = "fmp_meal_plan_servings"
    __table_args__ = (sa.UniqueConstraint("meal_plan_id", "person_id", name="uq_fmp_meal_plan_person"),)
    id: Mapped[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)
    meal_plan_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("group_meal_plans.id", ondelete="CASCADE"), index=True)
    person_id: Mapped[GUID] = mapped_column(GUID, sa.ForeignKey("fmp_person_profiles.id", ondelete="CASCADE"), index=True)
    servings: Mapped[float] = mapped_column(sa.Float, nullable=False, default=1.0)
