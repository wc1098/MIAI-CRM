<template>
  <div class="app-container mp-user-page">
    <el-card shadow="never" class="filter-card">
      <el-form :model="query" inline>
        <el-form-item label="关键词">
          <el-input v-model="query.keyword" clearable placeholder="昵称/手机号/姓名/微信号" @keyup.enter="fetchList" />
        </el-form-item>
        <el-form-item label="注册状态">
          <el-select v-model="query.is_registered" clearable placeholder="全部" style="width: 150px">
            <el-option label="已注册" :value="true" />
            <el-option label="未完成" :value="false" />
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
          <div class="toolbar-title">小程序注册用户</div>
          <el-button icon="Refresh" @click="fetchList">刷新</el-button>
        </div>
      </template>

      <el-table v-loading="loading" :data="rows" border stripe row-key="id">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column label="微信资料" min-width="220">
          <template #default="{ row }">
            <div class="wx-profile">
              <el-avatar :size="38" :src="row.avatar_url">
                {{ row.nickname?.slice(0, 1) || "微" }}
              </el-avatar>
              <div>
                <div class="nickname">{{ row.nickname || "-" }}</div>
                <div class="sub-text">{{ row.mobile || "-" }}</div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="姓名" min-width="110">
          <template #default="{ row }">{{ row.person?.name || "-" }}</template>
        </el-table-column>
        <el-table-column label="性别" width="90">
          <template #default="{ row }">{{ genderLabel(row.person?.gender) }}</template>
        </el-table-column>
        <el-table-column label="微信号" min-width="130">
          <template #default="{ row }">{{ row.person?.wechat || "-" }}</template>
        </el-table-column>
        <el-table-column label="线索ID" width="100">
          <template #default="{ row }">{{ row.lead_id || "-" }}</template>
        </el-table-column>
        <el-table-column label="来源事件" width="100">
          <template #default="{ row }">{{ eventCountLabel(row.source_event_count) }}</template>
        </el-table-column>
        <el-table-column label="注册状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.is_registered ? 'success' : 'info'">
              {{ row.is_registered ? "已注册" : "未完成" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="registered_at" label="注册时间" min-width="170" />
        <el-table-column prop="last_login_at" label="最近登录" min-width="170" />
        <el-table-column fixed="right" label="操作" width="110">
          <template #default="{ row }">
            <el-button v-hasPerm="['operation:miniprogram:detail']" link type="primary" icon="View" @click="openDetail(row.id)">详情</el-button>
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
          @size-change="fetchList"
          @current-change="fetchList"
        />
      </div>
    </el-card>

    <el-drawer v-model="detailVisible" size="64%" title="小程序注册用户详情" destroy-on-close>
      <template v-if="detail">
        <el-descriptions title="微信资料" :column="2" border>
          <el-descriptions-item label="头像">
            <el-avatar :size="46" :src="detail.avatar_url">{{ detail.nickname?.slice(0, 1) || "微" }}</el-avatar>
          </el-descriptions-item>
          <el-descriptions-item label="昵称">{{ detail.nickname || "-" }}</el-descriptions-item>
          <el-descriptions-item label="微信手机号">{{ detail.mobile || "-" }}</el-descriptions-item>
          <el-descriptions-item label="openid">{{ detail.openid || "-" }}</el-descriptions-item>
          <el-descriptions-item label="注册时间">{{ detail.registered_at || "-" }}</el-descriptions-item>
          <el-descriptions-item label="最近登录">{{ detail.last_login_at || "-" }}</el-descriptions-item>
          <el-descriptions-item label="当前线索ID">{{ detail.lead_id || "-" }}</el-descriptions-item>
          <el-descriptions-item label="来源事件数">{{ eventCountLabel(detail.source_event_count) }}</el-descriptions-item>
        </el-descriptions>

        <el-descriptions class="detail-section" title="CRM资料" :column="2" border>
          <el-descriptions-item label="姓名">{{ detail.person?.name || "-" }}</el-descriptions-item>
          <el-descriptions-item label="性别">{{ genderLabel(detail.person?.gender) }}</el-descriptions-item>
          <el-descriptions-item label="手机号">{{ detail.person?.primary_mobile || "-" }}</el-descriptions-item>
          <el-descriptions-item label="微信号">{{ detail.person?.wechat || "-" }}</el-descriptions-item>
          <el-descriptions-item label="出生日期">{{ detail.person?.birth_date || "-" }}</el-descriptions-item>
          <el-descriptions-item label="身高">{{ detail.person?.height_cm ? `${detail.person.height_cm} cm` : "-" }}</el-descriptions-item>
          <el-descriptions-item label="民族">{{ dictLabel("ethnicity", detail.person?.ethnicity) }}</el-descriptions-item>
          <el-descriptions-item label="职业">{{ detail.person?.occupation || "-" }}</el-descriptions-item>
          <el-descriptions-item label="年收入">{{ dictLabel("annualIncome", detail.person?.annual_income) }}</el-descriptions-item>
          <el-descriptions-item label="婚况">{{ dictLabel("maritalStatus", detail.person?.marital_status) }}</el-descriptions-item>
          <el-descriptions-item label="学历">{{ dictLabel("education", detail.person?.education) }}</el-descriptions-item>
          <el-descriptions-item label="籍贯">{{ detail.person?.hometown || "-" }}</el-descriptions-item>
          <el-descriptions-item label="常驻地">{{ detail.person?.residence || "-" }}</el-descriptions-item>
          <el-descriptions-item label="房产信息">{{ dictLabel("houseStatus", detail.person?.house_status) }}</el-descriptions-item>
          <el-descriptions-item label="购车信息">{{ dictLabel("carStatus", detail.person?.car_status) }}</el-descriptions-item>
        </el-descriptions>

        <div class="detail-section">
          <div class="section-title">觅AI印象</div>
          <div class="ai-profile-box">
            <div class="ai-profile-head">
              <el-tag :type="aiStatusTag(detail.ai_profile?.latest_task?.status || detail.ai_profile?.profile?.generation_status)">
                {{ aiStatusLabel(detail.ai_profile?.latest_task?.status || detail.ai_profile?.profile?.generation_status) }}
              </el-tag>
              <span v-if="detail.ai_profile?.profile?.source_type" class="ai-profile-meta">
                来源：{{ aiSourceLabel(detail.ai_profile.profile.source_type) }}
              </span>
              <span v-if="detail.ai_profile?.latest_task?.retry_count" class="ai-profile-meta">
                重试：{{ detail.ai_profile.latest_task.retry_count }} 次
              </span>
            </div>
            <div v-if="detail.ai_profile?.profile?.content" class="ai-profile-content">
              {{ detail.ai_profile.profile.content }}
            </div>
            <el-empty v-else description="暂无觅AI印象" :image-size="72" />
            <div v-if="detail.ai_profile?.latest_task?.last_error" class="ai-profile-error">
              最近错误：{{ detail.ai_profile.latest_task.last_error }}
            </div>
          </div>
        </div>

        <div class="detail-section">
          <div class="section-title">照片相册</div>
          <div v-if="detail.person?.photo_urls?.length" class="photo-list">
            <el-image
              v-for="url in detail.person.photo_urls"
              :key="url"
              :src="url"
              :preview-src-list="detail.person.photo_urls"
              fit="cover"
              class="photo-item"
            />
          </div>
          <el-empty v-else description="暂无照片" />
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";

import DictAPI, { type DictDataTable } from "@/api/module_system/dict";
import MpUserAPI, { type MpUserPageQuery, type MpUserTable } from "@/api/module_mp/user";

const query = reactive<MpUserPageQuery>({
  page_no: 1,
  page_size: 10,
  keyword: "",
  is_registered: undefined,
});
const loading = ref(false);
const rows = ref<MpUserTable[]>([]);
const total = ref(0);
const detailVisible = ref(false);
const detail = ref<MpUserTable>();
const dictOptions = reactive({
  ethnicity: [] as Array<{ label: string; value: string }>,
  annualIncome: [] as Array<{ label: string; value: string }>,
  maritalStatus: [] as Array<{ label: string; value: string }>,
  education: [] as Array<{ label: string; value: string }>,
  houseStatus: [] as Array<{ label: string; value: string }>,
  carStatus: [] as Array<{ label: string; value: string }>,
});

function genderLabel(value?: string) {
  const map: Record<string, string> = { "0": "男", "1": "女", "2": "未知" };
  return value ? map[value] || value : "-";
}

function eventCountLabel(value?: number) {
  return `${value || 0} 次`;
}

function dictLabel(type: keyof typeof dictOptions, value?: string) {
  if (!value) return "-";
  return dictOptions[type].find((item) => item.value === value)?.label || value;
}

function aiStatusLabel(value?: string) {
  return (
    {
      pending: "等待生成",
      processing: "生成中",
      success: "已生成",
      failed: "生成失败，等待重试",
      cancelled: "已取消",
    } as Record<string, string>
  )[value || ""] || "暂无任务";
}

function aiStatusTag(value?: string) {
  return (
    {
      pending: "info",
      processing: "warning",
      success: "success",
      failed: "danger",
      cancelled: "info",
    } as const
  )[value || ""] || "info";
}

function aiSourceLabel(value?: string) {
  return (
    {
      register: "小程序注册",
      admin_update: "后台资料维护",
      deep_interview: "红娘深访",
    } as Record<string, string>
  )[value || ""] || value || "-";
}

async function fetchList() {
  loading.value = true;
  try {
    const res = await MpUserAPI.listUser(query);
    rows.value = res.data.data.items || [];
    total.value = res.data.data.total || 0;
  } finally {
    loading.value = false;
  }
}

function resetQuery() {
  query.page_no = 1;
  query.page_size = 10;
  query.keyword = "";
  query.is_registered = undefined;
  fetchList();
}

async function openDetail(id: number) {
  await loadDictOptions();
  const res = await MpUserAPI.detailUser(id);
  detail.value = res.data.data;
  detailVisible.value = true;
}

let dictPromise: Promise<void> | null = null;

async function loadDictOptions() {
  if (dictPromise) return dictPromise;
  const dictMap = {
    ethnicity: "crm_ethnicity",
    annualIncome: "crm_annual_income",
    maritalStatus: "crm_marital_status",
    education: "crm_education",
    houseStatus: "crm_house_status",
    carStatus: "crm_car_status",
  } as const;
  dictPromise = Promise.all(
    Object.entries(dictMap).map(async ([key, type]) => {
      const res = await DictAPI.getInitDict(type);
      dictOptions[key as keyof typeof dictOptions] = ((res.data.data as DictDataTable[]) || []).map((item) => ({
        label: item.dict_label || item.dict_value || "",
        value: item.dict_value || "",
      }));
    })
  ).then(() => undefined);
  return dictPromise;
}

onMounted(() => {
  loadDictOptions();
  fetchList();
});
</script>

<style scoped>
.mp-user-page .filter-card {
  margin-bottom: 12px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.toolbar-title {
  font-size: 16px;
  font-weight: 600;
}

.wx-profile {
  display: flex;
  align-items: center;
  gap: 10px;
}

.nickname {
  font-weight: 600;
  line-height: 20px;
}

.sub-text {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 18px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.detail-section {
  margin-top: 18px;
}

.section-title {
  margin-bottom: 12px;
  color: var(--el-text-color-primary);
  font-size: 16px;
  font-weight: 600;
}

.ai-profile-box {
  padding: 16px 18px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  background: var(--el-fill-color-blank);
}

.ai-profile-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.ai-profile-meta {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.ai-profile-content {
  min-height: 132px;
  max-height: 420px;
  overflow-y: auto;
  padding: 14px 16px;
  border-radius: 8px;
  background: var(--el-fill-color-light);
  color: var(--el-text-color-primary);
  font-size: 14px;
  line-height: 1.9;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
  word-break: break-word;
}

.ai-profile-error {
  margin-top: 10px;
  color: var(--el-color-danger);
  font-size: 12px;
  line-height: 1.6;
}

.photo-list {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.photo-item {
  width: 112px;
  height: 112px;
  border-radius: 6px;
}
</style>
