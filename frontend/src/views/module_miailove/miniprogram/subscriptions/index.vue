<template>
  <div class="app-container">
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
      <el-table v-loading="loading" :data="items">
        <el-table-column prop="display_no" label="用户编号" width="110" />
        <el-table-column prop="nickname" label="昵称" min-width="120" />
        <el-table-column prop="mobile" label="手机号" min-width="130" />
        <el-table-column prop="plan_name" label="套餐" min-width="150" />
        <el-table-column prop="used_quota" label="已开放/总槽位" width="130"><template #default="{ row }">{{ row.used_quota }}/{{ row.total_quota }}</template></el-table-column>
        <el-table-column prop="started_at" label="开始时间" min-width="170" />
        <el-table-column prop="expired_at" label="过期时间" min-width="170" />
        <el-table-column prop="status" label="状态" width="90" />
      </el-table>
      <pagination v-if="total > 0" v-model:total="total" v-model:page="query.page_no" v-model:limit="query.page_size" @pagination="load" />
    </el-card>
  </div>
</template>
<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import MpSubscriptionAPI, { type UserSubscriptionRecord } from "@/api/module_mp/subscription";
const loading = ref(false);
const total = ref(0);
const items = ref<UserSubscriptionRecord[]>([]);
const query = reactive({ page_no: 1, page_size: 20, keyword: "", status: "" });
async function load() {
  loading.value = true;
  try {
    const res = await MpSubscriptionAPI.listSubscriptions(query);
    items.value = res.data.data.items || [];
    total.value = res.data.data.total || 0;
  } finally { loading.value = false; }
}
onMounted(load);
</script>
<style scoped>.toolbar{display:flex;justify-content:space-between;align-items:center}.toolbar-title{font-size:16px;font-weight:600}</style>
