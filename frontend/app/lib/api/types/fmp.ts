export type InventoryLocationType = "PANTRY" | "FRIDGE" | "FREEZER" | "CELLAR" | "OTHER";
export type StockLotStatus = "ACTIVE" | "CONSUMED" | "DISCARDED";
export type StockTransactionType = "PURCHASE" | "CONSUME" | "PRODUCE" | "ADJUST" | "TRANSFER" | "WASTE" | "OPEN" | "RESERVE" | "RELEASE";
export type FoodDataProvider = "OPEN_FOOD_FACTS" | "USDA_FDC" | "FOODON" | "USER";
export type CookingSessionStatus = "CREATED" | "IN_PROGRESS" | "PAUSED" | "COMPLETED" | "CANCELLED";
export type CookingStepStatus = "PENDING" | "IN_PROGRESS" | "COMPLETED" | "SKIPPED";
export type CookingMethod = "RAW" | "BOIL" | "SIMMER" | "STEAM" | "FRY" | "SAUTE" | "BAKE" | "ROAST" | "GRILL" | "PRESSURE" | "MICROWAVE" | "OTHER";
export type Sex = "FEMALE" | "MALE" | "OTHER" | "UNSPECIFIED";
export type NutrientTargetPeriod = "DAY" | "WEEK";

export interface FmpCapabilities {
  inventory: boolean;
  fefo: boolean;
  nutrition: boolean;
  externalFood: string[];
  cookingSessions: boolean;
  preparedBatches: boolean;
  people: boolean;
  bioavailability: boolean;
  mealPlanning: boolean;
  ui: string;
}

