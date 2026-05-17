<template>
  <div class="partner-preference-form">
    <el-alert
      v-if="modelValue?.is_final"
      title="服务推荐以深访版择偶要求为准，普通修改会保存历史，但不会覆盖最终版。"
      type="warning"
      :closable="false"
      show-icon
      class="preference-alert"
    />

    <template v-if="readOnly">
      <el-descriptions v-if="hasPreference" :column="3" border>
        <el-descriptions-item label="年龄范围">{{ rangeLabel(draft.age_min, draft.age_max, "岁") }}</el-descriptions-item>
        <el-descriptions-item label="身高范围">{{ rangeLabel(draft.height_min_cm, draft.height_max_cm, "cm") }}</el-descriptions-item>
        <el-descriptions-item label="常驻地">{{ regionLabels(draft.preferred_residence_region_codes) }}</el-descriptions-item>
        <el-descriptions-item label="籍贯">{{ regionLabels(draft.preferred_hometown_region_codes) }}</el-descriptions-item>
        <el-descriptions-item label="接受异地">{{ boolLabel(draft.accept_long_distance) }}</el-descriptions-item>
        <el-descriptions-item label="学历">{{ dictLabels(dictOptions.education, draft.preferred_education_codes) }}</el-descriptions-item>
        <el-descriptions-item label="婚况">{{ dictLabels(dictOptions.maritalStatus, draft.preferred_marital_status_codes) }}</el-descriptions-item>
        <el-descriptions-item label="年收入">{{ dictLabels(dictOptions.annualIncome, draft.preferred_annual_income_codes) }}</el-descriptions-item>
        <el-descriptions-item label="房产">{{ dictLabels(dictOptions.houseStatus, draft.preferred_house_status_codes) }}</el-descriptions-item>
        <el-descriptions-item label="车辆">{{ dictLabels(dictOptions.carStatus, draft.preferred_car_status_codes) }}</el-descriptions-item>
        <el-descriptions-item label="职业说明">{{ draft.preferred_occupation_text || "-" }}</el-descriptions-item>
        <el-descriptions-item label="接受离异">{{ boolLabel(draft.accept_divorced) }}</el-descriptions-item>
        <el-descriptions-item label="接受有子女">{{ boolLabel(draft.accept_children) }}</el-descriptions-item>
        <el-descriptions-item label="子女说明">{{ draft.children_requirement || "-" }}</el-descriptions-item>
        <el-descriptions-item label="性格偏好">{{ listLabel(draft.preferred_personality_tags) }}</el-descriptions-item>
        <el-descriptions-item label="生活方式">{{ listLabel(draft.preferred_lifestyle_tags) }}</el-descriptions-item>
        <el-descriptions-item label="关系期待">{{ listLabel(draft.preferred_relationship_tags) }}</el-descriptions-item>
        <el-descriptions-item label="硬性拒绝" :span="3">{{ listLabel(draft.hard_reject_items) }}</el-descriptions-item>
        <el-descriptions-item label="软性偏好" :span="3">{{ listLabel(draft.soft_preference_items) }}</el-descriptions-item>
        <el-descriptions-item label="自由描述" :span="3">{{ draft.preference_text || "-" }}</el-descriptions-item>
      </el-descriptions>
      <el-empty v-else description="暂无择偶要求" :image-size="72" />
    </template>

    <el-form v-else label-width="96px" class="preference-form">
      <div v-if="modelValue?.id" class="preference-meta-row">
        <el-tag effect="plain">来源：{{ sourceLabel(modelValue.source_type) }}</el-tag>
        <el-tag effect="plain">版本：{{ modelValue.version_no || "-" }}</el-tag>
        <el-tag :type="modelValue.is_final ? 'warning' : 'info'" effect="plain">最终版：{{ modelValue.is_final ? "是" : "否" }}</el-tag>
        <el-tag :type="modelValue.vector_dirty ? 'warning' : 'success'" effect="plain">向量更新：{{ modelValue.vector_dirty ? "待更新" : "已同步" }}</el-tag>
      </div>

      <div class="preference-section">
        <div class="section-title">基础范围</div>
        <el-row :gutter="16">
          <el-col :xs="24" :sm="12" :lg="6"><el-form-item label="年龄下限"><el-input-number v-model="draft.age_min" :min="18" :max="100" controls-position="right" style="width: 100%" /></el-form-item></el-col>
          <el-col :xs="24" :sm="12" :lg="6"><el-form-item label="年龄上限"><el-input-number v-model="draft.age_max" :min="18" :max="100" controls-position="right" style="width: 100%" /></el-form-item></el-col>
          <el-col :xs="24" :sm="12" :lg="6"><el-form-item label="身高下限"><el-input-number v-model="draft.height_min_cm" :min="80" :max="260" controls-position="right" style="width: 100%" /></el-form-item></el-col>
          <el-col :xs="24" :sm="12" :lg="6"><el-form-item label="身高上限"><el-input-number v-model="draft.height_max_cm" :min="80" :max="260" controls-position="right" style="width: 100%" /></el-form-item></el-col>
        </el-row>
      </div>

      <div class="preference-section">
        <div class="section-title">地区要求</div>
        <el-row :gutter="16">
          <el-col :xs="24" :lg="12">
            <el-form-item label="常驻地">
              <el-cascader v-model="draft.preferred_residence_region_codes" :options="regionOptions" :props="regionProps" clearable filterable collapse-tags collapse-tags-tooltip style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :lg="12">
            <el-form-item label="籍贯">
              <el-cascader v-model="draft.preferred_hometown_region_codes" :options="regionOptions" :props="regionProps" clearable filterable collapse-tags collapse-tags-tooltip style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :lg="8">
            <el-form-item label="接受异地">
              <el-select v-model="draft.accept_long_distance" clearable placeholder="不限" style="width: 100%">
                <el-option label="接受" :value="true" />
                <el-option label="不接受" :value="false" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
      </div>

      <div class="preference-section">
        <div class="section-title">现实条件</div>
        <el-row :gutter="16">
          <el-col :xs="24" :sm="12" :lg="8"><el-form-item label="学历"><el-select v-model="draft.preferred_education_codes" multiple clearable filterable collapse-tags collapse-tags-tooltip placeholder="不限" style="width: 100%"><el-option v-for="item in dictOptions.education" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item></el-col>
          <el-col :xs="24" :sm="12" :lg="8"><el-form-item label="婚况"><el-select v-model="draft.preferred_marital_status_codes" multiple clearable filterable collapse-tags collapse-tags-tooltip placeholder="不限" style="width: 100%"><el-option v-for="item in dictOptions.maritalStatus" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item></el-col>
          <el-col :xs="24" :sm="12" :lg="8"><el-form-item label="年收入"><el-select v-model="draft.preferred_annual_income_codes" multiple clearable filterable collapse-tags collapse-tags-tooltip placeholder="不限" style="width: 100%"><el-option v-for="item in dictOptions.annualIncome" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item></el-col>
          <el-col :xs="24" :sm="12" :lg="8"><el-form-item label="房产"><el-select v-model="draft.preferred_house_status_codes" multiple clearable filterable collapse-tags collapse-tags-tooltip placeholder="不限" style="width: 100%"><el-option v-for="item in dictOptions.houseStatus" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item></el-col>
          <el-col :xs="24" :sm="12" :lg="8"><el-form-item label="车辆"><el-select v-model="draft.preferred_car_status_codes" multiple clearable filterable collapse-tags collapse-tags-tooltip placeholder="不限" style="width: 100%"><el-option v-for="item in dictOptions.carStatus" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item></el-col>
          <el-col :xs="24" :sm="12" :lg="8"><el-form-item label="职业说明"><el-input v-model="draft.preferred_occupation_text" clearable placeholder="仅作说明，不参与硬筛" /></el-form-item></el-col>
        </el-row>
      </div>

      <div class="preference-section">
        <div class="section-title">婚育要求</div>
        <el-row :gutter="16">
          <el-col :xs="24" :sm="12" :lg="8">
            <el-form-item label="接受离异">
              <el-select v-model="draft.accept_divorced" clearable placeholder="不限" style="width: 100%">
                <el-option label="接受" :value="true" />
                <el-option label="不接受" :value="false" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :lg="8">
            <el-form-item label="接受有子女">
              <el-select v-model="draft.accept_children" clearable placeholder="不限" style="width: 100%">
                <el-option label="接受" :value="true" />
                <el-option label="不接受" :value="false" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :lg="8"><el-form-item label="子女说明"><el-input v-model="draft.children_requirement" clearable /></el-form-item></el-col>
        </el-row>
      </div>

      <div class="preference-section">
        <div class="section-title">性格生活</div>
        <el-row :gutter="16">
          <el-col :xs="24" :lg="8"><el-form-item label="性格偏好"><el-select v-model="draft.preferred_personality_tags" multiple filterable allow-create default-first-option clearable collapse-tags collapse-tags-tooltip placeholder="可多选" style="width: 100%"><el-option v-for="item in personalityOptions" :key="item" :label="item" :value="item" /></el-select></el-form-item></el-col>
          <el-col :xs="24" :lg="8"><el-form-item label="生活方式"><el-select v-model="draft.preferred_lifestyle_tags" multiple filterable allow-create default-first-option clearable collapse-tags collapse-tags-tooltip placeholder="可多选" style="width: 100%"><el-option v-for="item in lifestyleOptions" :key="item" :label="item" :value="item" /></el-select></el-form-item></el-col>
          <el-col :xs="24" :lg="8"><el-form-item label="关系期待"><el-select v-model="draft.preferred_relationship_tags" multiple filterable allow-create default-first-option clearable collapse-tags collapse-tags-tooltip placeholder="可多选" style="width: 100%"><el-option v-for="item in relationshipOptions" :key="item" :label="item" :value="item" /></el-select></el-form-item></el-col>
        </el-row>
      </div>

      <div class="preference-section">
        <div class="section-title">补充说明</div>
        <el-row :gutter="16">
          <el-col :xs="24" :lg="12"><el-form-item label="硬性拒绝"><el-select v-model="draft.hard_reject_items" multiple filterable allow-create default-first-option clearable collapse-tags collapse-tags-tooltip placeholder="可输入或选择" style="width: 100%" /></el-form-item></el-col>
          <el-col :xs="24" :lg="12"><el-form-item label="软性偏好"><el-select v-model="draft.soft_preference_items" multiple filterable allow-create default-first-option clearable collapse-tags collapse-tags-tooltip placeholder="可输入或选择" style="width: 100%" /></el-form-item></el-col>
          <el-col :span="24"><el-form-item label="自由描述"><el-input v-model="draft.preference_text" type="textarea" :rows="4" resize="none" placeholder="可以写希望遇到怎样的人，未填写表示不限制。" /></el-form-item></el-col>
        </el-row>
      </div>
    </el-form>

    <div v-if="showActions && !readOnly" class="preference-actions">
      <el-button @click="resetDraft">重置</el-button>
      <el-button type="primary" @click="emitSave">保存择偶要求</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, watch } from "vue";
