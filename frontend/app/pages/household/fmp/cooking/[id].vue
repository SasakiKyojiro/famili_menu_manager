<template>
  <v-container class="narrow-container">
    <BasePageTitle divider>
      <template #title>
        {{ recipe?.name || $t("fmp.cooking.title") }}
      </template>
      {{ $t("fmp.cooking.session") }} · {{ session?.status || "…" }}
    </BasePageTitle>

    <v-alert v-if="loadError" type="error" variant="tonal">
      {{ $t("fmp.cooking.not-found") }}
    </v-alert>

    <template v-if="session">
      <div class="d-flex flex-wrap ga-2 mb-4">
        <BaseButton
          v-if="session.status === 'CREATED' || session.status === 'PAUSED'"
          :icon="$globals.icons.play"
          @click="start"
        >
          {{ $t("fmp.cooking.start") }}
        </BaseButton>
        <BaseButton
          v-if="session.status === 'IN_PROGRESS'"
          :icon="$globals.icons.pending"
          @click="pause"
        >
          {{ $t("fmp.cooking.pause") }}
        </BaseButton>
        <v-spacer />
        <v-btn v-if="isActive" color="error" variant="text" @click="cancelDialog = true">
          {{ $t("fmp.cooking.cancel") }}
        </v-btn>
        <v-btn v-if="isActive" color="success" variant="flat" @click="completeDialog = true">
          {{ $t("fmp.cooking.complete") }}
        </v-btn>
      </div>

      <v-row>
        <v-col cols="12" md="5">
          <v-card variant="outlined" class="mb-4">
            <v-card-title>
              {{ $t("recipe.ingredients") }}
            </v-card-title>
            <v-list lines="two">
              <v-list-item v-for="ingredient in ingredients" :key="ingredient.id">
                <v-list-item-title>
                  {{ ingredientName(ingredient) }}
                </v-list-item-title>
                <v-list-item-subtitle>
                  {{ consumedLabel(ingredient) }}
                </v-list-item-subtitle>
                <template #append>
                  <v-progress-circular
                    v-if="ingredient.requiredQuantity"
                    :model-value="ingredientProgress(ingredient)"
                    :color="ingredientProgress(ingredient) >= 100 ? 'success' : 'primary'"
                    size="32"
                    width="4"
                    class="mr-2"
                  />
                  <v-btn
                    icon
                    variant="text"
                    :disabled="!isActive || !ingredient.foodId || !ingredient.requiredQuantity || ingredientProgress(ingredient) >= 100"
                    @click="consumeIngredient(ingredient)"
                  >
                    <v-icon>
                      {{ $globals.icons.check }}
                    </v-icon>
                    <v-tooltip activator="parent">
                      {{ $t("fmp.cooking.consume") }}
                    </v-tooltip>
                  </v-btn>
                </template>
              </v-list-item>
            </v-list>
          </v-card>
        </v-col>

        <v-col cols="12" md="7">
          <v-card variant="outlined">
            <v-card-title>
              {{ $t("recipe.instructions") }}
            </v-card-title>
            <v-list lines="three">
              <v-list-item v-for="step in steps" :key="step.id" :class="{ 'opacity-60': step.status === 'COMPLETED' }">
                <template #prepend>
                  <v-avatar :color="step.status === 'COMPLETED' ? 'success' : 'primary'" size="32">
                    <v-icon v-if="step.status === 'COMPLETED'" size="small">
                      {{ $globals.icons.check }}
                    </v-icon>
                    <span v-else>
                      {{ step.position + 1 }}
                    </span>
                  </v-avatar>
                </template>
                <v-list-item-title>
                  {{ stepTitle(step.position) }}
                </v-list-item-title>
                <v-list-item-subtitle class="text-wrap">
                  {{ stepText(step.position) }}
                </v-list-item-subtitle>
                <template #append>
                  <v-btn
                    v-if="step.status !== 'COMPLETED'"
                    size="small"
                    variant="tonal"
                    color="primary"
                    :disabled="session.status !== 'IN_PROGRESS'"
                    @click="completeStep(step.id)"
                  >
                    {{ $t("general.done") }}
                  </v-btn>
                </template>
              </v-list-item>
            </v-list>
          </v-card>
        </v-col>
      </v-row>
    </template>

    <BaseDialog v-model="completeDialog" :title="$t('fmp.cooking.complete-title')" :icon="$globals.icons.check" can-submit @submit="completeCooking">
      <v-card-text>
        <v-text-field v-model="output.name" :label="$t('general.name')" />
        <v-row>
          <v-col cols="7">
            <v-number-input v-model="output.quantity" :min="0.001" :label="$t('recipe.quantity')" />
          </v-col>
          <v-col cols="5">
            <v-autocomplete
              v-model="output.unitId"
              :items="units"
              :item-title="unitLabel"
              item-value="id"
              :label="$t('recipe.unit')"
              clearable
            />
          </v-col>
        </v-row>
        <v-row>
          <v-col cols="6">
            <v-number-input v-model="output.portions" :min="0" :label="$t('recipe.servings')" />
          </v-col>
          <v-col cols="6">
            <v-text-field v-model="output.bestBefore" type="date" :label="$t('fmp.inventory.best-before')" />
          </v-col>
        </v-row>
        <v-select
          v-model="output.locationId"
          :items="locations"
          item-title="name"
          item-value="id"
          :label="$t('fmp.inventory.location')"
          clearable
        />
        <v-switch v-model="consumeRemaining" color="primary" :label="$t('fmp.cooking.consume-remaining')" />
      </v-card-text>
    </BaseDialog>

    <BaseDialog
      v-model="cancelDialog"
      :title="$t('fmp.cooking.cancel-title')"
      :icon="$globals.icons.alertCircle"
      color="warning"
      can-submit
      @submit="cancelCooking"
    >
      <v-card-text>
        <v-switch v-model="preserveOnCancel" color="primary" :label="$t('fmp.cooking.preserve-partial')" />
        <template v-if="preserveOnCancel">
          <v-text-field v-model="cancelOutput.name" :label="$t('general.name')" />
          <v-row>
            <v-col cols="7">
              <v-number-input v-model="cancelOutput.quantity" :min="0.001" :label="$t('recipe.quantity')" />
            </v-col>
            <v-col cols="5">
              <v-autocomplete
                v-model="cancelOutput.unitId"
                :items="units"
                :item-title="unitLabel"
                item-value="id"
                :label="$t('recipe.unit')"
                clearable
              />
            </v-col>
          </v-row>
          <v-text-field v-model="cancelOutput.bestBefore" type="date" :label="$t('fmp.inventory.best-before')" />
          <v-select
            v-model="cancelOutput.locationId"
            :items="locations"
            item-title="name"
            item-value="id"
            :label="$t('fmp.inventory.location')"
            clearable
          />
        </template>
      </v-card-text>
    </BaseDialog>
  </v-container>
