import { BaseAPI } from "../base/base-clients";
import type {
  CodeTag,
  CookingIngredient,
  CookingSession,
  CookingStep,
  ExternalSearchResult,
  FmpCapabilities,
  FoodDataProvider,
  FoodExternalReference,
  FoodNutrientValue,
  GenerateMealPlanRequest,
  GeneratedMealPlanItem,
  InventoryLocation,
  InventoryTarget,
  LocationCreate,
  LowStockItem,
  Nutrient,
  NutrientTarget,
  NutritionProfile,
  PersonPreference,
  PersonProfile,
  PersonUpsert,
  PreparedBatch,
  PreparedBatchCreate,
  RecipeRecommendation,
  RecommendationRequest,
  StockLot,
  StockLotCreate,
  StockTransaction,
} from "~/lib/api/types/fmp";

const base = "/api/fmp";

export class FmpApi extends BaseAPI {
  capabilities() {
    return this.requests.get<FmpCapabilities>(`${base}/capabilities`);
  }

  listLocations() {
    return this.requests.get<InventoryLocation[]>(`${base}/inventory/locations`);
  }

  createLocation(payload: LocationCreate) {
    return this.requests.post<InventoryLocation>(`${base}/inventory/locations`, payload);
  }

  updateLocation(id: string, payload: Partial<LocationCreate>) {
    return this.requests.patch<InventoryLocation>(`${base}/inventory/locations/${id}`, payload);
  }

  deleteLocation(id: string) {
    return this.requests.delete<unknown>(`${base}/inventory/locations/${id}`);
  }

  listLots(activeOnly = true) {
    return this.requests.get<StockLot[]>(`${base}/inventory/lots`, { active_only: activeOnly });
  }

  expiringLots(days = 7) {
    return this.requests.get<StockLot[]>(`${base}/inventory/lots/expiring`, { days });
  }

  createLot(payload: StockLotCreate) {
    return this.requests.post<StockLot>(`${base}/inventory/lots`, payload);
  }

  updateLot(id: string, payload: Partial<StockLotCreate>) {
    return this.requests.patch<StockLot>(`${base}/inventory/lots/${id}`, payload);
  }

  consumeLot(id: string, quantity: number, unitId?: string | null, note?: string) {
    return this.requests.post<StockTransaction>(`${base}/inventory/lots/${id}/consume`, { quantity, unitId, note });
  }

  wasteLot(id: string, quantity: number, unitId?: string | null, note?: string) {
    return this.requests.post<StockTransaction>(`${base}/inventory/lots/${id}/waste`, { quantity, unitId, note });
  }

  adjustLot(id: string, newQuantity: number, note?: string) {
    return this.requests.post<StockTransaction>(`${base}/inventory/lots/${id}/adjust`, { newQuantity, note });
  }

  transferLot(id: string, locationId?: string | null, note?: string) {
    return this.requests.post<StockTransaction>(`${base}/inventory/lots/${id}/transfer`, { locationId, note });
  }

  transactions(lotId?: string) {
    return this.requests.get<StockTransaction[]>(`${base}/inventory/transactions`, lotId ? { lot_id: lotId } : undefined);
  }

  targets() {
    return this.requests.get<InventoryTarget[]>(`${base}/inventory/targets`);
  }

  lowStock() {
    return this.requests.get<LowStockItem[]>(`${base}/inventory/low-stock`);
  }

  setTarget(foodId: string, minimumQuantity: number, targetQuantity?: number | null, unitId?: string | null) {
    return this.requests.put<InventoryTarget>(`${base}/inventory/targets/${foodId}`, {
      foodId,
      minimumQuantity,
      targetQuantity,
      unitId,
    });
  }

  deleteTarget(foodId: string) {
    return this.requests.delete<unknown>(`${base}/inventory/targets/${foodId}`);
  }

  nutrients() {
    return this.requests.get<Nutrient[]>(`${base}/nutrition/nutrients`);
  }

  foodNutrition(foodId: string) {
    return this.requests.get<FoodNutrientValue[]>(`${base}/nutrition/foods/${foodId}`);
  }

  externalReferences(foodId: string) {
    return this.requests.get<FoodExternalReference[]>(`${base}/foods/${foodId}/external-references`);
  }

  recipeNutrition(recipeId: string) {
    return this.requests.get<NutritionProfile>(`${base}/nutrition/recipes/${recipeId}`);
  }

  calculateRecipeNutrition(recipeId: string, cookingMethod?: string | null, persist = true) {
    return this.requests.post<NutritionProfile>(`${base}/nutrition/recipes/${recipeId}/calculate`, {
      cookingMethod,
      persist,
    });
  }

  externalSearch(provider: FoodDataProvider, query: string, limit = 20) {
    return this.requests.get<ExternalSearchResult[]>(`${base}/external-food/search`, { provider, q: query, limit });
  }

  barcode(barcode: string) {
    return this.requests.get<ExternalSearchResult | null>(`${base}/external-food/barcode/${encodeURIComponent(barcode)}`);
  }

  linkExternal(foodId: string, provider: FoodDataProvider, externalId: string, barcode?: string | null) {
    return this.requests.post(`${base}/foods/${foodId}/external/${provider}/${encodeURIComponent(externalId)}${barcode ? `?barcode=${encodeURIComponent(barcode)}` : ""}`, {});
  }

  people() {
    return this.requests.get<PersonProfile[]>(`${base}/people`);
  }

