<template>
  <div class="app-container receipt-page">
    <el-card shadow="never" class="filter-card">
      <el-form :model="query" inline>
        <el-form-item label="关键词">
          <el-input v-model="query.keyword" clearable placeholder="单号/合同/客户/手机号" style="width: 220px" @keyup.enter="fetchList" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="query.receipt_type" clearable placeholder="全部" style="width: 130px">
            <el-option v-for="item in dictOptions.receiptType" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="场景">
          <el-select v-model="query.payment_scene" clearable placeholder="全部" style="width: 130px">
            <el-option v-for="item in dictOptions.paymentScene" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.receipt_status" clearable placeholder="全部" style="width: 130px">
            <el-option v-for="item in dictOptions.receiptStatus" :key="item.value" :label="item.label" :value="item.value" />
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
            <div class="toolbar-title">收款管理</div>
            <div class="toolbar-note">合同收款、在线支付、复核、冲正与退款登记</div>
          </div>
        </div>
      </template>

      <el-table v-loading="loading" :data="rows" border stripe row-key="id">
        <el-table-column prop="receipt_no" label="收款单号" min-width="165" show-overflow-tooltip />
        <el-table-column prop="contract_no" label="合同编号" min-width="170" show-overflow-tooltip />
        <el-table-column label="客户" min-width="130">
          <template #default="{ row }">{{ row.person_name || "-" }} <span class="muted">{{ row.person_display_no || "" }}</span></template>
        </el-table-column>
        <el-table-column label="类型" width="90"><template #default="{ row }">{{ optionLabel(dictOptions.receiptType, row.receipt_type) }}</template></el-table-column>
        <el-table-column label="场景" width="95"><template #default="{ row }">{{ optionLabel(dictOptions.paymentScene, row.payment_scene) }}</template></el-table-column>
        <el-table-column label="方式" width="95"><template #default="{ row }">{{ optionLabel(dictOptions.payMethod, row.pay_method) }}</template></el-table-column>
        <el-table-column label="金额" width="115" align="right"><template #default="{ row }">{{ money(row.amount) }}</template></el-table-column>
        <el-table-column label="状态" width="105"><template #default="{ row }"><el-tag :type="statusType(row.receipt_status)">{{ optionLabel(dictOptions.receiptStatus, row.receipt_status) }}</el-tag></template></el-table-column>
        <el-table-column prop="store_name" label="门店" min-width="110" show-overflow-tooltip />
        <el-table-column prop="owner_user_name" label="销售" min-width="100" />
        <el-table-column prop="submitted_at" label="提交时间" min-width="160" />
        <el-table-column prop="confirmed_at" label="确认时间" min-width="160" />
        <el-table-column fixed="right" label="操作" width="330" align="center">
          <template #default="{ row }">
            <div class="table-actions">
              <el-button v-hasPerm="['crm:receipt:detail']" link type="primary" icon="View" @click="openDetail(row.id)">详情</el-button>
              <el-button v-if="row.receipt_status === 'pending_payment'" v-hasPerm="['crm:receipt:create_online']" link type="warning" icon="Money" @click="openCashier(row)">收银</el-button>
              <el-button v-if="row.receipt_status === 'pending'" v-hasPerm="['crm:receipt:review']" link type="success" icon="Check" @click="review(row, true)">通过</el-button>
              <el-button v-if="row.receipt_status === 'pending'" v-hasPerm="['crm:receipt:review']" link type="danger" icon="Close" @click="review(row, false)">驳回</el-button>
              <el-button v-if="['pending', 'pending_payment', 'rejected'].includes(row.receipt_status)" v-hasPerm="['crm:receipt:void']" link type="danger" icon="CircleClose" @click="voidReceipt(row)">作废</el-button>
              <el-button v-if="row.receipt_status === 'approved'" v-hasPerm="['crm:receipt:reverse']" link type="danger" icon="RefreshLeft" @click="reverse(row)">冲正</el-button>
              <el-button v-if="row.receipt_status === 'approved'" v-hasPerm="['crm:receipt:refund_register']" link type="danger" icon="Tickets" @click="openRefund(row)">退款登记</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination v-model:current-page="query.page_no" v-model:page-size="query.page_size" :total="total" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next, jumper" @size-change="fetchList" @current-change="fetchList" />
      </div>
    </el-card>

    <el-drawer v-model="detailVisible" size="720px" destroy-on-close>
      <template #header><div class="drawer-title">收款详情 · {{ detail?.receipt_no || "" }}</div></template>
      <el-descriptions v-if="detail" :column="2" border>
        <el-descriptions-item label="合同">{{ detail.contract_no || "-" }}</el-descriptions-item>
        <el-descriptions-item label="客户">{{ detail.person_name || "-" }}</el-descriptions-item>
        <el-descriptions-item label="收款类型">{{ optionLabel(dictOptions.receiptType, detail.receipt_type) }}</el-descriptions-item>
        <el-descriptions-item label="支付场景">{{ optionLabel(dictOptions.paymentScene, detail.payment_scene) }}</el-descriptions-item>
        <el-descriptions-item label="支付方式">{{ optionLabel(dictOptions.payMethod, detail.pay_method) }}</el-descriptions-item>
        <el-descriptions-item label="金额">{{ money(detail.amount) }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ optionLabel(dictOptions.receiptStatus, detail.receipt_status) }}</el-descriptions-item>
        <el-descriptions-item label="渠道流水">{{ detail.channel_trade_no || "-" }}</el-descriptions-item>
        <el-descriptions-item label="订单号">{{ detail.order_no || "-" }}</el-descriptions-item>
        <el-descriptions-item label="订单状态">{{ detail.order_pay_status || "-" }}</el-descriptions-item>
        <el-descriptions-item label="提交时间">{{ detail.submitted_at || "-" }}</el-descriptions-item>
        <el-descriptions-item label="确认时间">{{ detail.confirmed_at || "-" }}</el-descriptions-item>
        <el-descriptions-item label="复核备注" :span="2">{{ detail.review_remark || "-" }}</el-descriptions-item>
        <el-descriptions-item label="作废原因" :span="2">{{ detail.void_reason || "-" }}</el-descriptions-item>
        <el-descriptions-item label="冲正/退款原因" :span="2">{{ detail.reverse_reason || "-" }}</el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">{{ detail.remark || "-" }}</el-descriptions-item>
      </el-descriptions>
    </el-drawer>

    <el-dialog v-model="cashierVisible" title="收银" width="560px">
      <el-descriptions v-if="cashierReceipt" :column="2" border size="small" class="cashier-summary">
        <el-descriptions-item label="收款单号">{{ cashierReceipt.receipt_no }}</el-descriptions-item>
        <el-descriptions-item label="客户">{{ cashierReceipt.person_name || "-" }}</el-descriptions-item>
        <el-descriptions-item label="收款类型">{{ optionLabel(dictOptions.receiptType, cashierReceipt.receipt_type) }}</el-descriptions-item>
        <el-descriptions-item label="金额">{{ money(cashierReceipt.amount) }}</el-descriptions-item>
      </el-descriptions>
      <el-form :model="cashierForm" label-width="96px">
        <el-form-item label="支付方式" required>
          <el-select v-model="cashierForm.pay_method" style="width: 100%" @change="handleCashierPayMethodChange">
            <el-option label="微信" value="wechat" />
            <el-option label="支付宝" value="alipay" />
            <el-option label="现金" value="cash" />
            <el-option label="银行转账" value="bank_transfer" />
          </el-select>
        </el-form-item>
        <el-form-item label="支付场景" required>
          <el-select v-model="cashierForm.payment_scene" style="width: 100%">
            <el-option v-for="item in cashierSceneOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="cashierForm.payment_scene === 'barcode'" label="付款码" required><el-input v-model="cashierForm.auth_code" clearable /></el-form-item>
        <el-form-item v-if="cashierForm.payment_scene === 'offline'" label="备注"><el-input v-model="cashierForm.remark" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <div v-if="qrImageUrl" class="qr-panel">
        <img :src="qrImageUrl" alt="收款二维码" />
        <div class="muted">请让客户扫码完成支付</div>
      </div>
      <template #footer>
        <el-button @click="cashierVisible = false">关闭</el-button>
        <el-button type="primary" @click="submitCashier">提交</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="refundVisible" title="退款登记" width="480px">
      <el-form :model="refundForm" label-width="96px">
        <el-form-item label="退款金额" required><el-input-number v-model="refundForm.amount" :min="0.01" :precision="2" style="width: 100%" /></el-form-item>
        <el-form-item label="退款原因" required><el-input v-model="refundForm.reason" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="refundVisible = false">取消</el-button>
        <el-button type="primary" @click="submitRefund">登记</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import QRCode from "qrcode";
