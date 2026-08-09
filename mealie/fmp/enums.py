from enum import StrEnum


class InventoryLocationType(StrEnum):
    PANTRY = "PANTRY"
    FRIDGE = "FRIDGE"
    FREEZER = "FREEZER"
    CELLAR = "CELLAR"
    OTHER = "OTHER"


class StockLotStatus(StrEnum):
    ACTIVE = "ACTIVE"
    CONSUMED = "CONSUMED"
    DISCARDED = "DISCARDED"


class StockTransactionType(StrEnum):
    PURCHASE = "PURCHASE"
    CONSUME = "CONSUME"
    PRODUCE = "PRODUCE"
    ADJUST = "ADJUST"
    TRANSFER = "TRANSFER"
    WASTE = "WASTE"
    OPEN = "OPEN"
    RESERVE = "RESERVE"
    RELEASE = "RELEASE"


class FoodDataProvider(StrEnum):
    OPEN_FOOD_FACTS = "OPEN_FOOD_FACTS"
    USDA_FDC = "USDA_FDC"
    FOODON = "FOODON"
    USER = "USER"


class NutrientCategory(StrEnum):
    ENERGY = "ENERGY"
    MACRO = "MACRO"
    VITAMIN = "VITAMIN"
    MINERAL = "MINERAL"
    AMINO_ACID = "AMINO_ACID"
    FATTY_ACID = "FATTY_ACID"
    OTHER = "OTHER"


class NutritionSource(StrEnum):
    USDA = "USDA"
    OPEN_FOOD_FACTS = "OPEN_FOOD_FACTS"
    USER = "USER"
    ESTIMATED = "ESTIMATED"
    CALCULATED = "CALCULATED"


class CalculationType(StrEnum):
    SOURCE = "SOURCE"
    CALCULATED = "CALCULATED"
    ESTIMATED = "ESTIMATED"


class CookingMethod(StrEnum):
    RAW = "RAW"
    BOIL = "BOIL"
    SIMMER = "SIMMER"
    STEAM = "STEAM"
    FRY = "FRY"
    SAUTE = "SAUTE"
    BAKE = "BAKE"
    ROAST = "ROAST"
    GRILL = "GRILL"
    PRESSURE = "PRESSURE"
    MICROWAVE = "MICROWAVE"
    OTHER = "OTHER"


class CookingSessionStatus(StrEnum):
    CREATED = "CREATED"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class CookingStepStatus(StrEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"


class BioavailabilityTriggerType(StrEnum):
    NUTRIENT = "NUTRIENT"
    FOOD = "FOOD"
    FOOD_CATEGORY = "FOOD_CATEGORY"
    BEVERAGE = "BEVERAGE"
    COOKING_METHOD = "COOKING_METHOD"


class EvidenceLevel(StrEnum):
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"
    EXPERIMENTAL = "EXPERIMENTAL"


class Sex(StrEnum):
    FEMALE = "FEMALE"
    MALE = "MALE"
    OTHER = "OTHER"
    UNSPECIFIED = "UNSPECIFIED"


class NutrientTargetPeriod(StrEnum):
    DAY = "DAY"
    WEEK = "WEEK"
