<template>
  <el-form ref="formRef" :model="draft" :rules="rules" label-width="112px">
    <el-row :gutter="12">
      <el-col :xs="24" :md="8">
        <el-form-item label="深访类型" prop="interview_type">
          <el-select v-model="draft.interview_type" style="width: 100%">
            <el-option v-for="item in interviewTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
      </el-col>
      <el-col :xs="24" :md="8">
        <el-form-item label="深访方式">
          <el-select v-model="draft.interview_method" clearable style="width: 100%">
            <el-option v-for="item in methodOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
      </el-col>
      <el-col :xs="24" :md="8">
        <el-form-item label="深访时间">
          <el-date-picker v-model="draft.interviewed_at" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width: 100%" />
        </el-form-item>
      </el-col>
    </el-row>

    <div class="section-title">个人与家庭背景</div>
    <el-row :gutter="12">
      <el-col :xs="24" :md="12"><el-form-item label="家庭结构"><el-input v-model="payload.family.family_structure" maxlength="500" placeholder="如：独生女，父母本地退休，自己独住，周末常回父母家" /></el-form-item></el-col>
      <el-col :xs="24" :md="12"><el-form-item label="家庭参与度"><el-select v-model="payload.family.family_involvement_level" clearable placeholder="请选择家庭参与度" style="width: 100%"><el-option v-for="item in levelOptions" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item></el-col>
      <el-col :span="24"><el-form-item label="家庭备注"><el-input v-model="payload.family.family_notes" type="textarea" :rows="2" maxlength="1000" show-word-limit placeholder="写家庭氛围、父母要求、经济支持、原生家庭影响等，如：父母希望男方本地稳定，对学历和家庭背景较看重" /></el-form-item></el-col>
    </el-row>

    <div class="section-title">性格与相处模式</div>
    <el-row :gutter="12">
      <el-col :span="24"><el-form-item label="性格标签"><el-select v-model="payload.personality.tags" multiple filterable allow-create default-first-option collapse-tags collapse-tags-tooltip placeholder="请选择或输入性格标签" style="width: 100%"><el-option v-for="item in tagOptions" :key="item" :label="item" :value="item" /></el-select></el-form-item></el-col>
      <el-col :xs="24" :md="12"><el-form-item label="沟通方式"><el-input v-model="payload.personality.communication_style" maxlength="500" placeholder="如：不喜欢被强推，适合先给资料让她自己判断，再电话补充" /></el-form-item></el-col>
      <el-col :xs="24" :md="12"><el-form-item label="关系节奏"><el-select v-model="payload.personality.relationship_pace" clearable placeholder="请选择关系节奏" style="width: 100%"><el-option v-for="item in paceOptions" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item></el-col>
      <el-col :span="24"><el-form-item label="红娘观察"><el-input v-model="payload.personality.matchmaker_observation" type="textarea" :rows="2" maxlength="1000" show-word-limit placeholder="写服务人员的真实判断，如：表达克制但标准清晰，对逻辑混乱或过度热情会抗拒" /></el-form-item></el-col>
    </el-row>

    <div class="section-title">情感经历与婚恋观</div>
    <el-row :gutter="12">
      <el-col :span="24"><el-form-item label="经历摘要"><el-input v-model="payload.relationship.history_summary" type="textarea" :rows="2" maxlength="1000" show-word-limit placeholder="只写影响匹配判断的信息，如：有一段三年恋爱，因异地和未来规划不一致分开" /></el-form-item></el-col>
      <el-col :span="24"><el-form-item label="婚恋观"><el-input v-model="payload.relationship.marriage_view" type="textarea" :rows="2" maxlength="1000" show-word-limit placeholder="如：认为婚姻需要共同成长，接受双方有各自空间，不接受情绪化争吵" /></el-form-item></el-col>
      <el-col :xs="24" :md="12"><el-form-item label="结婚意愿"><el-select v-model="payload.relationship.marriage_intention" clearable placeholder="请选择结婚意愿" style="width: 100%"><el-option v-for="item in levelOptions" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item></el-col>
      <el-col :xs="24" :md="12"><el-form-item label="期望时间"><el-input v-model="payload.relationship.marriage_timeline" maxlength="200" placeholder="如：如果合适，希望一年内订婚，两年内结婚" /></el-form-item></el-col>
    </el-row>

    <div class="section-title">择偶要求复核建议</div>
    <div class="section-hint">这里只记录深访中发现的调整建议，不会自动修改正式择偶要求；只有正式择偶要求才参与一票否决和硬过滤。</div>
    <el-row :gutter="12">
      <el-col :xs="24" :md="8"><el-form-item label="建议调整"><el-switch v-model="payload.preference_review.needs_update" active-text="需要" inactive-text="不需要" /></el-form-item></el-col>
      <el-col :xs="24" :md="16"><el-form-item label="建议新增一票否决"><el-select v-model="payload.preference_review.suggested_hard_reject_items" multiple filterable allow-create default-first-option collapse-tags collapse-tags-tooltip style="width: 100%" placeholder="建议同步到正式择偶要求后才生效，如：离异带孩、长期异地、无稳定工作"><el-option v-for="item in hardRejectOptions" :key="item" :label="item" :value="item" /></el-select></el-form-item></el-col>
      <el-col :xs="24" :md="12"><el-form-item label="建议放宽条件"><el-select v-model="payload.preference_review.suggested_relax_items" multiple filterable allow-create default-first-option collapse-tags collapse-tags-tooltip style="width: 100%" placeholder="如：身高可从175放宽到172，收入稳定比具体年薪更重要"><el-option v-for="item in compromiseOptions" :key="item" :label="item" :value="item" /></el-select></el-form-item></el-col>
      <el-col :xs="24" :md="12"><el-form-item label="建议重点偏好"><el-select v-model="payload.preference_review.suggested_priority_items" multiple filterable allow-create default-first-option collapse-tags collapse-tags-tooltip style="width: 100%" placeholder="建议红娘重点关注但不做一票否决，如：本地、性格稳定、愿意沟通"><el-option v-for="item in softPreferenceOptions" :key="item" :label="item" :value="item" /></el-select></el-form-item></el-col>
      <el-col :span="24"><el-form-item label="调整原因"><el-input v-model="payload.preference_review.review_reason" type="textarea" :rows="2" maxlength="1000" show-word-limit placeholder="说明为什么建议调整正式择偶要求，如：用户口头表示身高不是硬条件，但非常重视情绪稳定和家庭边界" /></el-form-item></el-col>
    </el-row>

    <div class="section-title">服务策略与风险</div>
    <el-row :gutter="12">
      <el-col :xs="24" :md="12"><el-form-item label="推荐策略"><el-input v-model="payload.service_strategy.candidate_strategy" type="textarea" :rows="2" maxlength="1000" show-word-limit placeholder="写后续怎么推荐更容易成功，如：先推荐价值观稳定、表达温和的人，不建议一开始推强势对象" /></el-form-item></el-col>
      <el-col :xs="24" :md="12"><el-form-item label="沟通建议"><el-input v-model="payload.service_strategy.first_contact_advice" type="textarea" :rows="2" maxlength="1000" show-word-limit placeholder="写红娘沟通话术重点，如：推荐时先讲生活方式和家庭观，再讲收入房车" /></el-form-item></el-col>
      <el-col :xs="24" :md="8"><el-form-item label="风险等级"><el-select v-model="payload.risk.risk_level" clearable placeholder="请选择风险等级" style="width: 100%"><el-option v-for="item in levelOptions" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item></el-col>
      <el-col :xs="24" :md="16"><el-form-item label="风险标签"><el-select v-model="payload.risk.risk_tags" multiple filterable allow-create default-first-option collapse-tags collapse-tags-tooltip style="width: 100%" placeholder="如：父母强干预、标准摇摆、前任影响、抗拒见面"><el-option v-for="item in riskTagOptions" :key="item" :label="item" :value="item" /></el-select></el-form-item></el-col>
      <el-col :span="24"><el-form-item label="沟通禁忌"><el-input v-model="payload.risk.communication_taboo" maxlength="1000" placeholder="如：不要直接说年龄压力，不要用催促式话术" /></el-form-item></el-col>
    </el-row>

    <div class="section-title">摘要与印象</div>
    <el-form-item label="内部摘要" prop="summary"><el-input v-model="draft.summary" type="textarea" :rows="3" maxlength="5000" show-word-limit placeholder="3-5句话概括，如：用户慢热理性，重视稳定和边界感。硬拒绝异地和离异带孩。推荐温和、稳定、有长期规划的候选。" /></el-form-item>
    <el-form-item label="深访内容" prop="content"><el-input v-model="draft.content" type="textarea" :rows="4" maxlength="20000" show-word-limit placeholder="填写完整沟通纪要或原始要点，可按家庭、经历、择偶、风险、服务策略分段记录" /></el-form-item>
    <el-form-item label="红娘印象"><el-input v-model="payload.summary.public_matchmaker_impression" type="textarea" :rows="2" maxlength="1000" show-word-limit placeholder="偏协作摘要，可脱敏展示，如：整体配合度较高，标准清晰，适合稳步推进" /></el-form-item>
    <el-form-item label="关键词"><el-select v-model="draft.keywords" multiple filterable allow-create default-first-option collapse-tags collapse-tags-tooltip style="width: 100%" placeholder="如：慢热、稳定、本地、父母参与、边界感"><el-option v-for="item in keywordOptions" :key="item" :label="item" :value="item" /></el-select></el-form-item>
    <el-form-item label="红娘备注"><el-input v-model="draft.manual_notes" type="textarea" :rows="2" maxlength="2000" show-word-limit placeholder="内部提醒，如：对第一次见面比较谨慎，建议提前充分沟通" /></el-form-item>
  </el-form>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from "vue";
