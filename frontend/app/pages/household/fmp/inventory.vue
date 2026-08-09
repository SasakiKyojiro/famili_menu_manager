<template>
  <v-container class="narrow-container">
    <BasePageTitle divider>
      <template #title>
        {{ $t("fmp.inventory.title") }}
      </template>
      {{ $t("fmp.inventory.description") }}
    </BasePageTitle>

    <div class="d-flex flex-wrap ga-2 justify-end mb-4">
      <BaseButton :icon="$globals.icons.home" @click="locationDialog = true">
        {{ $t("fmp.inventory.locations") }}
      </BaseButton>
      <BaseButton :icon="$globals.icons.search" @click="externalDialog = true">
        {{ $t("fmp.external.title") }}
      </BaseButton>
      <BaseButton create @click="lotDialog = true">
        {{ $t("fmp.inventory.add-lot") }}
      </BaseButton>
    </div>

    <v-row class="mb-2">
      <v-col cols="12" sm="4">
        <v-card variant="tonal">
          <v-card-text>
            <div class="text-caption">
              {{ $t("fmp.inventory.active-lots") }}
            </div>
            <div class="text-h5">
              {{ lots.length }}
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="4">
        <v-card variant="tonal" :color="expiringLots.length ? 'warning' : undefined">
          <v-card-text>
            <div class="text-caption">
              {{ $t("fmp.inventory.expiring") }}
            </div>
            <div class="text-h5">
              {{ expiringLots.length }}
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" sm="4">
        <v-card variant="tonal" :color="lowStock.length ? 'error' : undefined">
          <v-card-text>
            <div class="text-caption">
              {{ $t("fmp.inventory.low-stock") }}
            </div>
            <div class="text-h5">
              {{ lowStock.length }}
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-tabs v-model="tab" color="primary" class="mb-2">
      <v-tab value="stock">
        {{ $t("fmp.inventory.stock") }}
      </v-tab>
      <v-tab value="expiring">
        {{ $t("fmp.inventory.expiring") }}
      </v-tab>
      <v-tab value="low">
        {{ $t("fmp.inventory.low-stock") }}
      </v-tab>
      <v-tab value="history">
        {{ $t("fmp.inventory.history") }}
      </v-tab>
    </v-tabs>

    <v-window v-model="tab">
      <v-window-item value="stock">
        <v-data-table
          :headers="lotHeaders"
          :items="lots"
          :loading="loading"
          item-value="id"
        >
          <template #[`item.item`]="{ item }">
            <div class="font-weight-medium">
              {{ lotName(item) }}
            </div>
            <div v-if="item.barcode" class="text-caption text-medium-emphasis">
              {{ item.barcode }}
            </div>
          </template>
          <template #[`item.quantity`]="{ item }">
            {{ formatQuantity(item.quantity, item.unitId) }}
          </template>
          <template #[`item.locationId`]="{ item }">
            {{ locationName(item.locationId) }}
          </template>
          <template #[`item.expiresAt`]="{ item }">
            <v-chip v-if="item.expiresAt || item.bestBefore" size="small" :color="expiryColor(item)">
              {{ formatDate(item.expiresAt || item.bestBefore) }}
            </v-chip>
          </template>
          <template #[`item.actions`]="{ item }">
            <v-btn icon variant="text" @click="openAction(item, 'consume')">
              <v-icon>
                {{ $globals.icons.minus }}
              </v-icon>
              <v-tooltip activator="parent">
                {{ $t("fmp.inventory.consume") }}
              </v-tooltip>
            </v-btn>
            <v-btn icon variant="text" @click="openAction(item, 'waste')">
              <v-icon>
                {{ $globals.icons.delete }}
              </v-icon>
              <v-tooltip activator="parent">
                {{ $t("fmp.inventory.waste") }}
              </v-tooltip>
            </v-btn>
            <v-btn icon variant="text" @click="openAction(item, 'adjust')">
              <v-icon>
                {{ $globals.icons.edit }}
              </v-icon>
              <v-tooltip activator="parent">
                {{ $t("fmp.inventory.adjust") }}
              </v-tooltip>
            </v-btn>
            <v-btn icon variant="text" @click="openAction(item, 'transfer')">
              <v-icon>
                {{ $globals.icons.forward }}
              </v-icon>
              <v-tooltip activator="parent">
                {{ $t("fmp.inventory.transfer") }}
              </v-tooltip>
            </v-btn>
            <v-btn v-if="item.foodId" icon variant="text" @click="openFoodDetails(item.foodId)">
              <v-icon>
                {{ $globals.icons.testTube }}
              </v-icon>
              <v-tooltip activator="parent">
                {{ $t("fmp.nutrition.details") }}
              </v-tooltip>
            </v-btn>
            <v-btn v-if="item.foodId" icon variant="text" @click="openTarget(item.foodId)">
              <v-icon>
                {{ $globals.icons.alertOutline }}
              </v-icon>
              <v-tooltip activator="parent">
                {{ $t("fmp.inventory.target") }}
              </v-tooltip>
            </v-btn>
          </template>
        </v-data-table>
      </v-window-item>

      <v-window-item value="expiring">
        <v-alert v-if="!expiringLots.length" type="success" variant="tonal">
          {{ $t("fmp.inventory.no-expiring") }}
        </v-alert>
        <v-list v-else lines="two">
          <v-list-item v-for="item in expiringLots" :key="item.id">
            <template #prepend>
              <v-icon color="warning">
                {{ $globals.icons.alertCircle }}
              </v-icon>
            </template>
            <v-list-item-title>
              {{ lotName(item) }}
            </v-list-item-title>
            <v-list-item-subtitle>
              {{ formatQuantity(item.quantity, item.unitId) }} · {{ locationName(item.locationId) }} · {{ formatDate(item.expiresAt || item.bestBefore) }}
            </v-list-item-subtitle>
          </v-list-item>
        </v-list>
      </v-window-item>

      <v-window-item value="low">
        <v-alert v-if="!lowStock.length" type="success" variant="tonal">
          {{ $t("fmp.inventory.no-low-stock") }}
        </v-alert>
        <v-data-table v-else :headers="lowHeaders" :items="lowStock" hide-default-footer>
          <template #[`item.foodId`]="{ item }">
            {{ foodName(item.foodId) }}
          </template>
          <template #[`item.currentQuantity`]="{ item }">
            {{ formatQuantity(item.currentQuantity, item.unitId) }}
          </template>
          <template #[`item.minimumQuantity`]="{ item }">
            {{ formatQuantity(item.minimumQuantity, item.unitId) }}
          </template>
          <template #[`item.missingQuantity`]="{ item }">
            {{ formatQuantity(item.missingQuantity, item.unitId) }}
          </template>
          <template #[`item.actions`]="{ item }">
            <v-btn size="small" variant="text" @click="prefillLot(item.foodId, item.missingQuantity, item.unitId)">
              {{ $t("fmp.inventory.restock") }}
            </v-btn>
          </template>
        </v-data-table>
      </v-window-item>

      <v-window-item value="history">
        <v-data-table :headers="historyHeaders" :items="transactions" :loading="loading">
          <template #[`item.createdAt`]="{ item }">
            {{ formatDateTime(item.createdAt) }}
          </template>
          <template #[`item.quantity`]="{ item }">
            {{ formatQuantity(item.quantity, item.unitId) }}
          </template>
          <template #[`item.stockLotId`]="{ item }">
            {{ lotNameById(item.stockLotId) }}
          </template>
        </v-data-table>
      </v-window-item>
    </v-window>

    <BaseDialog v-model="lotDialog" :title="$t('fmp.inventory.add-lot')" :icon="$globals.icons.database" can-submit @submit="createLot">
      <v-card-text>
        <v-form>
          <v-autocomplete
            v-model="lotForm.foodId"
            :items="foods"
            item-title="name"
            item-value="id"
            :label="$t('fmp.food')"
            clearable
          />
          <v-row>
            <v-col cols="7">
              <v-number-input v-model="lotForm.quantity" :min="0" :label="$t('recipe.quantity')" />
            </v-col>
            <v-col cols="5">
              <v-autocomplete
                v-model="lotForm.unitId"
                :items="units"
                :item-title="unitLabel"
                item-value="id"
                :label="$t('recipe.unit')"
                clearable
              />
            </v-col>
          </v-row>
          <v-select
            v-model="lotForm.locationId"
            :items="locations"
            item-title="name"
            item-value="id"
            :label="$t('fmp.inventory.location')"
            clearable
          />
          <v-row>
            <v-col cols="12" sm="6">
              <v-text-field v-model="lotForm.bestBefore" type="date" :label="$t('fmp.inventory.best-before')" />
            </v-col>
            <v-col cols="12" sm="6">
              <v-text-field v-model="lotForm.expiresAt" type="date" :label="$t('fmp.inventory.expires-at')" />
            </v-col>
          </v-row>
          <v-text-field v-model="lotForm.barcode" :label="$t('fmp.external.barcode')" clearable />
          <v-row>
            <v-col cols="7">
              <v-number-input v-model="lotForm.price" :min="0" :label="$t('fmp.inventory.price')" />
            </v-col>
            <v-col cols="5">
              <v-text-field v-model="lotForm.currency" maxlength="3" :label="$t('fmp.inventory.currency')" />
            </v-col>
          </v-row>
        </v-form>
      </v-card-text>
    </BaseDialog>

    <BaseDialog v-model="locationDialog" :title="$t('fmp.inventory.locations')" :icon="$globals.icons.home" can-submit @submit="createLocation">
      <v-card-text>
        <v-row>
          <v-col cols="7">
            <v-text-field v-model="locationForm.name" :label="$t('general.name')" />
          </v-col>
          <v-col cols="5">
            <v-select v-model="locationForm.type" :items="locationTypes" :label="$t('general.type')" />
          </v-col>
        </v-row>
        <v-list v-if="locations.length" density="compact">
          <v-list-item v-for="location in locations" :key="location.id" :title="location.name" :subtitle="location.type">
            <template #append>
              <v-btn icon variant="text" @click.stop="deleteLocation(location.id)">
                <v-icon>
                  {{ $globals.icons.delete }}
                </v-icon>
              </v-btn>
            </template>
          </v-list-item>
        </v-list>
      </v-card-text>
    </BaseDialog>

    <BaseDialog v-model="actionDialog" :title="actionTitle" :icon="$globals.icons.edit" can-submit @submit="submitAction">
      <v-card-text v-if="selectedLot">
        <div class="mb-3 font-weight-medium">
          {{ lotName(selectedLot) }} · {{ formatQuantity(selectedLot.quantity, selectedLot.unitId) }}
        </div>
        <v-number-input
          v-if="actionMode !== 'transfer'"
          v-model="actionQuantity"
          :min="0"
          :label="actionMode === 'adjust' ? $t('fmp.inventory.new-quantity') : $t('recipe.quantity')"
        />
        <v-select
          v-if="actionMode === 'transfer'"
          v-model="actionLocationId"
          :items="locations"
          item-title="name"
          item-value="id"
          :label="$t('fmp.inventory.location')"
          clearable
        />
        <v-text-field v-model="actionNote" :label="$t('fmp.note')" clearable />
      </v-card-text>
    </BaseDialog>

    <BaseDialog v-model="targetDialog" :title="$t('fmp.inventory.target')" :icon="$globals.icons.alertOutline" can-submit @submit="saveTarget">
      <v-card-text>
        <v-row>
          <v-col cols="6">
            <v-number-input v-model="targetForm.minimum" :min="0" :label="$t('fmp.inventory.minimum')" />
          </v-col>
          <v-col cols="6">
            <v-number-input v-model="targetForm.target" :min="0" :label="$t('fmp.inventory.target-quantity')" />
          </v-col>
        </v-row>
        <v-autocomplete
          v-model="targetForm.unitId"
          :items="units"
          :item-title="unitLabel"
          item-value="id"
          :label="$t('recipe.unit')"
          clearable
        />
      </v-card-text>
    </BaseDialog>

    <BaseDialog v-model="foodDetailsDialog" :title="foodName(foodDetailsId)" :icon="$globals.icons.testTube" can-confirm @confirm="foodDetailsDialog = false">
      <v-card-text>
        <v-alert v-if="!foodNutrients.length" type="info" variant="tonal" class="mb-3">
          {{ $t("fmp.nutrition.no-data") }}
        </v-alert>
        <v-table v-else density="compact">
          <thead>
            <tr>
              <th>
                {{ $t("fmp.nutrition.nutrient") }}
              </th>
              <th>
                {{ $t("fmp.nutrition.amount") }}
              </th>
              <th>
                {{ $t("fmp.people.source") }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="value in foodNutrients" :key="value.id">
              <td>
                {{ nutrientLabel(value.nutrientId) }}
              </td>
              <td>
                {{ Number(value.amount.toFixed(3)) }} {{ nutrientUnit(value.nutrientId) }} / {{ value.basisAmount }} {{ value.basisUnit }}
              </td>
              <td>
                {{ value.source }}
              </td>
            </tr>
          </tbody>
        </v-table>
        <v-divider class="my-4" />
        <div class="text-subtitle-2 mb-2">
          {{ $t("fmp.external.title") }}
        </div>
        <v-chip v-for="ref in foodExternalRefs" :key="ref.id" size="small" class="mr-2 mb-2">
          {{ ref.provider }} · {{ ref.externalId }}
        </v-chip>
      </v-card-text>
    </BaseDialog>

    <BaseDialog v-model="externalDialog" :title="$t('fmp.external.title')" :icon="$globals.icons.search" can-confirm @confirm="externalDialog = false">
      <v-card-text>
        <v-alert type="info" variant="tonal" density="compact" class="mb-4">
          {{ $t("fmp.external.description") }}
        </v-alert>
        <v-autocomplete
          v-model="externalFoodId"
          :items="foods"
          item-title="name"
          item-value="id"
          :label="$t('fmp.external.link-to-food')"
          clearable
        />
        <v-row>
          <v-col cols="4">
            <v-select v-model="externalProvider" :items="externalProviders" :label="$t('fmp.external.provider')" />
          </v-col>
          <v-col cols="8">
            <v-text-field v-model="externalQuery" :label="$t('search.search')" @keyup.enter="searchExternal" />
          </v-col>
        </v-row>
        <div class="d-flex justify-end mb-2">
          <BaseButton :loading="externalLoading" @click="searchExternal">
            {{ $t("search.search") }}
          </BaseButton>
        </div>
        <v-list v-if="externalResults.length" lines="two">
          <v-list-item v-for="result in externalResults" :key="`${result.provider}-${result.externalId}`">
            <v-list-item-title>
              {{ result.name }}
            </v-list-item-title>
            <v-list-item-subtitle>
              {{ result.provider }} · {{ result.barcode || result.externalId }}
            </v-list-item-subtitle>
            <template #append>
              <v-btn size="small" color="primary" variant="tonal" :disabled="!externalFoodId" @click="linkExternal(result)">
                {{ $t("fmp.external.link") }}
              </v-btn>
            </template>
          </v-list-item>
        </v-list>
      </v-card-text>
    </BaseDialog>
  </v-container>
</template>

<script setup lang="ts">
import { alert } from "~/composables/use-toast";
import { useUserApi } from "~/composables/api";
import type { IngredientFood, IngredientUnit } from "~/lib/api/types/recipe";
import type { ExternalSearchResult, FoodDataProvider, FoodExternalReference, FoodNutrientValue, InventoryLocation, InventoryLocationType, LowStockItem, Nutrient, PreparedBatch, StockLot, StockTransaction } from "~/lib/api/types/fmp";

const api = useUserApi();
const i18n = useI18n();
useSeoMeta({ title: i18n.t("fmp.inventory.title") });

const tab = ref("stock");
const loading = ref(false);
const lots = ref<StockLot[]>([]);
const expiringLots = ref<StockLot[]>([]);
const lowStock = ref<LowStockItem[]>([]);
const transactions = ref<StockTransaction[]>([]);
const locations = ref<InventoryLocation[]>([]);
const foods = ref<IngredientFood[]>([]);
const units = ref<IngredientUnit[]>([]);
const preparedBatches = ref<PreparedBatch[]>([]);

const lotDialog = ref(false);
const locationDialog = ref(false);
const actionDialog = ref(false);
const targetDialog = ref(false);
const externalDialog = ref(false);
const selectedLot = ref<StockLot | null>(null);
const actionMode = ref<"consume" | "waste" | "adjust" | "transfer">("consume");
const actionQuantity = ref(0);
const actionLocationId = ref<string | null>(null);
const actionNote = ref("");
const selectedTargetFoodId = ref<string | null>(null);
const externalLoading = ref(false);
const externalFoodId = ref<string | null>(null);
const externalProvider = ref<FoodDataProvider>("OPEN_FOOD_FACTS");
const externalQuery = ref("");
const externalResults = ref<ExternalSearchResult[]>([]);
const foodDetailsDialog = ref(false);
const foodDetailsId = ref<string | null>(null);
const foodNutrients = ref<FoodNutrientValue[]>([]);
const foodExternalRefs = ref<FoodExternalReference[]>([]);
const nutrients = ref<Nutrient[]>([]);

const locationTypes: InventoryLocationType[] = ["PANTRY", "FRIDGE", "FREEZER", "CELLAR", "OTHER"];
const externalProviders: FoodDataProvider[] = ["OPEN_FOOD_FACTS", "USDA_FDC"];
const locationForm = reactive({ name: "", type: "PANTRY" as InventoryLocationType });
const lotForm = reactive({
  foodId: null as string | null,
  quantity: 1,
  unitId: null as string | null,
  locationId: null as string | null,
  bestBefore: "",
  expiresAt: "",
  barcode: "",
  price: null as number | null,
  currency: "",
});
const targetForm = reactive({ minimum: 0, target: null as number | null, unitId: null as string | null });

const lotHeaders = computed(() => [
  { title: i18n.t("fmp.food"), value: "item" },
  { title: i18n.t("recipe.quantity"), value: "quantity" },
  { title: i18n.t("fmp.inventory.location"), value: "locationId" },
  { title: i18n.t("fmp.inventory.expires-at"), value: "expiresAt" },
  { title: "", value: "actions", sortable: false, align: "end" as const },
]);
const lowHeaders = computed(() => [
  { title: i18n.t("fmp.food"), value: "foodId" },
  { title: i18n.t("fmp.inventory.current"), value: "currentQuantity" },
  { title: i18n.t("fmp.inventory.minimum"), value: "minimumQuantity" },
  { title: i18n.t("fmp.inventory.missing"), value: "missingQuantity" },
  { title: "", value: "actions", sortable: false },
]);
const historyHeaders = computed(() => [
  { title: i18n.t("general.date"), value: "createdAt" },
  { title: i18n.t("fmp.inventory.item"), value: "stockLotId" },
  { title: i18n.t("general.type"), value: "type" },
  { title: i18n.t("recipe.quantity"), value: "quantity" },
  { title: i18n.t("fmp.note"), value: "note" },
]);

const actionTitle = computed(() => i18n.t(`fmp.inventory.${actionMode.value}`));

function foodName(id?: string | null) {
  return foods.value.find(food => food.id === id)?.name || id || i18n.t("fmp.inventory.prepared-food");
}
function unitLabel(unit: IngredientUnit) {
  return unit.abbreviation || unit.name;
}
function unitName(id?: string | null) {
  const unit = units.value.find(item => item.id === id);
  return unit ? unitLabel(unit) : "";
}
function locationName(id?: string | null) {
  return locations.value.find(item => item.id === id)?.name || "—";
}
function nutrientLabel(id: string) { return nutrients.value.find(item => item.id === id)?.name || id; }
function nutrientUnit(id: string) { return nutrients.value.find(item => item.id === id)?.unit || ""; }
function lotName(item: StockLot) {
  if (item.foodId) return foodName(item.foodId);
  return preparedBatches.value.find(batch => batch.id === item.preparedBatchId)?.name || i18n.t("fmp.inventory.prepared-food");
}
function lotNameById(id: string) {
  const lot = lots.value.find(item => item.id === id);
  return lot ? lotName(lot) : id.slice(0, 8);
}
function formatQuantity(quantity: number, unitId?: string | null) {
  return `${Number(quantity.toFixed(3))}${unitName(unitId) ? ` ${unitName(unitId)}` : ""}`;
}
function formatDate(value?: string | null) {
  if (!value) return "—";
  return new Intl.DateTimeFormat(i18n.locale.value).format(new Date(`${value}T12:00:00`));
}
function formatDateTime(value?: string | null) {
  if (!value) return "—";
  return new Intl.DateTimeFormat(i18n.locale.value, { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}
function expiryColor(item: StockLot) {
  const value = item.expiresAt || item.bestBefore;
  if (!value) return undefined;
  const days = Math.ceil((new Date(`${value}T23:59:59`).getTime() - Date.now()) / 86400000);
  if (days < 0) return "error";
  if (days <= 3) return "warning";
  return undefined;
}

async function refresh() {
  loading.value = true;
  const [lotsRes, expiringRes, lowRes, txRes, locationsRes, foodsRes, unitsRes, batchesRes] = await Promise.all([
    api.fmp.listLots(), api.fmp.expiringLots(7), api.fmp.lowStock(), api.fmp.transactions(), api.fmp.listLocations(),
    api.foods.getAll(1, -1, { orderBy: "name", orderDirection: "asc" }),
    api.units.getAll(1, -1, { orderBy: "name", orderDirection: "asc" }), api.fmp.preparedBatches(),
  ]);
  lots.value = lotsRes.data || [];
  expiringLots.value = expiringRes.data || [];
  lowStock.value = lowRes.data || [];
  transactions.value = txRes.data || [];
  locations.value = locationsRes.data || [];
  foods.value = foodsRes.data?.items || [];
  units.value = unitsRes.data?.items || [];
  preparedBatches.value = batchesRes.data || [];
  loading.value = false;
}

async function createLot() {
  if (!lotForm.foodId || lotForm.quantity <= 0) return;
  const { error } = await api.fmp.createLot({
    foodId: lotForm.foodId,
    quantity: lotForm.quantity,
    unitId: lotForm.unitId,
    locationId: lotForm.locationId,
    bestBefore: lotForm.bestBefore || null,
    expiresAt: lotForm.expiresAt || null,
    barcode: lotForm.barcode || null,
    price: lotForm.price,
    currency: lotForm.currency ? lotForm.currency.toUpperCase() : null,
    purchasedAt: new Date().toISOString(),
  });
  if (error) return alert.error(i18n.t("fmp.error"));
  Object.assign(lotForm, { foodId: null, quantity: 1, unitId: null, locationId: null, bestBefore: "", expiresAt: "", barcode: "", price: null, currency: "" });
  lotDialog.value = false;
  alert.success(i18n.t("fmp.saved"));
  await refresh();
}

async function createLocation() {
  if (!locationForm.name.trim()) return;
  const { error } = await api.fmp.createLocation({ name: locationForm.name.trim(), type: locationForm.type });
  if (error) return alert.error(i18n.t("fmp.error"));
  locationForm.name = "";
  await refresh();
}

async function deleteLocation(id: string) {
  const { error } = await api.fmp.deleteLocation(id);
  if (error) {
    alert.error(i18n.t("fmp.error"));
    return;
  }
  await refresh();
}

function openAction(item: StockLot, mode: typeof actionMode.value) {
  selectedLot.value = item;
  actionMode.value = mode;
  actionQuantity.value = mode === "adjust" ? item.quantity : Math.min(item.quantity, 1);
  actionLocationId.value = item.locationId || null;
  actionNote.value = "";
  actionDialog.value = true;
}

async function submitAction() {
  if (!selectedLot.value) return;
  let result;
  if (actionMode.value === "consume") result = await api.fmp.consumeLot(selectedLot.value.id, actionQuantity.value, selectedLot.value.unitId, actionNote.value || undefined);
  else if (actionMode.value === "waste") result = await api.fmp.wasteLot(selectedLot.value.id, actionQuantity.value, selectedLot.value.unitId, actionNote.value || undefined);
  else if (actionMode.value === "adjust") result = await api.fmp.adjustLot(selectedLot.value.id, actionQuantity.value, actionNote.value || undefined);
  else result = await api.fmp.transferLot(selectedLot.value.id, actionLocationId.value, actionNote.value || undefined);
  if (result.error) return alert.error(i18n.t("fmp.error"));
  actionDialog.value = false;
  await refresh();
}

async function openTarget(foodId: string) {
  selectedTargetFoodId.value = foodId;
  const { data } = await api.fmp.targets();
  const existing = data?.find(item => item.foodId === foodId);
  targetForm.minimum = existing?.minimumQuantity || 0;
  targetForm.target = existing?.targetQuantity ?? null;
  targetForm.unitId = existing?.unitId || null;
  targetDialog.value = true;
}

async function saveTarget() {
  if (!selectedTargetFoodId.value) return;
  const { error } = await api.fmp.setTarget(selectedTargetFoodId.value, targetForm.minimum, targetForm.target, targetForm.unitId);
  if (error) return alert.error(i18n.t("fmp.error"));
  targetDialog.value = false;
  await refresh();
}

function prefillLot(foodId: string, quantity: number, unitId?: string | null) {
  lotForm.foodId = foodId;
  lotForm.quantity = Math.max(quantity, 0.001);
  lotForm.unitId = unitId || null;
  lotDialog.value = true;
}

async function openFoodDetails(foodId: string) {
  foodDetailsId.value = foodId;
  const [valuesRes, refsRes, nutrientsRes] = await Promise.all([api.fmp.foodNutrition(foodId), api.fmp.externalReferences(foodId), nutrients.value.length ? Promise.resolve({ data: nutrients.value }) : api.fmp.nutrients()]);
  foodNutrients.value = valuesRes.data || [];
  foodExternalRefs.value = refsRes.data || [];
  if (!nutrients.value.length) nutrients.value = nutrientsRes.data || [];
  foodDetailsDialog.value = true;
}

async function searchExternal() {
  if (!externalQuery.value.trim()) return;
  externalLoading.value = true;
  const { data, error } = await api.fmp.externalSearch(externalProvider.value, externalQuery.value.trim());
  externalLoading.value = false;
  if (error) return alert.error(i18n.t("fmp.error"));
  externalResults.value = data || [];
}

async function linkExternal(result: ExternalSearchResult) {
  if (!externalFoodId.value) return;
  const { error } = await api.fmp.linkExternal(externalFoodId.value, result.provider, result.externalId, result.barcode);
  if (error) return alert.error(i18n.t("fmp.error"));
  alert.success(i18n.t("fmp.external.linked"));
}

onMounted(refresh);
</script>
