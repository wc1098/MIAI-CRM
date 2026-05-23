<template>
  <el-drawer v-model="visible" size="82%" destroy-on-close class="customer-drawer" @closed="reset">
    <template #header>
      <div class="drawer-head">
        <div>
          <div class="drawer-title">{{ detail?.person?.name || "客户总档案" }}</div>
          <div class="drawer-subtitle">客户编号：{{ detail?.person?.display_no || "-" }} · {{ stageLabel(detail?.current_stage) }}</div>
        </div>
      </div>
    </template>

    <el-skeleton v-if="loading" :rows="8" animated />
    <el-tabs v-else v-model="activeTab">
      <el-tab-pane label="概览" name="overview">
        <div v-if="detail" class="overview-grid">
          <div class="profile-side">
            <el-carousel v-if="detail.person.photo_urls?.length" class="avatar-carousel" indicator-position="outside" arrow="hover" trigger="click">
              <el-carousel-item v-for="url in detail.person.photo_urls" :key="url">
                <el-image class="avatar-photo" :src="ossImage(url, { w: 360, h: 480 })" fit="cover" :preview-src-list="ossImageList(detail.person.photo_urls, { w: 1600 })" preview-teleported />
              </el-carousel-item>
            </el-carousel>
            <div v-else class="avatar-empty">暂无照片</div>
          </div>
          <el-descriptions :column="3" border class="overview-desc">
            <el-descriptions-item label="客户编号">{{ detail.person.display_no || "-" }}</el-descriptions-item>
            <el-descriptions-item label="姓名">{{ detail.person.name || "-" }}</el-descriptions-item>
            <el-descriptions-item label="手机号">{{ detail.mobile_masked || "-" }}</el-descriptions-item>
            <el-descriptions-item label="当前阶段">{{ stageLabel(detail.current_stage) }}</el-descriptions-item>
            <el-descriptions-item label="最高进展">{{ stageLabel(detail.max_stage) }}</el-descriptions-item>
            <el-descriptions-item label="归属人">{{ detail.owner_user?.name || "-" }}</el-descriptions-item>
            <el-descriptions-item label="最近跟进">{{ detail.latest_follow_at || "-" }}</el-descriptions-item>
            <el-descriptions-item label="下次跟进">{{ detail.next_follow_at || "-" }}</el-descriptions-item>
            <el-descriptions-item label="建档时间">{{ detail.created_time || "-" }}</el-descriptions-item>
            <el-descriptions-item label="个人介绍" :span="3">{{ detail.person.profile_intro || "-" }}</el-descriptions-item>
            <el-descriptions-item label="觅AI印象" :span="3">{{ detail.ai_profile?.profile?.content || "暂无觅AI印象" }}</el-descriptions-item>
          </el-descriptions>
        </div>
      </el-tab-pane>

      <el-tab-pane label="基本资料" name="profile">
        <template v-if="detail">
          <el-descriptions :column="3" border>
            <el-descriptions-item label="姓名">{{ detail.person.name || "-" }}</el-descriptions-item>
            <el-descriptions-item label="性别">{{ genderLabel(detail.person.gender) }}</el-descriptions-item>
            <el-descriptions-item label="手机号">{{ detail.person.primary_mobile || "-" }}</el-descriptions-item>
            <el-descriptions-item label="微信号">{{ detail.person.wechat || "-" }}</el-descriptions-item>
            <el-descriptions-item label="年龄">{{ detail.age ? `${detail.age}岁` : "-" }}</el-descriptions-item>
            <el-descriptions-item label="出生日期">{{ detail.person.birth_date || "-" }}</el-descriptions-item>
            <el-descriptions-item label="身高">{{ detail.person.height_cm ? `${detail.person.height_cm} cm` : "-" }}</el-descriptions-item>
            <el-descriptions-item label="体重">{{ detail.person.weight_kg ? `${detail.person.weight_kg} kg` : "-" }}</el-descriptions-item>
            <el-descriptions-item label="民族">{{ optionLabel(dictOptions.ethnicity, detail.person.ethnicity) }}</el-descriptions-item>
            <el-descriptions-item label="职业">{{ optionLabel(dictOptions.occupation, detail.person.occupation_code) || detail.person.occupation || "-" }}</el-descriptions-item>
            <el-descriptions-item label="年收入">{{ optionLabel(dictOptions.annualIncome, detail.person.annual_income) }}</el-descriptions-item>
            <el-descriptions-item label="婚况">{{ optionLabel(dictOptions.maritalStatus, detail.person.marital_status) }}</el-descriptions-item>
            <el-descriptions-item label="学历">{{ optionLabel(dictOptions.education, detail.person.education) }}</el-descriptions-item>
            <el-descriptions-item label="毕业院校">{{ detail.person.graduated_school || "-" }}</el-descriptions-item>
            <el-descriptions-item label="专业">{{ detail.person.major || "-" }}</el-descriptions-item>
            <el-descriptions-item label="单位类型">{{ optionLabel(dictOptions.unitType, detail.person.unit_type) }}</el-descriptions-item>
            <el-descriptions-item label="职务">{{ detail.person.job_title || "-" }}</el-descriptions-item>
            <el-descriptions-item label="工作单位">{{ detail.person.work_company || "-" }}</el-descriptions-item>
            <el-descriptions-item label="籍贯">{{ detail.person.hometown || "-" }}</el-descriptions-item>
            <el-descriptions-item label="常驻地">{{ detail.person.residence || "-" }}</el-descriptions-item>
            <el-descriptions-item label="房产信息">{{ optionLabel(dictOptions.houseStatus, detail.person.house_status) }}</el-descriptions-item>
            <el-descriptions-item label="购车信息">{{ optionLabel(dictOptions.carStatus, detail.person.car_status) }}</el-descriptions-item>
            <el-descriptions-item label="接受异地">{{ boolLabel(detail.person.accept_long_distance_self) }}</el-descriptions-item>
            <el-descriptions-item label="接受闪婚">{{ boolLabel(detail.person.accept_flash_marriage) }}</el-descriptions-item>
            <el-descriptions-item label="愿意搬家">{{ boolLabel(detail.person.willing_relocate) }}</el-descriptions-item>
            <el-descriptions-item label="结婚计划">{{ optionLabel(dictOptions.marriagePlan, detail.person.marriage_plan) }}</el-descriptions-item>
            <el-descriptions-item label="身份证号">{{ detail.id_card_no_masked || "-" }}</el-descriptions-item>
            <el-descriptions-item label="家庭情况" :span="3">{{ detail.person.family_background || "-" }}</el-descriptions-item>
            <el-descriptions-item label="备注" :span="3">{{ detail.person.profile_remark || "-" }}</el-descriptions-item>
            <el-descriptions-item label="个人介绍" :span="3">{{ detail.person.profile_intro || "-" }}</el-descriptions-item>
          </el-descriptions>
          <div class="photo-list">
            <el-image v-for="url in detail.person.photo_urls || []" :key="url" class="photo-item" :src="ossImage(url, { w: 120, h: 120 })" :preview-src-list="ossImageList(detail.person.photo_urls, { w: 1600 })" fit="cover" preview-teleported />
          </div>
        </template>
      </el-tab-pane>

      <el-tab-pane label="认证资料" name="certification">
        <el-alert title="认证结果为认证事实，只读展示；认证资料为存档材料。" type="info" show-icon :closable="false" />
        <el-descriptions v-if="detail" :column="2" border class="mt12">
          <el-descriptions-item label="认证等级">{{ detail.person.certification_level || "none" }}</el-descriptions-item>
          <el-descriptions-item label="身份证号">{{ detail.id_card_no_masked || "-" }}</el-descriptions-item>
          <el-descriptions-item label="认证摘要" :span="2">{{ jsonText(detail.person.certification_summary) }}</el-descriptions-item>
        </el-descriptions>
        <div v-if="detail" class="cert-material-grid">
          <div v-for="item in certificationArchiveItems" :key="item.item_code" class="cert-material-card">
            <div class="cert-material-head">
              <div>
                <div class="cert-material-title">{{ item.item_name }}</div>
                <div class="cert-material-desc">{{ item.material_desc || "资料图片存档" }}</div>
              </div>
            </div>
            <div v-if="materialsByItem(item.item_code).length" class="cert-material-list">
              <div v-for="material in materialsByItem(item.item_code)" :key="material.id" class="cert-material-item">
                <el-image class="cert-material-image" :src="ossImage(material.file_url, { w: 160, h: 160 })" :preview-src-list="ossImageList([material.file_url], { w: 1600 })" fit="cover" preview-teleported />
                <div class="cert-material-meta">{{ material.created_time || material.file_name || "已上传" }}</div>
              </div>
            </div>
            <el-empty v-else description="暂无资料" :image-size="48" />
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="择偶要求" name="preference">
        <partner-preference-form :model-value="detail?.partner_preference || undefined" :dict-options="dictOptions" :region-options="[]" read-only :show-actions="false" />
      </el-tab-pane>

      <el-tab-pane label="过程记录" name="process">
        <el-timeline>
          <el-timeline-item v-for="item in mergedProcess" :key="`${item.source}-${item.id}`" :timestamp="String(item.occurred_at || item.created_time || '')">
            <div class="timeline-title">{{ sourceLabel(item.source) }} · {{ operatorName(item) }} · {{ processTypeLabel(String(item.record_type || '')) }} · {{ processResultLabel(item) }}</div>
            <div class="timeline-content">{{ item.content }}</div>
            <div v-for="line in processExtraLines(item)" :key="line" class="timeline-extra">{{ line }}</div>
          </el-timeline-item>
        </el-timeline>
      </el-tab-pane>

      <el-tab-pane label="生命周期" name="lifecycle">
        <el-timeline>
          <el-timeline-item v-for="item in mergedLifecycle" :key="`${item.source}-${item.id}`" :timestamp="String(item.created_time || '')">
            <div class="timeline-title">{{ sourceLabel(item.source) }} · {{ operatorName(item) }} · {{ lifecycleLabel(String(item.operation_type || '')) }}</div>
            <div class="timeline-content">{{ item.remark || formatChange(item.change_detail as Record<string, unknown>, String(item.operation_type || '')) }}</div>
          </el-timeline-item>
        </el-timeline>
      </el-tab-pane>
    </el-tabs>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import CustomerAPI, { type CustomerDetail } from "@/api/module_crm/customer";
