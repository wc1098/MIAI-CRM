<template>
  <div class="app-container">
    <el-card shadow="never">
      <template #header><div class="toolbar"><div class="toolbar-title">订阅推荐记录</div><el-button @click="load">刷新</el-button></div></template>
      <el-form :inline="true" :model="query">
        <el-form-item label="关键词"><el-input v-model="query.keyword" clearable placeholder="编号/昵称" /></el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" clearable style="width: 150px">
            <el-option label="未到期" value="locked" />
            <el-option label="匹配中" value="matching" />
            <el-option label="持续寻找" value="waiting_candidate" />
            <el-option label="已开放" value="unlocked" />
            <el-option label="已查看" value="viewed" />
          </el-select>
        </el-form-item>
        <el-form-item><el-button type="primary" @click="load">查询</el-button></el-form-item>
      </el-form>
      <el-table v-loading="loading" :data="items">
        <el-table-column prop="viewer_display_no" label="订阅人" width="110" />
        <el-table-column prop="viewer_nickname" label="订阅人昵称" min-width="120" />
        <el-table-column prop="target_display_no" label="推荐对象" width="110" />
        <el-table-column prop="target_nickname" label="对象昵称" min-width="120" />
        <el-table-column prop="recommend_index" label="序号" width="70" />
        <el-table-column prop="unlock_at" label="开放时间" min-width="170" />
        <el-table-column prop="status" label="状态" width="110" />
        <el-table-column prop="match_score" label="匹配度" width="90" />
        <el-table-column label="AI状态" width="110">
          <template #default="{ row }">{{ reasonStatusText(row.reason_generation_status) }}</template>
        </el-table-column>
        <el-table-column prop="match_reason" label="展示理由" min-width="280" show-overflow-tooltip />
        <el-table-column prop="match_reason_rule" label="规则理由" min-width="240" show-overflow-tooltip />
        <el-table-column prop="match_reason_ai" label="AI润色理由" min-width="260" show-overflow-tooltip />
        <el-table-column prop="reason_last_error" label="AI错误" min-width="180" show-overflow-tooltip />
        <el-table-column label="操作" width="110" fixed="right">
          <template #default="{ row }"><el-button link type="primary" @click="rematch(row.id)">重新匹配</el-button></template>
        </el-table-column>
      </el-table>
      <pagination v-if="total > 0" v-model:total="total" v-model:page="query.page_no" v-model:limit="query.page_size" @pagination="load" />
    </el-card>
  </div>
</template>
<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import MpSubscriptionAPI, { type SubscriptionRecommendationRecord } from "@/api/module_mp/subscription";
const loading = ref(false);
const total = ref(0);
const items = ref<SubscriptionRecommendationRecord[]>([]);
const query = reactive({ page_no: 1, page_size: 20, keyword: "", status: "" });
async function load() {
  loading.value = true;
  try {
    const res = await MpSubscriptionAPI.listRecommendations(query);
    items.value = res.data.data.items || [];
    total.value = res.data.data.total || 0;
  } finally { loading.value = false; }
}
async function rematch(id: number) {
  await MpSubscriptionAPI.rematchRecommendation(id);
  ElMessage.success("已触发匹配");
  await load();
}
function reasonStatusText(status?: string) {
  const map: Record<string, string> = { none: "未生成", pending: "等待中", processing: "生成中", success: "已生成", failed: "失败", cancelled: "已取消" };
  return map[status || "none"] || status || "未生成";
}
onMounted(load);
</script>
<style scoped>.toolbar{display:flex;justify-content:space-between;align-items:center}.toolbar-title{font-size:16px;font-weight:600}</style>
