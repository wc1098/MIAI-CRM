<template>
  <div class="app-container activity-screen-page">
    <el-card shadow="never" class="filter-card">
      <el-form :model="query" inline>
        <el-form-item label="关键词">
          <el-input v-model="query.keyword" clearable placeholder="大屏名称/活动名称/门店" @keyup.enter="load" />
        </el-form-item>
        <el-form-item label="启用状态">
          <el-select v-model="query.enabled" clearable placeholder="全部" style="width: 130px">
            <el-option label="启用" :value="true" />
            <el-option label="停用" :value="false" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" icon="Search" @click="load">查询</el-button>
          <el-button icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="toolbar">
          <div>
            <div class="toolbar-title">活动大屏</div>
            <div class="toolbar-note">配置活动大屏基础信息、背景素材和插件启用开关；插件参数在下级菜单单独维护。</div>
          </div>
          <div class="toolbar-actions">
            <el-button icon="Monitor" @click="openPlayer">打开大屏</el-button>
            <el-button v-hasPerm="['screen:activity:create']" type="primary" icon="Plus" @click="openCreateDialog">创建活动大屏</el-button>
          </div>
        </div>
      </template>

      <el-table v-loading="loading" :data="rows" border stripe row-key="id">
        <el-table-column prop="screen_name" label="大屏名称" min-width="170" show-overflow-tooltip />
        <el-table-column label="关联活动" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">{{ row.event?.title || "-" }}</template>
        </el-table-column>
        <el-table-column label="门店" min-width="130">
          <template #default="{ row }">{{ row.event?.store_name || "-" }}</template>
        </el-table-column>
        <el-table-column label="活动时间" min-width="170">
          <template #default="{ row }">{{ shortTime(row.event?.start_time) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.enabled && row.status === '0' ? 'success' : 'info'">{{ row.enabled && row.status === "0" ? "启用" : "停用" }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="当前场景" width="110">
          <template #default="{ row }">{{ sceneLabel(row.current_scene) }}</template>
        </el-table-column>
        <el-table-column prop="checkin_count" label="签到" width="90" />
        <el-table-column label="签到码" width="100">
          <template #default="{ row }">
            <el-popover v-if="row.qrcode_url" placement="left" :width="220" trigger="hover">
              <img :src="row.qrcode_url" class="qr-preview" alt="" />
              <template #reference><el-link type="primary">查看</el-link></template>
            </el-popover>
            <el-tag v-else type="warning">未生成</el-tag>
          </template>
        </el-table-column>
        <el-table-column fixed="right" label="操作" width="310">
          <template #default="{ row }">
            <el-button v-hasPerm="['screen:activity:update']" link type="primary" @click="openSettings(row)">设置</el-button>
            <el-button v-hasPerm="['screen:activity:remote']" link type="primary" @click="openControl(row)">控制台</el-button>
            <el-button link type="primary" @click="openPlayer">打开大屏</el-button>
            <el-button v-hasPerm="['screen:activity:delete']" link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination v-model:current-page="query.page_no" v-model:page-size="query.page_size" :total="total" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next, jumper" @size-change="load" @current-change="load" />
      </div>
    </el-card>

    <el-dialog v-model="createDialog.visible" title="创建活动大屏" width="620px" destroy-on-close>
      <el-form :model="createDialog.form" label-width="110px">
        <el-form-item label="关联活动">
          <el-select v-model="createDialog.form.event_id" filterable placeholder="请选择活动" :loading="eventLoading" style="width: 100%" @change="syncScreenNameFromEvent">
            <el-option v-for="item in eventOptions" :key="item.id" :label="`${item.title}｜${item.store_name || '-'}`" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="大屏名称">
          <el-input v-model="createDialog.form.screen_name" maxlength="128" placeholder="默认取活动标题" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="createDialog.form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="createDialog.saving" @click="createActivity">创建</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="settings.visible" title="活动大屏设置" size="760px" destroy-on-close>
      <div v-if="settings.form" class="settings-panel">
        <el-card shadow="never">
          <template #header><span class="section-title">基础配置</span></template>
          <el-form :model="settings.form" label-width="130px">
            <el-form-item label="大屏名称">
              <el-input v-model="settings.form.screen_name" maxlength="128" />
            </el-form-item>
            <el-form-item label="关联活动">
              <el-select v-model="settings.form.event_id" filterable placeholder="请选择活动" :loading="eventLoading" style="width: 100%">
                <el-option v-for="item in eventOptions" :key="item.id" :label="`${item.title}｜${item.store_name || '-'}`" :value="item.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="手机欢迎语">
              <el-input v-model="settings.form.theme_config.welcome_message" type="textarea" maxlength="120" show-word-limit />
            </el-form-item>
            <el-form-item label="启用">
              <el-switch v-model="settings.form.enabled" />
            </el-form-item>
          </el-form>
        </el-card>

        <el-card shadow="never">
          <template #header><span class="section-title">高级设置</span></template>
          <div class="switch-grid">
            <el-switch v-model="settings.form.show_qrcode" active-text="显示签到二维码" />
            <el-switch v-model="settings.form.module_config.dominate.enabled" active-text="开启霸屏" />
            <el-switch v-model="settings.form.module_config.gift.enabled" active-text="开启礼物" />
            <el-switch v-model="settings.form.module_config.welfare.enabled" active-text="开启福利" />
            <el-switch v-model="settings.form.module_config.checkin_wall.enabled" active-text="开启签到墙" />
            <el-switch v-model="settings.form.module_config.barrage.enabled" active-text="开启普通弹幕" />
            <el-switch v-model="settings.form.module_config.music.enabled" active-text="开启背景音乐" />
          </div>
        </el-card>

        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span class="section-title">背景设置</span>
              <div>
                <el-upload :show-file-list="false" accept="image/jpeg,image/png,image/webp" :http-request="uploadBackground">
                  <el-button icon="Upload">上传背景</el-button>
                </el-upload>
                <el-button icon="Plus" @click="addColorBackground">添加纯色</el-button>
              </div>
            </div>
          </template>
          <div class="toolbar-note background-note">后台只维护背景素材；当前大屏背景由手机控制台现场切换。</div>
          <div class="background-list">
            <div v-for="item in settings.form.theme_config.backgrounds" :key="item.id" class="background-card">
              <div class="background-preview" :style="backgroundPreviewStyle(item)"></div>
              <el-input v-model="item.name" maxlength="20" />
              <el-color-picker v-if="item.type === 'color'" v-model="item.color" />
              <div class="background-actions">
                <el-button link type="danger" @click="removeBackground(item.id)">删除</el-button>
              </div>
            </div>
          </div>
          <el-form :model="settings.form" label-width="130px" class="mobile-bg">
            <el-form-item label="手机端背景">
              <el-upload :show-file-list="false" accept="image/jpeg,image/png,image/webp" :http-request="uploadMobileBackground">
                <el-button icon="Upload">上传手机背景</el-button>
              </el-upload>
              <el-link v-if="settings.form.theme_config.mobile_background_url" class="file-link" :href="settings.form.theme_config.mobile_background_url" target="_blank">已上传</el-link>
            </el-form-item>
          </el-form>
        </el-card>

        <div class="drawer-footer">
          <el-button @click="settings.visible = false">取消</el-button>
          <el-button type="primary" :loading="settings.saving" @click="saveSettings">保存设置</el-button>
        </div>
      </div>
    </el-drawer>

    <el-dialog v-model="controlDialog.visible" title="手机控制台" width="420px">
      <div class="control-dialog">
        <img v-if="controlDialog.qrcode" :src="controlDialog.qrcode" class="control-qr" alt="" />
        <el-input v-model="controlDialog.url" readonly />
        <div class="toolbar-actions">
          <el-button type="primary" @click="copyControlUrl">复制链接</el-button>
          <el-button @click="windowOpen(controlDialog.url)">打开控制台</el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import type { UploadRequestOptions } from "element-plus";
