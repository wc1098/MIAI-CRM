<template>
  <main class="activity-player">
    <section v-if="mode === 'binding'" class="center-page">
      <div class="brand">觅爱智慧大屏</div>
      <h1>绑定大屏设备</h1>
      <div class="device-code">{{ bootstrapInfo?.device_code || "生成中..." }}</div>
      <p>请在后台「大屏管理 > 设备管理」中输入设备码完成绑定</p>
      <button @click="bootstrap">重新生成</button>
    </section>

    <section v-else-if="mode === 'select'" class="select-page">
      <header>
        <div>
          <div class="brand">觅爱活动大屏</div>
          <h1>选择现场活动</h1>
        </div>
        <button @click="loadActivities">刷新</button>
      </header>
      <div class="activity-grid">
        <button v-for="item in activities" :key="item.id" class="activity-card" @click="enterActivity(item.id)">
          <strong>{{ item.screen_name || item.event?.title }}</strong>
          <span>{{ item.event?.store_name || "门店未设置" }}｜{{ timeText(item.event?.start_time) }}</span>
        </button>
      </div>
      <div v-if="!activities.length" class="empty">暂无可用活动大屏</div>
    </section>

    <section v-else-if="activity" class="stage" :style="stageStyle">
      <div class="barrage-layer">
        <div v-for="item in barrageItems" :key="item.uid" :class="['barrage-item', `size-${item.size || 'medium'}`]" :style="{ top: `${item.top}%`, animationDuration: `${item.duration}s` }">
          <img v-if="item.avatar_url" :src="item.avatar_url" alt="" />
          <span v-else class="barrage-avatar">{{ (item.nickname || "嘉").slice(0, 1) }}</span>
          <strong>{{ item.nickname || "现场嘉宾" }}</strong>
          <span class="barrage-separator">:</span>
          <span>{{ item.content }}</span>
        </div>
      </div>
      <div v-if="activity.current_scene === 'checkin' && checkinWallEnabled" :class="['checkin-wall', `list-${checkinWallSettings.list_size}`]">
        <header class="checkin-header">
          <h2>{{ checkinWallSettings.title }}</h2>
          <span v-if="checkinWallSettings.show_count">{{ activity.checkin_count || participants.length }} 人签到</span>
        </header>
        <transition name="featured-checkin">
          <article v-if="featuredParticipant" class="featured-person">
            <img v-if="checkinWallSettings.show_avatar && featuredParticipant.avatar_url" :src="featuredParticipant.avatar_url" alt="" />
            <div v-else-if="checkinWallSettings.show_avatar" class="avatar-fallback">{{ (featuredParticipant.display_nickname || "嘉").slice(0, 1) }}</div>
            <strong v-if="checkinWallSettings.show_nickname">{{ featuredParticipant.display_nickname || "现场嘉宾" }}</strong>
          </article>
        </transition>
        <div class="checkin-list">
          <article v-for="item in visibleParticipants" :key="item.id" class="person-card">
            <img v-if="checkinWallSettings.show_avatar && item.avatar_url" :src="item.avatar_url" alt="" />
            <div v-else-if="checkinWallSettings.show_avatar" class="avatar-fallback">{{ (item.display_nickname || "嘉").slice(0, 1) }}</div>
            <strong v-if="checkinWallSettings.show_nickname">{{ item.display_nickname || "现场嘉宾" }}</strong>
          </article>
        </div>
      </div>
      <aside v-if="showQrcode" :class="['qr-panel', `position-${qrcodePosition}`, `size-${qrcodeSize}`]">
        <img :src="activity.qrcode_url" alt="" />
        <span>扫码签到</span>
      </aside>
      <transition name="dominate-show">
        <div v-if="activeDominate" class="dominate-layer">
          <div class="dominate-stars"></div>
          <article class="dominate-card">
            <div class="dominate-avatar-wrap">
              <img v-if="activeDominate.avatar_url" :src="activeDominate.avatar_url" alt="" />
              <div v-else class="dominate-avatar-fallback">{{ (activeDominate.nickname || "嘉").slice(0, 1) }}</div>
            </div>
            <strong>{{ activeDominate.nickname || "现场嘉宾" }}</strong>
            <p>{{ activeDominate.content }}</p>
          </article>
        </div>
      </transition>
      <audio ref="audioRef" preload="auto" playsinline @ended="handleMusicEnded" />
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import ScreenAPI, { type ScreenActivityBackground, type ScreenActivityBarrage, type ScreenActivityConfig, type ScreenActivityMusicTrack, type ScreenActivityParticipant, type ScreenBootstrapResult } from "@/api/module_screen/screen";

