<template>
  <main class="screen-player" :class="{ 'tv-shell': isAndroidTvShell }">
    <section v-if="mode === 'binding'" class="binding-page">
      <div class="brand">觅爱智慧大屏</div>
      <h1>绑定大屏设备</h1>
      <div class="device-code">{{ bootstrapInfo?.device_code || "生成中..." }}</div>
      <p>请在后台「大屏管理 > 设备管理」中输入设备码完成绑定</p>
      <el-button size="large" :loading="loading" @click="bootstrap">重新生成设备码</el-button>
    </section>

    <section v-else-if="mode === 'error'" class="binding-page">
      <div class="brand">觅爱智慧大屏</div>
      <h1>设备需要重新绑定</h1>
      <p>{{ errorMessage }}</p>
      <el-button size="large" type="primary" @click="resetAndBootstrap">重新绑定</el-button>
    </section>

    <section v-else class="wall-page">
      <header>
        <div>
          <div class="brand-title">{{ config?.title || "觅爱用户墙" }}</div>
          <div class="subtitle">扫码进入小程序查看资料</div>
        </div>
        <div class="clock">{{ nowText }}</div>
      </header>

      <div v-if="!currentItem" class="empty-state">暂无可上墙用户</div>
      <article v-else class="profile-stage">
        <div class="photo-panel">
          <img v-if="displayPhotoUrl" :key="displayPhotoUrl" :src="displayPhotoUrl" alt="" />
          <div v-else class="photo-empty">暂无照片</div>
        </div>
        <div class="info-panel">
          <div class="identity-row">
            <div>
              <h1>{{ currentItem.display_name || "觅爱用户" }}</h1>
              <div class="display-no">ID：{{ currentItem.display_no || "-" }}</div>
            </div>
            <div class="cert">{{ currentItem.certification_level_name || "未认证" }}</div>
          </div>

          <div class="info-grid">
            <div><span>年龄 / Age</span><strong>{{ currentItem.age || "-" }} 岁</strong></div>
            <div><span>身高 / Height</span><strong>{{ currentItem.height_cm || "-" }} cm</strong></div>
            <div><span>民族 / Nation</span><strong>{{ currentItem.ethnicity || "-" }}</strong></div>
            <div><span>职业 / Job</span><strong>{{ currentItem.occupation || "-" }}</strong></div>
            <div><span>年收入 / Income</span><strong>{{ currentItem.annual_income || "-" }}</strong></div>
            <div><span>婚况 / Status</span><strong>{{ currentItem.marital_status || "-" }}</strong></div>
            <div><span>学历 / Education</span><strong>{{ currentItem.education || "-" }}</strong></div>
            <div><span>籍贯 / Native</span><strong>{{ currentItem.hometown || "-" }}</strong></div>
            <div><span>常住地 / Location</span><strong>{{ currentItem.residence || "-" }}</strong></div>
          </div>

          <section class="impression">
            <div class="section-label">觅AI印象</div>
            <p :style="impressionTextStyle">{{ impressionText }}</p>
          </section>

          <div class="bottom-row">
            <div class="asset-tags">
              <span>🏠 {{ currentItem.house_status || "住房待补充" }}</span>
              <span>🚗 {{ currentItem.car_status || "车辆待补充" }}</span>
            </div>

            <div class="qr-row" :class="{ 'has-qr': !!currentItem.qrcode_url }">
              <div>
                <div class="section-label">扫码获取联系方式</div>
                <p>查看更多资料 / 申请认识</p>
              </div>
              <img v-if="currentItem.qrcode_url" class="qr" :src="currentItem.qrcode_url" alt="小程序码" />
              <div v-else class="qr qr-empty">待生成</div>
            </div>
          </div>
        </div>
      </article>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import ScreenAPI, { type ScreenBootstrapResult, type ScreenUserWallConfig, type ScreenUserWallItem } from "@/api/module_screen/screen";
import { ossImage } from "@/utils/ossImage";

const WALL_REFRESH_SECONDS = 60;
const BOOTSTRAP_KEY = "screen_bootstrap_info";

const loading = ref(false);
const mode = ref<"binding" | "playing" | "error">("binding");
const bootstrapInfo = ref<ScreenBootstrapResult>();
const config = ref<ScreenUserWallConfig>();
const items = ref<ScreenUserWallItem[]>([]);
const currentIndex = ref(0);
const photoIndex = ref(0);
const nowText = ref("");
const errorMessage = ref("");
const displayPhotoUrl = ref("");
let bindTimer = 0;
let userTimer = 0;
let photoTimer = 0;
let refreshTimer = 0;
let clockTimer = 0;
let heartbeatTimer = 0;
let photoDebounceTimer = 0;

