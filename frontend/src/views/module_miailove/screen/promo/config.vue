<template>
  <div class="app-container promo-page">
    <el-card shadow="never">
      <template #header>
        <div class="toolbar">
          <div>
            <div class="toolbar-title">宣传大屏配置</div>
            <div class="toolbar-note">品牌维度宣传图片、视频和员工单人展示播放序列。</div>
          </div>
          <div class="toolbar-actions">
            <el-button icon="Monitor" @click="openPromoPlayer">跳转大屏</el-button>
            <el-button type="primary" icon="Check" :loading="savingConfig" @click="saveConfig">保存配置</el-button>
          </div>
        </div>
      </template>
      <el-form :model="configForm" label-width="150px" class="config-form">
        <el-form-item label="启用宣传大屏">
          <el-switch v-model="configForm.enabled" />
        </el-form-item>
        <el-form-item label="图片默认轮播">
          <el-input-number v-model="configForm.image_duration_seconds" :min="3" :max="3600" controls-position="right" />
          <span class="unit">秒/张</span>
        </el-form-item>
        <el-form-item label="员工默认轮播">
          <el-input-number v-model="configForm.staff_duration_seconds" :min="3" :max="3600" controls-position="right" />
          <span class="unit">秒/人</span>
        </el-form-item>
        <el-form-item label="安卓同步间隔">
          <el-input-number v-model="configForm.sync_interval_seconds" :min="10" :max="86400" controls-position="right" />
          <span class="unit">秒</span>
        </el-form-item>
        <el-form-item label="安卓缓存上限">
          <el-input-number v-model="configForm.cache_limit_gb" :min="1" :max="200" controls-position="right" />
          <span class="unit">GB</span>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="toolbar">
            <div>
              <div class="toolbar-title">播放序列</div>
              <div class="toolbar-note">最终按这里的顺序上屏；员工项可参与排序，同一上墙员工只能加入一次。</div>
            </div>
          <div class="toolbar-actions">
            <el-button icon="Picture" type="primary" @click="openItemDialog(undefined, 'image')">新增图片</el-button>
            <el-button icon="VideoCamera" type="primary" @click="openItemDialog(undefined, 'video')">新增视频</el-button>
            <el-button icon="User" type="primary" @click="openItemDialog(undefined, 'staff')">新增员工项</el-button>
            <el-button icon="Refresh" :loading="loading" @click="load">刷新</el-button>
          </div>
        </div>
      </template>
      <el-table :data="items" row-key="id" border class="promo-table">
        <el-table-column label="排序" width="120">
          <template #default="{ $index, row }">
            <el-button link :disabled="$index === 0" @click="moveItem(row.id, -1)">上移</el-button>
            <el-button link :disabled="$index === items.length - 1" @click="moveItem(row.id, 1)">下移</el-button>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="160" />
        <el-table-column label="类型" width="100">
          <template #default="{ row }">{{ typeText(row.item_type) }}</template>
        </el-table-column>
        <el-table-column label="素材/员工" min-width="240">
          <template #default="{ row }">
            <span v-if="row.item_type === 'staff'">{{ row.staff?.display_name || "-" }}</span>
            <el-link v-else-if="row.file_url" :href="row.file_url" target="_blank" type="primary">查看素材</el-link>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="duration_seconds" label="展示秒数" width="110" />
        <el-table-column prop="version" label="版本" width="80" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === '0' ? 'success' : 'info'">{{ row.status === "0" ? "启用" : "停用" }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="170">
          <template #default="{ row }">
            <el-button link type="primary" @click="openItemDialog(row)">编辑</el-button>
            <el-button link type="danger" @click="deleteItem(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="toolbar">
          <div>
            <div class="toolbar-title">上墙员工管理</div>
            <div class="toolbar-note">独立维护上墙员工公开资料；删除上墙员工会同步删除对应员工播放项。</div>
          </div>
          <el-button icon="Plus" type="primary" @click="openStaffDialog()">新增上墙员工</el-button>
        </div>
      </template>
      <el-table :data="staffs" row-key="id" border class="promo-table">
        <el-table-column label="形象照" width="96">
          <template #default="{ row }">
            <el-avatar :src="row.avatar_url" shape="square" :size="54">{{ row.display_name?.slice(0, 1) }}</el-avatar>
          </template>
        </el-table-column>
        <el-table-column prop="display_name" label="展示名" min-width="120" />
        <el-table-column prop="role_title" label="岗位" min-width="140" />
        <el-table-column prop="years_experience" label="从业年限" width="100" />
        <el-table-column label="擅长方向" min-width="220">
          <template #default="{ row }">
            <el-tag v-for="tag in row.specialties" :key="tag" class="staff-tag" type="danger" effect="plain">{{ tag }}</el-tag>
            <span v-if="!row.specialties?.length">-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === '0' ? 'success' : 'info'">{{ row.status === "0" ? "启用" : "停用" }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="170">
          <template #default="{ row }">
            <el-button link type="primary" @click="openStaffDialog(row)">编辑</el-button>
            <el-button link type="danger" @click="deleteStaff(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="itemDialog.visible" :title="itemDialog.form.id ? '编辑播放项' : '新增播放项'" width="680px">
      <el-form :model="itemDialog.form" label-width="120px">
        <el-form-item label="类型">
          <el-radio-group v-model="itemDialog.form.item_type">
            <el-radio-button value="image">图片</el-radio-button>
            <el-radio-button value="video">视频</el-radio-button>
            <el-radio-button value="staff">员工</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="itemDialog.form.title" maxlength="128" />
        </el-form-item>
        <el-form-item v-if="itemDialog.form.item_type === 'staff'" label="员工资料">
          <el-select v-model="itemDialog.form.staff_id" placeholder="选择员工资料" style="width: 100%">
            <el-option v-for="staff in availableStaffsForItem" :key="staff.id" :label="staff.display_name" :value="staff.id" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="itemDialog.form.item_type === 'image'" label="宣传图片">
          <el-upload :show-file-list="false" accept="image/jpeg,image/png,image/webp" :http-request="uploadItemImage">
            <el-button icon="Upload">上传图片</el-button>
          </el-upload>
          <el-link v-if="itemDialog.form.file_url" class="file-link" :href="itemDialog.form.file_url" target="_blank">已上传</el-link>
        </el-form-item>
        <el-form-item v-if="itemDialog.form.item_type === 'video'" label="宣传视频">
          <el-upload :show-file-list="false" accept="video/mp4" :http-request="uploadItemVideo">
            <el-button icon="Upload" :loading="videoUploading">上传 MP4</el-button>
          </el-upload>
          <el-link v-if="itemDialog.form.file_url" class="file-link" :href="itemDialog.form.file_url" target="_blank">已上传</el-link>
          <el-progress v-if="videoUploading || videoUploadProgress > 0" class="upload-progress" :percentage="videoUploadProgress" :stroke-width="8" />
        </el-form-item>
        <el-form-item label="展示秒数">
          <el-input-number v-model="itemDialog.form.duration_seconds" :min="1" :max="86400" controls-position="right" />
          <span class="unit">视频可留空，播完切换</span>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="itemEnabled" active-text="启用" inactive-text="停用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="itemDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="itemDialog.saving" @click="saveItem">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="staffDialog.visible" :title="staffDialog.form.id ? '编辑上墙员工' : '新增上墙员工'" width="760px">
      <el-form :model="staffDialog.form" label-width="120px">
        <el-form-item label="形象照">
          <el-upload v-if="!staffDialog.form.avatar_url" :show-file-list="false" accept="image/jpeg,image/png,image/webp" :http-request="uploadStaffAvatar">
            <el-button icon="Upload">上传形象照</el-button>
          </el-upload>
          <div v-else class="avatar-uploaded">
            <el-avatar :src="staffDialog.form.avatar_url" shape="square" :size="72" />
            <div class="avatar-actions">
              <el-upload :show-file-list="false" accept="image/jpeg,image/png,image/webp" :http-request="uploadStaffAvatar">
                <el-button link type="primary">更换</el-button>
              </el-upload>
              <el-button link type="danger" @click="staffDialog.form.avatar_url = ''">移除</el-button>
            </div>
          </div>
        </el-form-item>
        <el-form-item label="展示名">
          <el-input v-model="staffDialog.form.display_name" maxlength="64" />
        </el-form-item>
        <el-form-item label="岗位">
          <el-input v-model="staffDialog.form.role_title" maxlength="128" />
        </el-form-item>
        <el-form-item label="从业年限">
          <el-input-number v-model="staffDialog.form.years_experience" :min="0" :max="80" controls-position="right" />
        </el-form-item>
        <el-form-item label="擅长方向">
          <el-select v-model="staffDialog.form.specialties" multiple filterable allow-create default-first-option style="width: 100%" />
        </el-form-item>
        <el-form-item label="服务宣言">
          <el-input v-model="staffDialog.form.service_slogan" type="textarea" :rows="4" maxlength="2000" show-word-limit />
        </el-form-item>
        <el-form-item label="公开标签">
          <el-select v-model="staffDialog.form.public_tags" multiple filterable allow-create default-first-option style="width: 100%" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="staffEnabled" active-text="启用" inactive-text="停用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="staffDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="staffDialog.saving" @click="saveStaff">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import type { UploadRequestOptions } from "element-plus";