const BOOTSTRAP_KEY = "screen_bootstrap_info";
const mode = ref<"binding" | "select" | "playing">("binding");
const bootstrapInfo = ref<ScreenBootstrapResult>();
const activities = ref<ScreenActivityConfig[]>([]);
const activity = ref<ScreenActivityConfig>();
const participants = ref<ScreenActivityParticipant[]>([]);
const featuredParticipant = ref<ScreenActivityParticipant | null>(null);
const barrageItems = ref<Array<ScreenActivityBarrage & { uid: string; top: number; duration: number }>>([]);
const dominateQueue = ref<DominateItem[]>([]);
const activeDominate = ref<DominateItem | null>(null);
const audioRef = ref<HTMLAudioElement>();
const currentMusicTrackId = ref("");
const musicPlaying = ref(false);
let bindTimer = 0;
let heartbeatTimer = 0;
let barrageSeed = 0;
let featuredTimer = 0;
let dominateTimer = 0;
let ws: WebSocket | null = null;

interface DominateItem {
  id: string;
  nickname: string;
  avatar_url?: string;
  content: string;
  duration_seconds: number;
}

const activeBackground = computed<ScreenActivityBackground | undefined>(() => {
  const theme = activity.value?.theme_config;
  const activeId = theme?.active_background_id;
  return activity.value?.active_background || theme?.backgrounds?.find((item) => item.id === activeId) || theme?.backgrounds?.[0];
});
const stageStyle = computed(() => {
  const bg = activeBackground.value;
  if (bg?.type === "color" && bg.color) return { background: bg.color };
  const url = bg?.url || activity.value?.background_url || activity.value?.event?.cover_url || "";
  return url ? { backgroundImage: `url(${url})` } : {};
});
const checkinWallEnabled = computed(() => activity.value?.module_config?.checkin_wall?.enabled !== false);
const checkinWallSettings = computed(() => {
  const settings = activity.value?.module_config?.checkin_wall?.settings || {};
  const listSize = String(settings.list_size || "medium");
  return {
    title: String(settings.title || "签到墙"),
    show_count: settings.show_count !== false,
    show_avatar: settings.show_avatar !== false,
    show_nickname: settings.show_nickname !== false,
    list_size: ["small", "medium", "large"].includes(listSize) ? listSize : "medium",
  };
});
const visibleParticipants = computed(() => {
  const limit = checkinWallSettings.value.list_size === "large" ? 12 : checkinWallSettings.value.list_size === "small" ? 24 : 18;
  return participants.value.filter((item) => item.id !== featuredParticipant.value?.id).slice(0, limit);
});
const showQrcode = computed(() => activity.value?.show_qrcode === true && activity.value?.module_config?.activity_qrcode?.enabled !== false && !!activity.value?.qrcode_url);
const barrageEnabled = computed(() => activity.value?.module_config?.barrage?.enabled === true);
const musicEnabled = computed(() => activity.value?.module_config?.music?.enabled === true);
const musicSettings = computed(() => {
  const settings = activity.value?.module_config?.music?.settings || {};
  return {
    volume: normalizeNumber(settings.volume, 60, 0, 100),
    play_mode: ["list_loop", "single_loop", "random"].includes(String(settings.play_mode)) ? String(settings.play_mode) : "list_loop",
    tracks: Array.isArray(settings.tracks) ? (settings.tracks as ScreenActivityMusicTrack[]) : [],
  };
});
const enabledMusicTracks = computed(() => musicSettings.value.tracks.filter((item) => item.enabled !== false && !!item.url).sort((a, b) => Number(a.sort || 0) - Number(b.sort || 0)));
const currentMusicTrack = computed(() => enabledMusicTracks.value.find((item) => item.id === currentMusicTrackId.value) || enabledMusicTracks.value[0]);
const qrcodePosition = computed(() => {
  const value = String(activity.value?.module_config?.activity_qrcode?.settings?.position || "3");
  return ["1", "2", "3", "4", "5", "6", "7", "8", "9"].includes(value) ? value : "3";
});
const qrcodeSize = computed(() => {
  const value = String(activity.value?.module_config?.activity_qrcode?.settings?.size || "medium");
  return ["small", "medium", "large"].includes(value) ? value : "medium";
});

