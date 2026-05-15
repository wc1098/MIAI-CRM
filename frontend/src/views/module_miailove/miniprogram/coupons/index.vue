<template>
  <div class="app-container">
    <el-card shadow="never" class="filter-card">
      <el-form :model="query" inline>
        <el-form-item label="关键词">
          <el-input v-model="query.keyword" clearable placeholder="编号/昵称/手机号/姓名" @keyup.enter="fetchList" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.coupon_status" clearable placeholder="全部" style="width: 140px">
            <el-option label="未使用" value="unused" />
            <el-option label="已使用" value="used" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" icon="Search" @click="fetchList">查询</el-button>
          <el-button icon="Refresh" @click="resetQuery">重置</el-button>
          <el-button type="success" icon="Plus" @click="grantVisible = true">发放</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <el-table v-loading="loading" :data="rows" border stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="display_no" label="用户编号" width="120" />
        <el-table-column prop="nickname" label="昵称" min-width="120" />
        <el-table-column prop="mobile" label="手机号" min-width="140" />
        <el-table-column prop="coupon_name" label="券名称" min-width="150" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.coupon_status === 'unused' ? 'success' : 'info'">{{ row.coupon_status === "unused" ? "未使用" : "已使用" }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="valid_to" label="有效期至" min-width="170" />
        <el-table-column prop="used_at" label="使用时间" min-width="170" />
        <el-table-column prop="grant_reason" label="发放原因" min-width="180" show-overflow-tooltip />
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

    <el-dialog v-model="grantVisible" title="发放免费券" width="420px">
      <el-form :model="grantForm" label-width="100px">
        <el-form-item label="用户ID">
          <el-input-number v-model="grantForm.user_id" :min="1" />
        </el-form-item>
        <el-form-item label="数量">
          <el-input-number v-model="grantForm.quantity" :min="1" :max="100" />
        </el-form-item>
        <el-form-item label="券名称">
          <el-input v-model="grantForm.coupon_name" placeholder="默认使用小程序设置" />
        </el-form-item>
        <el-form-item label="有效天数">
          <el-input-number v-model="grantForm.valid_days" :min="1" :max="3650" />
        </el-form-item>
        <el-form-item label="原因">
          <el-input v-model="grantForm.grant_reason" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="grantVisible = false">取消</el-button>
        <el-button type="primary" :loading="granting" @click="grantCoupon">发放</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";

import MpUserAPI, { type MpCouponGrantForm, type MpCouponPageQuery, type MpCouponRecord } from "@/api/module_mp/user";

const query = reactive<MpCouponPageQuery>({ page_no: 1, page_size: 20, keyword: "", coupon_status: "" });
const rows = ref<MpCouponRecord[]>([]);
const total = ref(0);
const loading = ref(false);
const grantVisible = ref(false);
const granting = ref(false);
const grantForm = reactive<MpCouponGrantForm>({ user_id: 1, quantity: 1, coupon_name: "", valid_days: 30, grant_reason: "" });

async function fetchList() {
  loading.value = true;
  try {
    const res = await MpUserAPI.listCoupons(query);
    rows.value = res.data.data.items || [];
    total.value = res.data.data.total || 0;
  } finally {
    loading.value = false;
  }
}

function resetQuery() {
  query.page_no = 1;
  query.keyword = "";
  query.coupon_status = "";
  fetchList();
}

async function grantCoupon() {
  granting.value = true;
  try {
    await MpUserAPI.grantCoupon(grantForm);
    ElMessage.success("发放成功");
    grantVisible.value = false;
    fetchList();
  } finally {
    granting.value = false;
  }
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
