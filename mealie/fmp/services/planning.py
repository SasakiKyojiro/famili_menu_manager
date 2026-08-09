from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from mealie.db.models.household.mealplan import GroupMealPlan
from mealie.db.models.recipe.recipe import RecipeModel
from mealie.schema.user import PrivateUser

from ..models import (FoodExternalReference, NutritionProfile, NutritionProfileValue, PersonAllergen, PersonDietaryRestriction, PersonFoodPreference, PersonNutrientTarget, PersonProfile, StockLot)
from ..schemas import GeneratedMealPlanItem, RecipeRecommendation


class PlanningService:
    """Deterministic pantry-first planner. Kept behind a service so OR-Tools can replace selection without API changes."""
    def __init__(self, session: Session, user: PrivateUser): self.session, self.user = session, user

    def _validate_people(self, person_ids):
        if not person_ids:
            return
        people = list(self.session.scalars(select(PersonProfile).where(PersonProfile.id.in_(person_ids))))
        if len(people) != len(set(map(str, person_ids))) or any(str(p.household_id) != str(self.user.household_id) for p in people):
            from fastapi import HTTPException, status
            raise HTTPException(status.HTTP_404_NOT_FOUND, "person not found in household")

    @staticmethod
    def _normalize_token(value: str) -> str:
        token = str(value or "").strip().upper()
        if ":" in token:
            token = token.split(":", 1)[1]
        return token.replace("-", "_").replace(" ", "_")

    def _allergen_codes(self, person_ids):
        if not person_ids:
            return set()
        return {self._normalize_token(x) for x in self.session.scalars(select(PersonAllergen.code).where(PersonAllergen.person_id.in_(person_ids)))}

    def _restriction_codes(self, person_ids):
        if not person_ids:
            return set()
        return {self._normalize_token(x) for x in self.session.scalars(select(PersonDietaryRestriction.code).where(PersonDietaryRestriction.person_id.in_(person_ids)))}

    def _food_tokens(self, refs):
        tokens = set()
        for ref in refs:
            raw = ref.raw_metadata or {}
            for key in ("allergens_tags", "labels_tags", "categories_tags", "ingredients_analysis_tags", "traces_tags"):
                for value in raw.get(key) or []:
                    tokens.add(self._normalize_token(value))
            for key in ("ingredients_text", "ingredients_text_en", "product_name", "generic_name"):
                text = str(raw.get(key) or "").upper()
                for part in text.replace(",", " ").replace(";", " ").split():
                    tokens.add(self._normalize_token(part))
        return tokens

    @staticmethod
    def _violates_restrictions(restrictions, tokens):
        if not restrictions:
            return False
        common = {
            "VEGAN": {"NON_VEGAN"},
            "VEGETARIAN": {"NON_VEGETARIAN"},
            "GLUTEN_FREE": {"GLUTEN", "WHEAT"},
            "LACTOSE_FREE": {"MILK", "LACTOSE"},
            "NUT_FREE": {"PEANUTS", "PEANUT", "NUTS", "ALMONDS", "HAZELNUTS", "WALNUTS", "CASHEWS", "PISTACHIOS"},
        }
        for restriction in restrictions:
            blocked = common.get(restriction, {restriction})
            if blocked & tokens:
                return True
        return False

    def _target_totals(self, person_ids):
        totals = {}
        if not person_ids:
            return totals
        for target in self.session.scalars(select(PersonNutrientTarget).where(PersonNutrientTarget.person_id.in_(person_ids))):
            desired = target.target if target.target is not None else target.minimum
            if desired and desired > 0:
                totals[str(target.nutrient_id)] = totals.get(str(target.nutrient_id), 0.0) + desired
        return totals

    def _nutrition_score(self, recipe_id, targets):
        if not targets:
            return 0.0
        profile = self.session.scalar(select(NutritionProfile).where(
            NutritionProfile.recipe_id == recipe_id,
            NutritionProfile.household_id == self.user.household_id,
        ).order_by(NutritionProfile.created_at.desc()))
        if profile is None:
            return 0.0
        values = {str(v.nutrient_id): v.amount for v in self.session.scalars(select(NutritionProfileValue).where(NutritionProfileValue.profile_id == profile.id))}
        scores = []
        for nutrient_id, target in targets.items():
            amount = values.get(nutrient_id)
            if amount is None:
                continue
            scores.append(max(0.0, 1.0 - abs(amount - target) / target))
        return sum(scores) / len(scores) if scores else 0.0

    def recommend(self, request):
        self._validate_people(request.person_ids)
        lots = list(self.session.scalars(select(StockLot).where(
            StockLot.household_id == self.user.household_id, StockLot.quantity > 0
        )))
        pantry = {str(l.food_id) for l in lots if l.food_id}
        expiry_cutoff = date.today() + timedelta(days=7)
        expiring = {
            str(l.food_id) for l in lots
            if l.food_id and (expiry := (l.expires_at or l.best_before)) is not None and expiry <= expiry_cutoff
        }
        allergens = self._allergen_codes(request.person_ids)
        restrictions = self._restriction_codes(request.person_ids)
        targets = self._target_totals(request.person_ids)
        prefs = {}
        if request.person_ids:
            for pref in self.session.scalars(select(PersonFoodPreference).where(PersonFoodPreference.person_id.in_(request.person_ids))):
                prefs[str(pref.food_id)] = prefs.get(str(pref.food_id), 0.0) + pref.score
        recipes = list(self.session.scalars(select(RecipeModel).where(RecipeModel.group_id == self.user.group_id).options(selectinload(RecipeModel.recipe_ingredient))))
        results=[]
        for recipe in recipes:
            foods=[i.food_id for i in recipe.recipe_ingredient if i.food_id]
            if not foods: continue
            # Exclude recipes that conflict with selected people's known allergens/restrictions.
            if allergens or restrictions:
                refs=list(self.session.scalars(select(FoodExternalReference).where(FoodExternalReference.food_id.in_(foods))))
                tokens=self._food_tokens(refs)
                if tokens & allergens:
                    continue
                if self._violates_restrictions(restrictions, tokens):
                    continue
            in_pantry=sum(1 for f in foods if str(f) in pantry)
            exp_count=sum(1 for f in foods if str(f) in expiring)
            missing=[f for f in foods if str(f) not in pantry]
            coverage=in_pantry/max(1,len(foods))
            pref=sum(prefs.get(str(f),0.0) for f in foods)/max(1,len(foods))
            nutrition_score = self._nutrition_score(recipe.id, targets)
            score=coverage*request.pantry_weight + exp_count*request.expiry_weight + pref*request.preference_weight + nutrition_score*0.5 - len(missing)*0.05
            reasons=[]
            if coverage>=0.8: reasons.append("mostly available from pantry")
            if exp_count: reasons.append(f"uses {exp_count} expiring ingredient(s)")
            if pref>0: reasons.append("matches household preferences")
            if nutrition_score>0.7: reasons.append("matches nutrient targets")
            results.append(RecipeRecommendation(recipe_id=recipe.id,name=recipe.name,score=score,pantry_coverage=coverage,expiring_ingredients=exp_count,missing_food_ids=missing,reasons=reasons))
        return sorted(results,key=lambda x:x.score,reverse=True)[:request.limit]

    def generate(self, request):
        candidates=self.recommend(request)
        if not candidates: return []
        items=[]
        for idx in range(request.days):
            candidate=candidates[idx % len(candidates)]
            day=request.start_date+timedelta(days=idx)
            meal_id=None
            if request.create_entries:
                meal=GroupMealPlan(date=day,entry_type=request.entry_type,title=candidate.name,text="",group_id=self.user.group_id,user_id=self.user.id,recipe_id=candidate.recipe_id)
                self.session.add(meal); self.session.flush(); meal_id=meal.id
            items.append(GeneratedMealPlanItem(date=day,recipe_id=candidate.recipe_id,recipe_name=candidate.name,score=candidate.score,meal_plan_id=meal_id))
        if request.create_entries: self.session.commit()
        return items
