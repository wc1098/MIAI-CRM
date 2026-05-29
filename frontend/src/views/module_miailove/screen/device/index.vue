<template>
  <div class="app-container screen-device-page">
    <el-card shadow="never" class="filter-card">
      <el-form :model="query" inline>
        <el-form-item label="关键词">
          <el-input v-model="query.keyword" clearable placeholder="设备码/设备名称" @keyup.enter="fetchList" />
        </el-form-item>
        <el-form-item label="绑定状态">
          <el-select v-model="query.bind_status" clearable placeholder="全部" style="width: 140px">
            <el-option label="未绑定" value="unbound" />
            <el-option label="已绑定" value="bound" />
          </el-select>
        </el-form-item>
        <el-form-item label="在线状态">
          <el-select v-model="query.online_status" clearable placeholder="全部" style="width: 140px">
            <el-option label="在线" value="online" />
            <el-option label="离线" value="offline" />
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
            <div class="toolbar-title">大屏设备管理</div>
            <div class="toolbar-note">Web 大屏和安卓 TV 均通过设备码绑定，不使用后台账号登录。</div>
          </div>
          <el-button v-hasPerm="['screen:device:bind']" type="primary" icon="Connection" @click="openBind">绑定设备</el-button>
        </div>
      </template>

      <el-table v-loading="loading" :data="rows" border stripe row-key="id">
        <el-table-column prop="device_code" label="设备码" width="130" />
        <el-table-column prop="device_name" label="设备名称" min-width="150" show-overflow-tooltip />
        <el-table-column label="设备类型" width="120">
          <template #default="{ row }">{{ deviceTypeLabel(row.device_type) }}</template>
        </el-table-column>
        <el-table-column label="绑定状态" width="110">
          <template #default="{ row }"><el-tag :type="bindStatusType(row.bind_status)">{{ bindStatusLabel(row.bind_status) }}</el-tag></template>
        </el-table-column>
        <el-table-column label="在线状态" width="110">
          <template #default="{ row }"><el-tag :type="row.online_status === 'online' ? 'success' : 'info'">{{ onlineStatusLabel(row.online_status) }}</el-tag></template>
        </el-table-column>
        <el-table-column label="门店" min-width="140">
          <template #default="{ row }">{{ deptName(row.store_id) }}</template>
        </el-table-column>
        <el-table-column prop="bound_at" label="绑定时间" min-width="170" />
        <el-table-column prop="last_online_at" label="最近在线" min-width="170" />
        <el-table-column fixed="right" label="操作" width="230">
          <template #default="{ row }">
            <el-button v-hasPerm="['screen:device:unbind']" link type="primary" :disabled="row.bind_status !== 'bound'" @click="unbind(row)">解绑</el-button>
            <el-button v-hasPerm="['screen:device:update']" link type="warning" :disabled="row.bind_status !== 'bound'" @click="resetToken(row)">重置授权</el-button>
            <el-button v-hasPerm="['screen:device:delete']" link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination v-model:current-page="query.page_no" v-model:page-size="query.page_size" :total="total" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next, jumper" @size-change="fetchList" @current-change="fetchList" />
      </div>
    </el-card>

    <el-dialog v-model="bindVisible" title="绑定大屏设备" width="520px" destroy-on-close>
      <el-form :model="bindForm" label-width="92px">
        <el-form-item label="设备码"><el-input v-model="bindForm.device_code" placeholder="输入大屏页面显示的设备码" /></el-form-item>
        <el-form-item label="设备名称"><el-input v-model="bindForm.device_name" placeholder="如：大厅用户墙 Web 大屏" /></el-form-item>
        <el-form-item label="门店">
          <el-select v-model="bindForm.store_id" clearable filterable placeholder="可选，仅用于资产管理" style="width: 100%">
            <el-option v-for="item in deptOptions" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="bindVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitBind">绑定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import ScreenAPI, { type ScreenDevice, type ScreenDeviceBindForm, type ScreenDeviceQuery } from "@/api/module_screen/screen";