import { ElMessage, ElMessageBox } from "element-plus";
import QRCode from "qrcode";
import { onMounted, reactive, ref } from "vue";

import EventAPI, { type EventTable } from "@/api/module_event/event";
import ScreenAPI, { type ScreenActivityBackground, type ScreenActivityConfig, type ScreenActivityForm, type ScreenActivityModuleConfig, type ScreenActivityModuleItem, type ScreenActivityThemeConfig } from "@/api/module_screen/screen";
import { uploadImageDirect } from "@/utils/upload";

type ActivityModules = Record<string, ScreenActivityModuleItem> & {
  activity_qrcode: ScreenActivityModuleItem;
  checkin_wall: ScreenActivityModuleItem;
  barrage: ScreenActivityModuleItem;
  dominate: ScreenActivityModuleItem;
  gift: ScreenActivityModuleItem;
  welfare: ScreenActivityModuleItem;
  music: ScreenActivityModuleItem;
  lottery: ScreenActivityModuleItem;
  game: ScreenActivityModuleItem;
  message_wall: ScreenActivityModuleItem;
};
type ActivityForm = ScreenActivityForm & { id?: number; theme_config: ScreenActivityThemeConfig; module_config: ActivityModules };

const loading = ref(false);
const total = ref(0);
const rows = ref<ScreenActivityConfig[]>([]);
const eventLoading = ref(false);
const eventOptions = ref<EventTable[]>([]);
const query = reactive({ page_no: 1, page_size: 10, keyword: "", enabled: undefined as boolean | undefined });

