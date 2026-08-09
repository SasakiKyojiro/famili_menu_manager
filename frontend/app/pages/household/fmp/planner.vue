<template>
  <v-container class="narrow-container">
    <BasePageTitle divider>
      <template #title>
        {{ $t("fmp.planner.title") }}
      </template>
      {{ $t("fmp.planner.description") }}
    </BasePageTitle>

    <v-card class="mb-4" variant="outlined">
      <v-card-text>
        <v-select
          v-model="selectedPeople"
          :items="people"
          item-title="name"
          item-value="id"
          chips
          multiple
          clearable
          :label="$t('fmp.planner.people')"
        />
        <v-row>
          <v-col cols="12" sm="4">
            <v-number-input
              v-model="weights.pantry"
              :min="0"
              :step="0.1"
              :label="$t('fmp.planner.pantry-weight')"
            />
          </v-col>
          <v-col cols="12" sm="4">
            <v-number-input
              v-model="weights.expiry"
              :min="0"
              :step="0.1"
              :label="$t('fmp.planner.expiry-weight')"
            />
          </v-col>
          <v-col cols="12" sm="4">
            <v-number-input
              v-model="weights.preference"
              :min="0"
              :step="0.1"
              :label="$t('fmp.planner.preference-weight')"
            />
          </v-col>
        </v-row>
        <div class="d-flex justify-end">
          <BaseButton :loading="recommendLoading" @click="loadRecommendations">
            {{ $t("fmp.planner.recommend") }}
          </BaseButton>
        </div>
      </v-card-text>
    </v-card>

    <v-row v-if="recommendations.length" class="mb-6">
      <v-col v-for="item in recommendations" :key="item.recipeId" cols="12" md="6">
        <v-card class="h-100" :to="recipeRoute(item.recipeId)">
          <v-card-title>
            {{ item.name }}
          </v-card-title>
          <v-card-subtitle>
            {{ $t("fmp.planner.score") }}: {{ item.score.toFixed(2) }} · {{ $t("fmp.planner.pantry-coverage") }}: {{ Math.round(item.pantryCoverage * 100) }}%
          </v-card-subtitle>
          <v-card-text>
            <v-progress-linear :model-value="item.pantryCoverage * 100" color="success" rounded class="mb-3" />
            <v-chip v-if="item.expiringIngredients" color="warning" size="small" class="mr-2">
              {{ $t("fmp.planner.expiring-count", { count: item.expiringIngredients }) }}
            </v-chip>
            <v-chip v-if="item.missingFoodIds.length" size="small">
              {{ $t("fmp.planner.missing-count", { count: item.missingFoodIds.length }) }}
            </v-chip>
            <div v-if="item.reasons.length" class="mt-3 text-body-2 text-medium-emphasis">
              {{ item.reasons.join(" · ") }}
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-card variant="outlined">
      <v-card-title>
        {{ $t("fmp.planner.generate-title") }}
      </v-card-title>
      <v-card-text>
        <v-row>
          <v-col cols="12" sm="4">
            <v-text-field v-model="planForm.startDate" type="date" :label="$t('fmp.planner.start-date')" />
          </v-col>
          <v-col cols="12" sm="4">
            <v-number-input
              v-model="planForm.days"
              :min="1"
              :max="31"
              :label="$t('fmp.planner.days')"
            />
          </v-col>
          <v-col cols="12" sm="4">
            <v-select
              v-model="planForm.entryType"
              :items="entryTypes"
              item-title="label"
              item-value="value"
              :label="$t('fmp.planner.meal-type')"
            />
          </v-col>
        </v-row>
        <v-switch v-model="planForm.createEntries" color="primary" :label="$t('fmp.planner.create-entries')" />
        <div class="d-flex justify-end ga-2">
          <v-btn v-if="generated.length && planForm.createEntries" variant="text" to="/household/mealplan/planner/view">
            {{ $t("fmp.planner.open-meal-plan") }}
          </v-btn>
          <BaseButton :loading="generateLoading" @click="generatePlan">
            {{ $t("fmp.planner.generate") }}
          </BaseButton>
        </div>
      </v-card-text>
    </v-card>

    <v-timeline v-if="generated.length" side="end" density="compact" class="mt-4">
      <v-timeline-item v-for="item in generated" :key="`${item.date}-${item.recipeId}`" dot-color="primary" size="small">
        <template #opposite>
          {{ formatDate(item.date) }}
        </template>
        <v-card :to="recipeRoute(item.recipeId)" variant="tonal">
          <v-card-title class="text-body-1">
            {{ item.recipeName }}
          </v-card-title>
          <v-card-subtitle>
            {{ $t("fmp.planner.score") }}: {{ item.score.toFixed(2) }}
          </v-card-subtitle>
        </v-card>
      </v-timeline-item>
    </v-timeline>
  </v-container>
