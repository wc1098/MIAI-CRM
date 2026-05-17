<template>
  <div class="app-container">
    <el-card shadow="never">
      <template #header><div class="toolbar"><div class="toolbar-title">认证审核任务</div><el-button @click="load">刷新</el-button></div></template>
      <el-form :inline="true" :model="query">
        <el-form-item label="关键词"><el-input v-model="query.keyword" clearable placeholder="编号/昵称/手机号/姓名" /></el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" clearable style="width: 140px">
            <el-option label="待审核" value="pending_review" />
            <el-option label="已通过" value="approved" />
            <el-option label="已驳回" value="rejected" />
          </el-select>
        </el-form-item>
        <el-form-item label="认证项">
          <el-select v-model="query.item_code" clearable filterable style="width: 150px">
            <el-option v-for="item in items" :key="item.item_code" :label="item.item_name" :value="item.item_code" />
          </el-select>
        </el-form-item>
        <el-form-item><el-button type="primary" @click="load">查询</el-button></el-form-item>
      </el-form>
      <el-table v-loading="loading" :data="rows" border>
        <el-table-column prop="display_no" label="编号" width="100" />
        <el-table-column prop="person_name" label="姓名" width="110" />
        <el-table-column prop="mobile" label="手机号" width="130" />
        <el-table-column prop="item_name" label="认证项" width="140" />
        <el-table-column prop="record_status" label="状态" width="110"><template #default="{ row }"><el-tag :type="statusType(row.record_status)">{{ statusLabel(row.record_status) }}</el-tag></template></el-table-column>
        <el-table-column label="材料" min-width="180">
          <template #default="{ row }">
            <el-image v-for="material in row.materials || []" :key="material.id" class="thumb" :src="ossImage(material.file_url, { w: 64, h: 64 })" :preview-src-list="ossImageList([material.file_url], { w: 1600 })" preview-teleported fit="cover" />
            <span v-if="!row.materials?.length">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="submitted_at" label="提交时间" min-width="170" />
        <el-table-column prop="reject_reason" label="驳回原因" min-width="160" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.record_status === 'pending_review'" link type="success" @click="review(row, 'approve')">通过</el-button>
            <el-button v-if="row.record_status === 'pending_review'" link type="danger" @click="review(row, 'reject')">驳回</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pager"><el-pagination v-model:current-page="query.page_no" v-model:page-size="query.page_size" :total="total" layout="total, sizes, prev, pager, next" @size-change="load" @current-change="load" /></div>
    </el-card>
  </div>
</template>
<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import CertificationAdminAPI, { type CertificationItem, type CertificationRecord } from "@/api/module_certification/admin";
import { ossImage, ossImageList } from "@/utils/ossImage";
const loading = ref(false);
const total = ref(0);
const rows = ref<CertificationRecord[]>([]);
const items = ref<CertificationItem[]>([]);
const query = reactive({ page_no: 1, page_size: 20, keyword: "", status: "pending_review", item_code: "" });
function statusLabel(value: string) { return ({ pending_review: "待审核", approved: "已通过", rejected: "已驳回", not_submitted: "未提交" } as Record<string, string>)[value] || value; }
function statusType(value: string) { if (value === "approved") return "success"; if (value === "rejected") return "danger"; return "warning"; }
async function load() {
  loading.value = true;
  try {
    const res = await CertificationAdminAPI.listRecords(query);
    rows.value = res.data.data.items || [];
    total.value = res.data.data.total || 0;
  } finally { loading.value = false; }
}
async function loadItems() {
  const res = await CertificationAdminAPI.listItems();
  items.value = (res.data.data || []).filter((item) => item.verify_mode === "manual");
}
async function review(row: CertificationRecord, action: "approve" | "reject") {
  let reason = "";
  if (action === "reject") {
    const res = await ElMessageBox.prompt("请输入驳回原因", "驳回认证", { inputType: "textarea", inputPattern: /.+/, inputErrorMessage: "必须填写驳回原因" });
    reason = String(res.value || "");
  } else {
    await ElMessageBox.confirm("确认通过该认证项？", "认证审核");
  }
  await CertificationAdminAPI.reviewRecord(row.id, { action, reject_reason: reason });
  ElMessage.success("处理成功");
  await load();
}
onMounted(async () => { await loadItems(); await load(); });
</script>
<style scoped>
.toolbar{display:flex;justify-content:space-between;align-items:center}.toolbar-title{font-size:16px;font-weight:600}.pager{margin-top:16px;display:flex;justify-content:flex-end}.thumb{width:48px;height:48px;margin-right:6px;border-radius:6px;vertical-align:middle}
</style>
