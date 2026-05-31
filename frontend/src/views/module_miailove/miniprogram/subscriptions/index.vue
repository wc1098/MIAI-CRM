<template>
  <div class="app-container mp-admin-page">
    <el-card shadow="never">
      <template #header><div class="toolbar"><div class="toolbar-title">用户订阅</div><el-button @click="load">刷新</el-button></div></template>
      <el-form :inline="true" :model="query">
        <el-form-item label="关键词"><el-input v-model="query.keyword" clearable placeholder="编号/昵称/手机号" /></el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" clearable style="width: 140px">
            <el-option label="生效中" value="active" />
            <el-option label="已过期" value="expired" />
            <el-option label="作废" value="void" />
          </el-select>
        </el-form-item>
        <el-form-item><el-button type="primary" @click="load">查询</el-button></el-form-item>
      </el-form>
      <el-table
        :key="tableKey"
        ref="tableRef"
        v-loading="loading"
        :data="items"
        row-key="id"
        empty-text="暂无订阅数据"
        style="width: 100%; min-height: 120px"
      >
        <el-table-column prop="display_no" label="用户编号" width="110" />
        <el-table-column prop="nickname" label="昵称" min-width="120" />
        <el-table-column prop="mobile" label="手机号" min-width="130" />
        <el-table-column prop="plan_name" label="套餐" min-width="150" />
        <el-table-column prop="used_quota" label="已开放/总槽位" width="130"><template #default="{ row }">{{ row.used_quota }}/{{ row.total_quota }}</template></el-table-column>
        <el-table-column prop="started_at" label="开始时间" min-width="170" />
        <el-table-column prop="expired_at" label="过期时间" min-width="170" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)">{{ statusText(row.status) }}</el-tag>
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
          @size-change="load"
          @current-change="load"
        />
      </div>
    </el-card>
  </div>
</template>
<script setup lang="ts">
import { nextTick, onActivated, onMounted, reactive, ref } from "vue";
import MpSubscriptionAPI, { type UserSubscriptionRecord } from "@/api/module_mp/subscription";
const loading = ref(false);
const total = ref(0);
const items = ref<UserSubscriptionRecord[]>([]);
const tableKey = ref(0);
const tableRef = ref();
const query = reactive({ page_no: 1, page_size: 20, keyword: "", status: "" });

function pagePayload(res: any) {
  return res?.data?.data ?? res?.data ?? {};
}

async function load() {
  loading.value = true;
  try {
    const res = await MpSubscriptionAPI.listSubscriptions(query);
    const payload = pagePayload(res);
    items.value = Array.isArray(payload.items) ? payload.items : [];
    total.value = Number(payload.total || 0);
    tableKey.value += 1;
    await nextTick();
    tableRef.value?.doLayout?.();
  } finally { loading.value = false; }
}
function statusText(status?: string) {
  const map: Record<string, string> = { active: "生效中", expired: "已过期", void: "作废" };
  return map[status || ""] || status || "-";
}
function statusTagType(status?: string) {
  const map: Record<string, "success" | "info" | "warning" | "danger"> = { active: "success", expired: "info", void: "danger" };
  return map[status || ""] || "info";
}
onMounted(load);
onActivated(load);
</script>
<style scoped>.toolbar{display:flex;justify-content:space-between;align-items:center}.toolbar-title{font-size:16px;font-weight:600}</style>