const defaultTheme = (): ScreenActivityThemeConfig => ({
  backgrounds: [],
  active_background_id: "",
  mobile_background_url: "",
  welcome_message: "欢迎来到觅爱互动大厅，倡导文明用语，共建快乐活动现场！",
  show_people_count: false,
});
const defaultModules = (): ActivityModules => ({
  activity_qrcode: { enabled: true, settings: {} },
  checkin_wall: { enabled: true, settings: {} },
  barrage: { enabled: false, settings: { max_length: 50, duration_seconds: 16, need_review: false } },
  dominate: { enabled: false, settings: { durations: [20, 45, 90, 180, 300, 600], default_duration: 20, price: 20, max_length: 20, allow_image: true, need_review: false, templates: [] } },
  gift: { enabled: false, settings: {} },
  welfare: { enabled: false, settings: {} },
  music: { enabled: false, settings: {} },
  lottery: { enabled: false, placeholder: true, settings: {} },
  game: { enabled: false, placeholder: true, settings: {} },
  message_wall: { enabled: false, placeholder: true, settings: {} },
});
const emptyForm = (): ActivityForm => ({
  event_id: undefined,
  screen_name: "",
  title: "",
  subtitle: "",
  background_url: "",
  theme_config: defaultTheme(),
  module_config: defaultModules(),
  enabled: true,
  current_scene: "blank",
  show_qrcode: true,
  status: "0",
});

const createDialog = reactive({ visible: false, saving: false, form: emptyForm() });
const settings = reactive({ visible: false, saving: false, row: null as ScreenActivityConfig | null, form: null as ActivityForm | null });
const controlDialog = reactive({ visible: false, url: "", qrcode: "" });

async function load() {
  loading.value = true;
  try {
    const res = await ScreenAPI.listActivities(query);
    rows.value = res.data.data.items || [];
    total.value = res.data.data.total || 0;
  } finally {
    loading.value = false;
  }
}

function resetQuery() {
  query.page_no = 1;
  query.keyword = "";
  query.enabled = undefined;
  load();
}

async function loadEventOptions(keyword = "") {
  eventLoading.value = true;
  try {
    const res = await EventAPI.listEvent({ page_no: 1, page_size: 100, keyword, event_status: "published" });
    eventOptions.value = res.data.data.items || [];
  } finally {
    eventLoading.value = false;
  }
}

function openCreateDialog() {
  createDialog.form = emptyForm();
  createDialog.visible = true;
  loadEventOptions();
}

function syncScreenNameFromEvent() {
  const event = eventOptions.value.find((item) => item.id === createDialog.form.event_id);
  if (event && !createDialog.form.screen_name) createDialog.form.screen_name = event.title;
}

async function createActivity() {
  if (!createDialog.form.event_id) {
    ElMessage.warning("请选择活动");
    return;
  }
  createDialog.saving = true;
  try {
    await ScreenAPI.createActivity(normalizeForm(createDialog.form));
    createDialog.visible = false;
    await load();
  } finally {
    createDialog.saving = false;
  }
}

function openSettings(row: ScreenActivityConfig) {
  settings.row = { ...row };
  settings.form = normalizeForm({ ...emptyForm(), ...row, theme_config: mergeTheme(row.theme_config), module_config: mergeModules(row.module_config) }) as ActivityForm;
  if (row.event && !eventOptions.value.some((item) => item.id === row.event_id)) eventOptions.value.unshift(row.event as EventTable);
  settings.visible = true;
  loadEventOptions(row.event?.title || "");
}

function normalizeForm(form: ActivityForm): ActivityForm {
  const theme = mergeTheme(form.theme_config);
  const modules = mergeModules(form.module_config);
  const active = theme.backgrounds.find((item) => item.id === theme.active_background_id);
  return {
    ...form,
    title: "",
    subtitle: "",
    background_url: active?.type === "image" ? active.url || "" : form.background_url || "",
    theme_config: theme,
    module_config: modules,
    current_scene: form.current_scene || "blank",
    show_qrcode: form.show_qrcode !== false,
  };
}

function mergeTheme(value?: ScreenActivityThemeConfig): ScreenActivityThemeConfig {
  const theme = { ...defaultTheme(), ...(value || {}) };
  theme.backgrounds = Array.isArray(theme.backgrounds) ? theme.backgrounds : [];
  return theme;
}

function mergeModules(value?: ScreenActivityModuleConfig): ActivityModules {
  const modules = defaultModules();
  Object.entries(value || {}).forEach(([key, item]) => {
    if (!item) return;
    modules[key] = { ...(modules[key] || { enabled: false, settings: {} }), ...item, settings: { ...(modules[key]?.settings || {}), ...(item.settings || {}) } };
  });
  return modules;
}

