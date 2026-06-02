<template>
  <div class="app-container music-config-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div>
            <div class="toolbar-title">背景音乐</div>
            <div class="toolbar-note">维护背景音乐插件的全局音乐库；每个活动是否启用背景音乐，在「活动列表」里勾选。</div>
          </div>
          <el-button type="primary" :loading="saving" @click="save">保存设置</el-button>
        </div>
      </template>

      <el-form v-loading="loading" :model="form" label-width="110px" class="setting-form">
        <el-form-item label="默认音量">
          <el-slider v-model="form.volume" :min="0" :max="100" show-input />
        </el-form-item>
        <el-form-item label="播放模式">
          <el-segmented v-model="form.play_mode" :options="playModeOptions" />
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="section-card">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="音乐列表" name="tracks">
          <div class="tab-toolbar">
            <div class="toolbar-title">音乐列表</div>
            <el-button type="primary" icon="Plus" @click="openUploadDialog">添加音乐</el-button>
          </div>
          <el-table :data="form.tracks" row-key="id">
            <el-table-column label="歌名" min-width="220">
              <template #default="{ row }">
                <el-input v-model="row.name" maxlength="64" />
                <div class="muted">{{ row.file_name }}</div>
              </template>
            </el-table-column>
            <el-table-column label="分类" width="180">
              <template #default="{ row }">
                <el-select v-model="row.category_id" placeholder="选择分类">
                  <el-option v-for="item in form.categories" :key="item.id" :label="item.name" :value="item.id" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="排序" width="120">
              <template #default="{ row }">
                <el-input-number v-model="row.sort" :min="1" controls-position="right" />
              </template>
            </el-table-column>
            <el-table-column label="启用" width="90">
              <template #default="{ row }">
                <el-switch v-model="row.enabled" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <el-button link @click="preview(row.url)">试听</el-button>
                <el-button link type="danger" @click="removeTrack(row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="分类" name="categories">
          <div class="tab-toolbar">
            <div class="toolbar-title">分类</div>
            <el-button icon="Plus" @click="addCategory">新增分类</el-button>
          </div>
          <el-table :data="form.categories" row-key="id">
            <el-table-column label="分类名称">
              <template #default="{ row }">
                <el-input v-model="row.name" maxlength="32" />
              </template>
            </el-table-column>
            <el-table-column label="歌曲数量" width="120">
              <template #default="{ row }">{{ trackCount(row.id) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button link type="danger" @click="removeCategory(row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-dialog v-model="uploadDialog.visible" title="添加音乐" width="520px" destroy-on-close>
      <el-form :model="uploadForm" label-width="90px">
        <el-form-item label="歌名" required>
          <el-input v-model="uploadForm.name" maxlength="64" placeholder="请输入歌名" />
        </el-form-item>
        <el-form-item label="分类" required>
          <el-select v-model="uploadForm.category_id" placeholder="请选择分类">
            <el-option v-for="item in form.categories" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="音乐文件" required>
          <el-upload :show-file-list="false" accept="audio/mpeg,.mp3" :http-request="uploadTrack">
            <el-button type="primary" icon="Upload" :loading="uploadDialog.uploading">上传 MP3</el-button>
          </el-upload>
          <div class="upload-hint">请先填写歌名和分类，再上传 MP3 文件。</div>
        </el-form-item>
        <el-form-item v-if="uploadDialog.uploading || uploadDialog.progress > 0" label="上传进度">
          <el-progress :percentage="uploadDialog.progress" :status="uploadDialog.progress >= 100 ? 'success' : undefined" />
        </el-form-item>
        <el-form-item v-if="uploadDialog.fileName" label="已上传">
          <span class="uploaded-file">{{ uploadDialog.fileName }}</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadDialog.visible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import type { UploadRequestOptions } from "element-plus";
import { ElMessage, ElMessageBox } from "element-plus";
import { onMounted, reactive, ref, watch } from "vue";

import ScreenAPI, { type ScreenActivityMusicSettings } from "@/api/module_screen/screen";
import { uploadFileDirect } from "@/utils/upload";

const playModeOptions = [
  { label: "列表循环", value: "list_loop" },
  { label: "单曲循环", value: "single_loop" },
  { label: "随机播放", value: "random" },
];

const defaultSettings = (): ScreenActivityMusicSettings => ({
  volume: 60,
  play_mode: "list_loop",
  categories: [
    { id: "cat_warmup", name: "暖场" },
    { id: "cat_romantic", name: "浪漫" },
    { id: "cat_interaction", name: "互动" },
    { id: "cat_ending", name: "结束" },
  ],
  tracks: [],
});

