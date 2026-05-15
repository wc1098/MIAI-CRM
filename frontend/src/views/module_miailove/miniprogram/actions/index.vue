<template>
  <div class="app-container">
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

    <el-card shadow="never">
      <el-table v-loading="loading" :data="rows" border stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column label="行为" min-width="120">
          <template #default="{ row }">{{ actionLabel(row.action_type) }}</template>
        </el-table-column>
        <el-table-column prop="viewer_user_id" label="操作用户ID" width="120" />
        <el-table-column prop="target_user_id" label="目标用户ID" width="120" />
        <el-table-column prop="target_display_no" label="目标编号" width="120" />
        <el-table-column prop="target_nickname" label="目标昵称" min-width="120" />
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
import { onMounted, reactive, ref } from "vue";

import MpUserAPI, { type MpActionPageQuery, type MpActionRecord } from "@/api/module_mp/user";

const actionOptions = [
  { label: "浏览详情", value: "view" },
  { label: "喜欢", value: "like" },
  { label: "取消喜欢", value: "cancel_like" },
  { label: "收藏", value: "favorite" },
  { label: "取消收藏", value: "cancel_favorite" },
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
    rows.value = res.data.data.items || [];
    total.value = res.data.data.total || 0;
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
</script>

<style scoped>
.filter-card {
  margin-bottom: 12px;
}
.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