const currentItem = computed(() => items.value[currentIndex.value]);
const isAndroidTvShell = computed(() => navigator.userAgent.includes("MiaiTvShell"));
const currentPhoto = computed(() => {
  const photos = currentItem.value?.photos || [];
  return photos[photoIndex.value % Math.max(photos.length, 1)] || currentItem.value?.avatar_url || "";
});
const impressionText = computed(() => currentItem.value?.miai_impression || currentItem.value?.matchmaker_impression || "真诚认识，从一次轻松交流开始。");
const impressionTextStyle = computed(() => {
  const length = impressionText.value.length;
  if (length > 260) return { fontSize: "18px", lineHeight: "1.42" };
  if (length > 190) return { fontSize: "20px", lineHeight: "1.45" };
  if (length > 130) return { fontSize: "22px", lineHeight: "1.48" };
  return { fontSize: "24px", lineHeight: "1.55" };
});

function clearTimer(id: number) {
  if (id) window.clearInterval(id);
}

function clearAllTimers() {
  [bindTimer, userTimer, photoTimer, refreshTimer, clockTimer, heartbeatTimer, photoDebounceTimer].forEach(clearTimer);
  bindTimer = userTimer = photoTimer = refreshTimer = clockTimer = heartbeatTimer = photoDebounceTimer = 0;
}

function schedulePhotoUrlUpdate(url: string) {
  clearTimer(photoDebounceTimer);
  photoDebounceTimer = window.setTimeout(() => {
    displayPhotoUrl.value = url ? ossImage(url, { w: 720, h: 1080, q: 82, mode: "fill", format: "webp" }) : "";
  }, 120);
}

function saveBootstrapInfo(info: ScreenBootstrapResult) {
  localStorage.setItem(BOOTSTRAP_KEY, JSON.stringify(info));
}

function loadBootstrapInfo() {
  const raw = localStorage.getItem(BOOTSTRAP_KEY);
  if (!raw) return undefined;
  try {
    return JSON.parse(raw) as ScreenBootstrapResult;
  } catch {
    localStorage.removeItem(BOOTSTRAP_KEY);
    return undefined;
  }
}

function clearBootstrapInfo() {
  localStorage.removeItem(BOOTSTRAP_KEY);
}

function syncTokenToNative(token: string) {
  const bridge = (window as any).MiaiTvShell;
  if (bridge?.saveDeviceToken) bridge.saveDeviceToken(token);
}

function clearNativeToken() {
  const bridge = (window as any).MiaiTvShell;
  if (bridge?.clearDeviceToken) bridge.clearDeviceToken();
}

function saveDeviceToken(token: string) {
  localStorage.setItem(ScreenAPI.tokenKey, token);
  syncTokenToNative(token);
}

function removeDeviceToken() {
  localStorage.removeItem(ScreenAPI.tokenKey);
  clearNativeToken();
}

async function bootstrap() {
  loading.value = true;
  try {
    const res = await ScreenAPI.bootstrap({ device_type: isAndroidTvShell.value ? "android_tv" : "web", system_info: { userAgent: navigator.userAgent } });
    bootstrapInfo.value = res.data.data;
    saveBootstrapInfo(res.data.data);
    mode.value = "binding";
    startBindPolling();
  } finally {
    loading.value = false;
  }
}

function resumeBinding(info: ScreenBootstrapResult) {
  bootstrapInfo.value = info;
  mode.value = "binding";
  startBindPolling();
}

function startBindPolling() {
  clearTimer(bindTimer);
  bindTimer = window.setInterval(async () => {
    if (!bootstrapInfo.value?.device_code) return;
    try {
      const res = await ScreenAPI.bindStatus(bootstrapInfo.value.device_code);
      const data = res.data.data;
      if (data.device_token) {
        saveDeviceToken(data.device_token);
        clearBootstrapInfo();
        clearTimer(bindTimer);
        await enterPlayer();
      }
    } catch {
      clearTimer(bindTimer);
      clearBootstrapInfo();
      await bootstrap();
    }
  }, 3000);
}

async function enterPlayer() {
  try {
    const [configRes, wallRes] = await Promise.all([ScreenAPI.playerConfig(), ScreenAPI.playerUserWall()]);
    config.value = configRes.data.data.user_wall;
    items.value = wallRes.data.data.items || [];
    currentIndex.value = 0;
    photoIndex.value = 0;
    mode.value = "playing";
    startPlaybackTimers();
    await ScreenAPI.heartbeat({ app_version: isAndroidTvShell.value ? "android_tv" : "web", system_info: { userAgent: navigator.userAgent } });
  } catch (error) {
    removeDeviceToken();
    errorMessage.value = error instanceof Error ? error.message : "设备授权已失效";
    mode.value = "error";
  }
}

