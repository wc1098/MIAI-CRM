<template>
  <div class="person-profile-fields">
    <div class="form-section">
      <div class="section-title">基础资料</div>
      <el-row :gutter="16">
        <el-col :xs="24" :md="8"><el-form-item label="手机号" :prop="mobileField"><el-input v-model="form[mobileField]" :disabled="mobileDisabled" clearable /></el-form-item></el-col>
        <el-col :xs="24" :md="8"><el-form-item label="姓名" prop="name"><el-input v-model="form.name" clearable /></el-form-item></el-col>
        <el-col :xs="24" :md="8">
          <el-form-item label="性别" prop="gender">
            <el-radio-group v-model="form.gender">
              <el-radio-button value="0">男</el-radio-button>
              <el-radio-button value="1">女</el-radio-button>
              <el-radio-button value="2">未知</el-radio-button>
            </el-radio-group>
          </el-form-item>
        </el-col>
        <el-col :xs="24" :md="8"><el-form-item label="微信号"><el-input v-model="form.wechat" clearable /></el-form-item></el-col>
        <el-col v-if="showIdCard" :xs="24" :md="8"><el-form-item label="身份证号"><el-input v-model="form.id_card_no" clearable /></el-form-item></el-col>
        <el-col :xs="24" :md="8"><el-form-item label="出生日期"><el-date-picker v-model="form.birth_date" value-format="YYYY-MM-DD" type="date" style="width: 100%" /></el-form-item></el-col>
        <el-col v-if="showAstrology" :xs="24" :md="8"><el-form-item label="星座"><el-input :model-value="constellation || '-'" disabled /></el-form-item></el-col>
        <el-col v-if="showAstrology" :xs="24" :md="8"><el-form-item label="生肖"><el-input :model-value="zodiac || '-'" disabled /></el-form-item></el-col>
        <el-col :xs="24" :md="8"><el-form-item label="身高"><el-input-number v-model="form.height_cm" :min="80" :max="260" controls-position="right" style="width: 100%" /></el-form-item></el-col>
        <el-col :xs="24" :md="8"><el-form-item label="体重"><el-input-number v-model="form.weight_kg" :min="30" :max="250" controls-position="right" style="width: 100%" /></el-form-item></el-col>
      </el-row>
    </div>

    <div class="form-section">
      <div class="section-title">扩展资料</div>
      <el-row :gutter="16">
        <el-col :xs="24" :md="8"><el-form-item label="民族"><option-select v-model="form.ethnicity" :options="dictOptions.ethnicity" /></el-form-item></el-col>
        <el-col :xs="24" :md="8"><el-form-item label="职业"><option-select v-model="form.occupation_code" :options="dictOptions.occupation" /></el-form-item></el-col>
        <el-col :xs="24" :md="8"><el-form-item label="职业补充"><el-input v-model="form.occupation" clearable /></el-form-item></el-col>
        <el-col :xs="24" :md="8"><el-form-item label="年收入"><option-select v-model="form.annual_income" :options="dictOptions.annualIncome" /></el-form-item></el-col>
        <el-col :xs="24" :md="8"><el-form-item label="婚况"><option-select v-model="form.marital_status" :options="dictOptions.maritalStatus" /></el-form-item></el-col>
        <el-col :xs="24" :md="8"><el-form-item label="学历"><option-select v-model="form.education" :options="dictOptions.education" /></el-form-item></el-col>
        <el-col :xs="24" :md="8"><el-form-item label="毕业院校"><el-input v-model="form.graduated_school" clearable /></el-form-item></el-col>
        <el-col :xs="24" :md="8"><el-form-item label="专业"><el-input v-model="form.major" clearable /></el-form-item></el-col>
        <el-col :xs="24" :md="8"><el-form-item label="单位类型"><option-select v-model="form.unit_type" :options="dictOptions.unitType" /></el-form-item></el-col>
        <el-col :xs="24" :md="8"><el-form-item label="职务"><el-input v-model="form.job_title" clearable /></el-form-item></el-col>
        <el-col :xs="24" :md="8"><el-form-item label="工作单位"><el-input v-model="form.work_company" clearable /></el-form-item></el-col>
      </el-row>
    </div>

    <div class="form-section">
      <div class="section-title">房车婚恋</div>
      <el-row :gutter="16">
        <el-col :xs="24" :md="8"><el-form-item label="籍贯"><el-cascader v-model="hometownValue" :options="addressOptions" clearable filterable :props="addressProps" style="width: 100%" /></el-form-item></el-col>
        <el-col :xs="24" :md="8"><el-form-item label="常驻地"><el-cascader v-model="residenceValue" :options="addressOptions" clearable filterable :props="addressProps" style="width: 100%" /></el-form-item></el-col>
        <el-col :xs="24" :md="8"><el-form-item label="住房情况"><option-select v-model="form.house_status" :options="dictOptions.houseStatus" /></el-form-item></el-col>
        <el-col :xs="24" :md="8"><el-form-item label="购车情况"><option-select v-model="form.car_status" :options="dictOptions.carStatus" /></el-form-item></el-col>
        <el-col :xs="24" :md="8"><el-form-item label="接受异地"><bool-select v-model="form.accept_long_distance_self" /></el-form-item></el-col>
        <el-col :xs="24" :md="8"><el-form-item label="接受闪婚"><bool-select v-model="form.accept_flash_marriage" /></el-form-item></el-col>
        <el-col :xs="24" :md="8"><el-form-item label="愿意搬家"><bool-select v-model="form.willing_relocate" /></el-form-item></el-col>
        <el-col :xs="24" :md="8"><el-form-item label="结婚计划"><option-select v-model="form.marriage_plan" :options="dictOptions.marriagePlan" /></el-form-item></el-col>
        <el-col :span="24"><el-form-item label="家庭情况"><el-input v-model="form.family_background" type="textarea" :rows="3" maxlength="2000" show-word-limit /></el-form-item></el-col>
      </el-row>
    </div>

    <div class="form-section">
      <div class="section-title">照片与介绍</div>
      <el-row :gutter="16">
        <el-col v-if="$slots.photo" :span="24"><slot name="photo" /></el-col>
        <el-col v-if="showProfileIntro" :span="24"><el-form-item label="个人介绍"><el-input v-model="form.profile_intro" type="textarea" :rows="3" maxlength="2000" show-word-limit /></el-form-item></el-col>
        <el-col :span="24"><el-form-item label="备注"><el-input v-model="form.profile_remark" type="textarea" :rows="3" maxlength="2000" show-word-limit /></el-form-item></el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h } from "vue";