</template>

<script setup lang="ts">
import { alert } from "~/composables/use-toast";
import { useUserApi } from "~/composables/api";
import type { CookingIngredient, CookingSession, CookingStep, InventoryLocation, PreparedBatchCreate } from "~/lib/api/types/fmp";
import type { IngredientFood, IngredientUnit, Recipe, RecipeSummary } from "~/lib/api/types/recipe";

const api = useUserApi();
const auth = useMealieAuth();
const route = useRoute();
const i18n = useI18n();
const id = route.params.id as string;

const session = ref<CookingSession | null>(null);
const ingredients = ref<CookingIngredient[]>([]);
const steps = ref<CookingStep[]>([]);
const recipe = ref<Recipe | null>(null);
const foods = ref<IngredientFood[]>([]);
const units = ref<IngredientUnit[]>([]);
const locations = ref<InventoryLocation[]>([]);
const loadError = ref(false);
const completeDialog = ref(false);
const cancelDialog = ref(false);
const consumeRemaining = ref(true);
const preserveOnCancel = ref(false);
const output = reactive<PreparedBatchCreate>({ name: "", quantity: 1, unitId: null, portions: null, bestBefore: null, locationId: null });
const cancelOutput = reactive<PreparedBatchCreate>({ name: "", quantity: 1, unitId: null, portions: null, bestBefore: null, locationId: null });

const isActive = computed(() => session.value && ["CREATED", "IN_PROGRESS", "PAUSED"].includes(session.value.status));
useSeoMeta({ title: computed(() => recipe.value?.name || i18n.t("fmp.cooking.title")) });

