<template>
  <v-container class="narrow-container">
    <BasePageTitle divider>
      <template #title>
        {{ $t("fmp.people.title") }}
      </template>
      {{ $t("fmp.people.description") }}
    </BasePageTitle>

    <div class="d-flex justify-end mb-4">
      <BaseButton create @click="openCreate">
        {{ $t("fmp.people.add") }}
      </BaseButton>
    </div>

    <v-alert v-if="!people.length && !loading" type="info" variant="tonal">
      {{ $t("fmp.people.empty") }}
    </v-alert>

    <v-row>
      <v-col v-for="person in people" :key="person.id" cols="12" md="6">
        <v-card class="h-100">
          <v-card-title class="d-flex align-center">
            <v-icon class="mr-2">
              {{ $globals.icons.user }}
            </v-icon>
            <span class="flex-grow-1">
              {{ person.name }}
            </span>
            <v-chip size="small" :color="person.enabled ? 'success' : undefined">
              {{ person.enabled ? $t("general.enabled") : $t("general.disabled") }}
            </v-chip>
          </v-card-title>
          <v-card-subtitle>
            {{ person.birthDate ? formatDate(person.birthDate) : $t("fmp.people.no-birth-date") }}
            <span v-if="person.sex">
              · {{ sexLabel(person.sex) }}
            </span>
          </v-card-subtitle>
          <v-card-text>
            <div v-if="person.heightCm || person.weightKg" class="text-body-2 mb-2">
              <span v-if="person.heightCm">
                {{ person.heightCm }} cm
              </span>
              <span v-if="person.heightCm && person.weightKg">
                ·
              </span>
              <span v-if="person.weightKg">
                {{ person.weightKg }} kg
              </span>
            </div>
            <v-chip-group>
              <v-chip v-for="a in metadata[person.id]?.allergens || []" :key="`a-${a.code}`" color="error" size="small">
                {{ a.label || a.code }}
              </v-chip>
              <v-chip v-for="r in metadata[person.id]?.restrictions || []" :key="`r-${r.code}`" color="warning" size="small">
                {{ r.label || r.code }}
              </v-chip>
            </v-chip-group>
            <div class="text-caption mt-2">
              {{ $t("fmp.people.targets-count", { count: metadata[person.id]?.targets?.length || 0 }) }}
              · {{ $t("fmp.people.preferences-count", { count: metadata[person.id]?.preferences?.length || 0 }) }}
            </div>
          </v-card-text>
          <v-card-actions>
            <v-btn variant="text" @click="openDetails(person)">
              {{ $t("general.edit") }}
            </v-btn>
            <v-spacer />
            <v-btn icon variant="text" color="error" @click="removePerson(person)">
              <v-icon>
                {{ $globals.icons.delete }}
              </v-icon>
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <BaseDialog v-model="personDialog" :title="editingPerson ? $t('fmp.people.edit') : $t('fmp.people.add')" :icon="$globals.icons.user" can-submit @submit="savePerson">
      <v-card-text>
        <v-text-field v-model="personForm.name" :label="$t('general.name')" autofocus />
        <v-row>
          <v-col cols="12" sm="6">
            <v-text-field v-model="personForm.birthDate" type="date" :label="$t('fmp.people.birth-date')" />
          </v-col>
          <v-col cols="12" sm="6">
            <v-select
              v-model="personForm.sex"
              :items="sexOptions"
              item-title="label"
              item-value="value"
              :label="$t('fmp.people.sex')"
              clearable
            />
          </v-col>
        </v-row>
        <v-row>
          <v-col cols="6">
            <v-number-input v-model="personForm.heightCm" :min="0" :label="$t('fmp.people.height')" />
          </v-col>
          <v-col cols="6">
            <v-number-input v-model="personForm.weightKg" :min="0" :label="$t('fmp.people.weight')" />
          </v-col>
        </v-row>
        <v-switch v-model="personForm.enabled" color="primary" :label="$t('general.enabled')" />
      </v-card-text>
    </BaseDialog>

    <BaseDialog v-model="detailsDialog" :title="selectedPerson?.name || ''" :icon="$globals.icons.group" can-confirm @confirm="detailsDialog = false">
      <v-card-text v-if="selectedPerson">
        <div class="d-flex justify-end mb-2">
          <v-btn variant="text" @click="detailsDialog = false; personDialog = true">
            {{ $t("fmp.people.edit") }}
          </v-btn>
        </div>
        <v-tabs v-model="detailsTab" color="primary">
          <v-tab value="allergens">
            {{ $t("fmp.people.allergens") }}
          </v-tab>
          <v-tab value="restrictions">
            {{ $t("fmp.people.restrictions") }}
          </v-tab>
          <v-tab value="preferences">
            {{ $t("fmp.people.preferences") }}
          </v-tab>
          <v-tab value="targets">
            {{ $t("fmp.people.targets") }}
          </v-tab>
        </v-tabs>
        <v-window v-model="detailsTab" class="mt-3">
          <v-window-item value="allergens">
            <div class="d-flex ga-2 align-center mb-3">
              <v-text-field v-model="tagCode" density="compact" hide-details :label="$t('fmp.people.code')" />
              <v-text-field v-model="tagLabel" density="compact" hide-details :label="$t('fmp.people.label')" />
              <v-btn color="primary" @click="addAllergen">
                {{ $t("general.add") }}
              </v-btn>
            </div>
            <v-list density="compact">
              <v-list-item v-for="item in selectedMeta.allergens" :key="item.code" :title="item.label || item.code" :subtitle="item.code">
                <template #append>
                  <v-btn icon variant="text" @click="deleteAllergen(item.code)">
                    <v-icon>
                      {{ $globals.icons.delete }}
                    </v-icon>
                  </v-btn>
                </template>
              </v-list-item>
            </v-list>
          </v-window-item>

          <v-window-item value="restrictions">
            <div class="d-flex ga-2 align-center mb-3">
              <v-text-field v-model="tagCode" density="compact" hide-details :label="$t('fmp.people.code')" />
              <v-text-field v-model="tagLabel" density="compact" hide-details :label="$t('fmp.people.label')" />
              <v-btn color="primary" @click="addRestriction">
                {{ $t("general.add") }}
              </v-btn>
            </div>
            <v-list density="compact">
              <v-list-item v-for="item in selectedMeta.restrictions" :key="item.code" :title="item.label || item.code" :subtitle="item.code">
                <template #append>
                  <v-btn icon variant="text" @click="deleteRestriction(item.code)">
                    <v-icon>
                      {{ $globals.icons.delete }}
                    </v-icon>
                  </v-btn>
                </template>
              </v-list-item>
            </v-list>
          </v-window-item>

          <v-window-item value="preferences">
            <div class="d-flex ga-2 align-center mb-3">
              <v-autocomplete
                v-model="preferenceFoodId"
                class="flex-grow-1"
                :items="foods"
                item-title="name"
                item-value="id"
                density="compact"
                hide-details
                :label="$t('fmp.food')"
              />
              <v-select
                v-model="preferenceScore"
                :items="preferenceScores"
                item-title="label"
                item-value="value"
                density="compact"
                hide-details
                style="max-width: 170px"
              />
              <v-btn color="primary" @click="savePreference">
                {{ $t("general.add") }}
              </v-btn>
            </div>
            <v-list density="compact">
              <v-list-item v-for="item in selectedMeta.preferences" :key="item.foodId" :title="foodName(item.foodId)" :subtitle="preferenceLabel(item.score)">
                <template #append>
                  <v-btn icon variant="text" @click="deletePreference(item.foodId)">
                    <v-icon>
                      {{ $globals.icons.delete }}
                    </v-icon>
                  </v-btn>
                </template>
              </v-list-item>
            </v-list>
          </v-window-item>

          <v-window-item value="targets">
            <v-card variant="tonal" class="mb-3">
              <v-card-text>
                <v-autocomplete
                  v-model="targetForm.nutrientId"
                  :items="nutrients"
                  item-title="name"
                  item-value="id"
                  density="compact"
                  :label="$t('fmp.nutrition.nutrient')"
                />
                <v-row>
                  <v-col cols="4">
                    <v-number-input v-model="targetForm.minimum" :label="$t('fmp.people.minimum')" />
                  </v-col>
                  <v-col cols="4">
                    <v-number-input v-model="targetForm.target" :label="$t('fmp.people.target-value')" />
                  </v-col>
                  <v-col cols="4">
                    <v-number-input v-model="targetForm.maximum" :label="$t('fmp.people.maximum')" />
                  </v-col>
                </v-row>
                <v-row>
                  <v-col cols="6">
                    <v-select
                      v-model="targetForm.period"
                      :items="targetPeriods"
                      item-title="label"
                      item-value="value"
                      :label="$t('fmp.people.period')"
                    />
                  </v-col>
                  <v-col cols="6" class="d-flex align-center justify-end">
                    <v-btn color="primary" variant="tonal" @click="saveTarget">
                      {{ $t('general.save') }}
                    </v-btn>
                  </v-col>
                </v-row>
              </v-card-text>
            </v-card>
            <div class="d-flex flex-wrap ga-2 justify-end mb-3">
              <v-btn variant="tonal" color="primary" @click="applyReferenceValues(false)">
                {{ $t("fmp.people.apply-reference") }}
              </v-btn>
              <v-btn variant="text" @click="applyReferenceValues(true)">
                {{ $t("fmp.people.reapply-reference") }}
              </v-btn>
            </div>
            <v-alert v-if="!selectedMeta.targets.length" type="info" variant="tonal" class="mb-3">
              {{ $t("fmp.people.no-targets") }}
            </v-alert>
            <v-data-table v-else :headers="targetHeaders" :items="selectedMeta.targets" density="compact" hide-default-footer>
              <template #[`item.nutrientId`]="{ item }">
                {{ nutrientName(item.nutrientId) }}
              </template>
              <template #[`item.range`]="{ item }">
                {{ targetRange(item) }}
              </template>
              <template #[`item.actions`]="{ item }">
                <v-btn icon variant="text" @click="deleteTarget(item.nutrientId)">
                  <v-icon>
                    {{ $globals.icons.delete }}
                  </v-icon>
                </v-btn>
              </template>
            </v-data-table>
          </v-window-item>
        </v-window>
      </v-card-text>
    </BaseDialog>
  </v-container>
