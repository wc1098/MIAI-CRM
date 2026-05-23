<template>
  <div class="app-container contract-page">
    <el-card shadow="never" class="filter-card">
      <el-form :model="query" inline>
        <el-form-item label="关键词">
          <el-input v-model="query.keyword" clearable placeholder="合同号/客户/手机号" style="width: 220px" @keyup.enter="fetchList" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.contract_status" clearable placeholder="全部" style="width: 140px">
            <el-option v-for="item in dictOptions.contractStatus" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="支付状态">
          <el-select v-model="query.payment_status" clearable placeholder="全部" style="width: 130px">
            <el-option v-for="item in paymentStatusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="VIP等级">
          <el-select v-model="query.vip_level" clearable placeholder="全部" style="width: 140px">
            <el-option v-for="item in dictOptions.vipLevel" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" icon="Search" @click="fetchList">查询</el-button>
          <el-button icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="toolbar">
          <div>
            <div class="toolbar-title">合同管理</div>
            <div class="toolbar-note">合同签署与首付款复核后转入 VIP 阶段</div>
          </div>
          <div class="toolbar-actions">
            <el-button v-hasPerm="['crm:contract:rule:query']" icon="Setting" @click="openRule">合同规则</el-button>
            <el-button v-hasPerm="['crm:contract:create']" type="primary" icon="Plus" @click="openCreate()">新增合同</el-button>
          </div>
        </div>
      </template>

      <el-table v-loading="loading" :data="rows" border stripe row-key="id">
        <el-table-column prop="contract_no" label="合同编号" min-width="180" show-overflow-tooltip />
        <el-table-column prop="contract_name" label="合同名称" min-width="160" show-overflow-tooltip />
        <el-table-column label="客户" min-width="130">
          <template #default="{ row }">{{ row.person?.name || "-" }} <span class="muted">{{ row.person_display_no || "" }}</span></template>
        </el-table-column>
        <el-table-column label="手机号" min-width="130">
          <template #default="{ row }">{{ row.person_mobile || "-" }}</template>
        </el-table-column>
        <el-table-column label="合同金额" width="120" align="right">
          <template #default="{ row }">{{ money(row.contract_amount) }}</template>
        </el-table-column>
        <el-table-column label="已收金额" min-width="180">
          <template #default="{ row }">
            <div class="payment-progress">
              <div class="payment-progress__text">{{ money(row.received_amount) }} / {{ money(row.contract_amount) }} · {{ progressPercent(row.payment_progress) }}%</div>
              <el-progress :percentage="progressPercent(row.payment_progress)" :stroke-width="6" :show-text="false" />
            </div>
          </template>
        </el-table-column>
        <el-table-column label="支付状态" width="100">
          <template #default="{ row }">
            <el-tag :type="paymentStatusType(row.payment_status)">{{ paymentStatusLabel(row.payment_status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }"><el-tag :type="contractStatusType(row.contract_status)">{{ optionLabel(dictOptions.contractStatus, row.contract_status) }}</el-tag></template>
        </el-table-column>
        <el-table-column label="VIP等级" width="100">
          <template #default="{ row }">{{ optionLabel(dictOptions.vipLevel, row.vip_level) }}</template>
        </el-table-column>
        <el-table-column label="有效期限" min-width="190">
          <template #default="{ row }">{{ row.validity_period || `${row.start_date} 至 ${row.end_date}` }}</template>
        </el-table-column>
        <el-table-column prop="store_name" label="门店" min-width="120" />
        <el-table-column prop="owner_user_name" label="销售" min-width="100" />
        <el-table-column prop="updated_time" label="更新时间" min-width="170" />
        <el-table-column fixed="right" label="操作" width="360" align="center">
          <template #default="{ row }">
            <div class="table-actions">
              <el-button v-hasPerm="['crm:contract:detail']" link type="primary" icon="View" @click="openDetail(row.id)">详情</el-button>
              <el-button v-if="row.contract_status === 'draft'" v-hasPerm="['crm:contract:update']" link type="primary" icon="Edit" @click="openEdit(row.id)">编辑</el-button>
              <el-button v-if="row.contract_status === 'draft'" v-hasPerm="['crm:contract:sign']" link type="success" icon="Finished" @click="signContract(row)">已签</el-button>
              <el-button v-if="row.contract_status === 'signed'" v-hasPerm="['crm:contract:submit_review']" link type="warning" icon="Promotion" @click="submitReview(row)">提交审核</el-button>
              <el-button v-if="row.contract_status === 'pending_review'" v-hasPerm="['crm:contract:review']" link type="success" icon="Check" @click="reviewContract(row, true)">通过</el-button>
              <el-button v-if="row.contract_status === 'pending_review'" v-hasPerm="['crm:contract:review']" link type="danger" icon="Close" @click="reviewContract(row, false)">驳回</el-button>
              <el-button v-if="['pending_payment', 'effective'].includes(row.contract_status) && Number(row.pending_amount || 0) > 0" v-hasPerm="['crm:receipt:submit_offline']" link type="warning" icon="Money" @click="openReceipt(row)">收款</el-button>
              <el-button v-if="['draft', 'signed'].includes(row.contract_status)" v-hasPerm="['crm:contract:void']" link type="danger" icon="CircleClose" @click="voidContract(row)">作废</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination v-model:current-page="query.page_no" v-model:page-size="query.page_size" :total="total" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next, jumper" @size-change="fetchList" @current-change="fetchList" />
      </div>
    </el-card>

    <el-dialog v-model="formVisible" :title="formMode === 'create' ? '新增合同' : '编辑合同'" width="760px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="112px">
        <el-form-item label="客户" prop="customer_id">
          <el-select v-model="form.customer_id" filterable remote reserve-keyword :remote-method="searchCustomers" :loading="customerLoading" placeholder="搜索姓名或手机号" style="width: 100%">
            <el-option v-for="item in customerOptions" :key="item.id" :label="`${item.name} ${item.mobile} ${item.display_no || ''}`" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="产品套餐" prop="product_ids">
          <el-select v-model="form.product_ids" multiple filterable placeholder="请选择产品套餐" style="width: 100%" @change="handleProductsChange">
            <el-option v-for="item in productOptions" :key="item.id" :label="`${item.package_name} ${money(item.standard_price)}`" :value="item.id!" />
          </el-select>
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="合同名称" prop="contract_name"><el-input v-model="form.contract_name" maxlength="128" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="VIP等级" prop="vip_level"><el-select v-model="form.vip_level" style="width: 100%"><el-option v-for="item in dictOptions.vipLevel" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item></el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="应收价款"><el-input :model-value="money(originalAmount)" disabled /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="合同总金额" prop="contract_amount"><el-input-number v-model="form.contract_amount" :min="0" :precision="2" style="width: 100%" /></el-form-item></el-col>
        </el-row>
        <el-form-item v-if="Number(form.contract_amount || 0) < originalAmount" label="折扣原因" prop="discount_reason"><el-input v-model="form.discount_reason" type="textarea" :rows="2" /></el-form-item>
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="开始日期" prop="start_date"><el-date-picker v-model="form.start_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" @change="handleStartDateChange" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="结束日期" prop="end_date"><el-date-picker v-model="form.end_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" @change="handleEndDateChange" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="到期提醒" prop="expire_remind_days">
          <el-input-number v-model="form.expire_remind_days" :min="0" :max="3650" :precision="0" style="width: 220px" />
          <span class="form-tip">天前提醒，0 表示到期当天提醒</span>
        </el-form-item>
        <el-form-item label="签署人" prop="signer_name"><el-input v-model="form.signer_name" maxlength="64" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="ruleVisible" title="合同规则" width="540px">
      <el-form v-loading="ruleLoading" :model="ruleForm" label-width="150px">
        <el-form-item v-if="isBrandAdmin" label="适用门店">
          <el-select v-model="ruleStoreId" filterable placeholder="请选择实际门店" style="width: 100%" @change="loadRule">
            <el-option v-for="item in deptOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item v-else label="适用门店">
          <el-input :model-value="currentUser?.dept_name || '-'" disabled />
        </el-form-item>
        <el-form-item label="合同签署后审核">
          <el-switch v-model="ruleForm.require_contract_review" active-text="需要审核" inactive-text="免审核" />
        </el-form-item>
        <el-alert type="info" show-icon :closable="false" :title="ruleTip" />
      </el-form>
      <template #footer>
        <el-button @click="ruleVisible = false">取消</el-button>
        <el-button v-hasPerm="['crm:contract:rule:update']" type="primary" :loading="ruleSaving" :disabled="!ruleStoreId" @click="submitRule">保存</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailVisible" size="78%" destroy-on-close>
      <template #header><div class="drawer-title">{{ detail?.contract_name || "合同详情" }} · {{ detail?.contract_no || "" }}</div></template>
      <template v-if="detail">
        <el-descriptions :column="3" border>
          <el-descriptions-item label="客户">{{ detail.person?.name || "-" }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ optionLabel(dictOptions.contractStatus, detail.contract_status) }}</el-descriptions-item>
          <el-descriptions-item label="VIP等级">{{ optionLabel(dictOptions.vipLevel, detail.vip_level) }}</el-descriptions-item>
          <el-descriptions-item label="应收价款">{{ money(detail.original_amount) }}</el-descriptions-item>
          <el-descriptions-item label="合同金额">{{ money(detail.contract_amount) }}</el-descriptions-item>
          <el-descriptions-item label="已收金额">{{ money(detail.received_amount) }} / {{ money(detail.contract_amount) }}</el-descriptions-item>
          <el-descriptions-item label="支付状态">{{ paymentStatusLabel(detail.payment_status) }}</el-descriptions-item>
          <el-descriptions-item label="折扣">{{ money(detail.discount_amount) }}</el-descriptions-item>
          <el-descriptions-item label="有效期限">{{ detail.validity_period || `${detail.start_date} 至 ${detail.end_date}` }}</el-descriptions-item>
          <el-descriptions-item label="到期提醒">提前 {{ detail.expire_remind_days ?? 30 }} 天</el-descriptions-item>
          <el-descriptions-item label="签署人">{{ detail.signer_name }}</el-descriptions-item>
          <el-descriptions-item label="销售">{{ detail.owner_user_name || "-" }}</el-descriptions-item>
          <el-descriptions-item label="提交审核时间">{{ detail.review_submitted_at || "-" }}</el-descriptions-item>
          <el-descriptions-item label="审核时间">{{ detail.reviewed_at || "-" }}</el-descriptions-item>
          <el-descriptions-item label="审核备注">{{ detail.review_remark || "-" }}</el-descriptions-item>
          <el-descriptions-item label="折扣原因" :span="3">{{ detail.discount_reason || "-" }}</el-descriptions-item>
          <el-descriptions-item label="备注" :span="3">{{ detail.remark || "-" }}</el-descriptions-item>
        </el-descriptions>

        <div class="section-title">产品快照</div>
        <el-table :data="detail.items" border size="small">
          <el-table-column prop="product_name_snapshot" label="产品" min-width="160" />
          <el-table-column label="价格" width="110"><template #default="{ row }">{{ money(row.price_snapshot) }}</template></el-table-column>
          <el-table-column prop="service_days_snapshot" label="时长(天)" width="90" />
          <el-table-column prop="recommendation_quota_snapshot" label="推荐" width="80" />
          <el-table-column prop="meeting_quota_snapshot" label="约见" width="80" />
          <el-table-column prop="course_quota_snapshot" label="课程" width="80" />
          <el-table-column label="线上约见" width="100"><template #default="{ row }">{{ row.supports_online_meeting_snapshot ? "支持" : "不支持" }}</template></el-table-column>
        </el-table>

        <div class="section-title">合同影像</div>
        <el-upload v-hasPerm="['crm:contract:view_file']" :show-file-list="false" :http-request="uploadAttachment" accept="image/*,.pdf">
          <el-button v-if="detail.contract_status === 'draft'" type="primary" icon="Upload">上传影像</el-button>
        </el-upload>
        <div class="attachment-list">
          <div v-for="file in detail.attachments" :key="file.id" class="attachment-item">
            <el-link :href="file.file_url" target="_blank" type="primary">{{ file.file_name || file.file_url }}</el-link>
            <el-button v-if="detail.contract_status === 'draft'" v-hasPerm="['crm:contract:view_file']" link type="danger" icon="Delete" @click="deleteAttachment(file.id)">删除</el-button>
          </div>
        </div>

        <div class="section-title">收款记录</div>
        <el-table :data="detail.receipts" border size="small">
          <el-table-column prop="receipt_no" label="收款单号" min-width="160" />
          <el-table-column label="类型" width="90"><template #default="{ row }">{{ optionLabel(dictOptions.receiptType, row.receipt_type) }}</template></el-table-column>
          <el-table-column label="方式" width="100"><template #default="{ row }">{{ optionLabel(dictOptions.payMethod, row.pay_method) }}</template></el-table-column>
          <el-table-column label="金额" width="110"><template #default="{ row }">{{ money(row.amount) }}</template></el-table-column>
          <el-table-column label="状态" width="100"><template #default="{ row }">{{ optionLabel(dictOptions.receiptStatus, row.receipt_status) }}</template></el-table-column>
          <el-table-column prop="submitted_at" label="提交时间" min-width="160" />
        </el-table>
      </template>
    </el-drawer>

    <el-dialog v-model="receiptVisible" title="收款" width="560px">
      <el-form :model="receiptForm" label-width="96px">
        <el-descriptions :column="3" border size="small" class="receipt-summary">
          <el-descriptions-item label="合同金额">{{ money(receiptContext?.contract_amount) }}</el-descriptions-item>
          <el-descriptions-item label="已收金额">{{ money(receiptContext?.received_amount) }}</el-descriptions-item>
          <el-descriptions-item label="待收金额">{{ money(receiptContext?.pending_amount) }}</el-descriptions-item>
        </el-descriptions>
        <el-form-item label="收款类型" required><el-select v-model="receiptForm.receipt_type" style="width: 100%"><el-option v-for="item in receiptTypeOptions" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
        <el-form-item label="金额" required><el-input-number v-model="receiptForm.amount" :min="0.01" :max="pendingAmount" :precision="2" style="width: 100%" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="receiptForm.remark" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="receiptVisible = false">取消</el-button>
        <el-button type="primary" @click="submitReceipt">确认收款</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute } from "vue-router";
