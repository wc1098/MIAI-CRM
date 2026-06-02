<template>
  <main class="control-page">
    <section v-if="errorMessage" class="invalid">
      <h1>控制台已失效</h1>
      <p>{{ errorMessage }}</p>
    </section>

    <section v-else-if="activity" class="panel">
      <header class="hero">
        <div class="hero-actions">
          <button :class="['round-btn', { active: activity.module_config?.barrage?.enabled === true }]" @click="toggleModule('barrage')">
            <el-icon><ChatDotRound /></el-icon>
          </button>
          <button :class="['round-btn', { active: activity.show_qrcode === true }]" @click="send('toggle_qrcode', activity.show_qrcode !== true)">
            <el-icon><Grid /></el-icon>
          </button>
        </div>
        <p>{{ playerOnline ? "大屏在线" : "大屏离线" }}｜签到 {{ activity.checkin_count || 0 }} 人</p>
        <h1>{{ activity.screen_name || activity.event?.title || "桌面" }}</h1>
        <div class="quick-tabs">
          <button :class="{ active: activePanel === 'music' }" @click="activePanel = activePanel === 'music' ? '' : 'music'">音乐控制</button>
          <button :class="{ active: activePanel === 'dominate' }" @click="activePanel = activePanel === 'dominate' ? '' : 'dominate'">霸屏</button>
        </div>
      </header>

      <section class="desktop-grid">
        <button
          v-for="item in desktopItems"
          :key="item.key"
          :class="['desktop-item', { active: item.active, disabled: item.disabled }]"
          :disabled="item.disabled"
          @click="item.action"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </button>
      </section>

      <section v-if="backgrounds.length" class="background-strip">
        <button
          v-for="item in backgrounds"
          :key="item.id"
          :class="{ active: activeBackgroundId === item.id }"
          :style="backgroundPreviewStyle(item)"
          @click="send('set_background', { background_id: item.id })"
        >
          <span>{{ item.name }}</span>
        </button>
      </section>

      <section v-if="activePanel === 'music'" class="music-panel">
        <div class="music-title">
          <strong>背景音乐</strong>
          <span>{{ activity.module_config?.music?.enabled === true ? "已启用" : "未启用" }}</span>
        </div>
        <div class="music-actions">
          <button :disabled="!musicCanPlay" @click="sendMusicCommand('music_prev')">
            <el-icon><DArrowLeft /></el-icon>
          </button>
          <button class="primary" :disabled="!musicCanPlay" @click="sendMusicCommand('music_play')">
            <el-icon><VideoPlay /></el-icon>
          </button>
          <button :disabled="!musicEnabled" @click="sendMusicCommand('music_pause')">
            <el-icon><VideoPause /></el-icon>
          </button>
          <button :disabled="!musicCanPlay" @click="sendMusicCommand('music_next')">
            <el-icon><DArrowRight /></el-icon>
          </button>
        </div>
        <div v-if="!musicEnabled" class="music-warning">当前活动未开启背景音乐，请先在活动列表设置里开启。</div>
        <div v-else-if="!musicTracks.length" class="music-warning">背景音乐列表为空，请先在后台上传并保存音乐。</div>
        <div class="volume-row">
          <span>音量</span>
          <el-slider v-model="localVolume" :min="0" :max="100" :disabled="!musicEnabled" @change="setMusicVolume" />
        </div>
        <div class="category-tabs">
          <button :class="{ active: selectedMusicCategory === 'all' }" @click="selectedMusicCategory = 'all'">全部</button>
          <button v-for="item in musicCategories" :key="item.id" :class="{ active: selectedMusicCategory === item.id }" @click="selectedMusicCategory = item.id">
            {{ item.name }}
          </button>
        </div>
        <div class="track-list">
          <button v-for="item in visibleMusicTracks" :key="item.id" :class="{ active: currentTrackId === item.id }" :disabled="!musicEnabled" @click="selectMusicTrack(item.id)">
            <strong>{{ item.name }}</strong>
            <span>{{ categoryName(item.category_id) }}</span>
          </button>
          <div v-if="!visibleMusicTracks.length" class="music-empty">暂无可播放音乐</div>
        </div>
      </section>

      <section v-if="activePanel === 'dominate'" class="dominate-panel">
        <div class="music-title">
          <strong>头像霸屏</strong>
          <span>{{ dominateEnabled ? "已启用" : "未启用" }}</span>
        </div>
        <div v-if="!dominateEnabled" class="music-warning">当前活动未开启霸屏，请先在活动列表设置里开启。</div>
        <div class="dominate-form">
          <input v-model.trim="dominateForm.nickname" :disabled="!dominateEnabled" maxlength="24" placeholder="昵称" />
          <input v-model.trim="dominateForm.avatar_url" :disabled="!dominateEnabled" placeholder="头像URL，可不填" />
          <textarea v-model.trim="dominateForm.content" :disabled="!dominateEnabled" :maxlength="dominateSettings.max_length" placeholder="霸屏内容"></textarea>
          <div class="dominate-meta">
            <span>{{ dominateForm.content.length }}/{{ dominateSettings.max_length }}</span>
            <span>{{ dominateSettings.duration_seconds }} 秒</span>
          </div>
          <button class="dominate-submit" :disabled="!dominateEnabled" @click="sendDominate">发送霸屏</button>
        </div>
      </section>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, markRaw, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { Camera, ChatDotRound, DArrowLeft, DArrowRight, Delete, Film, Grid, MagicStick, Microphone, Monitor, Opportunity, Picture, Present, Refresh, Service, Star, SwitchButton, Trophy, UserFilled, VideoCamera, VideoPause, VideoPlay } from "@element-plus/icons-vue";
