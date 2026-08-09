from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..enums import BioavailabilityTriggerType
from ..models import BioavailabilityRule, Nutrient
from ..schemas import BioavailabilityResult


class BioavailabilityService:
    def __init__(self, session: Session): self.session = session

    def evaluate(self, nutrient_amounts: dict[str, float], trigger_codes: list[str]):
        trigger_set = {x.upper() for x in trigger_codes}
        nutrient_set = {x.upper() for x in nutrient_amounts}
        nutrients = {n.code.upper(): n for n in self.session.scalars(select(Nutrient).where(Nutrient.code.in_(nutrient_set)))}
        out = []
        for code, amount in nutrient_amounts.items():
            nutrient = nutrients.get(code.upper())
            if nutrient is None:
                out.append(BioavailabilityResult(nutrient_code=code, original_amount=amount, effective_min=amount, effective_max=amount, applied_rules=0)); continue
            rules = list(self.session.scalars(select(BioavailabilityRule).where(BioavailabilityRule.nutrient_id == nutrient.id)))
            min_factor = max_factor = 1.0; applied = 0
            for rule in rules:
                matched = False
                if rule.trigger_type == BioavailabilityTriggerType.NUTRIENT:
                    matched = rule.trigger_code.upper() in nutrient_set
                else:
                    matched = rule.trigger_code.upper() in trigger_set
                if matched:
                    min_factor *= rule.factor_min; max_factor *= rule.factor_max; applied += 1
            out.append(BioavailabilityResult(
                nutrient_code=code, original_amount=amount, effective_min=amount*min_factor,
                effective_max=amount*max_factor, applied_rules=applied,
            ))
        return out
