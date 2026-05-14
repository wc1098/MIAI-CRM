<template>
  <div class="app-container event-page">
    <el-card shadow="never" class="filter-card">
      <el-form :model="query" inline>
        <el-form-item label="关键词">
          <el-input v-model="query.keyword" clearable placeholder="标题/地点" @keyup.enter="fetchList" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.event_status" clearable placeholder="全部" style="width: 140px">
            <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="query.event_type" clearable placeholder="全部" style="width: 150px">
            <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="归属门店">
          <el-select v-model="query.store_id" clearable filterable placeholder="全部" style="width: 180px">
            <el-option v-for="item in deptOptions" :key="item.value" :label="item.label" :value="item.value" />
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
          <div class="toolbar-title">活动列表</div>
          <div class="toolbar-actions">
            <el-button v-hasPerm="['operation:event:create']" type="primary" icon="Plus" @click="openCreate">新增活动</el-button>
            <el-button v-hasPerm="['operation:event:delete']" icon="Delete" :disabled="!selectedIds.length" @click="deleteSelected">删除</el-button>
            <el-button icon="Refresh" @click="fetchList">刷新</el-button>
          </div>
        </div>
      </template>

      <el-table v-loading="loading" :data="rows" border stripe row-key="id" @selection-change="onSelection">
        <el-table-column type="selection" width="48" />
        <el-table-column prop="id" label="ID" width="76" />
        <el-table-column label="活动" min-width="230">
          <template #default="{ row }">
            <div class="event-title">{{ row.title }}</div>
            <div class="sub-text">{{ row.subtitle || row.location }}</div>
          </template>
        </el-table-column>
        <el-table-column label="归属门店" min-width="130">
          <template #default="{ row }">{{ row.store_name || row.store_id }}</template>
        </el-table-column>
        <el-table-column label="时间" min-width="180">
          <template #default="{ row }">
            <div>{{ row.start_time }}</div>
            <div class="sub-text">截止 {{ row.register_deadline }}</div>
          </template>
        </el-table-column>
        <el-table-column label="名额" width="130">
          <template #default="{ row }">男 {{ row.male_registered || 0 }}/{{ row.male_quota }} 女 {{ row.female_registered || 0 }}/{{ row.female_quota }}</template>
        </el-table-column>
        <el-table-column label="费用" width="130">
          <template #default="{ row }">男 {{ money(row.male_fee) }} / 女 {{ money(row.female_fee) }}</template>
        </el-table-column>
        <el-table-column label="签到" width="80">
          <template #default="{ row }">{{ row.checked_in_count || 0 }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.event_status)">{{ statusLabel(row.event_status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建人" min-width="110">
          <template #default="{ row }">{{ row.created_name || row.created_id || "-" }}</template>
        </el-table-column>
        <el-table-column fixed="right" label="操作" width="270">
          <template #default="{ row }">
            <el-button v-hasPerm="['operation:event:detail']" link type="primary" icon="View" @click="openDetail(row.id)">详情</el-button>
            <el-button v-hasPerm="['operation:event:update']" link type="primary" icon="Edit" @click="openEdit(row.id)">编辑</el-button>
            <el-button
              v-if="row.event_status !== 'finished'"
              v-hasPerm="['operation:event:publish']"
              link
              :type="publishActionType(row.event_status)"
              :icon="publishActionIcon(row.event_status)"
              @click="togglePublish(row)"
            >
              {{ publishActionLabel(row.event_status) }}
            </el-button>
            <el-button v-hasPerm="['operation:event:checkin']" link type="primary" icon="Tickets" @click="openRegistrations(row.id)">报名</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination
          v-model:current-page="query.page_no"
          v-model:page-size="query.page_size"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchList"
          @current-change="fetchList"
        />
      </div>
    </el-card>

    <el-drawer v-model="drawerVisible" size="72%" :title="drawerTitle" destroy-on-close>
      <el-tabs v-model="activeTab">
        <el-tab-pane label="活动资料" name="form">
          <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
            <el-row :gutter="16">
              <el-col :span="12"><el-form-item label="标题" prop="title"><el-input v-model="form.title" /></el-form-item></el-col>
              <el-col :span="12"><el-form-item label="副标题"><el-input v-model="form.subtitle" /></el-form-item></el-col>
              <el-col :span="8">
                <el-form-item label="活动类型" prop="event_type">
                  <el-select v-model="form.event_type" style="width: 100%">
                    <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="归属门店" prop="store_id">
                  <el-select v-model="form.store_id" filterable placeholder="选择门店" style="width: 100%">
                    <el-option v-for="item in deptOptions" :key="item.value" :label="item.label" :value="item.value" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8"><el-form-item label="地点" prop="location"><el-input v-model="form.location" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="开始时间" prop="start_time"><el-date-picker v-model="form.start_time" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width: 100%" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="结束时间" prop="end_time"><el-date-picker v-model="form.end_time" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width: 100%" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="报名截止" prop="register_deadline"><el-date-picker v-model="form.register_deadline" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width: 100%" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="男生名额" prop="male_quota"><el-input-number v-model="form.male_quota" :min="0" style="width: 100%" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="女生名额" prop="female_quota"><el-input-number v-model="form.female_quota" :min="0" style="width: 100%" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="男生费用"><el-input-number v-model="form.male_fee" :min="0" :precision="2" style="width: 100%" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="女生费用"><el-input-number v-model="form.female_fee" :min="0" :precision="2" style="width: 100%" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="最小年龄"><el-input-number v-model="form.min_age" :min="18" :max="100" style="width: 100%" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="最大年龄"><el-input-number v-model="form.max_age" :min="18" :max="100" style="width: 100%" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="VIP免费"><el-switch v-model="form.vip_free" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="实名要求"><el-switch v-model="form.require_realname" /></el-form-item></el-col>
              <el-col :span="24">
                <el-form-item label="封面图">
                  <el-upload class="cover-uploader" accept="image/*" :show-file-list="false" :http-request="uploadCover">
                    <el-image v-if="form.cover_url" :src="form.cover_url" fit="cover" class="cover-preview" />
                    <el-button v-else icon="Upload">上传封面</el-button>
                  </el-upload>
                </el-form-item>
              </el-col>
              <el-col :span="24">
                <el-form-item label="活动详情">
                  <WangEditor v-model="form.detail_html" height="320px" />
                </el-form-item>
              </el-col>
              <el-col :span="24">
                <el-form-item label="活动效果">
                  <WangEditor v-model="form.effect_html" height="260px" />
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
          <div class="drawer-actions">
            <el-button @click="drawerVisible = false">取消</el-button>
            <el-button v-hasPerm="['operation:event:create', 'operation:event:update']" type="primary" @click="submitForm">保存</el-button>
          </div>
        </el-tab-pane>

        <el-tab-pane v-if="detail" label="支付摘要" name="payment">
          <el-table :data="detail.payment_summary || []" border>
            <el-table-column label="订单状态">
              <template #default="{ row }">{{ orderStatusLabel(row.order_status as string) }}</template>
            </el-table-column>
            <el-table-column label="支付状态">
              <template #default="{ row }">{{ payStatusLabel(row.pay_status as string) }}</template>
            </el-table-column>
            <el-table-column prop="count" label="订单数" />
            <el-table-column label="实付金额">
              <template #default="{ row }">{{ money(row.paid_amount as number | string) }}</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-drawer>

    <el-drawer v-model="registrationVisible" size="70%" title="报名与签到管理" destroy-on-close>
      <el-tabs v-model="manageTab">
        <el-tab-pane label="报名用户" name="registrations">
          <el-table :data="registrations" border stripe>
            <el-table-column prop="registration_no" label="报名编号" min-width="150" />
            <el-table-column prop="name" label="姓名" width="100" />
            <el-table-column prop="mobile_masked" label="手机号" width="130" />
            <el-table-column label="性别" width="80"><template #default="{ row }">{{ genderLabel(row.gender) }}</template></el-table-column>
            <el-table-column label="报名状态" width="120"><template #default="{ row }">{{ registrationLabel(row.registration_status) }}</template></el-table-column>
            <el-table-column label="支付状态/实付" min-width="150">
              <template #default="{ row }">{{ payStatusLabel(row.pay_status) }} / {{ money(row.paid_amount) }}</template>
            </el-table-column>
            <el-table-column prop="registered_at" label="报名时间" min-width="170" />
            <el-table-column fixed="right" label="操作" width="120">
              <template #default="{ row }">
                <el-button v-hasPerm="['operation:event:checkin']" link type="primary" :disabled="row.registration_status === 'pending_payment'" @click="adminCheckin(row.id)">签到</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="签到记录" name="participants">
          <el-table :data="participants" border stripe>
            <el-table-column prop="onsite_no" label="现场编号" min-width="150" />
            <el-table-column prop="name" label="姓名" width="110" />
            <el-table-column prop="nickname" label="昵称" width="130" />
            <el-table-column label="性别" width="80"><template #default="{ row }">{{ genderLabel(row.gender) }}</template></el-table-column>
            <el-table-column label="签到类型" width="120">
              <template #default="{ row }">{{ checkinTypeLabel(row.checkin_type) }}</template>
            </el-table-column>
            <el-table-column prop="checked_in_at" label="签到时间" min-width="170" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessageBox, type FormInstance, type UploadRequestOptions } from "element-plus";