import ScreenAPI, { type ScreenActivityBackground, type ScreenActivityCommand, type ScreenActivityConfig, type ScreenActivityMusicCategory, type ScreenActivityMusicTrack } from "@/api/module_screen/screen";

const route = useRoute();
const token = computed(() => String(route.query.token || ""));
const activity = ref<ScreenActivityConfig>();
const errorMessage = ref("");
const playerOnline = ref(false);
const activePanel = ref("");
const selectedMusicCategory = ref("all");
const localVolume = ref(60);
const dominateForm = ref({ nickname: "现场嘉宾", avatar_url: "", content: "" });
let ws: WebSocket | null = null;

const backgrounds = computed(() => activity.value?.theme_config?.backgrounds || []);
const activeBackgroundId = computed(() => activity.value?.theme_config?.active_background_id || activity.value?.active_background?.id || backgrounds.value[0]?.id);
const moduleItems = computed(() => {
  const modules = activity.value?.module_config || {};
  return [
    { key: "checkin_wall", label: "签到墙", enabled: modules.checkin_wall?.enabled !== false },
    { key: "barrage", label: "普通弹幕", enabled: modules.barrage?.enabled === true },
    { key: "dominate", label: "霸屏", enabled: modules.dominate?.enabled === true },
    { key: "gift", label: "礼物", enabled: modules.gift?.enabled === true },
    { key: "welfare", label: "福利", enabled: modules.welfare?.enabled === true },
    { key: "music", label: "背景音乐", enabled: modules.music?.enabled === true },
  ];
});
const desktopItems = computed(() => [
  { key: "desktop", label: "桌面", icon: markRaw(Monitor), active: activity.value?.current_scene === "blank", action: () => send("set_scene", "blank") },
  { key: "checkin", label: "签到墙", icon: markRaw(UserFilled), active: activity.value?.current_scene === "checkin", action: () => send("set_scene", "checkin") },
  { key: "qrcode", label: "签到码", icon: markRaw(Grid), active: activity.value?.show_qrcode === true, action: () => send("toggle_qrcode", activity.value?.show_qrcode !== true) },
  { key: "refresh", label: "刷新大屏", icon: markRaw(Refresh), active: false, action: () => send("refresh") },
  { key: "clear", label: "清屏", icon: markRaw(Delete), active: false, action: () => send("clear_screen") },
  { key: "barrage", label: "消息上墙", icon: markRaw(ChatDotRound), active: activity.value?.module_config?.barrage?.enabled === true, action: () => toggleModule("barrage") },
  { key: "dominate", label: "霸屏", icon: markRaw(Star), active: activity.value?.module_config?.dominate?.enabled === true, action: () => toggleModule("dominate") },
  { key: "gift", label: "礼物", icon: markRaw(Present), active: activity.value?.module_config?.gift?.enabled === true, action: () => toggleModule("gift") },
  { key: "welfare", label: "福利", icon: markRaw(Trophy), active: activity.value?.module_config?.welfare?.enabled === true, action: () => toggleModule("welfare") },
  { key: "music", label: "音乐控制", icon: markRaw(Service), active: activity.value?.module_config?.music?.enabled === true, action: () => (activePanel.value = activePanel.value === "music" ? "" : "music") },
  { key: "album", label: "电子相册", icon: markRaw(Picture), disabled: true, action: noop },
  { key: "video", label: "放映室", icon: markRaw(VideoCamera), disabled: true, action: noop },
  { key: "draw", label: "滚动抽奖", icon: markRaw(MagicStick), disabled: true, action: noop },
  { key: "shake", label: "摇摇乐", icon: markRaw(Service), disabled: true, action: noop },
  { key: "vote", label: "现场投票", icon: markRaw(Opportunity), disabled: true, action: noop },
  { key: "song", label: "听歌识曲", icon: markRaw(Microphone), disabled: true, action: noop },
  { key: "karaoke", label: "台词秀", icon: markRaw(Film), disabled: true, action: noop },
  { key: "game", label: "骰王争霸", icon: markRaw(SwitchButton), disabled: true, action: noop },
  { key: "intro", label: "嘉宾介绍", icon: markRaw(Camera), disabled: true, action: noop },
]);
const musicSettings = computed(() => {
  const settings = activity.value?.module_config?.music?.settings || {};
  return {
    volume: normalizeNumber(settings.volume, 60, 0, 100),
    categories: Array.isArray(settings.categories) ? (settings.categories as ScreenActivityMusicCategory[]) : [],
    tracks: Array.isArray(settings.tracks) ? (settings.tracks as ScreenActivityMusicTrack[]) : [],
  };
});
const musicCategories = computed(() => musicSettings.value.categories);
const musicTracks = computed(() => musicSettings.value.tracks.filter((item) => item.enabled !== false && !!item.url).sort((a, b) => Number(a.sort || 0) - Number(b.sort || 0)));
const musicEnabled = computed(() => activity.value?.module_config?.music?.enabled === true);
const musicCanPlay = computed(() => musicEnabled.value && musicTracks.value.length > 0);
const visibleMusicTracks = computed(() => {
  if (selectedMusicCategory.value === "all") return musicTracks.value;
  return musicTracks.value.filter((item) => item.category_id === selectedMusicCategory.value);
});
const currentTrackId = computed(() => {
  const command = activity.value?.last_command;
  if (command?.command !== "music_set_track" || !command.value || typeof command.value !== "object") return "";
  return String((command.value as Record<string, unknown>).track_id || "");
});
const dominateEnabled = computed(() => activity.value?.module_config?.dominate?.enabled === true);
const dominateSettings = computed(() => {
  const settings = activity.value?.module_config?.dominate?.settings || {};
  return {
    max_length: normalizeNumber(settings.max_length, 20, 1, 60),
    duration_seconds: normalizeNumber(settings.duration_seconds, 8, 3, 30),
  };
});