import { ElOption, ElSelect } from "element-plus";
import { addressOptions } from "@/views/module_miailove/components/addressOptions";

export interface PersonDictOption {
  label?: string;
  value?: string | number;
  dict_label?: string;
  dict_value?: string | number;
}

export interface PersonProfileDictOptions {
  ethnicity?: PersonDictOption[];
  occupation?: PersonDictOption[];
  annualIncome?: PersonDictOption[];
  maritalStatus?: PersonDictOption[];
  education?: PersonDictOption[];
  unitType?: PersonDictOption[];
  houseStatus?: PersonDictOption[];
  carStatus?: PersonDictOption[];
  marriagePlan?: PersonDictOption[];
}

const props = withDefaults(defineProps<{
  form: Record<string, any>;
  dictOptions: PersonProfileDictOptions;
  mobileField?: string;
  mobileDisabled?: boolean;
  showIdCard?: boolean;
  showProfileIntro?: boolean;
  showAstrology?: boolean;
}>(), {
  mobileField: "mobile",
  mobileDisabled: false,
  showIdCard: true,
  showProfileIntro: true,
  showAstrology: true,
});

const optionValue = (item: PersonDictOption) => item.value ?? item.dict_value ?? "";
const optionLabel = (item: PersonDictOption) => item.label ?? item.dict_label ?? String(optionValue(item));
const addressProps = { emitPath: true };
const splitAddress = (value?: string) => (value ? value.split("/").filter(Boolean).slice(0, 2) : []);
const parseBirthDate = (value?: string) => {
  if (!value) return undefined;
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) return undefined;
  return { year, month, day };
};
const constellation = computed(() => {
  const date = parseBirthDate(props.form.birth_date);
  if (!date) return undefined;
  const boundaries: Array<[[number, number], string]> = [
    [[1, 20], "水瓶座"],
    [[2, 19], "双鱼座"],
    [[3, 21], "白羊座"],
    [[4, 20], "金牛座"],
    [[5, 21], "双子座"],
    [[6, 22], "巨蟹座"],
    [[7, 23], "狮子座"],
    [[8, 23], "处女座"],
    [[9, 23], "天秤座"],
    [[10, 24], "天蝎座"],
    [[11, 23], "射手座"],
    [[12, 22], "摩羯座"],
  ];
  const monthDay = [date.month, date.day] as [number, number];
  const index = boundaries.findIndex(([boundary]) => monthDay[0] < boundary[0] || (monthDay[0] === boundary[0] && monthDay[1] < boundary[1]));
  return index <= 0 ? "摩羯座" : boundaries[index - 1][1];
});
const zodiac = computed(() => {
  const date = parseBirthDate(props.form.birth_date);
  if (!date) return undefined;
  const animals = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"];
  return animals[(date.year - 1900) % 12];
});

const hometownValue = computed<string[]>({
  get: () => splitAddress(props.form.hometown),
  set: (value) => {
    props.form.hometown = value?.join("/") || undefined;
  },
});

const residenceValue = computed<string[]>({
  get: () => splitAddress(props.form.residence),
  set: (value) => {
    props.form.residence = value?.join("/") || undefined;
  },
});

const OptionSelect = defineComponent({
  props: {
    modelValue: [String, Number],
    options: { type: Array as () => PersonDictOption[], default: () => [] },
  },
  emits: ["update:modelValue"],
  setup(props, { emit }) {
    return () =>
      h(
        ElSelect,
        {
          modelValue: props.modelValue,
          clearable: true,
          filterable: true,
          style: "width: 100%",
          "onUpdate:modelValue": (value: unknown) => emit("update:modelValue", value),
        },
        () => props.options.map((item) => h(ElOption, { key: String(optionValue(item)), label: optionLabel(item), value: optionValue(item) })),
      );
  },
});

const BoolSelect = defineComponent({
  props: { modelValue: { type: Boolean, default: undefined } },
  emits: ["update:modelValue"],
  setup(props, { emit }) {
    return () =>
      h(
        ElSelect,
        {
          modelValue: props.modelValue,
          clearable: true,
          style: "width: 100%",
          "onUpdate:modelValue": (value: unknown) => emit("update:modelValue", value),
        },
        () => [h(ElOption, { label: "是", value: true }), h(ElOption, { label: "否", value: false })],
      );
  },
});
</script>

<style scoped>
.person-profile-fields {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.form-section {
  padding: 14px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: var(--el-bg-color);
}

.section-title {
  margin-bottom: 12px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}
</style>