function token() {
  return localStorage.getItem(ScreenAPI.tokenKey) || "";
}

function saveToken(value: string) {
  localStorage.setItem(ScreenAPI.tokenKey, value);
  const bridge = (window as any).MiaiTvShell;
  if (bridge?.saveDeviceToken) bridge.saveDeviceToken(value);
}

async function bootstrap() {
  const res = await ScreenAPI.bootstrap({ device_type: navigator.userAgent.includes("MiaiTvShell") ? "android_tv" : "web", system_info: { userAgent: navigator.userAgent } });
  bootstrapInfo.value = res.data.data;
  localStorage.setItem(BOOTSTRAP_KEY, JSON.stringify(res.data.data));
  startBindPolling();
}

function startBindPolling() {
  window.clearInterval(bindTimer);
  bindTimer = window.setInterval(async () => {
    if (!bootstrapInfo.value?.device_code) return;
    const res = await ScreenAPI.bindStatus(bootstrapInfo.value.device_code);
    const data = res.data.data;
    if (data.device_token) {
      saveToken(data.device_token);
      localStorage.removeItem(BOOTSTRAP_KEY);
      window.clearInterval(bindTimer);
      await loadActivities();
    }
  }, 3000);
}

async function loadActivities() {
  if (!token()) {
    mode.value = "binding";
    return;
  }
  try {
    const res = await ScreenAPI.playerActivityList();
    activities.value = res.data.data.items || [];
    mode.value = "select";
    startHeartbeat();
  } catch {
    mode.value = "binding";
    await bootstrap();
  }
}

async function enterActivity(id: number) {
  const res = await ScreenAPI.playerActivityDetail(id);
  activity.value = res.data.data.config;
  participants.value = res.data.data.participants || [];
  (res.data.data.barrages || []).slice(-8).forEach(pushBarrage);
  syncMusicVolume();
  ensureMusicTrack();
  mode.value = "playing";
  connectWs(id);
}

async function loadParticipants() {
  if (!activity.value) return;
  const res = await ScreenAPI.playerActivityParticipants(activity.value.id);
  participants.value = res.data.data.items || [];
  activity.value.checkin_count = res.data.data.counts.checkin_count;
  activity.value.registered_count = res.data.data.counts.registered_count;
}

function wsBase() {
  return import.meta.env.VITE_APP_WS_ENDPOINT || `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`;
}

function connectWs(id: number) {
  ws?.close();
  const url = new URL(`/api/v1/screen/player/activity/${id}/ws`, wsBase());
  url.searchParams.set("token", token());
  ws = new WebSocket(url.toString());
  ws.onmessage = async (event) => {
    try {
      const message = JSON.parse(event.data);
      if (["set_scene", "set_background", "toggle_module", "toggle_people_count", "toggle_qrcode", "refresh", "clear_screen", "music_play", "music_pause", "music_next", "music_prev", "music_set_volume", "music_set_track"].includes(message.type) && message.payload) {
        activity.value = message.payload;
        syncMusicVolume();
        await handleMusicCommand(message.type);
        if (message.type === "refresh") await loadParticipants();
      }
      if (message.type === "dominate_play" && message.payload) {
        activity.value = message.payload;
        enqueueDominate(message.payload?.last_command?.value);
      }
      if (message.type === "participant_checked_in") {
        participants.value = message.payload?.participants?.items || participants.value;
        const newest = participants.value[0];
        if (newest) showFeaturedParticipant(newest);
        if (activity.value) {
          activity.value.checkin_count = message.payload?.participants?.counts?.checkin_count ?? activity.value.checkin_count;
          activity.value.registered_count = message.payload?.participants?.counts?.registered_count ?? activity.value.registered_count;
        }
      }
      if (message.type === "barrage_created" && message.payload) {
        pushBarrage(message.payload);
      }
    } catch {}
  };
}