function startPlaybackTimers() {
  clearTimer(userTimer);
  clearTimer(photoTimer);
  clearTimer(refreshTimer);
  clearTimer(heartbeatTimer);
  const userSeconds = config.value?.user_switch_seconds || 12;
  const photoSeconds = config.value?.photo_switch_seconds || 4;
  userTimer = window.setInterval(nextUser, userSeconds * 1000);
  photoTimer = window.setInterval(() => {
    photoIndex.value += 1;
  }, photoSeconds * 1000);
  refreshTimer = window.setInterval(refreshWall, WALL_REFRESH_SECONDS * 1000);
  heartbeatTimer = window.setInterval(() => {
    ScreenAPI.heartbeat({ app_version: isAndroidTvShell.value ? "android_tv" : "web", system_info: { userAgent: navigator.userAgent } }).catch(() => {
      mode.value = "error";
      errorMessage.value = "设备授权已失效或已被禁用";
      removeDeviceToken();
      clearAllTimers();
    });
  }, 30000);
}

async function nextUser() {
  const item = currentItem.value;
  if (item) {
    ScreenAPI.recordUserWall({
      person_id: item.person_id,
      user_id: item.user_id,
      display_no: item.display_no,
      display_snapshot: item,
      duration_seconds: config.value?.user_switch_seconds,
      play_result: "success",
    }).catch(() => undefined);
  }
  if (!items.value.length) return;
  currentIndex.value = (currentIndex.value + 1) % items.value.length;
  photoIndex.value = 0;
}

async function refreshWall() {
  const current = currentItem.value;
  const [configRes, wallRes] = await Promise.all([ScreenAPI.playerConfig(), ScreenAPI.playerUserWall()]);
  config.value = configRes.data.data.user_wall;
  items.value = wallRes.data.data.items || [];
  if (current) {
    const nextIndex = items.value.findIndex((item) => item.person_id === current.person_id);
    if (nextIndex >= 0) {
      currentIndex.value = nextIndex;
      startPlaybackTimers();
      return;
    }
  }
  if (currentIndex.value >= items.value.length) {
    currentIndex.value = 0;
    photoIndex.value = 0;
  }
  startPlaybackTimers();
}

function tickClock() {
  nowText.value = new Date().toLocaleString("zh-CN", { hour12: false });
}

function handleTvConfirm() {
  if (mode.value === "binding" && !loading.value) {
    bootstrap();
    return;
  }
  if (mode.value === "error") {
    resetAndBootstrap();
  }
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key !== "Enter") return;
  handleTvConfirm();
}

function handleNativeTvConfirm() {
  handleTvConfirm();
}

async function resetAndBootstrap() {
  removeDeviceToken();
  clearBootstrapInfo();
  await bootstrap();
}

onMounted(async () => {
  tickClock();
  clockTimer = window.setInterval(tickClock, 1000);
  const pendingBootstrap = loadBootstrapInfo();
  const storedToken = localStorage.getItem(ScreenAPI.tokenKey);
  if (storedToken) {
    syncTokenToNative(storedToken);
    await enterPlayer();
  } else if (pendingBootstrap) resumeBinding(pendingBootstrap);
  else await bootstrap();
  window.addEventListener("keydown", handleKeydown);
  window.addEventListener("miai-tv-confirm", handleNativeTvConfirm);
});

watch(currentPhoto, schedulePhotoUrlUpdate, { immediate: true });

onBeforeUnmount(() => {
  window.removeEventListener("keydown", handleKeydown);
  window.removeEventListener("miai-tv-confirm", handleNativeTvConfirm);
  clearAllTimers();
});
</script>