function wsBase() {
  return import.meta.env.VITE_APP_WS_ENDPOINT || `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`;
}

function backgroundPreviewStyle(item: ScreenActivityBackground) {
  if (item.type === "color") return { background: item.color || "#111318" };
  return item.url ? { backgroundImage: `url(${item.url})` } : {};
}

function normalizeNumber(value: unknown, fallback: number, min: number, max: number) {
  const numberValue = Number(value);
  if (!Number.isFinite(numberValue)) return fallback;
  return Math.min(Math.max(numberValue, min), max);
}

async function load() {
  if (!token.value) {
    errorMessage.value = "缺少控制台授权";
    return;
  }
  try {
    const res = await ScreenAPI.controlActivity(token.value);
    activity.value = res.data.data.config;
    localVolume.value = musicSettings.value.volume;
    connectWs();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "控制台授权无效或已过期";
  }
}

function connectWs() {
  ws?.close();
  const url = new URL("/api/v1/screen/control/activity/ws", wsBase());
  url.searchParams.set("token", token.value);
  ws = new WebSocket(url.toString());
  ws.onmessage = (event) => {
    try {
      const message = JSON.parse(event.data);
      if (message.type === "online_status") playerOnline.value = !!message.payload?.player_online;
      if (message.payload?.id) {
        activity.value = message.payload;
        if (message.type === "music_set_volume" && activity.value?.last_command?.value !== undefined) {
          localVolume.value = normalizeNumber(activity.value.last_command.value, localVolume.value, 0, 100);
        }
      }
    } catch {}
  };
}