function showFeaturedParticipant(item: ScreenActivityParticipant) {
  featuredParticipant.value = item;
  window.clearTimeout(featuredTimer);
  featuredTimer = window.setTimeout(() => {
    featuredParticipant.value = null;
  }, 1000);
}

function pushBarrage(item: ScreenActivityBarrage) {
  if (!barrageEnabled.value || !item?.content) return;
  const uid = `${item.id || "local"}_${barrageSeed++}`;
  const top = 8 + ((barrageSeed * 13) % 58);
  const durationValue = Number(item.duration_seconds || 16);
  const duration = Number.isFinite(durationValue) ? Math.min(Math.max(durationValue, 8), 60) : 16;
  barrageItems.value.push({ ...item, uid, top, duration });
  window.setTimeout(() => {
    barrageItems.value = barrageItems.value.filter((row) => row.uid !== uid);
  }, duration * 1000 + 500);
}

function enqueueDominate(value: unknown) {
  if (!activity.value?.module_config?.dominate?.enabled || !value || typeof value !== "object") return;
  const payload = value as Record<string, unknown>;
  const content = String(payload.content || "").trim();
  if (!content) return;
  dominateQueue.value.push({
    id: String(payload.id || `dominate_${Date.now()}`),
    nickname: String(payload.nickname || "现场嘉宾").trim() || "现场嘉宾",
    avatar_url: String(payload.avatar_url || "").trim(),
    content,
    duration_seconds: normalizeNumber(payload.duration_seconds, 8, 3, 30),
  });
  playNextDominate();
}

function playNextDominate() {
  if (activeDominate.value || !dominateQueue.value.length) return;
  activeDominate.value = dominateQueue.value.shift() || null;
  window.clearTimeout(dominateTimer);
  dominateTimer = window.setTimeout(() => {
    activeDominate.value = null;
    window.setTimeout(playNextDominate, 360);
  }, (activeDominate.value?.duration_seconds || 8) * 1000);
}

function normalizeNumber(value: unknown, fallback: number, min: number, max: number) {
  const numberValue = Number(value);
  if (!Number.isFinite(numberValue)) return fallback;
  return Math.min(Math.max(numberValue, min), max);
}

function ensureMusicTrack() {
  if (!currentMusicTrackId.value || !enabledMusicTracks.value.some((item) => item.id === currentMusicTrackId.value)) {
    currentMusicTrackId.value = enabledMusicTracks.value[0]?.id || "";
  }
}

function syncMusicVolume() {
  if (audioRef.value) audioRef.value.volume = musicSettings.value.volume / 100;
}

function setMusicVolume(value: unknown) {
  if (audioRef.value) audioRef.value.volume = normalizeNumber(value, musicSettings.value.volume, 0, 100) / 100;
}

async function playMusic() {
  if (!musicEnabled.value || !currentMusicTrack.value) return;
  ensureMusicTrack();
  await nextTick();
  prepareAudioSource();
  syncMusicVolume();
  try {
    await audioRef.value?.play();
    musicPlaying.value = true;
  } catch {
    musicPlaying.value = false;
  }
}

function pauseMusic() {
  audioRef.value?.pause();
  musicPlaying.value = false;
}

function selectMusicTrack(trackId?: string) {
  if (!trackId) return;
  currentMusicTrackId.value = trackId;
}