import { ElMessage, ElMessageBox } from "element-plus";
import { computed, onMounted, reactive, ref } from "vue";

import ScreenAPI, { type ScreenPromoConfig, type ScreenPromoItem, type ScreenPromoItemForm, type ScreenPromoStaff, type ScreenPromoStaffForm } from "@/api/module_screen/screen";
import { uploadFileDirect, uploadImageDirect } from "@/utils/upload";

const loading = ref(false);
const savingConfig = ref(false);
const videoUploading = ref(false);
const videoUploadProgress = ref(0);
const items = ref<ScreenPromoItem[]>([]);
const staffs = ref<ScreenPromoStaff[]>([]);
const configForm = reactive<ScreenPromoConfig>({
  enabled: true,
  image_duration_seconds: 8,
  staff_duration_seconds: 12,
  sync_interval_seconds: 60,
  cache_limit_gb: 20,
  status: "0",
});

const emptyItemForm = (): ScreenPromoItemForm & { id?: number } => ({
  item_type: "image",
  title: "",
  file_url: "",
  cover_url: "",
  file_hash: "",
  file_size: undefined,
  version: 1,
  duration_seconds: undefined,
  sort: items.value.length + 1,
  staff_id: undefined,
  status: "0",
});
const emptyStaffForm = (): ScreenPromoStaffForm & { id?: number } => ({
  avatar_url: "",
  display_name: "",
  role_title: "",
  years_experience: undefined,
  specialties: [],
  service_slogan: "",
  public_tags: [],
  sort: staffs.value.length + 1,
  status: "0",
});