import type { PartnerPreference } from "@/api/module_crm/lead";

type Option = { label: string; value: string };

const props = withDefaults(
  defineProps<{
    modelValue?: PartnerPreference | null;
    dictOptions: {
      annualIncome: Option[];
      maritalStatus: Option[];
      education: Option[];
      houseStatus: Option[];
      carStatus: Option[];
    };
    regionOptions: Array<Record<string, unknown>>;
    readOnly?: boolean;
    showActions?: boolean;
  }>(),
  {
    readOnly: false,
    showActions: true,
  }
);

const emit = defineEmits<{
  save: [value: PartnerPreference];
}>();

const personalityOptions = ["情绪稳定", "外向开朗", "温和顾家", "独立成熟", "有责任心", "沟通主动"];
const lifestyleOptions = ["规律作息", "爱运动", "喜欢旅行", "重视家庭", "消费理性", "社交简单"];
const relationshipOptions = ["结婚目标明确", "重视陪伴", "重视沟通", "边界感清晰", "愿意共同成长"];
const regionProps = { multiple: true, emitPath: false, checkStrictly: true };

const defaultPreference = (): PartnerPreference => ({
  preferred_residence_region_codes: [],
  preferred_hometown_region_codes: [],
  preferred_education_codes: [],
  preferred_marital_status_codes: [],
  preferred_annual_income_codes: [],
  preferred_house_status_codes: [],
  preferred_car_status_codes: [],
  preferred_personality_tags: [],
  preferred_lifestyle_tags: [],
  preferred_relationship_tags: [],
  hard_reject_items: [],
  soft_preference_items: [],
  strictness_level: "normal",
  must_match_fields: [],
  preferred_match_fields: [],
});