import DeptAPI, { type DeptTable } from "@/api/module_system/dept";

const query = reactive<ScreenDeviceQuery>({ page_no: 1, page_size: 10 });
const rows = ref<ScreenDevice[]>([]);
const total = ref(0);
const loading = ref(false);
const saving = ref(false);
const bindVisible = ref(false);
const deptOptions = ref<Array<{ id: number; name?: string }>>([]);
const bindForm = reactive<ScreenDeviceBindForm>({ device_code: "", device_name: "", store_id: undefined });

async function fetchList() {
  loading.value = true;
  try {
    const res = await ScreenAPI.listDevices(query);
    rows.value = res.data.data.items || [];
    total.value = res.data.data.total || 0;
  } finally {
    loading.value = false;
  }
}

function resetQuery() {
  Object.assign(query, { page_no: 1, page_size: 10, keyword: undefined, bind_status: undefined, online_status: undefined });
  fetchList();
}

function openBind() {
  Object.assign(bindForm, { device_code: "", device_name: "", store_id: undefined });
  bindVisible.value = true;
}

async function submitBind() {
  if (!bindForm.device_code.trim()) {
    ElMessage.warning("请输入设备码");
    return;
  }
  saving.value = true;
  try {
    await ScreenAPI.bindDevice({ ...bindForm, device_code: bindForm.device_code.trim().toUpperCase() });
    bindVisible.value = false;
    await fetchList();
  } finally {
    saving.value = false;
  }
}

async function unbind(row: ScreenDevice) {
  await ElMessageBox.confirm(`确认解绑设备 ${row.device_code}？解绑后播放端需要重新绑定。`, "解绑设备");
  await ScreenAPI.unbindDevice(row.id);
  await fetchList();
}

async function resetToken(row: ScreenDevice) {
  await ElMessageBox.confirm(`确认重置设备 ${row.device_code} 的授权？当前播放端会失效。`, "重置授权");
  await ScreenAPI.resetDeviceToken(row.id);
  await fetchList();
}

async function remove(row: ScreenDevice) {
  await ElMessageBox.confirm(`确认删除设备 ${row.device_code}？删除后播放端需要重新生成设备码绑定。`, "删除设备", { type: "warning" });
  await ScreenAPI.deleteDevice(row.id);
  await fetchList();
}

async function loadDeptOptions() {
  const res = await DeptAPI.listDept({ status: "0" });
  const result: Array<{ id: number; name?: string }> = [];
  const walk = (items: DeptTable[]) => {
    items.forEach((item) => {
      if (typeof item.id === "number") result.push({ id: item.id, name: item.name });
      if (item.children?.length) walk(item.children);
    });
  };
  walk(res.data.data || []);
  deptOptions.value = result;
}

function deptName(id?: number) {
  if (!id) return "-";
  return deptOptions.value.find((item) => item.id === id)?.name || `ID ${id}`;
}

function bindStatusLabel(value: string) {
  return ({ unbound: "未绑定", bound: "已绑定" } as Record<string, string>)[value] || value;
}

function bindStatusType(value: string) {
  return ({ bound: "success", unbound: "info" } as Record<string, any>)[value] || "info";
}

function onlineStatusLabel(value: string) {
  return ({ online: "在线", offline: "离线" } as Record<string, string>)[value] || value;
}

function deviceTypeLabel(value: string) {
  return ({ web: "Web 大屏", android_tv: "安卓 TV" } as Record<string, string>)[value] || value;
}

onMounted(async () => {
  await loadDeptOptions();
  await fetchList();
});
</script>

<style scoped>
.screen-device-page { display: flex; flex-direction: column; gap: 12px; }
.toolbar { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.toolbar-title { font-size: 18px; font-weight: 600; }
.toolbar-note { margin-top: 4px; color: var(--el-text-color-secondary); font-size: 13px; }
.pager { display: flex; justify-content: flex-end; padding-top: 16px; }
</style>