</template>

<script setup lang="ts">
import { alert } from "~/composables/use-toast";
import { useUserApi } from "~/composables/api";
import type { GeneratedMealPlanItem, PersonProfile, RecipeRecommendation } from "~/lib/api/types/fmp";
import type { RecipeSummary } from "~/lib/api/types/recipe";

const api = useUserApi();
const auth = useMealieAuth();
const i18n = useI18n();
useSeoMeta({ title: i18n.t("fmp.planner.title") });

const people = ref<PersonProfile[]>([]);
const recipes = ref<RecipeSummary[]>([]);
const selectedPeople = ref<string[]>([]);
const recommendations = ref<RecipeRecommendation[]>([]);
const generated = ref<GeneratedMealPlanItem[]>([]);
const recommendLoading = ref(false);
const generateLoading = ref(false);
const weights = reactive({ pantry: 1, expiry: 1.5, preference: 0.5 });
const planForm = reactive({ startDate: localIsoDate(), days: 7, entryType: "dinner", createEntries: true });
const entryTypes = computed(() => [
  { value: "breakfast", label: i18n.t("fmp.planner.breakfast") },
  { value: "lunch", label: i18n.t("fmp.planner.lunch") },
  { value: "dinner", label: i18n.t("fmp.planner.dinner") },
  { value: "side", label: i18n.t("fmp.planner.side") },
]);

function localIsoDate() {
  const d = new Date();
  const offset = d.getTimezoneOffset() * 60000;
  return new Date(d.getTime() - offset).toISOString().slice(0, 10);
}
function formatDate(value: string) { return new Intl.DateTimeFormat(i18n.locale.value, { weekday: "short", month: "short", day: "numeric" }).format(new Date(`${value}T12:00:00`)); }
function recipeRoute(recipeId: string) {
  const recipe = recipes.value.find(item => item.id === recipeId);
  return recipe?.slug ? `/g/${auth.user.value?.groupSlug}/r/${recipe.slug}` : undefined;
}
function requestBase() {
  return { personIds: selectedPeople.value, pantryWeight: weights.pantry, expiryWeight: weights.expiry, preferenceWeight: weights.preference };
}

async function loadRecommendations() {
  recommendLoading.value = true;
  const { data, error } = await api.fmp.recommendations({ ...requestBase(), limit: 12 });
  recommendLoading.value = false;
  if (error) return alert.error(i18n.t("fmp.error"));
  recommendations.value = data || [];
}

async function generatePlan() {
  generateLoading.value = true;
  const { data, error } = await api.fmp.generateMealPlan({
    ...requestBase(), startDate: planForm.startDate, days: planForm.days, entryType: planForm.entryType, createEntries: planForm.createEntries,
  });
  generateLoading.value = false;
  if (error) return alert.error(i18n.t("fmp.error"));
  generated.value = data || [];
  if (planForm.createEntries) alert.success(i18n.t("fmp.planner.created"));
}

onMounted(async () => {
  const [peopleRes, recipeRes] = await Promise.all([api.fmp.people(), api.recipes.getAll(1, -1, { orderBy: "name", orderDirection: "asc" })]);
  people.value = (peopleRes.data || []).filter(person => person.enabled);
  selectedPeople.value = people.value.map(person => person.id);
  recipes.value = recipeRes.data?.items || [];
  await loadRecommendations();
});
</script>
