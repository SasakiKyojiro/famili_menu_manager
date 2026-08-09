"""Family Meal Planner backend tables

Revision ID: fmp001_backend
Revises: 2187537c52b8
Create Date: 2026-08-09

The extension tables intentionally live beside Mealie's upstream tables.  We create
from the frozen model set belonging to this revision so SQLite/PostgreSQL use the
same SQLAlchemy type adapters (notably GUID and NaiveDateTime).
"""
from collections.abc import Sequence

from alembic import op

import mealie.fmp.models  # noqa: F401 - registers FMP tables in shared metadata
from mealie.db.models._model_base import SqlAlchemyBase

revision: str = "fmp001_backend"
down_revision: str | Sequence[str] | None = "2187537c52b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = [
    "fmp_inventory_locations",
    "fmp_inventory_targets",
    "fmp_food_external_references",
    "fmp_food_unit_conversions",
    "fmp_nutrients",
    "fmp_food_nutrient_values",
    "fmp_cooking_retention_rules",
    "fmp_recipe_cooking_step_profiles",
    "fmp_nutrition_profiles",
    "fmp_nutrition_profile_values",
    "fmp_cooking_sessions",
    "fmp_cooking_session_steps",
    "fmp_cooking_session_ingredients",
    "fmp_prepared_food_batches",
    "fmp_stock_lots",
    "fmp_stock_transactions",
    "fmp_cooking_consumptions",
    "fmp_bioavailability_rules",
    "fmp_person_profiles",
    "fmp_person_allergens",
    "fmp_person_dietary_restrictions",
    "fmp_person_food_preferences",
    "fmp_nutrient_reference_values",
    "fmp_person_nutrient_targets",
    "fmp_meal_plan_servings",
]


def upgrade() -> None:
    bind = op.get_bind()
    for name in TABLES:
        SqlAlchemyBase.metadata.tables[name].create(bind=bind, checkfirst=False)


def downgrade() -> None:
    bind = op.get_bind()
    for name in reversed(TABLES):
        SqlAlchemyBase.metadata.tables[name].drop(bind=bind, checkfirst=True)