import EventAPI, { type EventForm, type EventParticipant, type EventRegistration, type EventTable } from "@/api/module_event/event";
import DeptAPI, { type DeptTable } from "@/api/module_system/dept";
import ParamsAPI from "@/api/module_system/params";

const statusOptions = [
  { label: "草稿", value: "draft" },
  { label: "已发布", value: "published" },
  { label: "已取消", value: "cancelled" },
  { label: "已结束", value: "finished" },
];
const typeOptions = [
  { label: "相亲会", value: "matchmaking" },
  { label: "主题沙龙", value: "salon" },
  { label: "户外活动", value: "outdoor" },
  { label: "节日活动", value: "festival" },
];

const loading = ref(false);
const rows = ref<EventTable[]>([]);
const total = ref(0);
const selectedIds = ref<number[]>([]);
const drawerVisible = ref(false);
const registrationVisible = ref(false);
const activeTab = ref("form");
const manageTab = ref("registrations");
const editingId = ref<number>();
const detail = ref<EventTable>();
const formRef = ref<FormInstance>();
const deptOptions = ref<Array<{ label: string; value: number }>>([]);
const registrations = ref<EventRegistration[]>([]);
const participants = ref<EventParticipant[]>([]);
const managingEventId = ref<number>();

const query = reactive({ page_no: 1, page_size: 10, keyword: "", event_status: "", event_type: "", store_id: undefined as number | undefined });
const defaultForm = (): EventForm => ({
  title: "",
  subtitle: "",
  event_type: "matchmaking",
  cover_url: "",
  location: "",
  start_time: "",
  end_time: "",
  register_deadline: "",
  detail_html: "",
  effect_html: "",
  male_quota: 10,
  female_quota: 10,
  male_fee: 0,
  female_fee: 0,
  vip_free: false,
  require_realname: true,
});
const form = reactive<EventForm>(defaultForm());
const rules = {
  title: [{ required: true, message: "请输入标题", trigger: "blur" }],
  event_type: [{ required: true, message: "请选择活动类型", trigger: "change" }],
  store_id: [{ required: true, message: "请选择归属门店", trigger: "change" }],
  location: [{ required: true, message: "请输入活动地点", trigger: "blur" }],
  start_time: [{ required: true, message: "请选择开始时间", trigger: "change" }],
  end_time: [{ required: true, message: "请选择结束时间", trigger: "change" }],
  register_deadline: [{ required: true, message: "请选择报名截止时间", trigger: "change" }],
};
const drawerTitle = computed(() => (editingId.value ? "编辑活动" : "新增活动"));