import DictAPI, { type DictDataTable } from "@/api/module_system/dict";
import PartnerPreferenceForm from "@/views/module_miailove/components/PartnerPreferenceForm.vue";
import { ossImage, ossImageList } from "@/utils/ossImage";

const props = defineProps<{ modelValue: boolean; customerId?: number }>();
const emit = defineEmits<{ "update:modelValue": [value: boolean] }>();

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit("update:modelValue", value),
});
const loading = ref(false);
const detail = ref<CustomerDetail>();
const activeTab = ref("overview");
let optionsLoaded = false;

type TimelineItem = Record<string, unknown> & { id?: number | string; source: string; created_time?: string; operation_type?: string; remark?: string; change_detail?: Record<string, unknown>; operator_user_id?: number; operator_user_name?: string; created_by?: { name?: string } };
type ProcessItem = Record<string, unknown> & { id?: number | string; source: string; created_time?: string; occurred_at?: string; record_type?: string; result?: string; content?: string; next_follow_at?: string; scheduled_at?: string; appointment_slot?: string; visit_purpose?: string; promised_gift?: string; appointment_status?: string; checked_in_at?: string; checked_in_user_name?: string; need_summary?: string; budget_range?: string; main_objection?: string; intention_level?: string; operator_user_id?: number; operator_user_name?: string; created_by?: { name?: string } };