  createPerson(payload: PersonUpsert) {
    return this.requests.post<PersonProfile>(`${base}/people`, payload);
  }

  updatePerson(id: string, payload: Partial<PersonUpsert>) {
    return this.requests.patch<PersonProfile>(`${base}/people/${id}`, payload);
  }

  deletePerson(id: string) {
    return this.requests.delete<unknown>(`${base}/people/${id}`);
  }

  allergens(personId: string) {
    return this.requests.get<CodeTag[]>(`${base}/people/${personId}/allergens`);
  }

  setAllergen(personId: string, code: string, label?: string | null, severity?: string | null) {
    return this.requests.put<CodeTag>(`${base}/people/${personId}/allergens/${encodeURIComponent(code)}`, { code, label, severity });
  }

  deleteAllergen(personId: string, code: string) {
    return this.requests.delete<unknown>(`${base}/people/${personId}/allergens/${encodeURIComponent(code)}`);
  }

  restrictions(personId: string) {
    return this.requests.get<CodeTag[]>(`${base}/people/${personId}/restrictions`);
  }

  setRestriction(personId: string, code: string, label?: string | null) {
    return this.requests.put<CodeTag>(`${base}/people/${personId}/restrictions/${encodeURIComponent(code)}`, { code, label });
  }

  deleteRestriction(personId: string, code: string) {
    return this.requests.delete<unknown>(`${base}/people/${personId}/restrictions/${encodeURIComponent(code)}`);
  }

  preferences(personId: string) {
    return this.requests.get<PersonPreference[]>(`${base}/people/${personId}/preferences`);
  }

  setPreference(personId: string, foodId: string, score: number) {
    return this.requests.put<PersonPreference>(`${base}/people/${personId}/preferences/${foodId}`, { foodId, score });
  }

  deletePreference(personId: string, foodId: string) {
    return this.requests.delete<unknown>(`${base}/people/${personId}/preferences/${foodId}`);
  }

  nutrientTargets(personId: string) {
    return this.requests.get<NutrientTarget[]>(`${base}/people/${personId}/nutrient-targets`);
  }

  setNutrientTarget(personId: string, nutrientId: string, payload: { minimum?: number | null; target?: number | null; maximum?: number | null; period?: "DAY" | "WEEK"; source?: string | null }) {
    return this.requests.put<NutrientTarget>(`${base}/people/${personId}/nutrient-targets/${nutrientId}`, {
      nutrientId,
      ...payload,
    });
  }

  deleteNutrientTarget(personId: string, nutrientId: string) {
    return this.requests.delete<unknown>(`${base}/people/${personId}/nutrient-targets/${nutrientId}`);
  }

  applyReferenceValues(personId: string, overwrite = false) {
    return this.requests.post<NutrientTarget[]>(`${base}/people/${personId}/nutrient-targets/apply-reference-values`, { overwrite });
  }

  recommendations(payload: RecommendationRequest) {
    return this.requests.post<RecipeRecommendation[]>(`${base}/recommendations/recipes`, payload);
  }

  generateMealPlan(payload: GenerateMealPlanRequest) {
    return this.requests.post<GeneratedMealPlanItem[]>(`${base}/recommendations/meal-plan`, payload);
  }

  preparedBatches() {
    return this.requests.get<PreparedBatch[]>(`${base}/prepared-batches`);
  }

  cookingSessions(activeOnly = false) {
    return this.requests.get<CookingSession[]>(`${base}/cooking/sessions`, { active_only: activeOnly });
  }

  createCookingSession(recipeId: string, recipeScale = 1, plannedServings?: number | null) {
    return this.requests.post<CookingSession>(`${base}/cooking/sessions`, { recipeId, recipeScale, plannedServings });
  }

  cookingSession(id: string) {
    return this.requests.get<CookingSession>(`${base}/cooking/sessions/${id}`);
  }

  cookingIngredients(id: string) {
    return this.requests.get<CookingIngredient[]>(`${base}/cooking/sessions/${id}/ingredients`);
  }

  cookingSteps(id: string) {
    return this.requests.get<CookingStep[]>(`${base}/cooking/sessions/${id}/steps`);
  }

  startCooking(id: string) {
    return this.requests.post<CookingSession>(`${base}/cooking/sessions/${id}/start`, {});
  }

  pauseCooking(id: string) {
    return this.requests.post<CookingSession>(`${base}/cooking/sessions/${id}/pause`, {});
  }

  completeCookingStep(sessionId: string, stepId: string) {
    return this.requests.post<CookingStep>(`${base}/cooking/sessions/${sessionId}/steps/${stepId}/complete`, {});
  }

  consumeCookingIngredient(sessionId: string, ingredientId: string, quantity?: number | null, allowPartial = false) {
    return this.requests.post<CookingIngredient>(`${base}/cooking/sessions/${sessionId}/ingredients/${ingredientId}/consume`, {
      quantity,
      allowPartial,
    });
  }

  completeCooking(sessionId: string, output: PreparedBatchCreate, consumeRemaining = true) {
    return this.requests.post<PreparedBatch>(`${base}/cooking/sessions/${sessionId}/complete`, { output, consumeRemaining });
  }

  cancelCooking(sessionId: string, preserveAsBatch?: PreparedBatchCreate | null) {
    return this.requests.post<{ session: CookingSession; preparedBatch?: PreparedBatch | null }>(`${base}/cooking/sessions/${sessionId}/cancel`, {
      preserveAsBatch,
    });
  }
}