</template>

<script setup lang="ts">
import { alert } from "~/composables/use-toast";
import { useUserApi } from "~/composables/api";
import type { IngredientFood } from "~/lib/api/types/recipe";
import type { CodeTag, Nutrient, NutrientTarget, PersonPreference, PersonProfile, Sex } from "~/lib/api/types/fmp";

interface PersonMeta {
  allergens: CodeTag[];
  restrictions: CodeTag[];
  preferences: PersonPreference[];
  targets: NutrientTarget[];
}

const api = useUserApi();
const i18n = useI18n();
useSeoMeta({ title: i18n.t("fmp.people.title") });

const loading = ref(false);
const people = ref<PersonProfile[]>([]);
const foods = ref<IngredientFood[]>([]);
const nutrients = ref<Nutrient[]>([]);
const metadata = reactive<Record<string, PersonMeta>>({});
const personDialog = ref(false);
const detailsDialog = ref(false);
const detailsTab = ref("allergens");
const editingPerson = ref<PersonProfile | null>(null);
const selectedPerson = ref<PersonProfile | null>(null);
const tagCode = ref("");
const tagLabel = ref("");
const preferenceFoodId = ref<string | null>(null);
const preferenceScore = ref(1);
const targetForm = reactive({ nutrientId: null as string | null, minimum: null as number | null, target: null as number | null, maximum: null as number | null, period: "DAY" as "DAY" | "WEEK" });
const personForm = reactive({ name: "", birthDate: "", sex: null as Sex | null, heightCm: null as number | null, weightKg: null as number | null, enabled: true });