function prepareAudioSource() {
  const audio = audioRef.value;
  const url = currentMusicTrack.value?.url || "";
  if (!audio || !url) return;
  if (audio.src !== url) {
    audio.src = url;
    audio.load();
  }
}

function switchMusicTrack(step: 1 | -1) {
  const tracks = enabledMusicTracks.value;
  if (!tracks.length) return;
  const currentIndex = Math.max(0, tracks.findIndex((item) => item.id === currentMusicTrackId.value));
  const nextIndex = (currentIndex + step + tracks.length) % tracks.length;
  currentMusicTrackId.value = tracks[nextIndex].id;
}

function nextMusicTrack() {
  const tracks = enabledMusicTracks.value;
  if (!tracks.length) return;
  if (musicSettings.value.play_mode === "single_loop") {
    audioRef.value?.play().catch(() => null);
    return;
  }
  if (musicSettings.value.play_mode === "random" && tracks.length > 1) {
    const nextTracks = tracks.filter((item) => item.id !== currentMusicTrackId.value);
    currentMusicTrackId.value = nextTracks[Math.floor(Math.random() * nextTracks.length)].id;
  } else {
    switchMusicTrack(1);
  }
}

async function handleMusicCommand(type: string) {
  if (!type.startsWith("music_")) return;
  const value = activity.value?.last_command?.value;
  if (type === "music_set_track") {
    const trackId = typeof value === "object" && value ? String((value as Record<string, unknown>).track_id || "") : "";
    selectMusicTrack(trackId);
    await playMusic();
  } else if (type === "music_set_volume") {
    setMusicVolume(value);
  } else if (type === "music_next") {
    nextMusicTrack();
    await playMusic();
  } else if (type === "music_prev") {
    switchMusicTrack(-1);
    await playMusic();
  } else if (type === "music_play") {
    await playMusic();
  } else if (type === "music_pause") {
    pauseMusic();
  }
}

function handleMusicEnded() {
  nextMusicTrack();
  if (musicPlaying.value) playMusic();
}

function startHeartbeat() {
  window.clearInterval(heartbeatTimer);
  heartbeatTimer = window.setInterval(() => {
    ScreenAPI.heartbeat({ scene: "activity" }).catch(() => null);
  }, 30000);
}

function timeText(value?: string) {
  return value ? `${value.slice(5, 10)} ${value.slice(11, 16)}` : "时间待定";
}

onMounted(() => {
  if (token()) loadActivities();
  else {
    const raw = localStorage.getItem(BOOTSTRAP_KEY);
    if (raw) {
      try {
        bootstrapInfo.value = JSON.parse(raw);
        startBindPolling();
      } catch {
        bootstrap();
      }
    } else bootstrap();
  }
});

onBeforeUnmount(() => {
  window.clearInterval(bindTimer);
  window.clearInterval(heartbeatTimer);
  window.clearTimeout(featuredTimer);
  window.clearTimeout(dominateTimer);
  pauseMusic();
  ws?.close();
});
</script>