function statusLabel(value: string) {
  return statusOptions.find((item) => item.value === value)?.label || value;
}
function statusTag(value: string) {
  return ({ draft: "info", published: "success", cancelled: "warning", finished: "primary" } as const)[value as "draft" | "published" | "cancelled" | "finished"] || "info";
}
function publishActionLabel(value: string) {
  return value === "published" ? "取消发布" : "发布";
}
function publishActionType(value: string) {
  return value === "published" ? "warning" : "success";
}
function publishActionIcon(value: string) {
  return value === "published" ? "CircleClose" : "Promotion";
}
function genderLabel(value?: string) {
  return ({ "0": "男", "1": "女", "2": "未知" } as Record<string, string>)[value || ""] || "-";
}
function registrationLabel(value: string) {
  return ({ pending_payment: "待支付", registered: "已报名", checked_in: "已签到", timeout: "已超时", cancelled: "已取消" } as Record<string, string>)[value] || value;
}
function payStatusLabel(value?: string) {
  return ({ pending: "待支付", processing: "支付中", paid: "已支付", timeout: "支付超时", closed: "已关闭", failed: "支付失败", refunded: "已退款" } as Record<string, string>)[value || ""] || "-";
}
function orderStatusLabel(value?: string) {
  return ({ pending: "待处理", paid: "已完成", closed: "已关闭", cancelled: "已取消", failed: "失败" } as Record<string, string>)[value || ""] || "-";
}
function checkinTypeLabel(value?: string) {
  return ({ registered: "报名用户签到", walk_in: "现场临时签到" } as Record<string, string>)[value || ""] || "-";
}
function money(value?: number | string) {
  return `¥${Number(value || 0).toFixed(2)}`;
}
function flattenDept(list: DeptTable[], prefix = ""): Array<{ label: string; value: number }> {
  return list.flatMap((item) => {
    const label = `${prefix}${item.name}`;
    const current = typeof item.id === "number" ? [{ label, value: item.id }] : [];
    return [...current, ...flattenDept(item.children || [], `${label}/`)];
  });
}