const itemDialog = reactive({ visible: false, saving: false, form: emptyItemForm() });
const staffDialog = reactive({ visible: false, saving: false, form: emptyStaffForm() });

const itemEnabled = computed({
  get: () => itemDialog.form.status === "0",
  set: (value: boolean) => {
    itemDialog.form.status = value ? "0" : "1";
  },
});
const staffEnabled = computed({
  get: () => staffDialog.form.status === "0",
  set: (value: boolean) => {
    staffDialog.form.status = value ? "0" : "1";
  },
});
const availableStaffsForItem = computed(() => {
  const editingItemId = itemDialog.form.id;
  const usedStaffIds = new Set(
    items.value
      .filter((item) => item.item_type === "staff" && item.staff_id && item.id !== editingItemId)
      .map((item) => item.staff_id)
  );
  return staffs.value.filter((staff) => !usedStaffIds.has(staff.id));
});

function typeText(type: string) {
  return ({ image: "图片", video: "视频", staff: "员工" } as Record<string, string>)[type] || type;
}

async function load() {
  loading.value = true;
  try {
    const res = await ScreenAPI.getPromoConfig();
    Object.assign(configForm, res.data.data.config);
    items.value = res.data.data.items;
    staffs.value = res.data.data.staffs;
  } finally {
    loading.value = false;
  }
}

async function saveConfig() {
  savingConfig.value = true;
  try {
    const res = await ScreenAPI.savePromoConfig(configForm);
    Object.assign(configForm, res.data.data);
  } finally {
    savingConfig.value = false;
  }
}

function openItemDialog(row?: ScreenPromoItem, itemType: "image" | "video" | "staff" = "image") {
  delete itemDialog.form.id;
  Object.assign(itemDialog.form, row ? { ...row, item_type: row.item_type } : { ...emptyItemForm(), item_type: itemType });
  itemDialog.visible = true;
}