<style scoped>
.activity-player {
  min-height: 100vh;
  overflow: hidden;
  background: #050507;
  color: #fff;
  font-family: Inter, "PingFang SC", "Microsoft YaHei", sans-serif;
}
.center-page,
.select-page {
  min-height: 100vh;
  display: grid;
  place-content: center;
  text-align: center;
  gap: 24px;
}
.brand {
  color: #ffd6a5;
  font-weight: 900;
  letter-spacing: 0.16em;
}
h1 {
  margin: 0;
  font-size: 72px;
  line-height: 1.05;
}
.device-code {
  border-radius: 12px;
  background: #fff;
  color: #111318;
  padding: 22px 44px;
  font-size: 64px;
  font-weight: 950;
}
button {
  border: 0;
  border-radius: 8px;
  padding: 18px 30px;
  background: #ff5f7b;
  color: #fff;
  font-size: 20px;
  cursor: pointer;
}
.select-page {
  width: min(1180px, 92vw);
  margin: 0 auto;
  place-content: center stretch;
  text-align: left;
}
.select-page header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.activity-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}
.activity-card {
  min-height: 136px;
  display: grid;
  gap: 12px;
  align-content: center;
  border: 1px solid rgba(255, 255, 255, 0.16);
  background: rgba(255, 255, 255, 0.08);
  text-align: left;
}
.activity-card strong {
  font-size: 24px;
}
.activity-card span,
.empty {
  color: rgba(255, 255, 255, 0.72);
}
.stage {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background-color: #050507;
  background-position: center;
  background-size: cover;
  background-repeat: no-repeat;
}
.barrage-layer {
  position: absolute;
  inset: 0;
  z-index: 3;
  pointer-events: none;
  overflow: hidden;
}
.barrage-item {
  position: absolute;
  left: 100vw;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  max-width: 80vw;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  background: rgba(0, 0, 0, 0.62);
  color: #fff;
  padding: var(--barrage-padding);
  font-size: var(--barrage-font-size);
  font-weight: 900;
  line-height: 1.2;
  white-space: nowrap;
  box-shadow:
    0 12px 34px rgba(0, 0, 0, 0.38),
    inset 0 1px 0 rgba(255, 255, 255, 0.18);
  text-shadow: 0 2px 6px rgba(0, 0, 0, 0.42);
  backdrop-filter: blur(6px);
  animation-name: barrage-move;
  animation-timing-function: linear;
  animation-fill-mode: forwards;
}
.barrage-item.size-small {
  --barrage-font-size: 26px;
  --barrage-avatar-size: 38px;
  --barrage-avatar-font-size: 20px;
  --barrage-padding: 8px 18px 8px 10px;
}
.barrage-item.size-medium {
  --barrage-font-size: 34px;
  --barrage-avatar-size: 46px;
  --barrage-avatar-font-size: 24px;
  --barrage-padding: 10px 24px 10px 12px;
}
.barrage-item.size-large {
  --barrage-font-size: 44px;
  --barrage-avatar-size: 60px;
  --barrage-avatar-font-size: 32px;
  --barrage-padding: 12px 30px 12px 14px;
}
.barrage-item img,
.barrage-avatar {
  width: var(--barrage-avatar-size);
  height: var(--barrage-avatar-size);
  border-radius: 50%;
  flex: 0 0 auto;
}
.barrage-item img {
  object-fit: cover;
}
.barrage-avatar {
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #6571ef, #25e4d5);
  color: #fff;
  font-size: var(--barrage-avatar-font-size);
}
.barrage-separator {
  margin-left: -4px;
}
@keyframes barrage-move {
  from {
    transform: translateX(0);
  }
  to {
    transform: translateX(calc(-180vw));
  }
}
.checkin-wall {
  position: absolute;
  inset: 8vh 6vw;
  display: flex;
  flex-direction: column;
  gap: 28px;
}
.checkin-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
}
.checkin-header h2 {
  margin: 0;
  color: #fff;
  font-size: 56px;
  font-weight: 900;
  text-shadow: 0 8px 24px rgba(0, 0, 0, 0.45);
}
.checkin-header span {
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.48);
  padding: 12px 18px;
  color: #fff;
  font-size: 34px;
  font-weight: 900;
}
.checkin-list {
  flex: 1;
  display: grid;
  gap: var(--checkin-gap);
  align-content: center;
}
.checkin-wall.list-small .checkin-list {
  --checkin-gap: 12px;
  --person-min-height: 116px;
  --person-avatar-size: 62px;
  --person-avatar-font-size: 28px;
  --person-name-size: 20px;
  grid-template-columns: repeat(8, minmax(0, 1fr));
}
.checkin-wall.list-medium .checkin-list {
  --checkin-gap: 16px;
  --person-min-height: 158px;
  --person-avatar-size: 86px;
  --person-avatar-font-size: 38px;
  --person-name-size: 24px;
  grid-template-columns: repeat(6, minmax(0, 1fr));
}
.checkin-wall.list-large .checkin-list {
  --checkin-gap: 20px;
  --person-min-height: 204px;
  --person-avatar-size: 116px;
  --person-avatar-font-size: 48px;
  --person-name-size: 30px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}
