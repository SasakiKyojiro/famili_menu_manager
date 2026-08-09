# Family Meal Planner backend extension

This namespace extends Mealie without replacing its recipe, household, shopping-list, auth, or meal-plan models.
The upstream Vue UI is preserved and minimally extended with FMP pages/components; existing Mealie recipe, meal-plan, shopping-list, and household flows remain intact.

## API

All routes live under `/api/fmp` and use Mealie authentication plus the current user's `group_id` / `household_id`.

Implemented domains:

- inventory locations, stock lots, immutable stock ledger, FEFO consumption, waste, transfer, adjustments, minimum/target stock;
- food-specific unit-to-mass conversion while preserving Mealie standard mass/volume conversions;
- Open Food Facts and USDA FoodData Central clients and food linking;
- normalized nutrients, food nutrient values, recipe calculation snapshots, retention factors, legacy Mealie nutrition sync;
- cooking-session snapshots, step progress, traced stock consumption, completion/cancellation and prepared-food batches;
- optional people profiles, allergens, dietary restrictions, food preferences, nutrient targets and reference values;
- bioavailability rule evaluation with evidence/source metadata;
- pantry/expiry/preference/nutrient-aware recipe recommendations and meal-plan generation;
- per-person servings for existing Mealie meal-plan entries.

## Frontend

The integrated UI uses the existing Mealie `UserApiClient` and lives in the normal Nuxt/Vuetify application:

- `/household/fmp/inventory` — stock lots, locations, expiry/low-stock views, ledger actions, external food linking, food nutrition details;
- `/household/fmp/people` — optional family profiles, allergens, restrictions, food preferences, and nutrient targets;
- `/household/fmp/planner` — pantry/expiry/preference-aware recommendations and generation of ordinary Mealie meal-plan entries;
- `/household/fmp/cooking/{id}` — tracked cooking session with FEFO ingredient consumption, step completion, cancellation, and prepared-batch creation;
- recipe pages include a compact FMP panel for normalized nutrition calculation and starting tracked cooking.

Only `en-US` and `ru-RU` have explicit FMP strings; all other locales use Mealie's `en-US` fallback.

## Database

Migration `fmp001_backend` branches directly from Mealie revision `2187537c52b8` and creates only `fmp_*` tables.
Existing upstream tables are not modified.

## External configuration

`FMP_USDA_API_KEY` is optional. If omitted, the USDA client uses `DEMO_KEY`; a real FoodData Central API key is recommended for non-development use.
Open Food Facts requires no project secret.

## Deliberate boundaries

- `IngredientFoodModel` remains the canonical group food dictionary; inventory is household-scoped through `StockLot`.
- Mealie `recipe_nutrition` remains a compatibility/export view. FMP `NutritionProfile` is the calculation snapshot.
- Stock transactions have no update/delete API. Corrections are new `ADJUST` transactions.
- Medical/DRI/bioavailability source data are versioned records, not hard-coded assumptions. The backend provides models and APIs for loading curated datasets.
- The planner currently has a deterministic service contract. It is intentionally isolated so an OR-Tools implementation can replace selection without changing API consumers.