const sexOptions = computed(() => [
  { value: "FEMALE", label: i18n.t("fmp.people.female") },
  { value: "MALE", label: i18n.t("fmp.people.male") },
  { value: "OTHER", label: i18n.t("fmp.people.other") },
  { value: "UNSPECIFIED", label: i18n.t("fmp.people.unspecified") },
]);
const preferenceScores = computed(() => [
  { value: 1, label: i18n.t("fmp.people.likes") },
  { value: 0.5, label: i18n.t("fmp.people.somewhat-likes") },
  { value: 0, label: i18n.t("fmp.people.neutral") },
  { value: -0.5, label: i18n.t("fmp.people.dislikes") },
  { value: -1, label: i18n.t("fmp.people.avoid") },
]);
const targetPeriods = computed(() => [{ value: "DAY", label: i18n.t("fmp.people.day") }, { value: "WEEK", label: i18n.t("fmp.people.week") }]);
const targetHeaders = computed(() => [
  { title: i18n.t("fmp.nutrition.nutrient"), value: "nutrientId" },
  { title: i18n.t("fmp.people.target-range"), value: "range" },
  { title: i18n.t("fmp.people.period"), value: "period" },
  { title: i18n.t("fmp.people.source"), value: "source" },
  { title: "", value: "actions", sortable: false },
]);
const selectedMeta = computed<PersonMeta>(() => selectedPerson.value ? metadata[selectedPerson.value.id] || emptyMeta() : emptyMeta());