.person-card {
  min-height: var(--person-min-height);
  display: grid;
  place-items: center;
  gap: 6px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.48);
  backdrop-filter: blur(8px);
  padding: 10px;
}
.person-card img,
.avatar-fallback {
  width: var(--person-avatar-size);
  height: var(--person-avatar-size);
  border-radius: 50%;
}
.person-card img {
  object-fit: cover;
}
.avatar-fallback {
  display: grid;
  place-items: center;
  background: #ff5f7b;
  font-size: var(--person-avatar-font-size);
  font-weight: 900;
}
.person-card strong {
  font-size: var(--person-name-size);
}
.featured-person {
  position: fixed;
  left: 50%;
  top: 50%;
  z-index: 5;
  min-width: 340px;
  min-height: 300px;
  display: grid;
  place-items: center;
  gap: 18px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.68);
  padding: 36px 48px;
  color: #fff;
  transform: translate(-50%, -50%);
  box-shadow: 0 28px 90px rgba(0, 0, 0, 0.38);
}
.featured-person img,
.featured-person .avatar-fallback {
  width: 150px;
  height: 150px;
}
.featured-person strong {
  font-size: 42px;
  font-weight: 900;
}
.featured-checkin-enter-active,
.featured-checkin-leave-active {
  transition:
    opacity 0.22s ease,
    transform 0.22s ease;
}
.featured-checkin-enter-from,
.featured-checkin-leave-to {
  opacity: 0;
  transform: translate(-50%, -50%) scale(0.86);
}
.qr-panel {
  position: fixed;
  width: var(--qr-panel-width);
  height: var(--qr-panel-height);
  display: grid;
  grid-template-rows: var(--qr-image-size) 30px;
  place-items: center;
  gap: 8px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.92);
  padding: 10px;
  box-shadow: 0 18px 48px rgba(0, 0, 0, 0.26);
}
.qr-panel.size-small {
  --qr-panel-width: 168px;
  --qr-panel-height: 204px;
  --qr-image-size: 148px;
}
.qr-panel.size-medium {
  --qr-panel-width: 210px;
  --qr-panel-height: 248px;
  --qr-image-size: 190px;
}
.qr-panel.size-large {
  --qr-panel-width: 270px;
  --qr-panel-height: 314px;
  --qr-image-size: 250px;
}
.qr-panel.position-7,
.qr-panel.position-8,
.qr-panel.position-9 {
  top: 34px;
}
.qr-panel.position-4,
.qr-panel.position-5,
.qr-panel.position-6 {
  top: 50%;
  transform: translateY(-50%);
}
.qr-panel.position-1,
.qr-panel.position-2,
.qr-panel.position-3 {
  bottom: 34px;
}
.qr-panel.position-7,
.qr-panel.position-4,
.qr-panel.position-1 {
  left: 34px;
}
.qr-panel.position-8,
.qr-panel.position-5,
.qr-panel.position-2 {
  left: 50%;
  transform: translateX(-50%);
}
.qr-panel.position-5 {
  transform: translate(-50%, -50%);
}
.qr-panel.position-9,
.qr-panel.position-6,
.qr-panel.position-3 {
  right: 34px;
}
.qr-panel img {
  width: 100%;
  max-width: var(--qr-image-size);
  height: 100%;
  max-height: var(--qr-image-size);
  object-fit: contain;
}
.qr-panel span {
  color: #111318;
  font-size: 24px;
  font-weight: 900;
  line-height: 1;
}
.dominate-layer {
  position: fixed;
  inset: 0;
  z-index: 20;
  display: grid;
  place-items: center;
  overflow: hidden;
  background:
    radial-gradient(circle at 50% 40%, rgba(255, 255, 255, 0.18), transparent 18%),
    radial-gradient(circle at 20% 20%, rgba(255, 95, 123, 0.28), transparent 22%),
    radial-gradient(circle at 80% 72%, rgba(101, 113, 239, 0.3), transparent 24%),
    rgba(0, 0, 0, 0.76);
  backdrop-filter: blur(4px);
}
.dominate-stars {
  position: absolute;
  inset: -20%;
  background-image:
    radial-gradient(circle, rgba(255, 255, 255, 0.8) 0 2px, transparent 3px),
    radial-gradient(circle, rgba(255, 214, 165, 0.9) 0 2px, transparent 3px);
  background-position:
    0 0,
    60px 80px;
  background-size:
    120px 120px,
    180px 180px;
  opacity: 0.34;
  animation: dominate-stars 8s linear infinite;
}
.dominate-card {
  position: relative;
  width: min(980px, 78vw);
  min-height: 520px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 24px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: linear-gradient(145deg, rgba(10, 12, 18, 0.82), rgba(26, 18, 38, 0.8));
  padding: 54px 72px;
  box-shadow:
    0 34px 120px rgba(0, 0, 0, 0.52),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
  animation: dominate-card-in 0.72s cubic-bezier(0.18, 0.92, 0.2, 1.18) both;
}
.dominate-avatar-wrap {
  position: relative;
  width: 190px;
  height: 190px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  animation: dominate-avatar-pulse 1.5s ease-in-out infinite;
}
.dominate-avatar-wrap::before,
.dominate-avatar-wrap::after {
  content: "";
  position: absolute;
  inset: -18px;
  border-radius: 50%;
  border: 4px solid rgba(255, 214, 165, 0.58);
  box-shadow: 0 0 38px rgba(255, 214, 165, 0.52);
}
.dominate-avatar-wrap::after {
  inset: -34px;
  border-color: rgba(101, 113, 239, 0.34);
  animation: dominate-ring 1.3s ease-out infinite;
}
.dominate-avatar-wrap img,
.dominate-avatar-fallback {
  width: 190px;
  height: 190px;
  border-radius: 50%;
  object-fit: cover;
}
.dominate-avatar-fallback {
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #ff5f7b, #6571ef);
  color: #fff;
  font-size: 82px;
  font-weight: 950;
}
.dominate-card strong {
  color: #ffd6a5;
  font-size: 42px;
  font-weight: 950;
  text-shadow: 0 8px 24px rgba(0, 0, 0, 0.48);
}
.dominate-card p {
  margin: 0;
  max-width: 840px;
  color: #fff;
  font-size: 78px;
  font-weight: 950;
  line-height: 1.12;
  text-align: center;
  text-shadow:
    0 0 22px rgba(255, 95, 123, 0.68),
    0 10px 32px rgba(0, 0, 0, 0.56);
  animation: dominate-text-in 0.58s 0.22s ease-out both;
}
.dominate-show-enter-active,
.dominate-show-leave-active {
  transition:
    opacity 0.34s ease,
    transform 0.34s ease;
}
.dominate-show-enter-from,
.dominate-show-leave-to {
  opacity: 0;
  transform: scale(0.96);
}
@keyframes dominate-card-in {
  0% {
    opacity: 0;
    transform: translateY(70px) scale(0.72);
  }
  62% {
    opacity: 1;
    transform: translateY(-10px) scale(1.04);
  }
  100% {
    transform: translateY(0) scale(1);
  }
}
@keyframes dominate-avatar-pulse {
  0%,
  100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.045);
  }
}
@keyframes dominate-ring {
  from {
    opacity: 0.9;
    transform: scale(0.86);
  }
  to {
    opacity: 0;
    transform: scale(1.18);
  }
}
@keyframes dominate-text-in {
  from {
    opacity: 0;
    transform: scale(0.82);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}
@keyframes dominate-stars {
  from {
    transform: translate3d(0, 0, 0) rotate(0deg);
  }
  to {
    transform: translate3d(-90px, -60px, 0) rotate(6deg);
  }
}
</style>
