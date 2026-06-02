<template>
  <div class="app-container checkin-wall-config-page">
    <el-card shadow="never">
      <template #header>
        <div>
          <div class="toolbar-title">签到墙</div>
          <div class="toolbar-note">这里维护签到墙插件的全局显示配置；每个活动是否启用签到墙，在「活动列表」的高级设置里勾选。</div>
        </div>
      </template>

      <el-form v-loading="loading" :model="form" label-width="120px" class="setting-form">
        <el-form-item label="标题">
          <el-input v-model="form.title" maxlength="64" />
        </el-form-item>
        <el-form-item label="显示人数">
          <el-switch v-model="form.show_count" />
        </el-form-item>
        <el-form-item label="显示头像">
          <el-switch v-model="form.show_avatar" />
        </el-form-item>
        <el-form-item label="显示昵称">
          <el-switch v-model="form.show_nickname" />
        </el-form-item>
        <el-form-item label="列表大小">
          <el-segmented v-model="form.list_size" :options="listSizeOptions" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="saving" @click="save">保存设置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from "element-plus";
import { onMounted, reactive, ref } from "vue";

import ScreenAPI, { type ScreenActivityCheckinWallSettings } from "@/api/module_screen/screen";

const defaultSettings = (): ScreenActivityCheckinWallSettings => ({
  title: "签到墙",
  show_count: true,
  show_avatar: true,
  show_nickname: true,
  list_size: "medium",
});
const listSizeOptions = [
  { label: "大", value: "large" },
  { label: "中", value: "medium" },
  { label: "小", value: "small" },
];

const loading = ref(false);
const saving = ref(false);
const form = reactive<ScreenActivityCheckinWallSettings>(defaultSettings());

function setForm(value: Partial<ScreenActivityCheckinWallSettings>) {
  Object.assign(form, defaultSettings(), value);
}

async function load() {
  loading.value = true;
  try {
    const res = await ScreenAPI.getActivityCheckinWallSettings();
    setForm(res.data.data || {});
  } finally {
    loading.value = false;
  }
}

async function save() {
  saving.value = true;
  try {
    const res = await ScreenAPI.updateActivityCheckinWallSettings({ ...form });
    setForm(res.data.data || {});
    ElMessage.success("签到墙设置已保存");
  } finally {
    saving.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.toolbar-title {
  color: #1f2329;
  font-size: 16px;
  font-weight: 700;
}
.toolbar-note {
  margin-top: 4px;
  color: #8a8f99;
  font-size: 13px;
}
.setting-form {
  max-width: 640px;
}
</style>