const draft = reactive<PartnerPreference>(defaultPreference());
const hasPreference = computed(() => Boolean(props.modelValue?.id || Object.keys(props.modelValue || {}).length));

watch(
  () => props.modelValue,
  () => resetDraft(),
  { immediate: true }
);

function resetDraft() {
  Object.assign(draft, normalizePreference(props.modelValue));
}

function cloneDraft() {
  return normalizePreference(draft);
}

function normalizePreference(value?: PartnerPreference | null) {
  const next = { ...defaultPreference(), ...(value || {}) } as PartnerPreference;
  const arrayKeys: Array<keyof PartnerPreference> = [
    "preferred_residence_region_codes",
    "preferred_hometown_region_codes",
    "preferred_education_codes",
    "preferred_marital_status_codes",
    "preferred_annual_income_codes",
    "preferred_house_status_codes",
    "preferred_car_status_codes",
    "preferred_personality_tags",
    "preferred_lifestyle_tags",
    "preferred_relationship_tags",
    "hard_reject_items",
    "soft_preference_items",
    "must_match_fields",
    "preferred_match_fields",
  ];
  arrayKeys.forEach((key) => {
    if (!Array.isArray(next[key])) {
      (next[key] as unknown as string[]) = [];
    }
  });
  if (!next.strictness_level) {
    next.strictness_level = "normal";
  }
  return JSON.parse(JSON.stringify(next)) as PartnerPreference;
}

