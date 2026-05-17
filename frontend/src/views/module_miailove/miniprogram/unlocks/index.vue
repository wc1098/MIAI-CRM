<template>
  <div class="app-container">
    <el-card shadow="never">
      <template #header>
        <div class="toolbar">
          <div>
            <div class="toolbar-title">联系方式解锁记录</div>
            <div class="toolbar-subtitle">一条记录代表一次解锁授权；手机号查看日志作为明细归在对应解锁记录下。</div>
          </div>
          <el-button @click="load">刷新</el-button>
        </div>
      </template>

      <div class="search-bar">
        <el-input v-model="query.keyword" clearable placeholder="解锁人/目标的编号/昵称/手机号/姓名" style="width: 300px" @keyup.enter="load" />
        <el-select v-model="query.unlock_status" clearable placeholder="状态" style="width: 140px">
          <el-option label="成功" value="success" />
          <el-option label="待处理" value="pending" />
          <el-option label="已撤销" value="revoked" />
          <el-option label="已屏蔽" value="blocked" />
        </el-select>
        <el-button type="primary" @click="load">查询</el-button>
      </div>

      <el-table :data="rows" border>
        <el-table-column label="解锁人" min-width="190">
          <template #default="{ row }">
            <div>{{ row.viewer_name || row.viewer_nickname || "-" }}</div>
            <div class="muted">
              {{ row.viewer_display_no || `用户ID ${row.viewer_user_id}` }}
              <span v-if="row.viewer_mobile"> / {{ row.viewer_mobile }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="被解锁目标" min-width="170">
          <template #default="{ row }">
            <div>{{ row.target_name || row.target_nickname || "-" }}</div>
            <div class="muted">{{ row.target_display_no || `用户ID ${row.target_user_id}` }}</div>
          </template>
        </el-table-column>
        <el-table-column label="解锁方式" width="120">
          <template #default="{ row }">{{ sourceLabel(row.unlock_source) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusType(row.unlock_status)">{{ statusLabel(row.unlock_status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="金额" width="90" />
        <el-table-column label="手机号查看" min-width="180">
          <template #default="{ row }">
            <el-button v-if="row.view_count" link type="primary" @click="openViews(row)">{{ row.view_count }} 次</el-button>
            <span v-else>0 次</span>
            <span v-if="row.last_viewed_at" class="muted">最近 {{ row.last_viewed_at }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="unlocked_at" label="解锁时间" min-width="170" />
        <el-table-column label="处理原因" min-width="160">
          <template #default="{ row }">{{ row.revoke_reason || "-" }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.unlock_status === 'success'" link type="danger" @click="revoke(row, 'revoked')">撤销</el-button>
            <el-button v-if="row.unlock_status === 'success'" link type="warning" @click="revoke(row, 'blocked')">屏蔽</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="viewVisible" title="手机号查看明细" width="640px">
      <el-table :data="viewRows" border>
        <el-table-column prop="target_display_no" label="目标编号" width="120" />
        <el-table-column prop="target_nickname" label="目标昵称" min-width="120" />
        <el-table-column prop="viewer_user_id" label="查看用户ID" width="110" />
        <el-table-column prop="viewed_at" label="查看时间" min-width="170" />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import MpUserAPI, { type MpContactViewRecord, type MpUnlockRecord, type MpUnlockRecordQuery } from "@/api/module_mp/user";

const query = reactive<MpUnlockRecordQuery>({ page_no: 1, page_size: 20, keyword: "", unlock_status: "" });
const rows = ref<MpUnlockRecord[]>([]);
const viewRows = ref<MpContactViewRecord[]>([]);
const viewVisible = ref(false);

async function load() {
  const unlockRes = await MpUserAPI.listUnlockRecords(query);
  rows.value = unlockRes.data.data.items || [];
}

async function openViews(row: MpUnlockRecord) {
  const res = await MpUserAPI.listContactViews({ page_no: 1, page_size: 50, keyword: row.target_display_no || "" });
  viewRows.value = (res.data.data.items || []).filter((item: MpContactViewRecord) => item.unlock_id === row.id);
  viewVisible.value = true;
}

function sourceLabel(value?: string) {
  const map: Record<string, string> = {
    task_free: "任务免费",
    free_coupon: "免费券",
    paid_boost: "付费补足",
    subscription: "订阅权益",
    admin_grant: "后台发放",
  };
  return map[value || ""] || value || "-";
}

function statusLabel(value?: string) {
  const map: Record<string, string> = { success: "成功", pending: "待处理", revoked: "已撤销", blocked: "已屏蔽" };
  return map[value || ""] || value || "-";
}

function statusType(value?: string) {
  if (value === "success") return "success";
  if (value === "blocked") return "danger";
  if (value === "revoked") return "warning";
  return "info";
}

async function revoke(row: MpUnlockRecord, status: "revoked" | "blocked") {
  const { value } = await ElMessageBox.prompt("请输入处理原因", status === "revoked" ? "撤销解锁" : "屏蔽解锁", { inputType: "textarea" });
  await MpUserAPI.revokeUnlockRecord(row.id, { status, reason: value });
  ElMessage.success("处理成功");
  load();
}

onMounted(load);
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; gap: 16px; }
.toolbar-title { font-size: 16px; font-weight: 600; }
.toolbar-subtitle { margin-top: 4px; color: var(--el-text-color-secondary); font-size: 12px; }
.search-bar { display: flex; gap: 10px; margin-bottom: 14px; }
.muted { display: block; margin-top: 2px; color: var(--el-text-color-secondary); font-size: 12px; }
</style>
