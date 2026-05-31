<template>
  <div class="app-container mp-admin-page mp-actions-page">
    <el-card shadow="never" class="filter-card">
      <el-form :model="query" inline>
        <el-form-item label="关键词">
          <el-input v-model="query.keyword" clearable placeholder="编号/昵称/手机号/姓名" @keyup.enter="fetchList" />
        </el-form-item>
        <el-form-item label="行为">
          <el-select v-model="query.action_type" clearable placeholder="全部" style="width: 160px">
            <el-option v-for="item in actionOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" icon="Search" @click="fetchList">查询</el-button>
          <el-button icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="data-card">
      <template #header>
        <div class="toolbar">
          <div class="toolbar-title">用户行为</div>
          <el-button icon="Refresh" @click="fetchList">刷新</el-button>
        </div>
      </template>
      <el-table v-loading="loading" class="action-table" :data="rows" border stripe row-key="id" empty-text="暂无行为记录" height="100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column label="行为" min-width="120">
          <template #default="{ row }">{{ actionLabel(row.action_type) }}</template>
        </el-table-column>
        <el-table-column label="操作人" min-width="190">
          <template #default="{ row }">
            <div>{{ row.viewer_name || row.viewer_nickname || "-" }}</div>
            <div class="muted">
              {{ row.viewer_display_no || `用户ID ${row.viewer_user_id || "-"}` }}
              <span v-if="row.viewer_mobile"> / {{ row.viewer_mobile }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="目标用户" min-width="190">
          <template #default="{ row }">
            <div>{{ row.target_name || row.target_nickname || "-" }}</div>
            <div class="muted">
              {{ row.target_display_no || `用户ID ${row.target_user_id || "-"}` }}
              <span v-if="row.target_mobile"> / {{ row.target_mobile }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="occurred_at" label="时间" min-width="170" />
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
  </div>
</template>

<script setup lang="ts">
import { onActivated, onMounted, reactive, ref } from "vue";

import MpUserAPI, { type MpActionPageQuery, type MpActionRecord } from "@/api/module_mp/user";

const actionOptions = [
  { label: "浏览详情", value: "view" },
  { label: "喜欢", value: "like" },
  { label: "取消喜欢", value: "cancel_like" },
  { label: "收藏", value: "favorite" },
  { label: "取消收藏", value: "cancel_favorite" },
  { label: "查看手机号", value: "contact_view" },
  { label: "回答默契题", value: "question_answer" },
  { label: "任务：浏览资料", value: "task_view_profile" },
  { label: "任务：喜欢", value: "task_like_profile" },
  { label: "任务：收藏", value: "task_favorite_profile" },
  { label: "任务：分享名片", value: "task_share_card" },
  { label: "任务：阅读AI印象", value: "task_read_ai_profile" },
  { label: "尝试心动值解锁", value: "unlock_heartbeat_attempt" },
  { label: "尝试免费券解锁", value: "unlock_coupon_attempt" },
  { label: "尝试付费解锁", value: "unlock_pay_attempt" },
  { label: "解锁成功", value: "unlock_success" },
];

const query = reactive<MpActionPageQuery>({ page_no: 1, page_size: 20, keyword: "", action_type: "" });
const loading = ref(false);
const rows = ref<MpActionRecord[]>([]);
const total = ref(0);

function actionLabel(value?: string) {
  return actionOptions.find((item) => item.value === value)?.label || value || "-";
}

async function fetchList() {
  loading.value = true;
  try {
    const res = await MpUserAPI.listActions(query);
    const payload = res.data.data;
    rows.value = payload.items || [];
    total.value = payload.total || 0;
  } finally {
    loading.value = false;
  }
}

function resetQuery() {
  query.page_no = 1;
  query.keyword = "";
  query.action_type = "";
  fetchList();
}

onMounted(fetchList);
onActivated(fetchList);
</script>

<style scoped>
.mp-actions-page {
  overflow: hidden;
}

.data-card {
  flex: 1;
  min-height: 0;
}

.data-card :deep(.el-card__body) {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.action-table {
  flex: 1;
  min-height: 0;
}

.toolbar { display: flex; justify-content: space-between; align-items: center; }
.toolbar-title { font-size: 16px; font-weight: 600; }
.muted { margin-top: 2px; color: var(--el-text-color-secondary); font-size: 12px; }
</style>