function emitSave() {
  emit("save", getValue());
}

function getValue() {
  return cloneDraft();
}

defineExpose({ getValue });

function sourceLabel(value?: string) {
  return (
    {
      miniapp: "小程序",
      admin: "后台",
      matchmaker: "红娘",
      deep_interview: "深访",
      import: "导入",
    } as Record<string, string>
  )[value || ""] || value || "-";
}

function rangeLabel(min?: number, max?: number, unit = "") {
  if (!min && !max) return "不限";
  if (min && max) return `${min}-${max}${unit}`;
  if (min) return `${min}${unit}以上`;
  return `${max}${unit}以下`;
}

function boolLabel(value?: boolean | null) {
  if (value === true) return "接受";
  if (value === false) return "不接受";
  return "不限";
}

function listLabel(values?: string[]) {
  return values?.length ? values.join("、") : "不限";
}

function dictLabels(options: Option[], values?: string[]) {
  if (!values?.length) return "不限";
  return values.map((value) => options.find((item) => item.value === value)?.label || value).join("、");
}

function regionLabels(values?: string[]) {
  if (!values?.length) return "不限";
  return values.map((value) => regionNameMap.value[value] || value).join("、");
}

const regionNameMap = computed(() => {
  const map: Record<string, string> = {};
  const walk = (items: Array<Record<string, unknown>>) => {
    items.forEach((item) => {
      const value = String(item.value || "");
      const label = String(item.label || value);
      if (value) map[value] = label;
      if (Array.isArray(item.children)) walk(item.children as Array<Record<string, unknown>>);
    });
  };
  walk(props.regionOptions || []);
  return map;
});
</script>

<style scoped>
.preference-alert {
  margin-bottom: 14px;
}

.preference-meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 14px;
}

.preference-section {
  padding: 16px 18px 4px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: var(--el-fill-color-blank);
}

.preference-section + .preference-section {
  margin-top: 14px;
}

.section-title {
  margin-bottom: 14px;
  color: var(--el-text-color-primary);
  font-size: 15px;
  font-weight: 700;
}

.preference-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 16px;
}
</style>