import { ElMessage, ElMessageBox, type FormInstance, type FormRules, type UploadRequestOptions } from "element-plus";
import ContractAPI, { type ContractCustomerOption, type ContractForm, type ContractPageQuery, type ContractStoreRule, type ContractTable } from "@/api/module_crm/contract";
import ProductAPI, { type ProductPackageTable } from "@/api/module_crm/product";
import ReceiptAPI from "@/api/module_crm/receipt";
import DeptAPI, { type DeptTable } from "@/api/module_system/dept";
import DictAPI, { type DictDataTable } from "@/api/module_system/dict";
import UserAPI, { type UserInfo } from "@/api/module_system/user";
import { uploadImageDirect } from "@/utils/upload";

defineOptions({ name: "MiailoveContract", inheritAttrs: false });

const loading = ref(false);
const submitting = ref(false);
const rows = ref<ContractTable[]>([]);
const total = ref(0);
const detail = ref<ContractTable>();
const formRef = ref<FormInstance>();
const formVisible = ref(false);
const formMode = ref<"create" | "update">("create");
const detailVisible = ref(false);
const receiptVisible = ref(false);
const ruleVisible = ref(false);
const ruleLoading = ref(false);
const ruleSaving = ref(false);
const receiptContractId = ref<number>();
const receiptContext = ref<ContractTable>();
const customerLoading = ref(false);
const customerOptions = ref<ContractCustomerOption[]>([]);
const productOptions = ref<ProductPackageTable[]>([]);
const deptOptions = ref<Array<{ label: string; value: number }>>([]);
const currentUser = ref<UserInfo>();
const endDateManuallyEdited = ref(false);
const ruleStoreId = ref<number>();
const route = useRoute();