function emptyMeta(): PersonMeta { return { allergens: [], restrictions: [], preferences: [], targets: [] }; }
function formatDate(value: string) { return new Intl.DateTimeFormat(i18n.locale.value).format(new Date(`${value}T12:00:00`)); }
function foodName(id: string) { return foods.value.find(item => item.id === id)?.name || id; }
function nutrientName(id: string) { const n = nutrients.value.find(item => item.id === id); return n ? `${n.name} (${n.unit})` : id; }
function sexLabel(value: Sex) { return sexOptions.value.find(item => item.value === value)?.label || value; }
function preferenceLabel(value: number) { return preferenceScores.value.find(item => item.value === value)?.label || String(value); }
function targetRange(item: NutrientTarget) {
  const nutrient = nutrients.value.find(n => n.id === item.nutrientId);
  const unit = nutrient?.unit || "";
  return [item.minimum != null ? `≥ ${item.minimum}` : null, item.target != null ? `≈ ${item.target}` : null, item.maximum != null ? `≤ ${item.maximum}` : null].filter(Boolean).join(" / ") + (unit ? ` ${unit}` : "");
}

async function loadMeta(personId: string) {
  const [a, r, p, t] = await Promise.all([api.fmp.allergens(personId), api.fmp.restrictions(personId), api.fmp.preferences(personId), api.fmp.nutrientTargets(personId)]);
  metadata[personId] = { allergens: a.data || [], restrictions: r.data || [], preferences: p.data || [], targets: t.data || [] };
}

async function refresh() {
  loading.value = true;
  const [peopleRes, foodsRes, nutrientsRes] = await Promise.all([
    api.fmp.people(), api.foods.getAll(1, -1, { orderBy: "name", orderDirection: "asc" }), api.fmp.nutrients(),
  ]);
  people.value = peopleRes.data || [];
  foods.value = foodsRes.data?.items || [];
  nutrients.value = nutrientsRes.data || [];
  await Promise.all(people.value.map(person => loadMeta(person.id)));
  loading.value = false;
}

function openCreate() {
  editingPerson.value = null;
  Object.assign(personForm, { name: "", birthDate: "", sex: null, heightCm: null, weightKg: null, enabled: true });
  personDialog.value = true;
}

