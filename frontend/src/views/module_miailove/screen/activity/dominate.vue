<template>
  <div class="app-container dominate-config-page">
    <el-card shadow="never">
      <template #header>
        <div>
          <div class="toolbar-title">霸屏设置</div>
          <div class="toolbar-note">这里维护头像霸屏插件的全局配置；每个活动是否启用霸屏，在「活动列表」的高级设置里勾选。</div>
        </div>
      </template>

      <el-form v-loading="loading" :model="form" label-width="120px" class="setting-form">
        <el-form-item label="展示秒数">
          <el-input-number v-model="form.duration_seconds" :min="3" :max="30" />
          <span class="form-tip">每条头像霸屏在大屏上固定停留的时间</span>
        </el-form-item>
        <el-form-item label="霸屏字数">
          <el-input-number v-model="form.max_length" :min="1" :max="60" />
          <span class="form-tip">控制台单条霸屏最多可输入的字数</span>
        </el-form-item>
        <el-form-item label="需要审核">
          <el-switch v-model="form.need_review" />
          <span class="form-tip">保留配置项；首版控制台发送暂不接审核队列</span>
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

import ScreenAPI, { type ScreenActivityDominateSettings } from "@/api/module_screen/screen";

const defaultSettings = (): ScreenActivityDominateSettings => ({
  max_length: 20,
  duration_seconds: 8,
  need_review: false,
});

const loading = ref(false);
const saving = ref(false);
const form = reactive<ScreenActivityDominateSettings>(defaultSettings());

function setForm(value: Partial<ScreenActivityDominateSettings>) {
  Object.assign(form, defaultSettings(), value);
}

async function load() {
  loading.value = true;
  try {
    const res = await ScreenAPI.getActivityDominateSettings();
    setForm(res.data.data || {});
  } finally {
    loading.value = false;
  }
}

async function save() {
  saving.value = true;
  try {
    const res = await ScreenAPI.updateActivityDominateSettings({ ...form });
    setForm(res.data.data || {});
    ElMessage.success("霸屏设置已保存");
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
.toolbar-note,
.form-tip {
  color: #8a8f99;
  font-size: 13px;
}
.toolbar-note {
  margin-top: 4px;
}
.setting-form {
  max-width: 640px;
}
.form-tip {
  margin-left: 10px;
}
</style>