type ContractReceiptForm = {
  receipt_type: string;
  amount: number;
  remark?: string;
};

const query = reactive<ContractPageQuery>({ page_no: 1, page_size: 10 });
const form = reactive<ContractForm>({ product_ids: [], contract_name: "", contract_amount: 0, expire_remind_days: 30, signer_name: "" });
const receiptForm = reactive<ContractReceiptForm>({ receipt_type: "deposit", amount: 0 });
const ruleForm = reactive<ContractStoreRule>({ require_contract_review: true });
const dictOptions = reactive({
  vipLevel: [] as Array<{ label: string; value: string }>,
  contractStatus: [] as Array<{ label: string; value: string }>,
  receiptType: [] as Array<{ label: string; value: string }>,
  payMethod: [] as Array<{ label: string; value: string }>,
  receiptStatus: [] as Array<{ label: string; value: string }>,
  paymentScene: [] as Array<{ label: string; value: string }>,
});

const originalAmount = computed(() => form.product_ids.reduce((sum, id) => sum + Number(productOptions.value.find((item) => item.id === id)?.standard_price || 0), 0));
const totalServiceDays = computed(() => form.product_ids.reduce((sum, id) => sum + Number(productOptions.value.find((item) => item.id === id)?.service_days || 0), 0));
const hasFirstPaymentReceipt = computed(() => {
  return Boolean(
    receiptContext.value?.receipts?.some((item) => {
      return ["deposit", "full"].includes(item.receipt_type) && ["pending", "pending_payment", "approved", "refund_registered"].includes(item.receipt_status);
    })
  );
});
const receiptTypeOptions = computed(() => {
  return dictOptions.receiptType.filter((item) => {
    if (item.value === "refund") return false;
    if (hasFirstPaymentReceipt.value && ["deposit", "full"].includes(item.value)) return false;
    return true;
  });
});
const paymentStatusOptions = [
  { label: "未支付", value: "unpaid" },
  { label: "部分支付", value: "partial" },
  { label: "已结清", value: "settled" },
];
const pendingAmount = computed(() => Number(receiptContext.value?.pending_amount ?? 0));
const currentRoleCodes = computed(() => new Set((currentUser.value?.roles || []).map((role) => role.code)));
const isBrandAdmin = computed(() => Boolean(currentUser.value?.is_superuser || currentRoleCodes.value.has("ADMIN") || currentRoleCodes.value.has("HQ_OPS")));
const currentRuleStoreName = computed(() => deptOptions.value.find((item) => item.value === ruleStoreId.value)?.label || currentUser.value?.dept_name || "-");
const ruleTip = computed(() =>
  ruleForm.require_contract_review
    ? `当前配置门店：${currentRuleStoreName.value}。开启后，合同已签后需要提交审核，审核通过才进入待收款。`
    : `当前配置门店：${currentRuleStoreName.value}。关闭后，合同标记已签会直接进入待收款。`
);
const rules: FormRules = {
  customer_id: [{ required: true, message: "请选择客户", trigger: "change" }],
  product_ids: [{ required: true, message: "请选择产品套餐", trigger: "change" }],
  contract_name: [{ required: true, message: "请输入合同名称", trigger: "blur" }],
  contract_amount: [{ required: true, message: "请输入合同总金额", trigger: "blur" }],
  discount_reason: [{ required: true, message: "请输入折扣原因", trigger: "blur" }],
  start_date: [{ required: true, message: "请选择开始日期", trigger: "change" }],
  end_date: [{ required: true, message: "请选择结束日期", trigger: "change" }],
  expire_remind_days: [{ required: true, message: "请设置到期提醒天数", trigger: "change" }],
  signer_name: [{ required: true, message: "请输入签署人", trigger: "blur" }],
  vip_level: [{ required: true, message: "请选择VIP等级", trigger: "change" }],
};