const dictOptions = reactive({
  ethnicity: [] as Array<{ label: string; value: string }>,
  annualIncome: [] as Array<{ label: string; value: string }>,
  maritalStatus: [] as Array<{ label: string; value: string }>,
  education: [] as Array<{ label: string; value: string }>,
  houseStatus: [] as Array<{ label: string; value: string }>,
  carStatus: [] as Array<{ label: string; value: string }>,
  occupation: [] as Array<{ label: string; value: string }>,
  unitType: [] as Array<{ label: string; value: string }>,
  marriagePlan: [] as Array<{ label: string; value: string }>,
  intentionLevel: [] as Array<{ label: string; value: string }>,
  visitPurpose: [] as Array<{ label: string; value: string }>,
  appointmentSlot: [] as Array<{ label: string; value: string }>,
  appointmentStatus: [] as Array<{ label: string; value: string }>,
});

const stageOptions = [
  { label: "建档完善", value: "profiling" },
  { label: "跟进经营", value: "following" },
  { label: "已邀约", value: "appointed" },
  { label: "已到店", value: "visited" },
  { label: "已面谈", value: "consulted" },
  { label: "签约推进", value: "signing" },
  { label: "已签约待付款", value: "contracted" },
  { label: "已转VIP", value: "converted_vip" },
];

