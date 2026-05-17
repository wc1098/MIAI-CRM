<template>
  <div class="app-container certification-page">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="认证套餐" name="packages">
        <el-card shadow="never">
          <template #header>
            <div class="toolbar"><div class="toolbar-title">认证套餐</div><el-button @click="loadConfig">刷新</el-button></div>
          </template>
          <el-table v-loading="configLoading" :data="packages" border>
            <el-table-column prop="level_name" label="等级" width="120" />
            <el-table-column prop="price" label="价格" width="110"><template #default="{ row }">¥{{ row.price }}</template></el-table-column>
            <el-table-column label="包含认证项" min-width="300"><template #default="{ row }">{{ row.item_codes.map(itemLabel).join("、") }}</template></el-table-column>
            <el-table-column label="赠券" width="140"><template #default="{ row }">{{ row.reward_coupon_count }} 张 / {{ row.reward_coupon_valid_days }} 天</template></el-table-column>
            <el-table-column prop="benefit_desc" label="权益" min-width="220" show-overflow-tooltip />
            <el-table-column prop="status" label="状态" width="90"><template #default="{ row }"><el-tag :type="row.status === '0' ? 'success' : 'info'">{{ row.status === "0" ? "启用" : "停用" }}</el-tag></template></el-table-column>
            <el-table-column label="操作" width="100" fixed="right"><template #default="{ row }"><el-button link type="primary" @click="openPackage(row)">编辑</el-button></template></el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="认证项" name="items">
        <el-card shadow="never">
          <template #header>
            <div class="toolbar"><div class="toolbar-title">认证项</div><el-button @click="loadConfig">刷新</el-button></div>
          </template>
          <el-table v-loading="configLoading" :data="items" border>
            <el-table-column prop="sort" label="排序" width="80" />
            <el-table-column prop="item_code" label="编码" width="120" />
            <el-table-column prop="item_name" label="名称" width="140" />
            <el-table-column prop="verify_mode" label="核验方式" width="120"><template #default="{ row }">{{ modeLabel(row.verify_mode) }}</template></el-table-column>
            <el-table-column prop="material_required" label="材料" width="90"><template #default="{ row }">{{ row.material_required ? "需要" : "无需" }}</template></el-table-column>
            <el-table-column prop="material_desc" label="材料说明" min-width="220" show-overflow-tooltip />
            <el-table-column prop="validity_days" label="有效期" width="110"><template #default="{ row }">{{ row.validity_days ? `${row.validity_days} 天` : "长期" }}</template></el-table-column>
            <el-table-column prop="status" label="状态" width="90"><template #default="{ row }"><el-tag :type="row.status === '0' ? 'success' : 'info'">{{ row.status === "0" ? "启用" : "停用" }}</el-tag></template></el-table-column>
            <el-table-column label="操作" width="100" fixed="right"><template #default="{ row }"><el-button link type="primary" @click="openItem(row)">编辑</el-button></template></el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="认证申请" name="applications">
        <el-card shadow="never">
          <template #header>
            <div class="toolbar"><div class="toolbar-title">认证申请</div><el-button @click="loadApplications">刷新</el-button></div>
          </template>
          <el-form :model="appQuery" inline>
            <el-form-item label="关键词"><el-input v-model="appQuery.keyword" clearable placeholder="编号/昵称/手机号/姓名" /></el-form-item>
            <el-form-item label="等级"><el-select v-model="appQuery.level_code" clearable style="width: 140px"><el-option v-for="item in levelOptions" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
            <el-form-item label="状态"><el-select v-model="appQuery.status" clearable style="width: 150px"><el-option v-for="item in appStatusOptions" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
            <el-form-item><el-button type="primary" @click="loadApplications">查询</el-button></el-form-item>
          </el-form>
          <el-table v-loading="appLoading" :data="applications" border>
            <el-table-column prop="display_no" label="编号" width="100" />
            <el-table-column prop="person_name" label="姓名" width="110" />
            <el-table-column prop="mobile" label="手机号" width="130" />
            <el-table-column prop="level_name" label="申请等级" width="120" />
            <el-table-column prop="current_level_name" label="当前等级" width="120" />
            <el-table-column label="状态" width="120"><template #default="{ row }"><el-tag :type="appStatusType(row.application_status)">{{ appStatusLabel(row.application_status) }}</el-tag></template></el-table-column>
            <el-table-column label="进度" min-width="220"><template #default="{ row }"><el-progress :percentage="row.progress?.percent || progressPercent(row)" :stroke-width="10" /></template></el-table-column>
            <el-table-column prop="paid_at" label="支付时间" min-width="170" />
            <el-table-column prop="approved_at" label="通过时间" min-width="170" />
            <el-table-column label="操作" width="110" fixed="right"><template #default="{ row }"><el-button link type="primary" @click="openApplication(row.id)">详情</el-button></template></el-table-column>
          </el-table>
          <div class="pager"><el-pagination v-model:current-page="appQuery.page_no" v-model:page-size="appQuery.page_size" :total="appTotal" layout="total, sizes, prev, pager, next" @size-change="loadApplications" @current-change="loadApplications" /></div>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="核验日志" name="logs">
        <el-card shadow="never">
          <template #header>
            <div class="toolbar"><div class="toolbar-title">核验日志</div><el-button @click="loadLogs">刷新</el-button></div>
          </template>
          <el-form :model="logQuery" inline>
            <el-form-item label="关键词"><el-input v-model="logQuery.keyword" clearable placeholder="编号/昵称/手机号/姓名" /></el-form-item>
            <el-form-item><el-button type="primary" @click="loadLogs">查询</el-button></el-form-item>
          </el-form>
          <el-table v-loading="logLoading" :data="verificationLogs" border>
            <el-table-column prop="display_no" label="编号" width="100" />
            <el-table-column prop="person_name" label="姓名" width="110" />
            <el-table-column prop="mobile" label="手机号" width="130" />
            <el-table-column prop="verifier_code" label="核验器" width="150" />
            <el-table-column label="状态" width="100"><template #default="{ row }"><el-tag :type="row.verify_status === 'success' ? 'success' : 'danger'">{{ row.verify_status }}</el-tag></template></el-table-column>
            <el-table-column prop="request_snapshot" label="请求摘要" min-width="220"><template #default="{ row }">{{ jsonText(row.request_snapshot) }}</template></el-table-column>
            <el-table-column prop="error_message" label="错误" min-width="180" />
            <el-table-column prop="verified_at" label="时间" min-width="170" />
          </el-table>
          <div class="pager"><el-pagination v-model:current-page="logQuery.page_no" v-model:page-size="logQuery.page_size" :total="logTotal" layout="total, sizes, prev, pager, next" @size-change="loadLogs" @current-change="loadLogs" /></div>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="人脸日志" name="faceLogs">
        <el-card shadow="never">
          <template #header>
            <div class="toolbar"><div class="toolbar-title">人脸检测日志</div><el-button @click="loadFaceLogs">刷新</el-button></div>
          </template>
          <el-table v-loading="faceLogLoading" :data="faceLogs" border>
            <el-table-column prop="display_no" label="编号" width="100" />
            <el-table-column prop="person_name" label="姓名" width="110" />
            <el-table-column label="图片" width="90"><template #default="{ row }"><el-image v-if="row.file_url" class="thumb" :src="ossImage(row.file_url, { w: 64, h: 64 })" :preview-src-list="ossImageList([row.file_url], { w: 1600 })" preview-teleported fit="cover" /></template></el-table-column>
            <el-table-column prop="business_type" label="业务" width="150" />
            <el-table-column prop="face_count" label="人脸数" width="80" />
            <el-table-column prop="quality_score" label="质量" width="90" />
            <el-table-column prop="beauty_score" label="颜值" width="90" />
            <el-table-column prop="age" label="年龄" width="80" />
            <el-table-column prop="gender" label="性别" width="80" />
            <el-table-column label="结果" width="90"><template #default="{ row }"><el-tag :type="row.passed ? 'success' : 'danger'">{{ row.passed ? "通过" : "拒绝" }}</el-tag></template></el-table-column>
            <el-table-column prop="error_message" label="错误" min-width="180" />
            <el-table-column prop="detected_at" label="时间" min-width="170" />
          </el-table>
          <div class="pager"><el-pagination v-model:current-page="faceLogQuery.page_no" v-model:page-size="faceLogQuery.page_size" :total="faceLogTotal" layout="total, sizes, prev, pager, next" @size-change="loadFaceLogs" @current-change="loadFaceLogs" /></div>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="packageVisible" title="认证套餐" width="680px">
      <el-form :model="packageForm" label-width="120px">
        <el-form-item label="等级名称"><el-input v-model="packageForm.level_name" /></el-form-item>
        <el-form-item label="价格"><el-input v-model="packageForm.price" style="width: 220px"><template #prepend>¥</template></el-input></el-form-item>
        <el-form-item label="认证项"><el-checkbox-group v-model="packageForm.item_codes"><el-checkbox v-for="item in items" :key="item.item_code" :label="item.item_code">{{ item.item_name }}</el-checkbox></el-checkbox-group></el-form-item>
        <el-form-item label="赠送解锁券"><el-input-number v-model="packageForm.reward_coupon_count" :min="0" /></el-form-item>
        <el-form-item label="赠券有效期"><el-input-number v-model="packageForm.reward_coupon_valid_days" :min="1" /><span class="muted">天</span></el-form-item>
        <el-form-item label="状态"><el-switch v-model="packageEnabled" /></el-form-item>
        <el-form-item label="权益"><el-input v-model="packageForm.benefit_desc" type="textarea" :rows="4" placeholder="填写线下权益、服务承诺或到店福利，小程序档位卡片会展示给用户" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="packageVisible = false">取消</el-button><el-button type="primary" @click="savePackage">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="itemVisible" title="认证项" width="620px">
      <el-form :model="itemForm" label-width="120px">
        <el-form-item label="名称"><el-input v-model="itemForm.item_name" /></el-form-item>
        <el-form-item label="核验方式"><el-select v-model="itemForm.verify_mode" style="width: 180px"><el-option label="接口自动" value="auto_api" /><el-option label="人工审核" value="manual" /></el-select></el-form-item>
        <el-form-item label="核验器"><el-input v-model="itemForm.verifier_code" /></el-form-item>
        <el-form-item label="材料说明"><el-input v-model="itemForm.material_desc" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="需要材料"><el-switch v-model="itemForm.material_required" /></el-form-item>
        <el-form-item label="有效期"><el-input-number v-model="itemForm.validity_days" :min="1" /><span class="muted">留空为长期</span></el-form-item>
        <el-form-item label="排序"><el-input-number v-model="itemForm.sort" :min="0" /></el-form-item>
        <el-form-item label="状态"><el-switch v-model="itemEnabled" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="itemVisible = false">取消</el-button><el-button type="primary" @click="saveItem">保存</el-button></template>
    </el-dialog>

    <el-drawer v-model="detailVisible" title="认证申请详情" size="760px">
      <template v-if="detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="用户">{{ detail.person_name }} / {{ detail.mobile }}</el-descriptions-item>
          <el-descriptions-item label="编号">{{ detail.display_no }}</el-descriptions-item>
          <el-descriptions-item label="申请等级">{{ detail.level_name }}</el-descriptions-item>
          <el-descriptions-item label="当前等级">{{ detail.current_level_name || detail.current_level }}</el-descriptions-item>
          <el-descriptions-item label="申请状态">{{ appStatusLabel(detail.application_status) }}</el-descriptions-item>
          <el-descriptions-item label="奖励">{{ detail.reward_granted ? "已发放" : "未发放" }}</el-descriptions-item>
          <el-descriptions-item label="订单号">{{ detail.order?.order_no || "-" }}</el-descriptions-item>
          <el-descriptions-item label="支付">{{ detail.order ? `${detail.order.pay_status} / ¥${detail.order.payable_amount}` : "-" }}</el-descriptions-item>
          <el-descriptions-item label="身份证">{{ detail.id_card_no_masked || "-" }} <el-button v-if="detail.person_id" link type="primary" @click="viewIdCard(detail.person_id)">查看完整</el-button></el-descriptions-item>
        </el-descriptions>
        <el-progress class="detail-progress" :percentage="detail.progress?.percent || progressPercent(detail)" />
        <el-table :data="detail.records || []" border>
          <el-table-column prop="item_name" label="认证项" width="130" />
          <el-table-column label="状态" width="110"><template #default="{ row }"><el-tag :type="recordStatusType(row.record_status)">{{ recordStatusLabel(row.record_status) }}</el-tag></template></el-table-column>
          <el-table-column label="材料" min-width="180">
            <template #default="{ row }">
              <el-image v-for="material in row.materials || []" :key="material.id" class="thumb" :src="ossImage(material.file_url, { w: 64, h: 64 })" :preview-src-list="ossImageList([material.file_url], { w: 1600 })" preview-teleported fit="cover" />
              <span v-if="!row.materials?.length">-</span>
            </template>
          </el-table-column>
          <el-table-column prop="reject_reason" label="驳回原因" min-width="160" />
          <el-table-column prop="submitted_at" label="提交时间" min-width="160" />
          <el-table-column prop="verified_at" label="通过时间" min-width="160" />
        </el-table>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import CertificationAdminAPI, {
  type CertificationApplication,
  type CertificationFaceLog,
  type CertificationItem,
  type CertificationPackage,
  type CertificationVerificationLog,
} from "@/api/module_certification/admin";
import { ossImage, ossImageList } from "@/utils/ossImage";

