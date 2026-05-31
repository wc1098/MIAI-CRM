<template>
  <div class="app-container mp-admin-page">
    <el-card shadow="never" class="filter-card">
      <template #header>
        <div class="toolbar">
          <div>
            <div class="toolbar-title">匹配调试</div>
            <div class="toolbar-subtitle">输入人员ID或展示编号，查看候选排序、匹配分、推荐原因和向量状态。</div>
          </div>
        </div>
      </template>
        <el-form :model="query" inline>
        <el-form-item label="人员ID">
          <el-input v-model="personIdInput" clearable placeholder="数据库ID" style="width: 140px" />
        </el-form-item>
        <el-form-item label="展示编号">
          <el-input v-model="query.display_no" clearable maxlength="32" placeholder="展示编号" style="width: 140px" />
        </el-form-item>
        <el-form-item label="场景">
          <el-select v-model="query.scene" style="width: 160px">
            <el-option label="后台调试" value="debug" />
            <el-option label="订阅/C端" value="subscription" />
            <el-option label="红娘服务" value="matchmaker_service" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" icon="Search" @click="fetchList">开始匹配</el-button>
          <el-button icon="Refresh" @click="resetQuery">重置</el-button>
          <el-button :disabled="!result?.query_person_id" icon="RefreshRight" @click="rebuildVector">重建发起人向量</el-button>
        </el-form-item>
      </el-form>
      <el-alert
        v-if="result"
        class="mt-2"
        type="info"
        :closable="false"
        show-icon
        :title="`当前模型：${result.model_info?.model_name || '-'} / ${result.model_info?.dimension || '-'}维，发起人：${result.query_display_no || result.query_person_id}`"
      />
    </el-card>

    <el-card shadow="never" class="status-card" v-if="result">
      <el-descriptions :column="4" border>
        <el-descriptions-item label="Provider">{{ result.model_info?.provider || "-" }}</el-descriptions-item>
        <el-descriptions-item label="模型">{{ result.model_info?.model_name || "-" }}</el-descriptions-item>
        <el-descriptions-item label="维度">{{ result.model_info?.dimension || "-" }}</el-descriptions-item>
        <el-descriptions-item label="启用">{{ result.model_info?.enabled ? "是" : "否" }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card shadow="never">
      <el-table v-loading="loading" :data="rows" border stripe>
        <el-table-column prop="display_no" label="编号" width="110" />
        <el-table-column label="基础信息" min-width="180">
          <template #default="{ row }">
            <div class="strong">{{ row.nickname || "-" }}</div>
            <div class="muted">{{ row.gender || "-" }} / {{ row.age || "-" }}岁 / {{ row.height_cm || "-" }}cm</div>
            <div class="muted">{{ row.residence || "-" }}</div>
          </template>
        </el-table-column>
        <el-table-column label="匹配度" width="150">
          <template #default="{ row }">
            <el-progress :percentage="row.match_score" :stroke-width="10" />
            <div class="muted">排序 {{ row.rank_score }} / 置信 {{ row.confidence_score }}</div>
          </template>
        </el-table-column>
        <el-table-column label="分数构成" width="180">
          <template #default="{ row }">
            <el-tag type="success">结构 {{ row.structured_score }}</el-tag>
            <el-tag class="ml-1" :type="row.vector_status === 'success' ? 'primary' : 'warning'">
              向量 {{ row.vector_score ?? "缺失" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="命中点" min-width="220">
          <template #default="{ row }">
            <el-tag v-for="item in row.matched_points" :key="item" class="tag" type="success">{{ item }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="风险点" min-width="200">
          <template #default="{ row }">
            <el-tag v-for="item in row.risk_points" :key="item" class="tag" type="warning">{{ item }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="admin_reason" label="后台说明" min-width="280" show-overflow-tooltip />
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
import { reactive, ref } from "vue";
import { ElMessage } from "element-plus";

import MpUserAPI, { type MatchCandidate, type MatchDebugQuery, type MatchDebugResult } from "@/api/module_mp/user";

const query = reactive<MatchDebugQuery>({ page_no: 1, page_size: 20, scene: "debug" });
const personIdInput = ref("");
const loading = ref(false);
const rows = ref<MatchCandidate[]>([]);
const total = ref(0);
const result = ref<MatchDebugResult>();

async function fetchList() {
  const personIdText = personIdInput.value.trim();
  const displayNo = query.display_no?.trim();
  if (!personIdText && !displayNo) {
    ElMessage.warning("请输入人员ID或展示编号");
    return;
  }
  if (personIdText && !/^\d+$/.test(personIdText)) {
    ElMessage.warning("人员ID必须是数字；展示编号请填写到展示编号输入框");
    return;
  }
  loading.value = true;
  try {
    const requestQuery: MatchDebugQuery = {
      page_no: query.page_no,
      page_size: query.page_size,
      scene: query.scene,
      person_id: personIdText ? Number(personIdText) : undefined,
      display_no: displayNo || undefined,
    };
    const res = await MpUserAPI.matchDebug(requestQuery);
    result.value = res.data.data;
    rows.value = res.data.data.items || [];
    total.value = res.data.data.total || 0;
  } finally {
    loading.value = false;
  }
}

function resetQuery() {
  query.page_no = 1;
  query.page_size = 20;
  personIdInput.value = "";
  query.display_no = "";
  query.scene = "debug";
  rows.value = [];
  total.value = 0;
  result.value = undefined;
}

async function rebuildVector() {
  if (!result.value?.query_person_id) return;
  await MpUserAPI.rebuildMatchVector(result.value.query_person_id);
  ElMessage.success("已投递重建任务，稍后刷新查看状态");
}
</script>

<style scoped>
.status-card {
  margin-bottom: 12px;
}
.toolbar-title {
  font-size: 18px;
  font-weight: 700;
}
.toolbar-subtitle,
.muted {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.strong {
  font-weight: 600;
}
.mt-2 {
  margin-top: 8px;
}
.ml-1 {
  margin-left: 6px;
}
.tag {
  margin: 2px 4px 2px 0;
}
</style>