async function saveSettings() {
  if (!settings.form?.id || !settings.form.event_id) {
    ElMessage.warning("请选择活动");
    return;
  }
  settings.saving = true;
  try {
    await ScreenAPI.updateActivity(settings.form.id, normalizeForm(settings.form));
    settings.visible = false;
    await load();
  } finally {
    settings.saving = false;
  }
}

function newBackgroundId() {
  return `bg_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
}

async function uploadBackground(options: UploadRequestOptions) {
  if (!settings.form) return;
  const info = await uploadImageDirect(options.file as File, "screen_promo_image");
  const item: ScreenActivityBackground = { id: newBackgroundId(), name: `背景${settings.form.theme_config.backgrounds.length + 1}`, type: "image", url: info.file_url };
  settings.form.theme_config.backgrounds.push(item);
}

async function uploadMobileBackground(options: UploadRequestOptions) {
  if (!settings.form) return;
  const info = await uploadImageDirect(options.file as File, "screen_promo_image");
  settings.form.theme_config.mobile_background_url = info.file_url;
}

function addColorBackground() {
  if (!settings.form) return;
  const item: ScreenActivityBackground = { id: newBackgroundId(), name: `纯色${settings.form.theme_config.backgrounds.length + 1}`, type: "color", color: "#050507" };
  settings.form.theme_config.backgrounds.push(item);
}

function removeBackground(id: string) {
  if (!settings.form) return;
  settings.form.theme_config.backgrounds = settings.form.theme_config.backgrounds.filter((item) => item.id !== id);
  if (settings.form.theme_config.active_background_id === id) settings.form.theme_config.active_background_id = settings.form.theme_config.backgrounds[0]?.id || "";
}

function backgroundPreviewStyle(item: ScreenActivityBackground) {
  if (item.type === "color") return { background: item.color || "#050507" };
  return item.url ? { backgroundImage: `url(${item.url})` } : {};
}

async function openControl(row: ScreenActivityConfig) {
  const res = await ScreenAPI.createActivityControlToken(row.id);
  controlDialog.url = res.data.data.control_url;
  controlDialog.qrcode = await QRCode.toDataURL(controlDialog.url, { margin: 1, width: 220 });
  controlDialog.visible = true;
}

async function copyControlUrl() {
  await copyText(controlDialog.url);
}

async function copyText(value: string) {
  if (!value) return;
  await navigator.clipboard.writeText(value);
  ElMessage.success("已复制");
}

function windowOpen(url: string) {
  window.open(url, "_blank");
}

async function remove(row: ScreenActivityConfig) {
  await ElMessageBox.confirm(`确认删除「${row.screen_name || row.event?.title}」活动大屏？`, "删除确认", { type: "warning" });
  await ScreenAPI.deleteActivity(row.id);
  await load();
}

function openPlayer() {
  window.open(`${window.location.origin}${window.location.pathname}#/screen/activity-player`, "_blank");
}

function shortTime(value?: string) {
  return value ? `${value.slice(5, 10)} ${value.slice(11, 16)}` : "-";
}

function sceneLabel(value: string) {
  return value === "checkin" ? "签到墙" : "空白舞台";
}

onMounted(() => {
  loadEventOptions();
  load();
});
</script>

<style scoped>
.activity-screen-page .toolbar,
.toolbar-actions,
.card-header,
.background-actions {
  display: flex;
  align-items: center;
}
.toolbar,
.card-header {
  justify-content: space-between;
  gap: 16px;
}
.toolbar-title,
.section-title {
  font-size: 16px;
  font-weight: 700;
}
.toolbar-note {
  margin-top: 4px;
  color: #8a8f99;
  font-size: 13px;
}
.background-note {
  margin: 0 0 12px;
}
.toolbar-actions,
.card-header > div,
.background-actions {
  gap: 10px;
}
.filter-card,
.pager {
  margin-bottom: 16px;
}
.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
.qr-preview {
  width: 180px;
  height: 180px;
  object-fit: contain;
}
.muted {
  color: #8a8f99;
  font-size: 13px;
}
.settings-panel {
  display: grid;
  gap: 16px;
}
.switch-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}
.background-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}
.background-card {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 10px;
}
.background-preview {
  height: 92px;
  margin-bottom: 10px;
  border-radius: 6px;
  background-color: #111318;
  background-position: center;
  background-size: cover;
}
.background-actions {
  justify-content: flex-end;
  margin-top: 6px;
}
.mobile-bg {
  margin-top: 16px;
}
.file-link {
  margin-left: 12px;
}
.drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 4px 0 20px;
}
.control-dialog {
  display: grid;
  justify-items: center;
  gap: 14px;
}
.control-qr {
  width: 220px;
  height: 220px;
}
</style>