<style scoped>
.screen-player { width: 100vw; height: 100vh; overflow: hidden; background: #fff; color: #2f3338; }
.binding-page { width: 100%; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 28px; text-align: center; background: #f8f3f4; color: #2f3338; }
.brand { font-size: 28px; color: #f05d7b; }
.binding-page h1 { margin: 0; font-size: 56px; font-weight: 700; }
.device-code { padding: 24px 42px; border: 2px solid rgba(240, 93, 123, 0.38); border-radius: 8px; font-size: 72px; font-weight: 800; letter-spacing: 6px; color: #2f3338; background: #fff; }
.binding-page p { margin: 0; font-size: 24px; color: #6f7782; }
.wall-page { box-sizing: border-box; width: 100%; height: 100%; padding: 0; background: linear-gradient(90deg, #ffffff 0%, #ffffff 74%, #fff6f7 100%); }
header { display: none; }
.empty-state { display: flex; align-items: center; justify-content: center; width: 100%; height: 100%; color: #9aa1aa; font-size: 36px; }
.profile-stage { display: grid; grid-template-columns: 30vw minmax(0, 1fr); width: 100%; height: 100vh; }
.photo-panel { width: 100%; height: 100%; overflow: hidden; background: #f3f4f6; }
.photo-panel img, .photo-empty { width: 100%; height: 100%; object-fit: cover; object-position: center center; background: #f3f4f6; }
.photo-panel img { animation: photo-fade-in 720ms ease-out both; will-change: opacity, transform; }
.photo-empty { display: flex; align-items: center; justify-content: center; color: #9aa1aa; font-size: 32px; }
.info-panel { position: relative; display: grid; grid-template-rows: auto auto minmax(178px, auto) minmax(170px, 1fr); row-gap: 34px; min-width: 0; height: 100vh; padding: 60px 96px 34px; box-sizing: border-box; }
.identity-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 28px; padding-bottom: 28px; border-bottom: 1px solid #eceff2; }
.identity-row > div:first-child { display: flex; align-items: center; min-width: 0; gap: 30px; }
.identity-row h1 { margin: 0; max-width: 420px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #2b2f33; font-size: 56px; line-height: 1; font-weight: 800; letter-spacing: 0; }
.display-no { flex: 0 0 auto; padding: 10px 24px; border-radius: 5px; background: #eef0f3; color: #707783; font-family: Georgia, "Times New Roman", serif; font-size: 24px; font-weight: 700; }
.cert { flex: 0 0 auto; min-width: 150px; padding: 16px 24px; border-radius: 999px; color: #fff; background: #9ca1a8; box-shadow: 0 14px 28px rgba(120, 124, 130, 0.25); text-align: center; font-size: 24px; font-weight: 800; }
.info-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); column-gap: 80px; row-gap: 34px; align-content: start; }
.info-grid div { min-width: 0; padding-left: 16px; border-left: 4px solid #eef0f2; }
.info-grid span, .section-label { display: block; color: #8b929d; font-size: 20px; line-height: 1.2; }
.info-grid strong { display: block; margin-top: 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #2d333a; font-size: 34px; line-height: 1.15; font-weight: 800; }
.info-grid div:nth-child(4) { border-left-color: #ff6680; }
.info-grid div:nth-child(5) { border-left-color: #ff6680; }
.impression { align-self: start; min-height: 178px; max-height: 258px; padding: 28px 32px; border-radius: 8px; background: #f5f6f8; overflow: hidden; box-sizing: border-box; }
.impression .section-label { color: #ff6680; font-size: 22px; font-weight: 800; }
.impression .section-label::before { content: "♥ "; }
.impression p { margin: 16px 0 0; color: #34404c; }
.bottom-row { display: flex; align-items: flex-end; justify-content: space-between; gap: 28px; min-width: 0; }
.qr-row { flex: 0 0 auto; display: flex; align-items: center; gap: 24px; width: 360px; height: 134px; padding: 16px 20px; border: 1px solid #f0f1f3; border-radius: 12px; background: #fff; box-shadow: 0 14px 34px rgba(36, 42, 50, 0.08); box-sizing: border-box; }
.qr-row .section-label { color: #2f3338; font-size: 24px; font-weight: 800; white-space: nowrap; }
.qr-row p { margin: 8px 0 0; color: #8b929d; font-size: 15px; line-height: 1.3; }
.qr { flex: 0 0 auto; width: 98px; height: 98px; border: 4px solid #fff; background: #fff; object-fit: cover; }
.qr-empty { display: flex; align-items: center; justify-content: center; color: #8b929d; border: 1px solid #e6e8eb; font-size: 18px; }
.asset-tags { display: flex; gap: 38px; min-width: 0; flex-wrap: wrap; }
.asset-tags span { min-width: 160px; padding: 14px 26px; border-radius: 7px; background: #ffeef2; color: #ff5474; text-align: center; font-size: 24px; font-weight: 800; box-sizing: border-box; }
@keyframes photo-fade-in {
  from { opacity: 0; transform: scale(1.025); }
  to { opacity: 1; transform: scale(1); }
}
@media (max-width: 1366px) {
  .profile-stage { grid-template-columns: 32vw minmax(0, 1fr); }
  .info-panel { row-gap: 22px; padding: 42px 56px 28px; grid-template-rows: auto auto minmax(150px, auto) minmax(136px, 1fr); }
  .identity-row h1 { font-size: 44px; }
  .display-no { font-size: 18px; padding: 8px 16px; }
  .cert { min-width: 128px; padding: 12px 18px; font-size: 20px; }
  .info-grid { column-gap: 42px; row-gap: 24px; }
  .info-grid strong { font-size: 26px; }
  .info-grid span, .section-label { font-size: 17px; }
  .impression { min-height: 150px; max-height: 210px; padding: 22px 28px; }
  .qr-row { width: 320px; height: 118px; }
  .qr { width: 84px; height: 84px; }
  .asset-tags span { min-width: 130px; font-size: 20px; }
}
@media (max-height: 700px) {
  .tv-shell .profile-stage { grid-template-columns: 32vw minmax(0, 1fr); }
  .tv-shell .info-panel { row-gap: 10px; padding: 22px 40px 14px; grid-template-rows: auto auto 132px 86px; }
  .tv-shell .identity-row { gap: 16px; padding-bottom: 12px; }
  .identity-row > div:first-child { gap: 18px; }
  .tv-shell .identity-row h1 { max-width: 210px; font-size: 36px; }
  .tv-shell .display-no { padding: 7px 14px; font-size: 16px; }
  .tv-shell .cert { min-width: 104px; padding: 10px 16px; font-size: 18px; }
  .tv-shell .info-grid { column-gap: 28px; row-gap: 13px; }
  .tv-shell .info-grid div { padding-left: 12px; border-left-width: 3px; }
  .tv-shell .info-grid span, .tv-shell .section-label { font-size: 14px; }
  .tv-shell .info-grid strong { margin-top: 4px; font-size: 23px; }
  .tv-shell .impression { min-height: 0; max-height: none; height: 132px; padding: 14px 22px; }
  .tv-shell .impression .section-label { font-size: 18px; }
  .tv-shell .impression p { display: -webkit-box; margin-top: 8px; overflow: hidden; -webkit-line-clamp: 3; -webkit-box-orient: vertical; font-size: 17px !important; line-height: 1.34 !important; }
  .tv-shell .bottom-row { align-items: flex-end; gap: 14px; }
  .tv-shell .qr-row { gap: 12px; width: 256px; height: 84px; padding: 9px 12px; border-radius: 8px; }
  .tv-shell .qr-row .section-label { font-size: 17px; }
  .tv-shell .qr-row p { margin-top: 4px; font-size: 12px; }
  .tv-shell .qr { width: 64px; height: 64px; border-width: 3px; }
  .tv-shell .asset-tags { gap: 16px; max-width: calc(100% - 270px); }
  .tv-shell .asset-tags span { min-width: 124px; padding: 9px 14px; font-size: 17px; white-space: nowrap; }
}
@media (max-height: 560px) {
  .tv-shell .profile-stage { grid-template-columns: 31vw minmax(0, 1fr); }
  .tv-shell .info-panel { row-gap: 8px; padding: 20px 36px 10px; grid-template-rows: auto auto 118px 78px; }
  .tv-shell .identity-row h1 { font-size: 34px; }
  .tv-shell .info-grid { row-gap: 10px; }
  .tv-shell .info-grid span, .tv-shell .section-label { font-size: 13px; }
  .tv-shell .info-grid strong { font-size: 21px; }
  .tv-shell .impression { height: 118px; padding: 12px 20px; }
  .tv-shell .impression p { -webkit-line-clamp: 3; font-size: 15px !important; line-height: 1.32 !important; }
  .tv-shell .qr-row { width: 246px; height: 78px; }
  .tv-shell .qr { width: 58px; height: 58px; }
  .tv-shell .asset-tags { max-width: calc(100% - 258px); }
  .tv-shell .asset-tags span { min-width: 118px; padding: 8px 12px; font-size: 16px; }
}
@media (min-width: 2200px) and (min-height: 1200px) {
  .info-panel { padding: 84px 132px 52px; row-gap: 48px; }
  .identity-row h1 { max-width: 620px; font-size: 76px; }
  .display-no { font-size: 32px; }
  .cert { min-width: 210px; font-size: 34px; }
  .info-grid span, .section-label { font-size: 28px; }
  .info-grid strong { font-size: 48px; }
  .impression .section-label { font-size: 32px; }
  .qr-row { width: 500px; height: 186px; }
  .qr-row .section-label { font-size: 34px; }
  .qr-row p { font-size: 22px; }
  .qr { width: 138px; height: 138px; }
  .asset-tags span { min-width: 220px; font-size: 34px; }
}
</style>
