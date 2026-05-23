<template>
  <div class="visit-page">
    <el-card class="filter-card" shadow="never">
      <el-form :model="query" inline>
        <el-form-item label="关键词"><el-input v-model="query.keyword" clearable placeholder="编号/姓名/手机号" /></el-form-item>
        <el-form-item label="预约日期"><el-date-picker v-model="queryDateRange" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始日期" end-placeholder="结束日期" @change="syncDateRange" /></el-form-item>
        <el-form-item label="时段"><el-select v-model="query.appointment_slot" clearable style="width: 150px"><el-option v-for="item in dictOptions.appointmentSlot" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
        <el-form-item label="目的"><el-select v-model="query.visit_purpose" clearable style="width: 150px"><el-option v-for="item in dictOptions.visitPurpose" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
        <el-form-item label="状态"><el-select v-model="query.appointment_status" clearable style="width: 150px"><el-option v-for="item in dictOptions.appointmentStatus" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
        <el-form-item label="邀约人"><el-select v-model="query.operator_user_id" clearable filterable style="width: 150px"><el-option v-for="item in userOptions" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
        <el-form-item>
          <el-button type="primary" icon="Search" @click="fetchList">查询</el-button>
          <el-button icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="table-card" shadow="never">
      <el-table v-loading="loading" :data="rows" border>
        <el-table-column label="预约日期" min-width="120"><template #default="{ row }">{{ formatDate(row.scheduled_at) }}</template></el-table-column>
        <el-table-column label="预约时段" min-width="120">
          <template #default="{ row }">{{ optionLabel(dictOptions.appointmentSlot, row.appointment_slot) }}</template>
        </el-table-column>
        <el-table-column label="会员信息" min-width="220">
          <template #default="{ row }">
            <div>{{ row.person?.name || "-" }} <span class="muted">{{ row.person?.display_no || "" }}</span></div>
            <div class="muted">{{ row.person?.primary_mobile || "-" }}</div>
          </template>
        </el-table-column>
        <el-table-column label="到访目的" min-width="130">
          <template #default="{ row }">{{ optionLabel(dictOptions.visitPurpose, row.visit_purpose) }}</template>
        </el-table-column>
        <el-table-column label="邀约来源" min-width="100">
          <template #default="{ row }"><el-tag :type="row.appointment_source === 'service' ? 'success' : 'primary'">{{ sourceLabel(row.appointment_source) }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="promised_gift" label="到店礼" min-width="130" show-overflow-tooltip />
        <el-table-column prop="operator_user_name" label="邀约人" min-width="120" />
        <el-table-column label="状态" min-width="110">
          <template #default="{ row }"><el-tag>{{ optionLabel(dictOptions.appointmentStatus, row.appointment_status) }}</el-tag></template>
        </el-table-column>
        <el-table-column fixed="right" label="操作" width="410">
          <template #default="{ row }">
            <el-button v-hasPerm="['crm:customer:visit:checkin']" link type="success" :disabled="row.appointment_status !== 'pending'" @click="checkin(row)">登记到店</el-button>
            <el-button v-hasPerm="['crm:customer:visit:consultation']" link type="primary" :disabled="!['pending', 'checked_in'].includes(row.appointment_status || '')" @click="openConsultation(row)">记录面谈</el-button>
            <el-button v-hasPerm="['crm:customer:visit:no_show']" link type="warning" :disabled="row.appointment_status !== 'pending'" @click="noShow(row)">标记爽约</el-button>
            <el-button v-hasPerm="['crm:customer:visit:cancel']" link type="danger" :disabled="row.appointment_status !== 'pending'" @click="cancel(row)">取消预约</el-button>
            <el-button link type="primary" @click="openCustomerDetail(row)">查看客户</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pager">
        <el-pagination v-model:current-page="query.page_no" v-model:page-size="query.page_size" :total="total" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next, jumper" @size-change="fetchList" @current-change="fetchList" />
      </div>
    </el-card>

    <el-dialog v-model="consultationVisible" title="记录面谈" width="620px">
      <el-form :model="consultationForm" label-width="96px">
        <el-form-item label="面谈内容" required><el-input v-model="consultationForm.content" type="textarea" :rows="4" /></el-form-item>
        <el-form-item label="需求摘要"><el-input v-model="consultationForm.need_summary" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="预算区间"><el-input v-model="consultationForm.budget_range" clearable /></el-form-item>
        <el-form-item label="主要异议"><el-input v-model="consultationForm.main_objection" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="意向等级"><el-select v-model="consultationForm.intention_level" clearable style="width: 100%"><el-option v-for="item in dictOptions.intentionLevel" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
        <el-form-item label="下次联系"><el-date-picker v-model="consultationForm.next_follow_at" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width: 100%" /></el-form-item>
        <el-form-item label="进入签约推进"><el-switch v-model="consultationForm.enter_signing" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="consultationVisible = false">取消</el-button>
        <el-button type="primary" @click="submitConsultation">保存</el-button>
      </template>
    </el-dialog>

    <customer-detail-drawer v-model="customerDetailVisible" :customer-id="customerDetailId" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";

import CustomerAPI, { type CustomerVisitConsultationForm, type CustomerVisitQuery, type CustomerVisitRecord } from "@/api/module_crm/customer";
import LeadAPI from "@/api/module_crm/lead";
import DictAPI, { type DictDataTable } from "@/api/module_system/dict";
import CustomerDetailDrawer from "@/views/module_miailove/customer/components/CustomerDetailDrawer.vue";

