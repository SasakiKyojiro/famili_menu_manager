import pytest
from pydantic import ValidationError

from mealie.fmp.schemas import BioavailabilityRuleCreate, StockLotCreate


def test_stock_lot_requires_exactly_one_source():
    with pytest.raises(ValidationError):
        StockLotCreate(quantity=1)


def test_stock_lot_rejects_two_sources():
    with pytest.raises(ValidationError):
        StockLotCreate(
            food_id="00000000-0000-4000-8000-000000000001",
            prepared_batch_id="00000000-0000-4000-8000-000000000002",
            quantity=1,
        )


def test_bioavailability_factor_range_is_ordered():
    with pytest.raises(ValidationError):
        BioavailabilityRuleCreate(
            nutrient_id="00000000-0000-4000-8000-000000000001",
            trigger_type="NUTRIENT",
            trigger_code="VITAMIN_C",
            factor_min=2,
            factor_max=1,
        )