const mergedLifecycle = computed(() => {
  const customerItems: TimelineItem[] = (detail.value?.lifecycle_records || []).map((item) => ({ ...item, source: "customer" }));
  const leadItems: TimelineItem[] = (detail.value?.lead_lifecycle_records || []).map((item) => ({ ...item, source: "lead" }));
  return [...customerItems, ...leadItems].sort((a, b) => String(b.created_time || "").localeCompare(String(a.created_time || "")));
});
const mergedProcess = computed(() => {
  const customerItems: ProcessItem[] = (detail.value?.process_records || []).map((item) => ({ ...item, source: "customer" }));
  const leadItems: ProcessItem[] = (detail.value?.lead_process_records || []).map((item) => ({ ...item, source: "lead" }));
  return [...customerItems, ...leadItems].sort((a, b) => String(b.occurred_at || b.created_time || "").localeCompare(String(a.occurred_at || a.created_time || "")));
});
const certificationArchiveItems = computed(() => detail.value?.certification?.archive_items || []);

watch(
  () => [props.modelValue, props.customerId] as const,
  async ([open, id]) => {
    if (!open || !id) return;
    await openDetail(id);
  },
);

async function openDetail(id: number) {
  loading.value = true;
  try {
    await ensureOptionsLoaded();
    const res = await CustomerAPI.detailCustomer(id);
    detail.value = res.data.data;
    activeTab.value = "overview";
  } finally {
    loading.value = false;
  }
}

function reset() {
  detail.value = undefined;
  activeTab.value = "overview";
}

async function ensureOptionsLoaded() {
  if (optionsLoaded) return;
  const dictMap = {
    ethnicity: "crm_ethnicity",
    annualIncome: "crm_annual_income",
    maritalStatus: "crm_marital_status",
    education: "crm_education",
    houseStatus: "crm_house_status",
    carStatus: "crm_car_status",
    occupation: "crm_occupation",
    unitType: "crm_unit_type",
    marriagePlan: "crm_marriage_plan",
    intentionLevel: "crm_customer_intention_level",
    visitPurpose: "crm_customer_visit_purpose",
    appointmentSlot: "crm_customer_appointment_slot",
    appointmentStatus: "crm_customer_appointment_status",
  } as const;
  await Promise.all(Object.entries(dictMap).map(async ([key, type]) => {
    const res = await DictAPI.getInitDict(type);
    dictOptions[key as keyof typeof dictOptions] = ((res.data.data as DictDataTable[]) || []).map((item) => ({ label: item.dict_label || item.dict_value || "", value: item.dict_value || "" }));
  }));
  optionsLoaded = true;
}