const loading = ref(false);
const rows = ref<CustomerVisitRecord[]>([]);
const total = ref(0);
const query = reactive<CustomerVisitQuery>({ page_no: 1, page_size: 10 });
const queryDateRange = ref<string[]>();
const userOptions = ref<Array<{ label: string; value: number }>>([]);
const consultationVisible = ref(false);
const customerDetailVisible = ref(false);
const customerDetailId = ref<number>();
const activeProcessId = ref<number>();
const consultationForm = reactive<CustomerVisitConsultationForm>({ content: "", enter_signing: false });

const dictOptions = reactive({
  appointmentSlot: [] as Array<{ label: string; value: string }>,
  visitPurpose: [] as Array<{ label: string; value: string }>,
  appointmentStatus: [] as Array<{ label: string; value: string }>,
  intentionLevel: [] as Array<{ label: string; value: string }>,
});

async function fetchList() {
  loading.value = true;
  try {
    const res = await CustomerAPI.listVisit(query);
    rows.value = res.data.data.items || [];
    total.value = res.data.data.total || 0;
  } finally {
    loading.value = false;
  }
}

function resetQuery() {
  Object.assign(query, { page_no: 1, page_size: query.page_size, keyword: undefined, scheduled_time: undefined, appointment_slot: undefined, visit_purpose: undefined, appointment_status: undefined, operator_user_id: undefined, store_id: undefined });
  queryDateRange.value = undefined;
  fetchList();
}

function syncDateRange(value?: string[]) {
  query.scheduled_time = value?.length === 2 ? [`${value[0]} 00:00:00`, `${value[1]} 23:59:59`] : undefined;
}

async function checkin(row: CustomerVisitRecord) {
  if (!row.id) return;
  await CustomerAPI.checkinVisit(row.id);
  ElMessage.success("已登记到店");
  fetchList();
}

async function noShow(row: CustomerVisitRecord) {
  if (!row.id) return;
  await ElMessageBox.confirm("确认标记该预约为爽约？", "标记爽约", { type: "warning" });
  await CustomerAPI.noShowVisit(row.id);
  ElMessage.success("已标记爽约");
  fetchList();
}

async function cancel(row: CustomerVisitRecord) {
  if (!row.id) return;
  await ElMessageBox.confirm("确认取消该预约？", "取消预约", { type: "warning" });
  await CustomerAPI.cancelVisit(row.id);
  ElMessage.success("已取消预约");
  fetchList();
}

function openConsultation(row: CustomerVisitRecord) {
  activeProcessId.value = row.id;
  Object.assign(consultationForm, { content: "", need_summary: "", budget_range: "", main_objection: "", intention_level: "", next_follow_at: "", enter_signing: false });
  consultationVisible.value = true;
}

async function submitConsultation() {
  if (!activeProcessId.value || !consultationForm.content) return;
  await CustomerAPI.consultationVisit(activeProcessId.value, consultationForm);
  ElMessage.success("面谈已记录");
  consultationVisible.value = false;
  fetchList();
}

async function openCustomerDetail(row: CustomerVisitRecord) {
  const customerId = row.customer?.id || (row as CustomerVisitRecord & { customer_id?: number }).customer_id;
  if (!customerId) {
    ElMessage.warning("当前到店记录缺少客户ID");
    return;
  }
  customerDetailId.value = customerId;
  customerDetailVisible.value = true;
}

function optionLabel(options: Array<{ label: string; value: string }>, value?: string) {
  if (!value) return "-";
  return options.find((item) => item.value === value)?.label || visitPurposeFallback(value);
}

function sourceLabel(value?: string) {
  return value === "service" ? "服务邀约" : "销售邀约";
}

function visitPurposeFallback(value: string) {
  return (
    {
      service_communication: "服务沟通",
      service_profile_completion: "资料补充",
      service_deep_interview: "深访沟通",
      service_renewal: "续费沟通",
      service_intro: "服务介绍",
      consultation: "面谈沟通",
      signing: "签约沟通",
      profile: "资料完善",
      other: "其他",
    } as Record<string, string>
  )[value] || value;
}

function formatDate(value?: string) {
  return value ? String(value).slice(0, 10) : "-";
}

async function loadOptions() {
  const [userRes] = await Promise.all([LeadAPI.salesOptions(), loadDictOptions()]);
  userOptions.value = (userRes.data.data || []).map((item) => ({ label: item.name || String(item.id), value: item.id! }));
}

async function loadDictOptions() {
  const dictMap = {
    appointmentSlot: "crm_customer_appointment_slot",
    visitPurpose: "crm_customer_visit_purpose",
    appointmentStatus: "crm_customer_appointment_status",
    intentionLevel: "crm_customer_intention_level",
  } as const;
  await Promise.all(
    Object.entries(dictMap).map(async ([key, type]) => {
      const res = await DictAPI.getInitDict(type);
      dictOptions[key as keyof typeof dictOptions] = ((res.data.data as DictDataTable[]) || []).map((item) => ({ label: item.dict_label || item.dict_value || "", value: item.dict_value || "" }));
    })
  );
}

onMounted(async () => {
  await loadOptions();
  fetchList();
});
</script>

<style scoped>
.visit-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.pager {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
.muted {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
</style>
