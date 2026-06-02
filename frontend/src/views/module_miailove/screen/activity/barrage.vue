<template>
  <div class="app-container barrage-config-page">
    <el-card shadow="never">
      <template #header>
        <div>
          <div class="toolbar-title">弹幕设置</div>
          <div class="toolbar-note">这里维护普通弹幕插件的全局配置；每个活动是否启用弹幕，在「活动列表」的高级设置里勾选。</div>
        </div>
      </template>

      <el-form v-loading="loading" :model="form" label-width="120px" class="setting-form">
        <el-form-item label="弹幕字数">
          <el-input-number v-model="form.max_length" :min="1" :max="100" />
          <span class="form-tip">用户单条弹幕最多可输入的字数</span>
        </el-form-item>
        <el-form-item label="滚动秒数">
          <el-input-number v-model="form.duration_seconds" :min="8" :max="60" />
          <span class="form-tip">数值越大，弹幕在大屏上移动越慢</span>
        </el-form-item>
        <el-form-item label="弹幕尺寸">
          <el-segmented v-model="form.size" :options="sizeOptions" />
        </el-form-item>
        <el-form-item label="需要审核">
          <el-switch v-model="form.need_review" />
          <span class="form-tip">开启后将进入审核模式，审核队列后续在弹幕功能内补齐</span>
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

import ScreenAPI, { type ScreenActivityBarrageSettings } from "@/api/module_screen/screen";

const defaultSettings = (): ScreenActivityBarrageSettings => ({
  max_length: 50,
  duration_seconds: 16,
  size: "medium",
  need_review: false,
});
const sizeOptions = [
  { label: "大", value: "large" },
  { label: "中", value: "medium" },
  { label: "小", value: "small" },
];

const loading = ref(false);
const saving = ref(false);
const form = reactive<ScreenActivityBarrageSettings>(defaultSettings());

function setForm(value: Partial<ScreenActivityBarrageSettings>) {
  Object.assign(form, defaultSettings(), value);
}

async function load() {
  loading.value = true;
  try {
    const res = await ScreenAPI.getActivityBarrageSettings();
    setForm(res.data.data || {});
  } finally {
    loading.value = false;
  }
}

async function save() {
  saving.value = true;
  try {
    const res = await ScreenAPI.updateActivityBarrageSettings({ ...form });
    setForm(res.data.data || {});
    ElMessage.success("弹幕设置已保存");
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
