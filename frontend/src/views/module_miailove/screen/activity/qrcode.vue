<template>
  <div class="app-container qrcode-config-page">
    <el-card shadow="never">
      <template #header>
        <div>
          <div class="toolbar-title">签到二维码</div>
          <div class="toolbar-note">这里维护签到二维码插件的全局显示配置；每个活动是否显示二维码，在「活动列表」的高级设置里勾选。</div>
        </div>
      </template>

      <el-form v-loading="loading" :model="form" label-width="120px" class="setting-form">
        <el-form-item label="显示位置">
          <div class="position-grid">
            <button
              v-for="item in positions"
              :key="item"
              type="button"
              :class="{ active: form.position === item }"
              @click="form.position = item"
            >
              <el-icon><component :is="positionIcons[item]" /></el-icon>
            </button>
          </div>
        </el-form-item>
        <el-form-item label="二维码大小">
          <el-segmented v-model="form.size" :options="sizeOptions" />
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
import { Aim, Back, Bottom, BottomLeft, BottomRight, Right, Top, TopLeft, TopRight } from "@element-plus/icons-vue";
import { onMounted, reactive, ref } from "vue";

import ScreenAPI, { type ScreenActivityQrcodeSettings } from "@/api/module_screen/screen";

const positions: ScreenActivityQrcodeSettings["position"][] = ["7", "8", "9", "4", "5", "6", "1", "2", "3"];
const positionIcons = {
  "7": TopLeft,
  "8": Top,
  "9": TopRight,
  "4": Back,
  "5": Aim,
  "6": Right,
  "1": BottomLeft,
  "2": Bottom,
  "3": BottomRight,
};
const sizeOptions = [
  { label: "大", value: "large" },
  { label: "中", value: "medium" },
  { label: "小", value: "small" },
];

const loading = ref(false);
const saving = ref(false);
const form = reactive<ScreenActivityQrcodeSettings>({
  position: "3",
  size: "medium",
});

function setForm(value: Partial<ScreenActivityQrcodeSettings>) {
  form.position = value.position || "3";
  form.size = value.size || "medium";
}

async function load() {
  loading.value = true;
  try {
    const res = await ScreenAPI.getActivityQrcodeSettings();
    setForm(res.data.data || {});
  } finally {
    loading.value = false;
  }
}

async function save() {
  saving.value = true;
  try {
    const res = await ScreenAPI.updateActivityQrcodeSettings({ ...form });
    setForm(res.data.data || {});
    ElMessage.success("签到二维码设置已保存");
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
.position-grid {
  width: 162px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 7px;
}
.position-grid button {
  height: 42px;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  background: #fff;
  color: #303133;
  cursor: pointer;
}
.position-grid button.active {
  border-color: #409eff;
  background: #ecf5ff;
  color: #409eff;
  font-weight: 700;
}
</style>
