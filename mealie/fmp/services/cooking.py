from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from mealie.schema.user import PrivateUser

from ..enums import CookingSessionStatus, CookingStepStatus, StockTransactionType
from ..models import (
    CookingConsumption,
    CookingSession,
    CookingSessionIngredient,
    CookingSessionStep,
    PreparedFoodBatch,
)
from ..schemas import PreparedBatchCreate, StockLotCreate
from .common import require_group_recipe, require_household, utcnow_naive
from .inventory import InventoryService
from .nutrition import NutritionService


class CookingService:
    def __init__(self, session: Session, user: PrivateUser):
        self.session, self.user = session, user
        self.inventory = InventoryService(session, user)

    def _session(self, session_id, lock=False) -> CookingSession:
        stmt = select(CookingSession).where(CookingSession.id == session_id)
        if lock:
            stmt = stmt.with_for_update()
        return require_household(self.session.scalar(stmt), self.user)

    def create(self, recipe_id, recipe_scale=1.0, planned_servings=None):
        recipe = require_group_recipe(self.session, recipe_id, self.user)
        model = CookingSession(
            household_id=self.user.household_id, recipe_id=recipe.id, user_id=self.user.id,
            recipe_scale=recipe_scale, planned_servings=planned_servings, status=CookingSessionStatus.CREATED,
        )
        self.session.add(model); self.session.flush()
        for ingredient in recipe.recipe_ingredient:
            self.session.add(CookingSessionIngredient(
                session_id=model.id, recipe_ingredient_id=ingredient.id, food_id=ingredient.food_id,
                required_quantity=(ingredient.quantity * recipe_scale if ingredient.quantity is not None else None),
                required_unit_id=ingredient.unit_id, consumed_quantity=0, original_text=ingredient.original_text or ingredient.note,
            ))
        for pos, instruction in enumerate(recipe.recipe_instructions):
            self.session.add(CookingSessionStep(
                session_id=model.id, instruction_id=instruction.id, position=pos,
                status=CookingStepStatus.PENDING,
            ))
        self.session.commit(); self.session.refresh(model); return model

    def list(self, active_only=False):
        stmt = select(CookingSession).where(CookingSession.household_id == self.user.household_id)
        if active_only:
            stmt = stmt.where(CookingSession.status.in_([CookingSessionStatus.CREATED, CookingSessionStatus.IN_PROGRESS, CookingSessionStatus.PAUSED]))
        return list(self.session.scalars(stmt.order_by(CookingSession.created_at.desc())))

    def ingredients(self, session_id):
        self._session(session_id)
        return list(self.session.scalars(select(CookingSessionIngredient).where(CookingSessionIngredient.session_id == session_id).order_by(CookingSessionIngredient.id)))

    def steps(self, session_id):
        self._session(session_id)
        return list(self.session.scalars(select(CookingSessionStep).where(CookingSessionStep.session_id == session_id).order_by(CookingSessionStep.position)))

    def start(self, session_id):
        model = self._session(session_id, lock=True)
        if model.status not in {CookingSessionStatus.CREATED, CookingSessionStatus.PAUSED}:
            raise HTTPException(status.HTTP_409_CONFLICT, f"cannot start session in {model.status}")
        if model.started_at is None:
            model.started_at = utcnow_naive()
        model.status = CookingSessionStatus.IN_PROGRESS
        self.session.commit(); self.session.refresh(model); return model

    def pause(self, session_id):
        model = self._session(session_id, lock=True)
        if model.status != CookingSessionStatus.IN_PROGRESS:
            raise HTTPException(status.HTTP_409_CONFLICT, "only an in-progress session can be paused")
        model.status = CookingSessionStatus.PAUSED
        self.session.commit(); self.session.refresh(model); return model

    def complete_step(self, session_id, step_id):
        model = self._session(session_id, lock=True)
        if model.status != CookingSessionStatus.IN_PROGRESS:
            raise HTTPException(status.HTTP_409_CONFLICT, "session is not in progress")
        step = self.session.get(CookingSessionStep, step_id)
        if step is None or str(step.session_id) != str(session_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "step not found")
        now = utcnow_naive()
        step.started_at = step.started_at or now; step.completed_at = now; step.status = CookingStepStatus.COMPLETED
        model.current_step = step.position
        self.session.commit(); return step

    def consume_ingredient(self, session_id, ingredient_id, quantity=None, allow_partial=False):
        model = self._session(session_id, lock=True)
        if model.status not in {CookingSessionStatus.IN_PROGRESS, CookingSessionStatus.PAUSED}:
            raise HTTPException(status.HTTP_409_CONFLICT, "session is not active")
        ingredient = self.session.get(CookingSessionIngredient, ingredient_id)
        if ingredient is None or str(ingredient.session_id) != str(session_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "session ingredient not found")
        if not ingredient.food_id:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "ingredient is not linked to a food")
        if ingredient.required_quantity is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "ingredient has no numeric quantity")
        remaining = max(0.0, ingredient.required_quantity - ingredient.consumed_quantity)
        requested = min(quantity, remaining) if quantity is not None else remaining
        if requested <= 1e-9:
            return ingredient, []
        consumed, txs = self.inventory.consume_food(
            ingredient.food_id, requested, ingredient.required_unit_id, allow_partial=allow_partial,
            source_type="COOKING_SESSION", source_id=model.id, commit=False,
        )
        for tx in txs:
            self.session.add(CookingConsumption(
                session_ingredient_id=ingredient.id, stock_lot_id=tx.stock_lot_id, stock_transaction_id=tx.id,
                quantity=tx.quantity, unit_id=tx.unit_id,
            ))
        ingredient.consumed_quantity += consumed
        ingredient.consumed_unit_id = ingredient.required_unit_id
        self.session.commit(); self.session.refresh(ingredient)
        return ingredient, txs

    def consume_remaining(self, session_id, allow_partial=False):
        results = []
        for ingredient in self.ingredients(session_id):
            if ingredient.food_id and ingredient.required_quantity and ingredient.consumed_quantity < ingredient.required_quantity:
                results.append(self.consume_ingredient(session_id, ingredient.id, allow_partial=allow_partial))
        return results

    def _make_batch(self, model: CookingSession, output: PreparedBatchCreate, *, completed_instruction_id=None):
        recipe = require_group_recipe(self.session, model.recipe_id, self.user)
        profile_id = None
        try:
            profile = NutritionService(self.session, self.user).calculate_recipe(recipe.id, persist=True)
            profile_id = profile.id
        except Exception:
            # Cooking must still be completable when nutrition data is incomplete/broken.
            self.session.rollback()
            model = self._session(model.id, lock=True)
        batch = PreparedFoodBatch(
            household_id=self.user.household_id, cooking_session_id=model.id, recipe_id=model.recipe_id,
            completed_instruction_id=completed_instruction_id, name=output.name, quantity=output.quantity,
            unit_id=output.unit_id, portions=output.portions, prepared_at=utcnow_naive(), best_before=output.best_before,
            nutrition_profile_id=profile_id,
        )
        self.session.add(batch); self.session.flush()
        lot_data = StockLotCreate(
            prepared_batch_id=batch.id, location_id=output.location_id, quantity=output.quantity, unit_id=output.unit_id,
            produced_at=batch.prepared_at, best_before=output.best_before,
        )
        self.inventory.create_lot(lot_data, tx_type=StockTransactionType.PRODUCE, source_type="COOKING_SESSION", source_id=model.id, commit=False)
        return batch

    def complete(self, session_id, output: PreparedBatchCreate, consume_remaining=True):
        model = self._session(session_id, lock=True)
        if model.status not in {CookingSessionStatus.IN_PROGRESS, CookingSessionStatus.PAUSED}:
            raise HTTPException(status.HTTP_409_CONFLICT, "session is not active")
        if consume_remaining:
            self.consume_remaining(session_id, allow_partial=False)
            model = self._session(session_id, lock=True)
        batch = self._make_batch(model, output)
        model.status = CookingSessionStatus.COMPLETED; model.completed_at = utcnow_naive()
        self.session.commit(); self.session.refresh(batch); return batch

    def cancel(self, session_id, preserve_as_batch: PreparedBatchCreate | None = None):
        model = self._session(session_id, lock=True)
        if model.status in {CookingSessionStatus.COMPLETED, CookingSessionStatus.CANCELLED}:
            raise HTTPException(status.HTTP_409_CONFLICT, "session is already closed")
        batch = None
        if preserve_as_batch:
            completed = self.session.scalar(select(CookingSessionStep).where(
                CookingSessionStep.session_id == session_id, CookingSessionStep.status == CookingStepStatus.COMPLETED
            ).order_by(CookingSessionStep.position.desc()))
            batch = self._make_batch(model, preserve_as_batch, completed_instruction_id=completed.instruction_id if completed else None)
        model.status = CookingSessionStatus.CANCELLED; model.cancelled_at = utcnow_naive()
        self.session.commit()
        return model, batch