function openStaffDialog(row?: ScreenPromoStaff) {
  delete staffDialog.form.id;
  Object.assign(staffDialog.form, row ? { ...row, specialties: [...(row.specialties || [])], public_tags: [...(row.public_tags || [])] } : emptyStaffForm());
  staffDialog.visible = true;
}

async function uploadItemImage(options: UploadRequestOptions) {
  const file = options.file as File;
  const info = await uploadImageDirect(file, "screen_promo_image");
  itemDialog.form.file_url = info.file_url;
  itemDialog.form.file_size = undefined;
  itemDialog.form.version = (itemDialog.form.version || 1) + 1;
}

async function uploadItemVideo(options: UploadRequestOptions) {
  const file = options.file as File;
  videoUploading.value = true;
  videoUploadProgress.value = 0;
  try {
    const info = await uploadFileDirect(file, "screen_promo_video", (percent) => {
      videoUploadProgress.value = percent;
      options.onProgress?.({ percent } as any);
    });
    itemDialog.form.file_url = info.file_url;
    itemDialog.form.file_size = file.size;
    itemDialog.form.version = (itemDialog.form.version || 1) + 1;
    options.onSuccess?.(info);
  } catch (error) {
    options.onError?.(error as any);
    throw error;
  } finally {
    videoUploading.value = false;
  }
}

async function uploadStaffAvatar(options: UploadRequestOptions) {
  const info = await uploadImageDirect(options.file as File, "screen_promo_image");
  staffDialog.form.avatar_url = info.file_url;
}

async function saveItem() {
  itemDialog.saving = true;
  try {
    const body = { ...itemDialog.form };
    if (body.item_type !== "staff") body.staff_id = undefined;
    if (body.item_type === "staff") {
      body.file_url = "";
      const staff = staffs.value.find((item) => item.id === body.staff_id);
      if (!body.title?.trim() && staff) body.title = staff.display_name;
    }
    if (body.id) await ScreenAPI.updatePromoItem(body.id, body);
    else await ScreenAPI.createPromoItem(body);
    itemDialog.visible = false;
    await load();
  } finally {
    itemDialog.saving = false;
  }
}

async function saveStaff() {
  staffDialog.saving = true;
  try {
    const body = { ...staffDialog.form };
    if (body.id) await ScreenAPI.updatePromoStaff(body.id, body);
    else await ScreenAPI.createPromoStaff(body);
    staffDialog.visible = false;
    await load();
  } finally {
    staffDialog.saving = false;
  }
}

async function deleteItem(id: number) {
  await ElMessageBox.confirm("确认删除该播放项？", "删除确认", { type: "warning" });
  await ScreenAPI.deletePromoItem(id);
  await load();
}

async function deleteStaff(id: number) {
  await ElMessageBox.confirm("确认删除该上墙员工？对应员工播放项会同步删除。", "删除确认", { type: "warning" });
  await ScreenAPI.deletePromoStaff(id);
  await load();
}

async function moveItem(id: number, offset: number) {
  const index = items.value.findIndex((item) => item.id === id);
  const target = index + offset;
  if (index < 0 || target < 0 || target >= items.value.length) return;
  const next = [...items.value];
  [next[index], next[target]] = [next[target], next[index]];
  await ScreenAPI.sortPromoItems(next.map((item) => item.id));
  items.value = next.map((item, sort) => ({ ...item, sort: sort + 1 }));
  ElMessage.success("排序已保存");
}

onMounted(load);

function openPromoPlayer() {
  window.open(`${window.location.origin}${window.location.pathname}#/screen/promo/player`, "_blank");
}
</script>

<style scoped>
.promo-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: auto;
  min-height: 100%;
  overflow: visible;
  padding-bottom: 32px;
}
.promo-page > .el-card { flex: none; }
.toolbar { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.toolbar-title { font-size: 18px; font-weight: 600; }
.toolbar-note { margin-top: 4px; color: var(--el-text-color-secondary); font-size: 13px; }
.toolbar-actions { display: flex; gap: 8px; }
.config-form { max-width: 760px; }
.unit { margin-left: 10px; color: var(--el-text-color-secondary); }
.file-link { margin-left: 12px; }
.upload-progress { width: 220px; margin-left: 12px; }
.avatar-uploaded { display: flex; align-items: center; gap: 14px; }
.avatar-actions { display: flex; align-items: center; gap: 10px; }
.promo-table { width: 100%; }
.staff-tag { margin: 2px 6px 2px 0; }
</style>
