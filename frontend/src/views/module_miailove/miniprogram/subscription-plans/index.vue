<template>
  <div class="app-container">
    <el-card shadow="never">
      <template #header>
        <div class="toolbar">
          <div>
            <div class="toolbar-title">订阅方案</div>
            <div class="toolbar-subtitle">维护小程序月付、季付、年付订阅权益。</div>
          </div>
          <el-button type="primary" @click="openDialog()">新增方案</el-button>
        </div>
      </template>
      <el-table v-loading="loading" :data="items">
        <el-table-column prop="plan_name" label="方案名称" min-width="150" />
        <el-table-column prop="pay_period" label="周期" width="100">
          <template #default="{ row }">{{ periodMap[row.pay_period] || row.pay_period }}</template>
        </el-table-column>
        <el-table-column prop="period_days" label="权益天数" width="100" />
        <el-table-column prop="price" label="价格" width="120">
          <template #default="{ row }">¥{{ row.price }}</template>
        </el-table-column>
        <el-table-column prop="total_quota" label="总槽位" width="100" />
        <el-table-column prop="monthly_recommend_count" label="每月推荐" width="100" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }"><el-tag :type="row.status === '0' ? 'success' : 'info'">{{ row.status === "0" ? "启用" : "停用" }}</el-tag></template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }"><el-button link type="primary" @click="openDialog(row)">编辑</el-button></template>
        </el-table-column>
      </el-table>
    </el-card>
    <el-dialog v-model="dialogVisible" title="订阅方案" width="560px">
      <el-form :model="form" label-width="110px">
        <el-form-item label="方案编码"><el-input v-model="form.plan_code" /></el-form-item>
        <el-form-item label="方案名称"><el-input v-model="form.plan_name" /></el-form-item>
        <el-form-item label="支付周期">
          <el-select v-model="form.pay_period" style="width: 220px">
            <el-option label="月付" value="month" />
            <el-option label="季付" value="quarter" />
            <el-option label="年付" value="year" />
          </el-select>
        </el-form-item>
        <el-form-item label="权益天数"><el-input-number v-model="form.period_days" :min="1" /></el-form-item>
        <el-form-item label="价格"><el-input v-model="form.price" style="width: 220px"><template #prepend>¥</template></el-input></el-form-item>
        <el-form-item label="每月推荐"><el-input-number v-model="form.monthly_recommend_count" :min="1" /></el-form-item>
        <el-form-item label="总槽位"><el-input-number v-model="form.total_quota" :min="1" /></el-form-item>
        <el-form-item label="排序"><el-input-number v-model="form.sort" :min="0" /></el-form-item>
        <el-form-item label="状态"><el-switch v-model="enabled" /></el-form-item>
        <el-form-item label="权益说明"><el-input v-model="form.benefit_desc" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import MpSubscriptionAPI, { type SubscriptionPlan } from "@/api/module_mp/subscription";

const periodMap: Record<string, string> = { month: "月付", quarter: "季付", year: "年付" };
const loading = ref(false);
const saving = ref(false);
const dialogVisible = ref(false);
const items = ref<SubscriptionPlan[]>([]);
const editingId = ref<number>();
const form = reactive<SubscriptionPlan>({ plan_code: "", plan_name: "", pay_period: "month", period_days: 30, price: "0.00", monthly_recommend_count: 4, total_quota: 4, benefit_desc: "", sort: 0, status: "0" });
const enabled = computed({ get: () => form.status === "0", set: (value: boolean) => (form.status = value ? "0" : "1") });

async function load() {
  loading.value = true;
  try {
    const res = await MpSubscriptionAPI.listPlans();
    items.value = res.data.data || [];
  } finally {
    loading.value = false;
  }
}
function openDialog(row?: SubscriptionPlan) {
  editingId.value = row?.id;
  Object.assign(form, row || { plan_code: "", plan_name: "", pay_period: "month", period_days: 30, price: "0.00", monthly_recommend_count: 4, total_quota: 4, benefit_desc: "", sort: 0, status: "0" });
  dialogVisible.value = true;
}
async function save() {
  saving.value = true;
  try {
    await MpSubscriptionAPI.savePlan(form, editingId.value);
    ElMessage.success("保存成功");
    dialogVisible.value = false;
    await load();
  } finally {
    saving.value = false;
  }
}
onMounted(load);
</script>

<style scoped>
.toolbar { display: flex; align-items: center; justify-content: space-between; }
.toolbar-title { font-size: 16px; font-weight: 600; }
.toolbar-subtitle { margin-top: 4px; color: var(--el-text-color-secondary); font-size: 12px; }
</style>