function materialsByItem(itemCode: string) {
  return (detail.value?.certification?.archive_materials || []).filter((item) => item.item_code === itemCode);
}
function stageLabel(value?: string) {
  return stageOptions.find((item) => item.value === value)?.label || value || "-";
}
function genderLabel(value?: string) {
  return ({ "0": "男", "1": "女", "2": "未知" } as Record<string, string>)[value || ""] || "-";
}
function optionLabel(options: Array<{ label: string; value: string }>, value?: string) {
  if (!value) return "-";
  return options.find((item) => item.value === value)?.label || value;
}
function boolLabel(value?: boolean | null) {
  if (value === true) return "是";
  if (value === false) return "否";
  return "-";
}
function sourceLabel(value?: string) {
  return value === "lead" ? "线索阶段" : "客户阶段";
}
function processTypeLabel(value?: string) {
  return ({ follow: "跟进", appointment: "邀约", visit: "到店", visit_checkin: "登记到店", consultation: "面谈", no_show: "爽约", appointment_cancel: "取消预约" } as Record<string, string>)[value || ""] || value || "";
}
function processResultLabel(item: ProcessItem) {
  const result = String(item.result || "");
  if (!result) return "无结果";
  if (["pending", "checked_in", "consulted", "no_show", "cancelled"].includes(result)) return optionLabel(dictOptions.appointmentStatus, result);
  return result;
}
function processExtraLines(item: ProcessItem) {
  const lines: string[] = [];
  if (item.scheduled_at) lines.push(`预约日期：${formatDate(item.scheduled_at)}`);
  if (item.appointment_slot) lines.push(`预约时段：${optionLabel(dictOptions.appointmentSlot, item.appointment_slot)}`);
  if (item.visit_purpose) lines.push(`到访目的：${optionLabel(dictOptions.visitPurpose, item.visit_purpose)}`);
  if (item.need_summary) lines.push(`需求摘要：${item.need_summary}`);
  if (item.intention_level) lines.push(`意向等级：${optionLabel(dictOptions.intentionLevel, item.intention_level)}`);
  return lines;
}
function lifecycleLabel(value: string) {
  return ({ create_from_lead: "线索转客户", edit: "编辑资料", transfer_owner: "同店转派", transfer_store: "跨店转交", return_lead: "退回线索", contract_create: "创建合同草稿", contract_sign: "合同已签", contract_submit_review: "合同提交审核", contract_review: "合同审核", contract_receipt_confirm: "确认收款" } as Record<string, string>)[value] || value;
}
function operatorName(item: { operator_user_name?: string; operator_user_id?: number; created_by?: { name?: string } }) {
  return item.operator_user_name || item.created_by?.name || (item.operator_user_id ? `用户ID ${item.operator_user_id}` : "系统");
}
function formatChange(value?: Record<string, unknown>, operationType?: string) {
  if (!value) return "-";
  if (operationType === "edit") return "资料已更新";
  return Object.entries(value).map(([key, val]) => `${key}：${Array.isArray(val) ? val.join("、") : String(val ?? "未设置")}`).join("；");
}
function formatDate(value?: string) {
  return value ? String(value).slice(0, 10) : "-";
}
function jsonText(value?: Record<string, unknown>) {
  return value ? JSON.stringify(value) : "-";
}
</script>

<style scoped>
.drawer-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.drawer-title {
  font-size: 18px;
  font-weight: 600;
}
.drawer-subtitle {
  margin-top: 4px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.overview-grid {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 16px;
}
.profile-side {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.avatar-carousel,
.avatar-empty {
  width: 100%;
  height: 300px;
}
.avatar-photo {
  width: 100%;
  height: 100%;
}
.avatar-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color-light);
  border-radius: 8px;
}
.photo-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}
.photo-item {
  width: 96px;
  height: 96px;
  border-radius: 6px;
}
.mt12 {
  margin-top: 12px;
}
.cert-material-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 12px;
  margin-top: 14px;
}
.cert-material-card {
  padding: 12px;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
}
.cert-material-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}
.cert-material-title {
  font-weight: 600;
}
.cert-material-desc,
.cert-material-meta,
.timeline-extra {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.cert-material-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(92px, 1fr));
  gap: 10px;
}
.cert-material-image {
  width: 100%;
  aspect-ratio: 1;
  border-radius: 6px;
}
.timeline-title {
  font-weight: 600;
}
.timeline-content {
  margin-top: 4px;
  white-space: pre-wrap;
}
</style>
