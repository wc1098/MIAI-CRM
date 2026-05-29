<template>
  <div class="app-container screen-config-page">
    <el-card shadow="never">
      <template #header>
        <div class="toolbar">
          <div>
            <div class="toolbar-title">用户墙配置</div>
            <div class="toolbar-note">品牌维度用户墙配置，Web 大屏与安卓 TV 共用。</div>
          </div>
          <div class="toolbar-actions">
            <el-button icon="Monitor" @click="openScreenPlayer">跳转大屏</el-button>
            <el-button type="primary" icon="Check" :loading="saving" @click="save">保存配置</el-button>
          </div>
        </div>
      </template>

      <el-form :model="form" label-width="150px" class="config-form">
        <el-form-item label="大屏标题">
          <el-input v-model="form.title" maxlength="128" />
        </el-form-item>
        <el-form-item label="用户轮播时间">
          <el-input-number v-model="form.user_switch_seconds" :min="5" :max="120" controls-position="right" />
          <span class="unit">秒/人</span>
        </el-form-item>
        <el-form-item label="用户多图切换时间">
          <el-input-number v-model="form.photo_switch_seconds" :min="2" :max="60" controls-position="right" />
          <span class="unit">秒/张</span>
        </el-form-item>
        <el-form-item label="排序策略">
          <el-radio-group v-model="form.sort_strategy">
            <el-radio-button value="latest">最新注册</el-radio-button>
            <el-radio-button value="certified">认证优先</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="筛选性别">
          <el-select v-model="filterGender" clearable placeholder="不限" style="width: 220px">
            <el-option label="男" value="0" />
            <el-option label="女" value="1" />
          </el-select>
        </el-form-item>
        <el-form-item label="筛选认证">
          <el-select v-model="filterCertification" clearable placeholder="不限" style="width: 220px">
            <el-option label="未认证" value="none" />
            <el-option label="基础认证" value="basic" />
            <el-option label="高级认证" value="advanced" />
            <el-option label="尊享认证" value="premium" />
          </el-select>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import ScreenAPI, { type ScreenUserWallConfig } from "@/api/module_screen/screen";

const saving = ref(false);
const form = reactive<ScreenUserWallConfig>({
  title: "觅爱用户墙",
  user_switch_seconds: 12,
  photo_switch_seconds: 4,
  sort_strategy: "latest",
  filter_config: {},
  qr_action: "mini_profile",
  status: "0",
});

const filterGender = computed({
  get: () => String(form.filter_config.gender || ""),
  set: (value: string) => {
    form.filter_config = { ...form.filter_config, gender: value || undefined };
  },
});

const filterCertification = computed({
  get: () => String(form.filter_config.certification_level || ""),
  set: (value: string) => {
    form.filter_config = { ...form.filter_config, certification_level: value || undefined };
  },
});

async function load() {
  const res = await ScreenAPI.getUserWallConfig();
  Object.assign(form, res.data.data);
}

async function save() {
  saving.value = true;
  try {
    const res = await ScreenAPI.saveUserWallConfig(form);
    Object.assign(form, res.data.data);
  } finally {
    saving.value = false;
  }
}

function openScreenPlayer() {
  window.open(`${window.location.origin}${window.location.pathname}#/screen/player`, "_blank");
}

onMounted(load);
</script>

<style scoped>
.screen-config-page { display: flex; flex-direction: column; gap: 12px; }
.toolbar { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.toolbar-actions { display: flex; align-items: center; gap: 8px; }
.toolbar-title { font-size: 18px; font-weight: 600; }
.toolbar-note { margin-top: 4px; color: var(--el-text-color-secondary); font-size: 13px; }
.config-form { max-width: 760px; }
.unit { margin-left: 10px; color: var(--el-text-color-secondary); }
</style>