import DictAPI, { type DictDataTable } from "@/api/module_system/dict";
import ReceiptAPI, { type ReceiptPageQuery, type ReceiptTable } from "@/api/module_crm/receipt";

defineOptions({ name: "MiailoveReceipt", inheritAttrs: false });

const loading = ref(false);
const rows = ref<ReceiptTable[]>([]);
const total = ref(0);
const detail = ref<ReceiptTable>();
const detailVisible = ref(false);
const cashierVisible = ref(false);
const cashierReceipt = ref<ReceiptTable>();
const qrImageUrl = ref("");
const cashierPollingTimer = ref<ReturnType<typeof setInterval>>();
const cashierPollingCount = ref(0);
const refundVisible = ref(false);
const refundReceiptId = ref<number>();

const query = reactive<ReceiptPageQuery>({ page_no: 1, page_size: 10 });
const cashierForm = reactive({ pay_method: "wechat", payment_scene: "qrcode", auth_code: "", remark: "" });
const refundForm = reactive({ amount: 0, reason: "" });
const dictOptions = reactive({
  receiptType: [] as Array<{ label: string; value: string }>,
  payMethod: [] as Array<{ label: string; value: string }>,
  receiptStatus: [] as Array<{ label: string; value: string }>,
  paymentScene: [] as Array<{ label: string; value: string }>,
});
const cashierSceneOptions = computed(() => {
  if (["wechat", "alipay"].includes(cashierForm.pay_method)) {
    return [
      { label: "扫码支付", value: "qrcode" },
      { label: "条码支付", value: "barcode" },
    ];
  }
  return [{ label: "线下确认", value: "offline" }];
});