function money(value?: string | number) {
  const amount = Number(value ?? 0);
  return Number.isFinite(amount) ? `¥${amount.toFixed(2)}` : "¥0.00";
}
function optionLabel(options: Array<{ label: string; value: string }>, value?: string) {
  return options.find((item) => item.value === value)?.label || value || "-";
}
function contractStatusType(status?: string) {
  return status === "effective" ? "success" : status === "expired" || status === "voided" ? "danger" : ["signed", "pending_review"].includes(status || "") ? "warning" : status === "pending_payment" ? "primary" : "info";
}
function progressPercent(value?: string | number) {
  const percent = Number(value ?? 0);
  if (!Number.isFinite(percent)) return 0;
  return Math.max(0, Math.min(100, Math.round(percent)));
}
function paymentStatusLabel(status?: string) {
  return ({ unpaid: "未支付", partial: "部分支付", settled: "已结清" } as Record<string, string>)[status || ""] || status || "-";
}
function paymentStatusType(status?: string) {
  return status === "settled" ? "success" : status === "partial" ? "warning" : "info";
}
function toOptions(rows: DictDataTable[]) {
  return rows.map((item) => ({ label: item.dict_label || "", value: item.dict_value || "" })).filter((item) => item.value);
}
function flattenDept(rows: DeptTable[], result: Array<{ label: string; value: number }> = []) {
  rows.forEach((item) => {
    if (item.id && item.parent_id) result.push({ label: item.name || String(item.id), value: item.id });
    if (item.children?.length) flattenDept(item.children, result);
  });
  return result;
}
function formatDate(date: Date) {
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, "0");
  const day = `${date.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}
function calcDefaultEndDate(startDate?: string) {
  const days = totalServiceDays.value;
  if (!startDate || days <= 0) return undefined;
  const date = new Date(`${startDate}T00:00:00`);
  if (Number.isNaN(date.getTime())) return undefined;
  date.setDate(date.getDate() + days - 1);
  return formatDate(date);
}
function syncEndDateFromProducts(force = false) {
  if (!force && endDateManuallyEdited.value) return;
  const endDate = calcDefaultEndDate(form.start_date);
  if (endDate) form.end_date = endDate;
}

async function fetchList() {
  loading.value = true;
  try {
    const res = await ContractAPI.listContract(query);
    rows.value = res.data.data.items || [];
    total.value = res.data.data.total || 0;
  } finally {
    loading.value = false;
  }
}
function resetQuery() {
  Object.assign(query, { page_no: 1, page_size: query.page_size, keyword: undefined, contract_status: undefined, payment_status: undefined, vip_level: undefined });
  fetchList();
}
async function searchCustomers(keyword: string) {
  customerLoading.value = true;
  try {
    const res = await ContractAPI.searchCustomer({ keyword, limit: 20 });
    customerOptions.value = res.data.data || [];
  } finally {
    customerLoading.value = false;
  }
}
async function loadOptions() {
  const dictTypes = ["crm_vip_level", "crm_contract_status", "crm_contract_receipt_type", "crm_contract_pay_method", "crm_contract_receipt_status", "crm_contract_payment_scene"];
  const [dictRows, deptRes, currentUserRes] = await Promise.all([
    Promise.all(dictTypes.map((type) => DictAPI.getInitDict(type))),
    DeptAPI.listDept({ status: "0" }),
    UserAPI.getCurrentUserInfo(),
  ]);
  currentUser.value = currentUserRes.data.data;
  deptOptions.value = flattenDept(deptRes.data.data || []);
  dictOptions.vipLevel = toOptions(dictRows[0].data.data || []);
  dictOptions.contractStatus = toOptions(dictRows[1].data.data || []);
  dictOptions.receiptType = toOptions(dictRows[2].data.data || []);
  dictOptions.payMethod = toOptions(dictRows[3].data.data || []);
  dictOptions.receiptStatus = toOptions(dictRows[4].data.data || []);
  dictOptions.paymentScene = toOptions(dictRows[5].data.data || []);
  productOptions.value = await fetchEnabledProducts();
  await searchCustomers("");
}

async function fetchEnabledProducts() {
  const pageSize = 100;
  let pageNo = 1;
  const items: ProductPackageTable[] = [];
  while (true) {
    const products = await ProductAPI.listProduct({ page_no: pageNo, page_size: pageSize, status: "0" });
    const page = products.data.data;
    items.push(...(page.items || []));
    if (items.length >= Number(page.total || 0) || (page.items || []).length < pageSize) break;
    pageNo += 1;
  }
  return items;
}
function resetForm() {
  endDateManuallyEdited.value = false;
  Object.assign(form, { id: undefined, customer_id: undefined, product_ids: [], contract_name: "", contract_amount: 0, discount_reason: undefined, start_date: undefined, end_date: undefined, expire_remind_days: 30, signer_name: "", vip_level: dictOptions.vipLevel[0]?.value, remark: undefined });
  formRef.value?.clearValidate();
}
function openCreate(customerId?: number) {
  formMode.value = "create";
  resetForm();
  if (customerId) form.customer_id = customerId;
  formVisible.value = true;
}
async function openEdit(id?: number) {
  if (!id) return;
  const res = await ContractAPI.detailContract(id);
  const row = res.data.data;
  formMode.value = "update";
  Object.assign(form, { ...row, product_ids: row.items.map((item) => item.product_id).filter(Boolean) as number[] });
  endDateManuallyEdited.value = true;
  formVisible.value = true;
}
async function openDetail(id?: number) {
  if (!id) return;
  const res = await ContractAPI.detailContract(id);
  detail.value = res.data.data;
  detailVisible.value = true;
}
function syncAmountFromProducts() {
  form.contract_amount = Number(originalAmount.value.toFixed(2));
}
function handleProductsChange() {
  syncAmountFromProducts();
  syncEndDateFromProducts();
}
function handleStartDateChange() {
  endDateManuallyEdited.value = false;
  syncEndDateFromProducts(true);
}
function handleEndDateChange() {
  endDateManuallyEdited.value = true;
}
async function submitForm() {
  const valid = await formRef.value?.validate();
  if (!valid) return;
  if (Number(form.contract_amount) < originalAmount.value && !form.discount_reason) {
    ElMessage.warning("合同总金额低于应收价款时必须填写折扣原因");
    return;
  }
  submitting.value = true;
  try {
    if (form.id) await ContractAPI.updateContract(Number(form.id), form);
    else await ContractAPI.createContract(form);
    ElMessage.success("合同已保存");
    formVisible.value = false;
    await fetchList();
  } finally {
    submitting.value = false;
  }
}
async function signContract(row: ContractTable) {
  if (!row.id) return;
  await ElMessageBox.confirm("确认标记合同已签？合同必须已上传影像。", "标记已签", { type: "warning" });
  const res = await ContractAPI.signContract(row.id, {});
  ElMessage.success(res.data.data.contract_status === "pending_payment" ? "合同已签，已按门店规则进入待收款" : "合同已签");
  await fetchList();
}
async function submitReview(row: ContractTable) {
  if (!row.id) return;
  await ElMessageBox.confirm("确认提交合同审核？审核通过后销售可发起收款。", "提交审核", { type: "warning" });
  await ContractAPI.submitReview(row.id);
  ElMessage.success("合同已提交审核");
  await fetchList();
}
async function reviewContract(row: ContractTable, approved: boolean) {
  if (!row.id) return;
  const { value } = await ElMessageBox.prompt(`确认${approved ? "通过" : "驳回"}合同审核？`, "合同审核", {
    inputType: "textarea",
    inputPlaceholder: approved ? "审核备注，可不填" : "请输入驳回原因",
    inputValidator: (val) => approved || !!val || "驳回必须填写原因",
  });
  await ContractAPI.reviewContract(row.id, { approved, review_remark: value });
  ElMessage.success("合同审核完成");
  await fetchList();
}
async function voidContract(row: ContractTable) {
  if (!row.id) return;
  const { value } = await ElMessageBox.prompt("请输入作废原因", "作废合同", { inputType: "textarea", inputValidator: (val) => !!val || "必须填写作废原因" });
  await ContractAPI.voidContract(row.id, { reason: value });
  ElMessage.success("合同已作废");
  await fetchList();
}
function openReceipt(row: ContractTable) {
  receiptContractId.value = row.id;
  receiptContext.value = row;
  const defaultType = receiptTypeOptions.value[0]?.value || "final";
  Object.assign(receiptForm, { receipt_type: defaultType, amount: Number(row.pending_amount || 0), remark: undefined });
  receiptVisible.value = true;
}
async function submitReceipt() {
  if (!receiptContractId.value) return;
  if (!receiptTypeOptions.value.some((item) => item.value === receiptForm.receipt_type)) {
    ElMessage.warning("请选择有效的收款类型");
    return;
  }
  if (Number(receiptForm.amount || 0) > pendingAmount.value) {
    ElMessage.warning("收款金额不能大于待收金额");
    return;
  }
  await ReceiptAPI.createPending(receiptContractId.value, receiptForm);
  ElMessage.success("待收款单已创建，请到收款管理完成收银");
  receiptVisible.value = false;
  await fetchList();
}
async function openRule() {
  const defaultStoreId = isBrandAdmin.value ? Number(query.store_id || deptOptions.value[0]?.value) : Number(currentUser.value?.dept_id);
  if (!Number.isFinite(defaultStoreId) || !defaultStoreId) {
    ElMessage.warning("当前账号未关联实际门店，无法配置合同规则");
    return;
  }
  ruleStoreId.value = defaultStoreId;
  ruleVisible.value = true;
  await loadRule();
}
async function loadRule() {
  if (!ruleStoreId.value) return;
  ruleLoading.value = true;
  try {
    const res = await ContractAPI.getStoreRule(ruleStoreId.value);
    Object.assign(ruleForm, res.data.data || { require_contract_review: true });
  } finally {
    ruleLoading.value = false;
  }
}
async function submitRule() {
  if (!ruleStoreId.value) return;
  ruleSaving.value = true;
  try {
    await ContractAPI.setStoreRule(ruleStoreId.value, { require_contract_review: ruleForm.require_contract_review });
    ElMessage.success("合同规则已保存");
    ruleVisible.value = false;
    await fetchList();
  } finally {
    ruleSaving.value = false;
  }
}
async function uploadAttachment(options: UploadRequestOptions) {
  if (!detail.value?.id) return;
  const fileInfo = await uploadImageDirect(options.file, "crm_contract_attachment");
  await ContractAPI.saveAttachment(detail.value.id, {
    file_name: fileInfo.origin_name || fileInfo.file_name,
    file_path: fileInfo.object_key || fileInfo.file_path,
    file_url: fileInfo.file_url,
    file_type: options.file.type === "application/pdf" ? "pdf" : "image",
  });
  ElMessage.success("合同影像已上传");
  await openDetail(detail.value.id);
}
async function deleteAttachment(attachmentId?: number) {
  if (!attachmentId || !detail.value?.id) return;
  await ElMessageBox.confirm("确认删除这份合同影像？删除后不会作为有效合同影像参与签署。", "删除合同影像", { type: "warning" });
  await ContractAPI.deleteAttachment(attachmentId);
  ElMessage.success("合同影像已删除");
  await openDetail(detail.value.id);
}

defineExpose({ openCreate, fetchList });

onMounted(async () => {
  await loadOptions();
  await fetchList();
  const customerId = Number(route.query.customer_id || 0);
  const contractId = Number(route.query.contract_id || 0);
  if (customerId) openCreate(customerId);
  if (contractId) await openDetail(contractId);
});
</script>

<style scoped>
.contract-page { display: flex; flex-direction: column; gap: 12px; }
.filter-card :deep(.el-card__body) { padding-bottom: 0; }
.toolbar { display: flex; justify-content: space-between; align-items: center; gap: 16px; }
.toolbar-title { font-size: 16px; font-weight: 600; color: var(--el-text-color-primary); }
.toolbar-note, .muted { color: var(--el-text-color-secondary); font-size: 13px; }
.form-tip { margin-left: 10px; color: var(--el-text-color-secondary); font-size: 13px; }
.receipt-summary { margin-bottom: 16px; }
.table-actions { display: inline-flex; align-items: center; justify-content: center; gap: 6px; white-space: nowrap; }
.payment-progress { display: flex; flex-direction: column; gap: 4px; }
.payment-progress__text { font-size: 12px; line-height: 16px; color: var(--el-text-color-primary); white-space: nowrap; }
.pager { display: flex; justify-content: flex-end; padding-top: 16px; }
.drawer-title { font-size: 16px; font-weight: 600; }
.section-title { margin: 18px 0 10px; font-size: 15px; font-weight: 600; color: var(--el-text-color-primary); }
.attachment-list { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px; }
.attachment-item { display: inline-flex; align-items: center; gap: 6px; padding: 4px 8px; border: 1px solid var(--el-border-color-light); border-radius: 4px; }
</style>