async function send(command: ScreenActivityCommand["command"], value?: ScreenActivityCommand["value"]) {
  if (!token.value) return;
  const res = await ScreenAPI.sendControlCommand(token.value, { command, value });
  activity.value = res.data.data;
  ElMessage.success("已发送");
}

function toggleModule(key: string) {
  const item = moduleItems.value.find((moduleItem) => moduleItem.key === key);
  send("toggle_module", { key, enabled: !(item?.enabled === true) });
}

function selectMusicTrack(trackId: string) {
  if (!musicCanPlay.value) {
    ElMessage.warning(musicEnabled.value ? "暂无可播放音乐" : "当前活动未开启背景音乐");
    return;
  }
  send("music_set_track", { track_id: trackId });
}

function setMusicVolume() {
  if (!musicEnabled.value) {
    ElMessage.warning("当前活动未开启背景音乐");
    return;
  }
  send("music_set_volume", localVolume.value);
}

function sendDominate() {
  if (!dominateEnabled.value) {
    ElMessage.warning("当前活动未开启霸屏");
    return;
  }
  if (!dominateForm.value.content) {
    ElMessage.warning("请输入霸屏内容");
    return;
  }
  send("dominate_play", {
    nickname: dominateForm.value.nickname || "现场嘉宾",
    avatar_url: dominateForm.value.avatar_url,
    content: dominateForm.value.content,
  });
  dominateForm.value.content = "";
}

function sendMusicCommand(command: Extract<ScreenActivityCommand["command"], "music_play" | "music_pause" | "music_next" | "music_prev">) {
  if (command !== "music_pause" && !musicCanPlay.value) {
    ElMessage.warning(musicEnabled.value ? "暂无可播放音乐" : "当前活动未开启背景音乐");
    return;
  }
  if (command === "music_pause" && !musicEnabled.value) {
    ElMessage.warning("当前活动未开启背景音乐");
    return;
  }
  send(command);
}

function categoryName(categoryId?: string) {
  return musicCategories.value.find((item) => item.id === categoryId)?.name || "未分类";
}

watch(
  () => musicSettings.value.volume,
  (volume) => {
    localVolume.value = volume;
  },
  { immediate: true },
);

watch(
  () => musicCategories.value.map((item) => item.id).join(","),
  () => {
    if (selectedMusicCategory.value !== "all" && !musicCategories.value.some((item) => item.id === selectedMusicCategory.value)) selectedMusicCategory.value = "all";
  },
  { immediate: true },
);

function noop() {
  ElMessage.info("该功能已预留，后续开放");
}

onMounted(load);
onBeforeUnmount(() => ws?.close());
</script>