const loading = ref(false);
const saving = ref(false);
const form = reactive<ScreenActivityMusicSettings>(defaultSettings());
const activeTab = ref("tracks");
const uploadForm = reactive({ name: "", category_id: "" });
const uploadDialog = reactive({ visible: false, uploading: false, progress: 0, fileName: "" });

function setForm(value: Partial<ScreenActivityMusicSettings>) {
  Object.assign(form, defaultSettings(), value);
  form.categories = [...(value.categories || defaultSettings().categories)];
  form.tracks = [...(value.tracks || [])];
}

function newId(prefix: string) {
  return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
}

async function load() {
  loading.value = true;
  try {
    const res = await ScreenAPI.getActivityMusicSettings();
    setForm(res.data.data || {});
  } finally {
    loading.value = false;
  }
}

async function save() {
  saving.value = true;
  try {
    form.tracks.sort((a, b) => a.sort - b.sort);
    const res = await ScreenAPI.updateActivityMusicSettings({ ...form, categories: [...form.categories], tracks: [...form.tracks] });
    setForm(res.data.data || {});
    ElMessage.success("背景音乐设置已保存");
  } finally {
    saving.value = false;
  }
}

function addCategory() {
  form.categories.push({ id: newId("cat"), name: `分类${form.categories.length + 1}` });
}

async function removeCategory(id: string) {
  if (form.tracks.some((item) => item.category_id === id)) {
    ElMessage.warning("该分类下有音乐，不能删除");
    return;
  }
  form.categories = form.categories.filter((item) => item.id !== id);
}

function openUploadDialog() {
  uploadForm.name = "";
  uploadForm.category_id = form.categories[0]?.id || "";
  uploadDialog.progress = 0;
  uploadDialog.fileName = "";
  uploadDialog.uploading = false;
  uploadDialog.visible = true;
}

async function uploadTrack(options: UploadRequestOptions) {
  const trackName = uploadForm.name.trim();
  if (!trackName) {
    ElMessage.warning("请先填写歌名");
    return;
  }
  if (!uploadForm.category_id) {
    ElMessage.warning("请先选择上传分类");
    return;
  }
  const file = options.file as File;
  const name = file.name || "";
  if (!name.toLowerCase().endsWith(".mp3") && !["audio/mpeg", "audio/mp3"].includes(file.type)) {
    ElMessage.warning("只支持上传 MP3 文件");
    return;
  }
  uploadDialog.uploading = true;
  uploadDialog.progress = 0;
  uploadDialog.fileName = "";
  try {
    const info = await uploadFileDirect(file, "screen_activity_music", (percent) => {
      uploadDialog.progress = percent;
    }, false);
    form.tracks.push({
      id: newId("track"),
      name: trackName,
      url: info.file_url,
      file_name: info.origin_name || info.file_name || name,
      category_id: uploadForm.category_id,
      enabled: true,
      sort: form.tracks.length + 1,
    });
    uploadDialog.fileName = info.origin_name || info.file_name || name;
    uploadDialog.progress = 100;
    ElMessage.success("上传成功，已加入音乐列表，请保存设置");
    options.onSuccess?.(info);
  } catch (error) {
    uploadDialog.progress = 0;
    ElMessage.error(error instanceof Error ? error.message : "上传失败，请检查 OSS 配置或网络");
  } finally {
    uploadDialog.uploading = false;
  }
}

async function removeTrack(id: string) {
  await ElMessageBox.confirm("确认删除这首音乐？", "删除确认", { type: "warning" });
  form.tracks = form.tracks.filter((item) => item.id !== id);
}

function preview(url: string) {
  window.open(url, "_blank");
}

function trackCount(categoryId: string) {
  return form.tracks.filter((item) => item.category_id === categoryId).length;
}

onMounted(load);
</script>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.toolbar-title {
  color: #1f2329;
  font-size: 16px;
  font-weight: 700;
}
.toolbar-note,
.muted {
  color: #8a8f99;
  font-size: 13px;
}
.toolbar-note {
  margin-top: 4px;
}
.setting-form {
  max-width: 680px;
}
.section-card {
  margin-top: 16px;
}
.tab-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}
.upload-hint,
.uploaded-file {
  margin-left: 10px;
  color: #8a8f99;
  font-size: 13px;
}
</style>