export interface InventoryLocation {
  id: string;
  householdId: string;
  name: string;
  type: InventoryLocationType;
  parentId?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface LocationCreate {
  name: string;
  type: InventoryLocationType;
  parentId?: string | null;
}

export interface StockLot {
  id: string;
  householdId: string;
  foodId?: string | null;
  preparedBatchId?: string | null;
  locationId?: string | null;
  quantity: number;
  unitId?: string | null;
  purchasedAt?: string | null;
  producedAt?: string | null;
  openedAt?: string | null;
  bestBefore?: string | null;
  expiresAt?: string | null;
  price?: number | null;
  currency?: string | null;
  status: StockLotStatus;
  barcode?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface StockLotCreate {
  foodId?: string | null;
  preparedBatchId?: string | null;
  locationId?: string | null;
  quantity: number;
  unitId?: string | null;
  purchasedAt?: string | null;
  producedAt?: string | null;
  bestBefore?: string | null;
  expiresAt?: string | null;
  price?: number | null;
  currency?: string | null;
  barcode?: string | null;
}

export interface StockTransaction {
  id: string;
  householdId: string;
  stockLotId: string;
  type: StockTransactionType;
  quantity: number;
  unitId?: string | null;
  userId?: string | null;
  sourceType?: string | null;
  sourceId?: string | null;
  note?: string | null;
  createdAt?: string | null;
}

export interface InventoryTarget {
  id: string;
  householdId: string;
  foodId: string;
  minimumQuantity: number;
  targetQuantity?: number | null;
  unitId?: string | null;
}

export interface LowStockItem {
  foodId: string;
  currentQuantity: number;
  minimumQuantity: number;
  targetQuantity?: number | null;
  missingQuantity: number;
  unitId?: string | null;
}

export interface Nutrient {
  id: string;
  code: string;
  name: string;
  unit: string;
  category: string;
}

export interface FoodNutrientValue {
  id: string;
  foodId: string;
  nutrientId: string;
  amount: number;
  basisAmount: number;
  basisUnit: string;
  minAmount?: number | null;
  maxAmount?: number | null;
  source: string;
  sourceReference?: string | null;
  confidence?: number | null;
}

export interface NutritionProfileValue {
  id: string;
  nutrientId: string;
  amount: number;
  minAmount?: number | null;
  maxAmount?: number | null;
}

export interface NutritionProfile {
  id: string;
  householdId?: string | null;
  foodId?: string | null;
  recipeId?: string | null;
  preparedBatchId?: string | null;
  basisAmount: number;
  basisUnit: string;
  calculationType: string;
  algorithmVersion: string;
  confidence?: number | null;
  values: NutritionProfileValue[];
  createdAt?: string | null;
}

export interface PersonProfile {
  id: string;
  householdId: string;
  userId?: string | null;
  name: string;
  birthDate?: string | null;
  sex?: Sex | null;
  heightCm?: number | null;
  weightKg?: number | null;
  enabled: boolean;
}

export interface PersonUpsert {
  userId?: string | null;
  name: string;
  birthDate?: string | null;
  sex?: Sex | null;
  heightCm?: number | null;
  weightKg?: number | null;
  enabled?: boolean;
}

export interface CodeTag {
  code: string;
  label?: string | null;
  severity?: string | null;
}

export interface PersonPreference {
  id?: string;
  personId?: string;
  foodId: string;
  score: number;
}

export interface NutrientTarget {
  id: string;
  personId: string;
  nutrientId: string;
  minimum?: number | null;
  target?: number | null;
  maximum?: number | null;
  period: NutrientTargetPeriod;
  source?: string | null;
}

export interface RecipeRecommendation {
  recipeId: string;
  name: string;
  score: number;
  pantryCoverage: number;
  expiringIngredients: number;
  missingFoodIds: string[];
  reasons: string[];
}

export interface RecommendationRequest {
  personIds: string[];
  limit?: number;
  pantryWeight?: number;
  expiryWeight?: number;
  preferenceWeight?: number;
}

export interface GenerateMealPlanRequest extends RecommendationRequest {
  startDate: string;
  days: number;
  entryType: string;
  createEntries: boolean;
}

export interface GeneratedMealPlanItem {
  date: string;
  recipeId: string;
  recipeName: string;
  score: number;
  mealPlanId?: number | null;
}

export interface CookingSession {
  id: string;
  householdId: string;
  recipeId: string;
  userId?: string | null;
  recipeScale: number;
  plannedServings?: number | null;
  status: CookingSessionStatus;
  startedAt?: string | null;
  completedAt?: string | null;
  cancelledAt?: string | null;
  currentStep?: number | null;
  createdAt?: string | null;
}

export interface CookingIngredient {
  id: string;
  sessionId: string;
  recipeIngredientId?: string | number | null;
  foodId?: string | null;
  requiredQuantity?: number | null;
  requiredUnitId?: string | null;
  consumedQuantity: number;
  consumedUnitId?: string | null;
  originalText?: string | null;
}

export interface CookingStep {
  id: string;
  sessionId: string;
  instructionId?: string | null;
  position: number;
  status: CookingStepStatus;
  startedAt?: string | null;
  completedAt?: string | null;
  instruction?: { title?: string | null; text?: string | null } | null;
  [key: string]: unknown;
}

export interface PreparedBatch {
  id: string;
  householdId: string;
  cookingSessionId?: string | null;
  recipeId?: string | null;
  completedInstructionId?: string | null;
  name: string;
  quantity: number;
  unitId?: string | null;
  portions?: number | null;
  preparedAt: string;
  bestBefore?: string | null;
  nutritionProfileId?: string | null;
}

export interface PreparedBatchCreate {
  name: string;
  quantity: number;
  unitId?: string | null;
  portions?: number | null;
  bestBefore?: string | null;
  locationId?: string | null;
}

export interface FoodExternalReference {
  id: string;
  foodId: string;
  provider: FoodDataProvider;
  externalId: string;
  barcode?: string | null;
  confidence?: number | null;
  lastSyncedAt?: string | null;
  rawMetadata?: Record<string, unknown> | null;
}

export interface ExternalSearchResult {
  provider: FoodDataProvider;
  externalId: string;
  name: string;
  barcode?: string | null;
  nutrients: Record<string, number>;
  raw: Record<string, unknown>;
}