async function loadDeptOptions() {
  const res = await DeptAPI.listDept();
  deptOptions.value = flattenDept(res.data.data || []);
}
async function fetchList() {
  loading.value = true;
  try {
    const res = await EventAPI.listEvent(query);
    rows.value = res.data.data.items || [];
    total.value = res.data.data.total || 0;
  } finally {
    loading.value = false;
  }
}
function resetQuery() {
  Object.assign(query, { page_no: 1, page_size: query.page_size, keyword: "", event_status: "", event_type: "", store_id: undefined });
  fetchList();
}
function resetForm() {
  Object.assign(form, defaultForm());
  editingId.value = undefined;
  detail.value = undefined;
  activeTab.value = "form";
}
async function openCreate() {
  resetForm();
  drawerVisible.value = true;
}
async function openDetail(id: number) {
  const res = await EventAPI.detailEvent(id);
  detail.value = res.data.data;
  Object.assign(form, detail.value);
  editingId.value = id;
  drawerVisible.value = true;
}
async function openEdit(id: number) {
  await openDetail(id);
}
async function submitForm() {
  await formRef.value?.validate();
  if (editingId.value) {
    await EventAPI.updateEvent(editingId.value, form);
  } else {
    await EventAPI.createEvent(form);
  }
  drawerVisible.value = false;
  fetchList();
}
function onSelection(selection: EventTable[]) {
  selectedIds.value = selection.map((item) => item.id);
}
async function togglePublish(row: EventTable) {
  if (row.event_status === "published") {
    await EventAPI.cancelEvent(row.id);
  } else {
    await EventAPI.publishEvent(row.id);
  }
  fetchList();
}
async function deleteSelected() {
  await ElMessageBox.confirm("确认删除选中的活动吗？", "删除确认", { type: "warning" });
  await EventAPI.deleteEvent(selectedIds.value);
  fetchList();
}
async function openRegistrations(id: number) {
  managingEventId.value = id;
  const [regRes, partRes] = await Promise.all([EventAPI.listRegistrations(id), EventAPI.listParticipants(id)]);
  registrations.value = regRes.data.data || [];
  participants.value = partRes.data.data || [];
  registrationVisible.value = true;
}
async function adminCheckin(registrationId: number) {
  await EventAPI.adminCheckin(registrationId);
  if (managingEventId.value) await openRegistrations(managingEventId.value);
}
async function uploadCover(options: UploadRequestOptions) {
  const body = new FormData();
  body.append("file", options.file);
  const res = await ParamsAPI.uploadFile(body);
  form.cover_url = res.data.data.file_url;
  options.onSuccess?.(res.data.data);
}

onMounted(() => {
  loadDeptOptions();
  fetchList();
});
</script>

<style scoped>
.event-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.toolbar,
.toolbar-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.toolbar-title,
.event-title {
  font-weight: 600;
}
.sub-text {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 20px;
}
.pager,
.drawer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 16px;
}
.cover-preview {
  width: 220px;
  height: 124px;
  border-radius: 6px;
}
</style>