function unitLabel(unit: IngredientUnit) { return unit.abbreviation || unit.name; }
function unitName(id?: string | null) { const unit = units.value.find(item => item.id === id); return unit ? unitLabel(unit) : ""; }
function ingredientName(ingredient: CookingIngredient) { return ingredient.foodId ? foods.value.find(item => item.id === ingredient.foodId)?.name || ingredient.originalText || i18n.t("fmp.food") : ingredient.originalText || i18n.t("fmp.cooking.unlinked-ingredient"); }
function ingredientProgress(ingredient: CookingIngredient) { return ingredient.requiredQuantity ? Math.min(100, (ingredient.consumedQuantity / ingredient.requiredQuantity) * 100) : 0; }
function consumedLabel(ingredient: CookingIngredient) {
  if (ingredient.requiredQuantity == null) return ingredient.originalText || "—";
  const unit = unitName(ingredient.requiredUnitId);
  return `${Number(ingredient.consumedQuantity.toFixed(3))} / ${Number(ingredient.requiredQuantity.toFixed(3))}${unit ? ` ${unit}` : ""}`;
}
function recipeInstruction(position: number) { return recipe.value?.recipeInstructions?.[position]; }
function stepTitle(position: number) { return recipeInstruction(position)?.title || `${i18n.t("fmp.cooking.step")} ${position + 1}`; }
function stepText(position: number) { return recipeInstruction(position)?.text || ""; }

async function refresh() {
  const [sessionRes, ingredientRes, stepRes, foodRes, unitRes, locationRes] = await Promise.all([
    api.fmp.cookingSession(id), api.fmp.cookingIngredients(id), api.fmp.cookingSteps(id),
    api.foods.getAll(1, -1, { orderBy: "name" }), api.units.getAll(1, -1, { orderBy: "name" }), api.fmp.listLocations(),
  ]);
  if (!sessionRes.data) { loadError.value = true; return; }
  session.value = sessionRes.data;
  ingredients.value = ingredientRes.data || [];
  steps.value = stepRes.data || [];
  foods.value = foodRes.data?.items || [];
  units.value = unitRes.data?.items || [];
  locations.value = locationRes.data || [];

  const { data: recipePage } = await api.recipes.getAll(1, -1, { orderBy: "name" });
  const summary = (recipePage?.items || []).find((item: RecipeSummary) => item.id === session.value?.recipeId);
  if (summary?.slug) {
    const recipeRes = await api.recipes.getOne(summary.slug);
    recipe.value = recipeRes.data || null;
    output.name ||= recipe.value?.name || i18n.t("fmp.cooking.prepared-food");
    cancelOutput.name ||= `${recipe.value?.name || i18n.t("fmp.cooking.prepared-food")} — ${i18n.t("fmp.cooking.partial")}`;
  }
}

async function start() { const { data, error } = await api.fmp.startCooking(id); if (error) return alert.error(i18n.t("fmp.error")); session.value = data; }
async function pause() { const { data, error } = await api.fmp.pauseCooking(id); if (error) return alert.error(i18n.t("fmp.error")); session.value = data; }
async function completeStep(stepId: string) { const { error } = await api.fmp.completeCookingStep(id, stepId); if (error) return alert.error(i18n.t("fmp.error")); await refresh(); }
async function consumeIngredient(ingredient: CookingIngredient) {
  const { error } = await api.fmp.consumeCookingIngredient(id, ingredient.id, null, false);
  if (error) return alert.error(i18n.t("fmp.cooking.not-enough-stock"));
  await refresh();
}
async function completeCooking() {
  if (!output.name.trim() || output.quantity <= 0) return;
  const { error } = await api.fmp.completeCooking(id, { ...output, name: output.name.trim(), bestBefore: output.bestBefore || null }, consumeRemaining.value);
  if (error) return alert.error(i18n.t("fmp.cooking.complete-error"));
  completeDialog.value = false;
  alert.success(i18n.t("fmp.cooking.completed"));
  await navigateTo("/household/fmp/inventory");
}
async function cancelCooking() {
  const preserve = preserveOnCancel.value ? { ...cancelOutput, name: cancelOutput.name.trim(), bestBefore: cancelOutput.bestBefore || null } : null;
  const { error } = await api.fmp.cancelCooking(id, preserve);
  if (error) return alert.error(i18n.t("fmp.error"));
  cancelDialog.value = false;
  alert.success(i18n.t("fmp.cooking.cancelled"));
  await navigateTo(recipe.value?.slug ? `/g/${auth.user.value?.groupSlug}/r/${recipe.value.slug}` : "/");
}

onMounted(refresh);
</script>
