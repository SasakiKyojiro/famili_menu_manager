from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from mealie.schema.user import PrivateUser
from mealie.db.models.users.users import User

from ..models import NutrientReferenceValue, PersonAllergen, PersonDietaryRestriction, PersonFoodPreference, PersonNutrientTarget, PersonProfile
from .common import require_group_food, require_household


class PeopleService:
    def __init__(self, session: Session, user: PrivateUser):
        self.session, self.user = session, user

    def _person(self, person_id):
        return require_household(self.session.get(PersonProfile, person_id), self.user)

    def list(self):
        return list(self.session.scalars(select(PersonProfile).where(PersonProfile.household_id == self.user.household_id).order_by(PersonProfile.name)))

    def create(self, data):
        if data.user_id:
            linked_user = self.session.get(User, data.user_id)
            if linked_user is None or str(linked_user.household_id) != str(self.user.household_id):
                raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found in household")
            linked = self.session.scalar(select(PersonProfile).where(PersonProfile.user_id == data.user_id, PersonProfile.household_id == self.user.household_id))
            if linked:
                raise HTTPException(status.HTTP_409_CONFLICT, "user already linked to a person profile")
        model = PersonProfile(household_id=self.user.household_id, **data.model_dump())
        self.session.add(model); self.session.commit(); self.session.refresh(model); return model

    def update(self, person_id, data):
        model = self._person(person_id)
        for key, value in data.model_dump(exclude_unset=True).items(): setattr(model, key, value)
        self.session.commit(); self.session.refresh(model); return model

    def delete(self, person_id):
        model = self._person(person_id); self.session.delete(model); self.session.commit()

    def add_allergen(self, person_id, data):
        self._person(person_id)
        model = self.session.scalar(select(PersonAllergen).where(PersonAllergen.person_id == person_id, PersonAllergen.code == data.code))
        if model is None:
            model = PersonAllergen(person_id=person_id, **data.model_dump()); self.session.add(model)
        else:
            model.label, model.severity = data.label, data.severity
        self.session.commit(); self.session.refresh(model); return model

    def allergens(self, person_id):
        self._person(person_id); return list(self.session.scalars(select(PersonAllergen).where(PersonAllergen.person_id == person_id)))

    def add_restriction(self, person_id, data):
        self._person(person_id)
        model = self.session.scalar(select(PersonDietaryRestriction).where(PersonDietaryRestriction.person_id == person_id, PersonDietaryRestriction.code == data.code))
        if model is None:
            model = PersonDietaryRestriction(person_id=person_id, **data.model_dump()); self.session.add(model)
        else: model.label = data.label
        self.session.commit(); self.session.refresh(model); return model

    def restrictions(self, person_id):
        self._person(person_id); return list(self.session.scalars(select(PersonDietaryRestriction).where(PersonDietaryRestriction.person_id == person_id)))

    def preference(self, person_id, data):
        self._person(person_id); require_group_food(self.session, data.food_id, self.user)
        model = self.session.scalar(select(PersonFoodPreference).where(PersonFoodPreference.person_id == person_id, PersonFoodPreference.food_id == data.food_id))
        if model is None:
            model = PersonFoodPreference(person_id=person_id, **data.model_dump()); self.session.add(model)
        else: model.score = data.score
        self.session.commit(); self.session.refresh(model); return model

    def preferences(self, person_id):
        self._person(person_id); return list(self.session.scalars(select(PersonFoodPreference).where(PersonFoodPreference.person_id == person_id)))

    def reference_values(self, person_id):
        from datetime import date
        person = self._person(person_id)
        age_days = (date.today() - person.birth_date).days if person.birth_date else None
        stmt = select(NutrientReferenceValue)
        refs = list(self.session.scalars(stmt))
        out = []
        for ref in refs:
            if ref.sex is not None and person.sex is not None and ref.sex != person.sex:
                continue
            if age_days is not None:
                if ref.age_from_days is not None and age_days < ref.age_from_days:
                    continue
                if ref.age_to_days is not None and age_days > ref.age_to_days:
                    continue
            elif ref.age_from_days is not None or ref.age_to_days is not None:
                continue
            if ref.pregnancy is True or ref.lactation is True:
                continue
            out.append(ref)
        return out

    def apply_reference_values(self, person_id, overwrite=False):
        self._person(person_id)
        created_or_updated = []
        for ref in self.reference_values(person_id):
            model = self.session.scalar(select(PersonNutrientTarget).where(
                PersonNutrientTarget.person_id == person_id,
                PersonNutrientTarget.nutrient_id == ref.nutrient_id,
                PersonNutrientTarget.period == ref.period,
            ))
            if model is not None and not overwrite:
                continue
            if model is None:
                model = PersonNutrientTarget(
                    person_id=person_id,
                    nutrient_id=ref.nutrient_id,
                    period=ref.period,
                )
                self.session.add(model)
            model.minimum = ref.minimum
            model.target = ref.target
            model.maximum = ref.maximum
            model.source = f"{ref.source}:{ref.source_version}" if ref.source_version else ref.source
            created_or_updated.append(model)
        self.session.commit()
        return created_or_updated

    def target(self, person_id, data):
        self._person(person_id)
        model = self.session.scalar(select(PersonNutrientTarget).where(
            PersonNutrientTarget.person_id == person_id,
            PersonNutrientTarget.nutrient_id == data.nutrient_id,
            PersonNutrientTarget.period == data.period,
        ))
        if model is None:
            model = PersonNutrientTarget(person_id=person_id, **data.model_dump()); self.session.add(model)
        else:
            for k,v in data.model_dump().items(): setattr(model,k,v)
        self.session.commit(); self.session.refresh(model); return model

    def targets(self, person_id):
        self._person(person_id); return list(self.session.scalars(select(PersonNutrientTarget).where(PersonNutrientTarget.person_id == person_id)))