<style scoped>
.control-page {
  min-height: 100vh;
  background: #f5f6fb;
  color: #111318;
  font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
}
.invalid,
.panel {
  width: min(100%, 430px);
  margin: 0 auto;
  box-sizing: border-box;
}
.invalid {
  min-height: 100vh;
  display: grid;
  place-content: center;
  gap: 10px;
  text-align: center;
}
.hero {
  position: relative;
  min-height: 178px;
  background: #6571ef;
  color: #fff;
  padding: 12px 10px 16px;
  text-align: center;
  box-sizing: border-box;
}
.hero-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.round-btn {
  width: 28px;
  height: 28px;
  min-height: 28px;
  display: inline-grid;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, 0.9);
  border-radius: 50%;
  background: transparent;
  color: #fff;
  padding: 0;
}
.round-btn.active {
  background: rgba(255, 255, 255, 0.22);
}
.hero p {
  margin: 20px 0 6px;
  color: rgba(255, 255, 255, 0.78);
  font-size: 12px;
}
.hero h1 {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
}
.quick-tabs {
  position: absolute;
  left: 10px;
  bottom: 15px;
  display: flex;
  gap: 10px;
}
.quick-tabs button {
  min-height: 32px;
  border-radius: 0;
  background: #fff;
  color: #202431;
  padding: 0 14px;
  font-size: 14px;
}
.quick-tabs button.active {
  color: #6571ef;
  font-weight: 700;
}
button {
  border: 0;
  cursor: pointer;
}
.desktop-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  background: #fff;
  border-top: 1px solid #eef0f6;
  border-left: 1px solid #eef0f6;
}
.desktop-item {
  height: 88px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 9px;
  border-right: 1px solid #eef0f6;
  border-bottom: 1px solid #eef0f6;
  background: #fff;
  color: #111318;
  padding: 0;
}
.desktop-item .el-icon {
  font-size: 27px;
  color: #030305;
}
.desktop-item span {
  font-size: 13px;
  line-height: 1;
}
.desktop-item.active {
  background: #f0f3ff;
}
.desktop-item.active .el-icon,
.desktop-item.active span {
  color: #6571ef;
}
.desktop-item.disabled {
  opacity: 0.48;
}
.background-strip {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  background: #fff;
  padding: 10px;
}
.background-strip button {
  min-height: 72px;
  position: relative;
  overflow: hidden;
  border-radius: 6px;
  background-color: #191b22;
  background-position: center;
  background-size: cover;
}
.background-strip button.active {
  box-shadow: inset 0 0 0 2px #6571ef;
}
.background-strip span {
  position: absolute;
  left: 8px;
  right: 8px;
  bottom: 8px;
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.5);
  padding: 5px 6px;
  font-size: 12px;
}
.music-panel {
  background: #fff;
  padding: 12px 10px 16px;
  border-top: 1px solid #eef0f6;
}
.music-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}
.music-title strong {
  font-size: 15px;
}
.music-title span {
  color: #8a8f99;
  font-size: 12px;
}
.music-actions {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}
.music-actions button {
  min-height: 40px;
  border-radius: 6px;
  background: #f2f4fb;
  color: #202431;
  font-size: 18px;
}
.music-actions button.primary {
  background: #6571ef;
  color: #fff;
}
.music-actions button:disabled,
.track-list button:disabled {
  cursor: not-allowed;
  opacity: 0.48;
}
.music-warning {
  margin-top: 8px;
  border-radius: 6px;
  background: #fff7e8;
  color: #ad6800;
  padding: 8px 10px;
  font-size: 12px;
  line-height: 1.4;
}
.volume-row {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  color: #5b6270;
  font-size: 13px;
}
.category-tabs {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding: 4px 0 10px;
}
.category-tabs button {
  flex: 0 0 auto;
  min-height: 30px;
  border-radius: 6px;
  background: #f2f4fb;
  color: #202431;
  padding: 0 12px;
}
.category-tabs button.active {
  background: #6571ef;
  color: #fff;
}
.track-list {
  display: grid;
  gap: 8px;
}
.track-list button {
  min-height: 48px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  border-radius: 6px;
  background: #f7f8fc;
  color: #202431;
  padding: 0 12px;
  text-align: left;
}
.track-list button.active {
  box-shadow: inset 0 0 0 2px #6571ef;
}
.track-list strong {
  overflow: hidden;
  font-size: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.track-list span,
.music-empty {
  color: #8a8f99;
  font-size: 12px;
}
.music-empty {
  padding: 16px 0;
  text-align: center;
}
.dominate-panel {
  background: #fff;
  padding: 12px 10px 16px;
  border-top: 1px solid #eef0f6;
}
.dominate-form {
  display: grid;
  gap: 10px;
}
.dominate-form input,
.dominate-form textarea {
  width: 100%;
  border: 1px solid #e5e8f0;
  border-radius: 6px;
  background: #f7f8fc;
  color: #202431;
  font-size: 14px;
  outline: none;
  box-sizing: border-box;
}
.dominate-form input {
  height: 40px;
  padding: 0 12px;
}
.dominate-form textarea {
  min-height: 90px;
  resize: vertical;
  padding: 10px 12px;
  font-family: inherit;
}
.dominate-form input:disabled,
.dominate-form textarea:disabled,
.dominate-submit:disabled {
  cursor: not-allowed;
  opacity: 0.48;
}
.dominate-meta {
  display: flex;
  justify-content: space-between;
  color: #8a8f99;
  font-size: 12px;
}
.dominate-submit {
  min-height: 42px;
  border-radius: 999px;
  background: #6571ef;
  color: #fff;
  font-size: 15px;
  font-weight: 700;
}
</style>