const activeTab = ref("packages");
const configLoading = ref(false);
const appLoading = ref(false);
const logLoading = ref(false);
const faceLogLoading = ref(false);
const items = ref<CertificationItem[]>([]);
const packages = ref<CertificationPackage[]>([]);
const applications = ref<CertificationApplication[]>([]);
const verificationLogs = ref<CertificationVerificationLog[]>([]);
const faceLogs = ref<CertificationFaceLog[]>([]);
const appTotal = ref(0);
const logTotal = ref(0);
const faceLogTotal = ref(0);
const packageVisible = ref(false);
const itemVisible = ref(false);
const detailVisible = ref(false);
const detail = ref<CertificationApplication>();
const editingPackage = ref<string>();
const editingItem = ref<string>();
const appQuery = reactive({ page_no: 1, page_size: 20, keyword: "", status: "", level_code: "" });
const logQuery = reactive({ page_no: 1, page_size: 20, keyword: "" });
const faceLogQuery = reactive({ page_no: 1, page_size: 20, keyword: "" });
const packageForm = reactive<CertificationPackage>({ level_code: "basic", level_name: "", price: "0.00", item_codes: [], reward_coupon_count: 0, reward_coupon_valid_days: 7, benefit_desc: "", sort: 0, status: "0" });
const itemForm = reactive<CertificationItem>({ item_code: "", item_name: "", verify_mode: "manual", verifier_code: "", material_required: false, material_desc: "", validity_days: undefined, sort: 0, status: "0" });
const packageEnabled = computed({ get: () => packageForm.status === "0", set: (value: boolean) => (packageForm.status = value ? "0" : "1") });
const itemEnabled = computed({ get: () => itemForm.status === "0", set: (value: boolean) => (itemForm.status = value ? "0" : "1") });
const levelOptions = [{ label: "基础认证", value: "basic" }, { label: "高级认证", value: "advanced" }, { label: "尊享认证", value: "premium" }];
const appStatusOptions = [
  { label: "待支付", value: "pending_payment" },
  { label: "待提交", value: "paid_pending_submit" },
  { label: "进行中", value: "in_progress" },
  { label: "已通过", value: "approved" },
  { label: "已驳回", value: "rejected" },
  { label: "已过期", value: "expired" },
];
function itemLabel(code: string) { return items.value.find((item) => item.item_code === code)?.item_name || code; }
function modeLabel(value: string) { return value === "auto_api" ? "接口自动" : "人工审核"; }
function appStatusLabel(value: string) { return appStatusOptions.find((item) => item.value === value)?.label || value; }
function appStatusType(value: string) { if (value === "approved") return "success"; if (value === "rejected" || value === "expired") return "danger"; if (value === "pending_payment") return "info"; return "warning"; }
function recordStatusLabel(value: string) { return ({ not_submitted: "未提交", submitted: "已提交", verifying: "核验中", pending_review: "待审核", approved: "通过", rejected: "驳回", expired: "过期" } as Record<string, string>)[value] || value; }
function recordStatusType(value: string) { if (value === "approved") return "success"; if (value === "rejected" || value === "expired") return "danger"; if (value === "not_submitted") return "info"; return "warning"; }
function progressPercent(row: CertificationApplication) {
  const records = row.records || [];
  const total = row.item_codes?.length || records.length || 0;
  if (!total) return 0;
  return Math.round((records.filter((record) => record.record_status === "approved").length / total) * 100);
}
function jsonText(value?: Record<string, unknown>) { return value ? JSON.stringify(value) : "-"; }
async function loadConfig() {
  configLoading.value = true;
  try {
    const [itemRes, packageRes] = await Promise.all([CertificationAdminAPI.listItems(), CertificationAdminAPI.listPackages()]);
    items.value = itemRes.data.data || [];
    packages.value = packageRes.data.data || [];
  } finally { configLoading.value = false; }
}
async function loadApplications() {
  appLoading.value = true;
  try {
    const res = await CertificationAdminAPI.listApplications(appQuery);
    applications.value = res.data.data.items || [];
    appTotal.value = res.data.data.total || 0;
  } finally { appLoading.value = false; }
}
async function loadLogs() {
  logLoading.value = true;
  try {
    const res = await CertificationAdminAPI.listVerificationLogs(logQuery);
    verificationLogs.value = res.data.data.items || [];
    logTotal.value = res.data.data.total || 0;
  } finally { logLoading.value = false; }
}
async function loadFaceLogs() {
  faceLogLoading.value = true;
  try {
    const res = await CertificationAdminAPI.listFaceLogs(faceLogQuery);
    faceLogs.value = res.data.data.items || [];
    faceLogTotal.value = res.data.data.total || 0;
  } finally { faceLogLoading.value = false; }
}
function openPackage(row: CertificationPackage) { editingPackage.value = row.level_code; Object.assign(packageForm, { ...row, item_codes: [...row.item_codes] }); packageVisible.value = true; }
function openItem(row: CertificationItem) { editingItem.value = row.item_code; Object.assign(itemForm, row); itemVisible.value = true; }
async function savePackage() {
  if (!editingPackage.value) return;
  await CertificationAdminAPI.savePackage(editingPackage.value, packageForm);
  ElMessage.success("保存成功");
  packageVisible.value = false;
  await loadConfig();
}
async function saveItem() {
  if (!editingItem.value) return;
  await CertificationAdminAPI.saveItem(editingItem.value, itemForm);
  ElMessage.success("保存成功");
  itemVisible.value = false;
  await loadConfig();
}
async function openApplication(id: number) {
  const res = await CertificationAdminAPI.getApplication(id);
  detail.value = res.data.data;
  detailVisible.value = true;
}
async function viewIdCard(personId: number) {
  const res = await ElMessageBox.prompt("请输入查看原因", "查看完整身份证号", { inputType: "textarea", inputPattern: /.+/, inputErrorMessage: "必须填写查看原因" });
  const idRes = await CertificationAdminAPI.viewIdCard(personId, String(res.value || ""));
  await ElMessageBox.alert(idRes.data.data.id_card_no || "未保存身份证号", "完整身份证号");
}
onMounted(async () => { await loadConfig(); await Promise.all([loadApplications(), loadLogs(), loadFaceLogs()]); });
</script>

<style scoped>
.toolbar { display: flex; align-items: center; justify-content: space-between; }
.toolbar-title { font-size: 16px; font-weight: 600; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
.muted { margin-left: 8px; color: var(--el-text-color-secondary); font-size: 12px; }
.thumb { width: 48px; height: 48px; margin-right: 6px; border-radius: 6px; vertical-align: middle; }
.detail-progress { margin: 18px 0; }
</style>
