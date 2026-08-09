from __future__ import annotations

from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy import case, select
from sqlalchemy.orm import Session

from mealie.schema.user import PrivateUser

from ..enums import StockLotStatus, StockTransactionType
from ..models import InventoryLocation, InventoryTarget, PreparedFoodBatch, StockLot, StockTransaction
from ..schemas import StockLotCreate
from .common import require_group_food, require_group_unit, require_household, utcnow_naive
from .unit_conversion import UnitConversionService


class InventoryService:
    def __init__(self, session: Session, user: PrivateUser):
        self.session = session
        self.user = user
        self.converter = UnitConversionService(session)

    def _lot(self, lot_id, lock=False) -> StockLot:
        stmt = select(StockLot).where(StockLot.id == lot_id)
        if lock:
            stmt = stmt.with_for_update()
        return require_household(self.session.scalar(stmt), self.user)

    def _location(self, location_id):
        if location_id is None:
            return None
        return require_household(self.session.get(InventoryLocation, location_id), self.user)

    def create_location(self, name, type_, parent_id=None):
        if parent_id:
            self._location(parent_id)
        model = InventoryLocation(household_id=self.user.household_id, name=name, type=type_, parent_id=parent_id)
        self.session.add(model)
        self.session.commit(); self.session.refresh(model)
        return model

    def list_locations(self):
        return list(self.session.scalars(select(InventoryLocation).where(InventoryLocation.household_id == self.user.household_id).order_by(InventoryLocation.name)))

    def create_lot(self, data: StockLotCreate, *, tx_type=StockTransactionType.PURCHASE, source_type=None, source_id=None, commit=True):
        if data.food_id:
            require_group_food(self.session, data.food_id, self.user)
        if data.prepared_batch_id:
            batch = require_household(self.session.get(PreparedFoodBatch, data.prepared_batch_id), self.user)
            if batch is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "prepared batch not found")
        require_group_unit(self.session, data.unit_id, self.user)
        self._location(data.location_id)
        lot = StockLot(household_id=self.user.household_id, status=StockLotStatus.ACTIVE, **data.model_dump())
        self.session.add(lot); self.session.flush()
        self._tx(lot, tx_type, data.quantity, data.unit_id, source_type=source_type, source_id=source_id)
        if commit:
            self.session.commit(); self.session.refresh(lot)
        else:
            self.session.flush()
        return lot

    def list_lots(self, *, food_id=None, active_only=True):
        stmt = select(StockLot).where(StockLot.household_id == self.user.household_id)
        if active_only:
            stmt = stmt.where(StockLot.status == StockLotStatus.ACTIVE, StockLot.quantity > 0)
        if food_id:
            stmt = stmt.where(StockLot.food_id == food_id)
        return list(self.session.scalars(stmt.order_by(StockLot.expires_at, StockLot.best_before, StockLot.created_at)))

    def expiring(self, days=7):
        until = date.today() + timedelta(days=days)
        stmt = select(StockLot).where(
            StockLot.household_id == self.user.household_id,
            StockLot.status == StockLotStatus.ACTIVE,
            StockLot.quantity > 0,
            sa_or_expiry(until),
        ).order_by(StockLot.expires_at, StockLot.best_before)
        return list(self.session.scalars(stmt))

    def upsert_target(self, data):
        require_group_food(self.session, data.food_id, self.user)
        require_group_unit(self.session, data.unit_id, self.user)
        model = self.session.scalar(select(InventoryTarget).where(
            InventoryTarget.household_id == self.user.household_id,
            InventoryTarget.food_id == data.food_id,
        ))
        if model is None:
            model = InventoryTarget(household_id=self.user.household_id, **data.model_dump())
            self.session.add(model)
        else:
            for key, value in data.model_dump().items():
                setattr(model, key, value)
        self.session.commit(); self.session.refresh(model); return model

    def targets(self):
        return list(self.session.scalars(select(InventoryTarget).where(
            InventoryTarget.household_id == self.user.household_id
        ).order_by(InventoryTarget.created_at)))

    def low_stock(self):
        result = []
        for target in self.targets():
            current = 0.0
            for lot in self.list_lots(food_id=target.food_id, active_only=True):
                try:
                    current += self.converter.convert(target.food_id, lot.quantity, lot.unit_id, target.unit_id)
                except HTTPException:
                    continue
            if current + 1e-9 < target.minimum_quantity:
                desired = target.target_quantity if target.target_quantity is not None else target.minimum_quantity
                result.append({
                    "food_id": target.food_id,
                    "current_quantity": current,
                    "minimum_quantity": target.minimum_quantity,
                    "target_quantity": target.target_quantity,
                    "missing_quantity": max(0.0, desired - current),
                    "unit_id": target.unit_id,
                })
        return result

    def _tx(self, lot, type_, quantity, unit_id, *, source_type=None, source_id=None, note=None):
        tx = StockTransaction(
            household_id=self.user.household_id, stock_lot_id=lot.id, type=type_, quantity=quantity,
            unit_id=unit_id, user_id=self.user.id, source_type=source_type, source_id=str(source_id) if source_id else None, note=note,
        )
        self.session.add(tx); self.session.flush()
        return tx

    def transactions(self, lot_id=None):
        stmt = select(StockTransaction).where(StockTransaction.household_id == self.user.household_id)
        if lot_id:
            self._lot(lot_id)
            stmt = stmt.where(StockTransaction.stock_lot_id == lot_id)
        return list(self.session.scalars(stmt.order_by(StockTransaction.created_at.desc())))

    def consume_lot(self, lot_id, quantity, unit_id=None, *, note=None, source_type=None, source_id=None):
        lot = self._lot(lot_id, lock=True)
        if lot.status != StockLotStatus.ACTIVE or lot.quantity <= 0:
            raise HTTPException(status.HTTP_409_CONFLICT, "stock lot is not active")
        target_unit = unit_id or lot.unit_id
        in_lot_units = self.converter.convert(lot.food_id, quantity, target_unit, lot.unit_id) if lot.food_id else quantity
        if in_lot_units > lot.quantity + 1e-9:
            raise HTTPException(status.HTTP_409_CONFLICT, "insufficient stock in lot")
        lot.quantity = max(0.0, lot.quantity - in_lot_units)
        if lot.quantity <= 1e-9:
            lot.quantity = 0.0; lot.status = StockLotStatus.CONSUMED
        tx = self._tx(lot, StockTransactionType.CONSUME, quantity, target_unit, source_type=source_type, source_id=source_id, note=note)
        self.session.commit(); self.session.refresh(lot)
        return tx

    def consume_food(self, food_id, quantity, unit_id=None, *, allow_partial=False, note=None, source_type=None, source_id=None, commit=True):
        require_group_food(self.session, food_id, self.user)
        require_group_unit(self.session, unit_id, self.user)
        stmt = select(StockLot).where(
            StockLot.household_id == self.user.household_id,
            StockLot.food_id == food_id,
            StockLot.status == StockLotStatus.ACTIVE,
            StockLot.quantity > 0,
        ).order_by(
            case((StockLot.expires_at.is_(None), 1), else_=0), StockLot.expires_at,
            case((StockLot.best_before.is_(None), 1), else_=0), StockLot.best_before,
            StockLot.created_at,
        ).with_for_update()
        lots = list(self.session.scalars(stmt))
        remaining = quantity
        txs = []
        for lot in lots:
            if remaining <= 1e-9:
                break
            try:
                lot_available_target = self.converter.convert(food_id, lot.quantity, lot.unit_id, unit_id)
            except HTTPException:
                continue
            take_target = min(remaining, lot_available_target)
            take_lot = self.converter.convert(food_id, take_target, unit_id, lot.unit_id)
            lot.quantity = max(0.0, lot.quantity - take_lot)
            if lot.quantity <= 1e-9:
                lot.quantity = 0.0; lot.status = StockLotStatus.CONSUMED
            txs.append(self._tx(lot, StockTransactionType.CONSUME, take_target, unit_id, source_type=source_type, source_id=source_id, note=note))
            remaining -= take_target
        if remaining > 1e-9 and not allow_partial:
            self.session.rollback()
            raise HTTPException(status.HTTP_409_CONFLICT, f"insufficient stock: missing {remaining:g}")
        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return quantity - max(remaining, 0), txs

    def adjust(self, lot_id, new_quantity, note=None):
        lot = self._lot(lot_id, lock=True)
        delta = new_quantity - lot.quantity
        lot.quantity = new_quantity
        lot.status = StockLotStatus.ACTIVE if new_quantity > 0 else StockLotStatus.CONSUMED
        tx = self._tx(lot, StockTransactionType.ADJUST, delta, lot.unit_id, note=note)
        self.session.commit(); return tx

    def transfer(self, lot_id, location_id, note=None):
        lot = self._lot(lot_id, lock=True); self._location(location_id)
        lot.location_id = location_id
        tx = self._tx(lot, StockTransactionType.TRANSFER, 0, lot.unit_id, note=note)
        self.session.commit(); return tx

    def waste(self, lot_id, quantity, unit_id=None, note=None):
        tx = self.consume_lot(lot_id, quantity, unit_id, note=note)
        tx.type = StockTransactionType.WASTE
        self.session.commit(); return tx


def sa_or_expiry(until):
    from sqlalchemy import and_, or_
    return or_(
        and_(StockLot.expires_at.is_not(None), StockLot.expires_at <= until),
        and_(StockLot.expires_at.is_(None), StockLot.best_before.is_not(None), StockLot.best_before <= until),
    )