function openDetails(person: PersonProfile) {
  selectedPerson.value = person;
  editingPerson.value = person;
  Object.assign(personForm, { name: person.name, birthDate: person.birthDate || "", sex: person.sex || null, heightCm: person.heightCm ?? null, weightKg: person.weightKg ?? null, enabled: person.enabled });
  detailsTab.value = "allergens";
  detailsDialog.value = true;
}

async function savePerson() {
  if (!personForm.name.trim()) return;
  const payload = { name: personForm.name.trim(), birthDate: personForm.birthDate || null, sex: personForm.sex, heightCm: personForm.heightCm, weightKg: personForm.weightKg, enabled: personForm.enabled };
  const result = editingPerson.value ? await api.fmp.updatePerson(editingPerson.value.id, payload) : await api.fmp.createPerson(payload);
  if (result.error) return alert.error(i18n.t("fmp.error"));
  personDialog.value = false;
  await refresh();
}

async function removePerson(person: PersonProfile) {
  const { error } = await api.fmp.deletePerson(person.id);
  if (error) return alert.error(i18n.t("fmp.error"));
  await refresh();
}

async function addAllergen() {
  if (!selectedPerson.value || !tagCode.value.trim()) return;
  const { error } = await api.fmp.setAllergen(selectedPerson.value.id, tagCode.value.trim().toUpperCase(), tagLabel.value.trim() || null);
  if (error) return alert.error(i18n.t("fmp.error"));
  tagCode.value = ""; tagLabel.value = ""; await loadMeta(selectedPerson.value.id);
}
async function deleteAllergen(code: string) { if (selectedPerson.value) { await api.fmp.deleteAllergen(selectedPerson.value.id, code); await loadMeta(selectedPerson.value.id); } }
async function addRestriction() {
  if (!selectedPerson.value || !tagCode.value.trim()) return;
  const { error } = await api.fmp.setRestriction(selectedPerson.value.id, tagCode.value.trim().toUpperCase(), tagLabel.value.trim() || null);
  if (error) return alert.error(i18n.t("fmp.error"));
  tagCode.value = ""; tagLabel.value = ""; await loadMeta(selectedPerson.value.id);
}
async function deleteRestriction(code: string) { if (selectedPerson.value) { await api.fmp.deleteRestriction(selectedPerson.value.id, code); await loadMeta(selectedPerson.value.id); } }
async function savePreference() {
  if (!selectedPerson.value || !preferenceFoodId.value) return;
  const { error } = await api.fmp.setPreference(selectedPerson.value.id, preferenceFoodId.value, preferenceScore.value);
  if (error) return alert.error(i18n.t("fmp.error"));
  preferenceFoodId.value = null; await loadMeta(selectedPerson.value.id);
}
async function deletePreference(foodId: string) { if (selectedPerson.value) { await api.fmp.deletePreference(selectedPerson.value.id, foodId); await loadMeta(selectedPerson.value.id); } }
async function saveTarget() {
  if (!selectedPerson.value || !targetForm.nutrientId) return;
  const { error } = await api.fmp.setNutrientTarget(selectedPerson.value.id, targetForm.nutrientId, { minimum: targetForm.minimum, target: targetForm.target, maximum: targetForm.maximum, period: targetForm.period, source: "USER" });
  if (error) return alert.error(i18n.t("fmp.error"));
  Object.assign(targetForm, { nutrientId: null, minimum: null, target: null, maximum: null, period: "DAY" });
  await loadMeta(selectedPerson.value.id);
}
async function deleteTarget(nutrientId: string) {
  if (!selectedPerson.value) return;
  await api.fmp.deleteNutrientTarget(selectedPerson.value.id, nutrientId);
  await loadMeta(selectedPerson.value.id);
}

async function applyReferenceValues(overwrite: boolean) {
  if (!selectedPerson.value) return;
  const { error } = await api.fmp.applyReferenceValues(selectedPerson.value.id, overwrite);
  if (error) return alert.error(i18n.t("fmp.people.no-reference-values"));
  alert.success(i18n.t("fmp.saved")); await loadMeta(selectedPerson.value.id);
}

onMounted(refresh);
</script>