import type { FormInstance, FormRules } from "element-plus";
import type { InterviewForm } from "@/api/module_service/vip";

const props = defineProps<{ modelValue: InterviewForm }>();
const emit = defineEmits<{ (event: "update:modelValue", value: InterviewForm): void }>();

const formRef = ref<FormInstance>();
const interviewTypeOptions = [
  { label: "首次深访", value: "first" },
  { label: "阶段深访", value: "stage" },
  { label: "结案深访", value: "closing" },
  { label: "补充深访", value: "supplement" },
];
const methodOptions = [
  { label: "线下面谈", value: "offline" },
  { label: "电话", value: "phone" },
  { label: "微信语音", value: "wechat_voice" },
  { label: "视频", value: "video" },
  { label: "历史补录", value: "history" },
];
const levelOptions = [
  { label: "低", value: "low" },
  { label: "中", value: "medium" },
  { label: "高", value: "high" },
];
const paceOptions = [
  { label: "慢热", value: "slow" },
  { label: "正常", value: "normal" },
  { label: "快速推进", value: "fast" },
];
const tagOptions = ["慢热", "外向", "内向", "理性", "感性", "温和", "稳定", "重视边界感", "主动表达", "需要引导"];
const hardRejectOptions = ["离异带孩", "长期异地", "无稳定工作", "抽烟", "酗酒", "赌博", "负债过高", "父母强干预", "不接受生育", "无结婚计划"];
const softPreferenceOptions = ["本科以上", "本地", "有房", "有车", "性格稳定", "愿意沟通", "收入稳定", "家庭简单", "作息规律", "情绪稳定", "有责任感"];
const compromiseOptions = ["身高可放宽", "年龄可放宽", "收入可放宽", "学历可放宽", "房车可放宽", "地域可放宽", "婚史可视情况", "职业不限但需稳定"];
const riskTagOptions = ["父母强干预", "标准摇摆", "前任影响", "抗拒见面", "沟通被动", "情绪敏感", "时间配合差", "服务预期过高", "隐私顾虑强"];
const keywordOptions = Array.from(new Set([...tagOptions, ...softPreferenceOptions, ...riskTagOptions, "本地", "稳定", "边界感", "结婚意愿高", "家庭参与"]));