function toOptions(rows: DictDataTable[]) {
  return rows.map((item) => ({ label: item.dict_label || "", value: item.dict_value || "" })).filter((item) => item.value);
}
function money(value?: string | number) {
  const amount = Number(value ?? 0);
  return Number.isFinite(amount) ? `¥${amount.toFixed(2)}` : "¥0.00";
}
function optionLabel(options: Array<{ label: string; value: string }>, value?: string) {
  return options.find((item) => item.value === value)?.label || value || "-";
}
function statusType(status?: string) {
  if (status === "approved") return "success";
  if (["rejected", "reversed", "refund_registered"].includes(status || "")) return "danger";
  if (["pending", "pending_payment"].includes(status || "")) return "warning";
  return "info";
}
function paymentPayloadValue(payload: Record<string, unknown> | undefined, key: string): string {
  const direct = payload?.[key];
  if (typeof direct === "string") return direct;
  const payPayload = payload?.pay_payload;
  if (payPayload && typeof payPayload === "object" && key in payPayload) {
    const value = (payPayload as Record<string, unknown>)[key];
    return typeof value === "string" ? value : "";
  }
  return "";
}
async function loadOptions() {
  const dictTypes = ["crm_contract_receipt_type", "crm_contract_pay_method", "crm_contract_receipt_status", "crm_contract_payment_scene"];
  const rows = await Promise.all(dictTypes.map((type) => DictAPI.getInitDict(type)));
  dictOptions.receiptType = toOptions(rows[0].data.data || []);
  dictOptions.payMethod = toOptions(rows[1].data.data || []);
  dictOptions.receiptStatus = toOptions(rows[2].data.data || []);
  dictOptions.paymentScene = toOptions(rows[3].data.data || []);
}
async function fetchList() {
  loading.value = true;
  try {
    const res = await ReceiptAPI.listReceipt(query);
    rows.value = res.data.data.items || [];
    total.value = res.data.data.total || 0;
  } finally {
    loading.value = false;
  }
}
function resetQuery() {
  Object.assign(query, { page_no: 1, page_size: query.page_size, keyword: undefined, receipt_type: undefined, payment_scene: undefined, pay_method: undefined, receipt_status: undefined });
  fetchList();
}
async function openDetail(id?: number) {
  if (!id) return;
  const res = await ReceiptAPI.detailReceipt(id);
  detail.value = res.data.data;
  detailVisible.value = true;
}
async function review(row: ReceiptTable, approved: boolean) {
  if (!row.id) return;
  await ElMessageBox.confirm(`确认${approved ? "通过" : "驳回"}该收款？`, "收款复核", { type: "warning" });
  await ReceiptAPI.reviewReceipt(row.id, { approved });
  ElMessage.success("收款复核完成");
  await fetchList();
}
async function voidReceipt(row: ReceiptTable) {
  if (!row.id) return;
  const { value } = await ElMessageBox.prompt("请输入作废原因", "作废收款", { inputType: "textarea", inputValidator: (val) => !!val || "必须填写作废原因" });
  await ReceiptAPI.voidReceipt(row.id, { reason: value });
  ElMessage.success("收款已作废");
  await fetchList();
}
async function reverse(row: ReceiptTable) {
  if (!row.id) return;
  const { value } = await ElMessageBox.prompt("请输入冲正原因", "冲正收款", { inputType: "textarea", inputValidator: (val) => !!val || "必须填写冲正原因" });
  await ReceiptAPI.reverseReceipt(row.id, { reason: value });
  ElMessage.success("收款已冲正");
  await fetchList();
}
function handleCashierPayMethodChange() {
  stopCashierPolling();
  cashierForm.payment_scene = ["wechat", "alipay"].includes(cashierForm.pay_method) ? "qrcode" : "offline";
  cashierForm.auth_code = "";
  qrImageUrl.value = "";
}
function openCashier(row: ReceiptTable) {
  stopCashierPolling();
  cashierReceipt.value = row;
  qrImageUrl.value = "";
  Object.assign(cashierForm, { pay_method: "wechat", payment_scene: "qrcode", auth_code: "", remark: "" });
  cashierVisible.value = true;
}
function stopCashierPolling() {
  if (cashierPollingTimer.value) {
    clearInterval(cashierPollingTimer.value);
    cashierPollingTimer.value = undefined;
  }
  cashierPollingCount.value = 0;
}
function startCashierPolling(receiptId: number) {
  stopCashierPolling();
  cashierPollingTimer.value = setInterval(async () => {
    cashierPollingCount.value += 1;
    try {
      const res = await ReceiptAPI.detailReceipt(receiptId);
      const receipt = res.data.data;
      cashierReceipt.value = receipt;
      if (receipt.receipt_status === "approved") {
        stopCashierPolling();
        qrImageUrl.value = "";
        cashierVisible.value = false;
        ElMessage.success("支付成功，收款已确认");
        await fetchList();
      } else if (receipt.receipt_status !== "pending_payment") {
        stopCashierPolling();
        await fetchList();
      } else if (cashierPollingCount.value >= 90) {
        stopCashierPolling();
      }
    } catch {
      if (cashierPollingCount.value >= 3) {
        stopCashierPolling();
      }
    }
  }, 2000);
}
async function submitCashier() {
  if (!cashierReceipt.value?.id) return;
  if (cashierForm.payment_scene === "offline") {
    await ReceiptAPI.offlineConfirm(cashierReceipt.value.id, {
      pay_method: cashierForm.pay_method,
      remark: cashierForm.remark,
    });
    ElMessage.success("线下收款已提交，等待复核");
    cashierVisible.value = false;
    await fetchList();
    return;
  }
  if (cashierForm.payment_scene === "qrcode") {
    const res = await ReceiptAPI.qrcodePay(cashierReceipt.value.id, { pay_channel: cashierForm.pay_method });
    const qrCode = paymentPayloadValue(res.data.data.payment, "qr_code");
    if (qrCode) {
      qrImageUrl.value = await QRCode.toDataURL(qrCode, { width: 220, margin: 1 });
      startCashierPolling(cashierReceipt.value.id);
      ElMessage.success("二维码已生成");
    } else {
      ElMessage.warning("支付已创建，但未返回二维码");
    }
    await fetchList();
    return;
  }
  if (!cashierForm.auth_code) {
    ElMessage.warning("请填写付款码");
    return;
  }
  const res = await ReceiptAPI.barcodePay(cashierReceipt.value.id, {
    auth_code: cashierForm.auth_code,
    pay_channel: cashierForm.pay_method,
  });
  ElMessage.success(res.data.data.payment?.paid ? "支付成功" : "支付请求已提交");
  cashierVisible.value = false;
  await fetchList();
}
function openRefund(row: ReceiptTable) {
  refundReceiptId.value = row.id;
  Object.assign(refundForm, { amount: Math.abs(Number(row.amount || 0)), reason: "" });
  refundVisible.value = true;
}
async function submitRefund() {
  if (!refundReceiptId.value || !refundForm.reason) {
    ElMessage.warning("请填写退款原因");
    return;
  }
  await ReceiptAPI.refundRegister(refundReceiptId.value, refundForm);
  ElMessage.success("退款已登记");
  refundVisible.value = false;
  await fetchList();
}

onMounted(async () => {
  await loadOptions();
  await fetchList();
});
onUnmounted(stopCashierPolling);
watch(cashierVisible, (visible) => {
  if (!visible) stopCashierPolling();
});
</script>

<style scoped>
.receipt-page { display: flex; flex-direction: column; gap: 12px; }
.filter-card :deep(.el-card__body) { padding-bottom: 0; }
.toolbar { display: flex; justify-content: space-between; align-items: center; gap: 16px; }
.toolbar-title { font-size: 16px; font-weight: 600; color: var(--el-text-color-primary); }
.toolbar-note, .muted { color: var(--el-text-color-secondary); font-size: 13px; }
.table-actions { display: inline-flex; align-items: center; justify-content: center; flex-wrap: wrap; gap: 6px; }
.cashier-summary { margin-bottom: 16px; }
.qr-panel { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 12px 0; }
.qr-panel img { width: 220px; height: 220px; }
.pager { display: flex; justify-content: flex-end; padding-top: 16px; }
.drawer-title { font-size: 16px; font-weight: 600; }
</style>
