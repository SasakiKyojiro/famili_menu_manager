<template>
  <v-card v-if="isOwnGroup" variant="tonal" class="my-4 d-print-none">
    <v-card-title class="d-flex align-center flex-wrap ga-2">
      <v-icon>
        {{ $globals.icons.chefHat }}
      </v-icon>
      <span class="flex-grow-1">
        {{ $t("fmp.recipe.title") }}
      </span>
      <v-btn variant="text" size="small" :loading="nutritionLoading" @click="calculateNutrition">
        {{ $t("fmp.recipe.calculate-nutrition") }}
      </v-btn>
      <v-btn color="primary" variant="flat" size="small" :loading="cookingLoading" @click="startTrackedCooking">
        <v-icon start>
          {{ $globals.icons.play }}
        </v-icon>
        {{ $t("fmp.recipe.start-cooking") }}
      </v-btn>
    </v-card-title>
    <v-card-text v-if="profile">
      <div class="text-caption text-medium-emphasis mb-2">
        {{ $t("fmp.recipe.profile-meta", { type: profile.calculationType, confidence: profile.confidence == null ? "—" : Math.round(profile.confidence * 100) + "%" }) }}
      </div>
      <div class="d-flex flex-wrap ga-2">
        <v-chip v-for="value in importantValues" :key="value.nutrientId" size="small" variant="outlined">
          {{ nutrientLabel(value.nutrientId) }}: {{ formatAmount(value.amount) }} {{ nutrientUnit(value.nutrientId) }}
        </v-chip>
      </div>
    </v-card-text>
    <v-card-text v-else class="text-body-2 text-medium-emphasis">
      {{ $t("fmp.recipe.nutrition-hint") }}
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { alert } from "~/composables/use-toast";
import { useUserApi } from "~/composables/api";
import { useLoggedInState } from "~/composables/use-logged-in-state";
import type { Nutrient, NutritionProfile } from "~/lib/api/types/fmp";
import type { NoUndefinedField } from "~/lib/api/types/non-generated";
import type { Recipe } from "~/lib/api/types/recipe";

const props = defineProps<{ recipe: NoUndefinedField<Recipe>; recipeScale: number }>();
const api = useUserApi();
const i18n = useI18n();
const { isOwnGroup } = useLoggedInState();
const profile = ref<NutritionProfile | null>(null);
const nutrients = ref<Nutrient[]>([]);
const nutritionLoading = ref(false);
const cookingLoading = ref(false);

const importantCodes = ["ENERGY", "CALORIES", "PROTEIN", "FAT", "CARBOHYDRATE", "FIBER", "IRON", "CALCIUM", "VITAMIN_C", "VITAMIN_B12"];
const importantValues = computed(() => {
  if (!profile.value) return [];
  const order = new Map(importantCodes.map((code, i) => [code, i]));
  return [...profile.value.values]
    .filter(value => order.has(nutrients.value.find(n => n.id === value.nutrientId)?.code || ""))
    .sort((a, b) => (order.get(nutrients.value.find(n => n.id === a.nutrientId)?.code || "") ?? 999) - (order.get(nutrients.value.find(n => n.id === b.nutrientId)?.code || "") ?? 999))
    .slice(0, 10);
});

function nutrient(id: string) { return nutrients.value.find(item => item.id === id); }
function nutrientLabel(id: string) { return nutrient(id)?.name || id; }
function nutrientUnit(id: string) { return nutrient(id)?.unit || ""; }
function formatAmount(value: number) { return Number(value.toFixed(value >= 100 ? 0 : value >= 10 ? 1 : 2)); }

async function loadExisting() {
  if (!isOwnGroup.value) return;
  const [nutrientRes, profileRes] = await Promise.all([api.fmp.nutrients(), api.fmp.recipeNutrition(props.recipe.id)]);
  nutrients.value = nutrientRes.data || [];
  profile.value = profileRes.data || null;
}

async function calculateNutrition() {
  nutritionLoading.value = true;
  if (!nutrients.value.length) nutrients.value = (await api.fmp.nutrients()).data || [];
  const { data, error } = await api.fmp.calculateRecipeNutrition(props.recipe.id, null, true);
  nutritionLoading.value = false;
  if (error) return alert.error(i18n.t("fmp.recipe.nutrition-error"));
  profile.value = data;
  alert.success(i18n.t("fmp.recipe.nutrition-calculated"));
}

async function startTrackedCooking() {
  cookingLoading.value = true;
  const { data, error } = await api.fmp.createCookingSession(props.recipe.id, props.recipeScale, props.recipe.recipeServings ? Number(props.recipe.recipeServings) * props.recipeScale : null);
  cookingLoading.value = false;
  if (error || !data) return alert.error(i18n.t("fmp.error"));
  await navigateTo(`/household/fmp/cooking/${data.id}`);
}

onMounted(loadExisting);
</script>