function defaultPayload() {
  return {
    family: { family_structure: "", family_involvement_level: "", family_notes: "" },
    personality: { tags: [] as string[], communication_style: "", relationship_pace: "", matchmaker_observation: "" },
    relationship: { history_summary: "", marriage_view: "", marriage_intention: "", marriage_timeline: "" },
    preference_review: {
      needs_update: false,
      suggested_hard_reject_items: [] as string[],
      suggested_relax_items: [] as string[],
      suggested_priority_items: [] as string[],
      review_reason: "",
    },
    service_strategy: { candidate_strategy: "", first_contact_advice: "" },
    risk: { risk_level: "", risk_tags: [] as string[], communication_taboo: "" },
    summary: { public_matchmaker_impression: "" },
  };
}

const draft = reactive<InterviewForm>({});
const payload = reactive(defaultPayload());
let syncingFromParent = false;
const rules = reactive<FormRules<InterviewForm>>({
  interview_type: [{ required: true, message: "请选择深访类型", trigger: "change" }],
  content: [{ required: true, message: "请填写深访内容", trigger: "blur" }],
});

function syncPayload(value?: Record<string, any>) {
  const next = defaultPayload();
  const source = value || {};
  if (!source.preference_review && source.preference_insight) {
    source.preference_review = {
      needs_update: true,
      suggested_hard_reject_items: source.preference_insight.hard_reject_items || [],
      suggested_priority_items: source.preference_insight.soft_preference_items || [],
      suggested_relax_items: source.preference_insight.compromise_items || [],
      review_reason: "",
    };
  }
  for (const key of Object.keys(next) as Array<keyof ReturnType<typeof defaultPayload>>) {
    Object.assign(payload[key], next[key], source[key] || {});
  }
}

watch(
  () => props.modelValue,
  (value) => {
    syncingFromParent = true;
    Object.assign(draft, value || {});
    syncPayload(value?.structured_payload);
    queueMicrotask(() => {
      syncingFromParent = false;
    });
  },
  { immediate: true, deep: true },
);

watch(
  [draft, payload],
  () => {
    if (syncingFromParent) return;
    emit("update:modelValue", { ...draft, structured_payload: JSON.parse(JSON.stringify(payload)) });
  },
  { deep: true },
);

async function validate() {
  return formRef.value?.validate();
}

defineExpose({ validate });
</script>

<style scoped>
.section-title {
  margin: 8px 0 12px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.section-hint {
  margin: -6px 0 12px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.5;
}
</style>
