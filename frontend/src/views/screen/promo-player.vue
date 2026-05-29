<template>
  <main class="promo-player">
    <section v-if="mode === 'loading'" class="state">
      <div class="state-brand">觅爱智慧大屏</div>
      <h1>宣传大屏</h1>
      <p>正在同步播放内容...</p>
    </section>

    <section v-else-if="mode === 'error'" class="state">
      <div class="state-brand">觅爱智慧大屏</div>
      <h1>宣传大屏暂不可用</h1>
      <p>{{ errorMessage }}</p>
      <el-button size="large" type="primary" @click="load">重试</el-button>
    </section>

    <section v-else-if="!currentItem" class="state">
      <div class="state-brand">觅爱智慧大屏</div>
      <h1>暂无宣传内容</h1>
      <p>请在后台配置宣传图片、视频或上墙员工。</p>
    </section>

    <section v-else class="stage" :class="`stage-${currentItem.item_type}`">
      <div v-if="currentItem.item_type !== 'staff'" class="media-shell">
        <video v-if="currentItem.item_type === 'video' && currentItem.file_url" :key="currentItem.id" class="media" :src="currentItem.file_url" autoplay muted playsinline @ended="next" />
        <Transition v-else-if="currentItem.item_type === 'image' && displayMediaImageUrl" name="promo-image" mode="out-in">
          <img :key="displayMediaImageUrl" class="media" :src="displayMediaImageUrl" alt="" />
        </Transition>
        <div class="media-caption">
          <span>{{ currentItem.item_type === "video" ? "宣传视频" : "宣传海报" }}</span>
          <strong>{{ currentItem.title }}</strong>
        </div>
      </div>
      <article v-else-if="currentItem.item_type === 'staff' && currentItem.staff" class="staff-card">
        <div class="staff-photo-wrap">
          <div class="staff-photo">
            <Transition v-if="displayStaffAvatarUrl" name="promo-image" mode="out-in">
              <img :key="displayStaffAvatarUrl" :src="displayStaffAvatarUrl" alt="" />
            </Transition>
            <div v-else>{{ currentItem.staff.display_name.slice(0, 1) }}</div>
          </div>
        </div>
        <div class="staff-info">
          <div class="staff-top">
            <div class="staff-kicker">MATCHMAKER PROFILE</div>
            <div class="staff-header">
              <h1>{{ currentItem.staff.display_name }}</h1>
              <span v-if="currentItem.staff.role_title">{{ currentItem.staff.role_title }}</span>
            </div>
            <div class="staff-subtitle">
              专注婚恋服务 <strong>{{ currentItem.staff.years_experience || "-" }}</strong> 年
            </div>
            <div class="staff-line"></div>
          </div>

          <section class="staff-section specialty-section">
            <div class="section-title">擅长方向</div>
            <div class="specialty-tags">
              <span v-for="specialty in specialtiesList" :key="specialty">{{ specialty }}</span>
            </div>
          </section>

          <section class="staff-section tag-section">
            <div class="section-title">服务标签</div>
            <div class="tags">
              <b v-for="(tag, index) in currentItem.staff.public_tags" :key="tag" :class="`tag-color-${index % 5}`">{{ tag }}</b>
              <span v-if="!currentItem.staff.public_tags?.length" class="empty-mark">暂无标签</span>
            </div>
          </section>

          <section class="slogan-panel">
            <p>{{ currentItem.staff.service_slogan || "用真诚连接彼此，用专业守护每一次相遇。" }}</p>
          </section>
        </div>
      </article>
      <div class="progress">
        <span v-for="(item, index) in items" :key="item.id" :class="{ active: index === currentIndex }"></span>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

import ScreenAPI, { type ScreenPromoItem, type ScreenPromoPlayerPayload } from "@/api/module_screen/screen";
import { ossImage } from "@/utils/ossImage";

const mode = ref<"loading" | "playing" | "error">("loading");
const errorMessage = ref("");
const payload = ref<ScreenPromoPlayerPayload>();
const currentIndex = ref(0);
const displayMediaImageUrl = ref("");
const displayStaffAvatarUrl = ref("");
let timer = 0;
let imageDebounceTimer = 0;
let staffAvatarDebounceTimer = 0;

const items = computed(() => payload.value?.items || []);
const currentItem = computed(() => items.value[currentIndex.value]);
const staffMeta = computed(() => {
  const staff = currentItem.value?.staff;
  if (!staff) return "";
  return [staff.role_title, staff.years_experience ? `${staff.years_experience}年从业经验` : ""].filter(Boolean).join(" / ");
});
const specialtiesList = computed(() => {
  const source = currentItem.value?.staff?.specialties;
  if (Array.isArray(source)) return source.filter(Boolean);
  const text = source || "";
  const parts = text
    .split(/[、,，;；\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
  return parts.length ? parts : ["情感关系深度咨询与辅导", "婚前心态建设与形象定制", "家庭背景与价值观契合度分析", "高知人群精准匹配"];
});

async function load() {
  window.clearTimeout(timer);
  mode.value = "loading";
  try {
    const res = await ScreenAPI.playerPromo();
    payload.value = res.data.data;
    currentIndex.value = 0;
    mode.value = "playing";
    schedule();
  } catch (error: any) {
    errorMessage.value = error?.message || "请先完成大屏设备绑定，或检查宣传大屏配置。";
    mode.value = "error";
  }
}

function next() {
  if (!items.value.length) return;
  currentIndex.value = (currentIndex.value + 1) % items.value.length;
}

function schedule() {
  window.clearTimeout(timer);
  const item = currentItem.value;
  scheduleImageDisplay(item);
  if (!item || item.item_type === "video") return;
  const seconds = item.duration_seconds || (item.item_type === "staff" ? payload.value?.config.staff_duration_seconds : payload.value?.config.image_duration_seconds) || 8;
  timer = window.setTimeout(next, seconds * 1000);
}

function scheduleImageDisplay(item?: ScreenPromoItem) {
  window.clearTimeout(imageDebounceTimer);
  window.clearTimeout(staffAvatarDebounceTimer);
  imageDebounceTimer = window.setTimeout(() => {
    displayMediaImageUrl.value = item?.item_type === "image" && item.file_url ? ossImage(item.file_url, { w: 1920, h: 1080, q: 86, mode: "lfit", format: "webp" }) : "";
  }, 120);
  staffAvatarDebounceTimer = window.setTimeout(() => {
    const avatar = item?.item_type === "staff" ? item.staff?.avatar_url : "";
    displayStaffAvatarUrl.value = avatar ? ossImage(avatar, { w: 920, h: 1440, q: 84, mode: "fill", format: "webp" }) : "";
  }, 120);
}

watch(currentItem, schedule);
onMounted(load);
onBeforeUnmount(() => {
  window.clearTimeout(timer);
  window.clearTimeout(imageDebounceTimer);
  window.clearTimeout(staffAvatarDebounceTimer);
});
</script>

<style scoped>
.promo-player {
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background:
    linear-gradient(135deg, rgba(255, 88, 118, 0.10), transparent 38%),
    linear-gradient(225deg, rgba(18, 28, 45, 0.12), transparent 42%),
    #f7f8fb;
  color: #fff;
  font-family: Inter, "PingFang SC", "Microsoft YaHei", sans-serif;
}
.state {
  display: flex;
  width: 100%;
  height: 100%;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  background:
    linear-gradient(135deg, rgba(255, 88, 118, 0.18), transparent 34%),
    linear-gradient(225deg, rgba(24, 34, 52, 0.22), transparent 44%),
    #111827;
}
.state-brand {
  margin-bottom: 18px;
  color: #ff7a92;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 0;
}
.state h1 { margin: 0 0 18px; font-size: 56px; font-weight: 800; }
.state p { margin: 0 0 28px; color: #cbd5e1; font-size: 24px; }
.stage { width: 100%; height: 100%; }
.media-shell {
  position: relative;
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;
  background: #05070b;
}
.media {
  width: 100%;
  height: 100%;
  object-fit: cover;
  background: #000;
}
.promo-image-enter-active,
.promo-image-leave-active {
  transition:
    opacity 520ms ease,
    transform 520ms ease,
    filter 520ms ease;
}
.promo-image-enter-from {
  opacity: 0;
  transform: scale(1.025);
  filter: blur(6px);
}
.promo-image-leave-to {
  opacity: 0;
  transform: scale(0.99);
  filter: blur(3px);
}
.stage-image .media { object-fit: contain; background: #0b0f17; }
.media-caption {
  position: absolute;
  left: 56px;
  bottom: 48px;
  min-width: 320px;
  max-width: min(760px, 58vw);
  border-left: 5px solid #ff5876;
  padding: 4px 0 6px 24px;
  color: #fff;
  text-shadow: 0 2px 18px rgba(0, 0, 0, 0.35);
}
.media-caption span {
  display: block;
  margin-bottom: 8px;
  color: rgba(255, 255, 255, 0.72);
  font-size: 18px;
}
.media-caption strong {
  display: block;
  font-size: 40px;
  line-height: 1.18;
}
.staff-card {
  display: grid;
  width: 100%;
  height: 100%;
  grid-template-columns: 43vw 1fr;
  gap: 4vw;
  align-items: stretch;
  padding: 0 4vw 0 0;
  background:
    linear-gradient(90deg, rgba(255, 255, 255, 0.98) 0%, rgba(255, 255, 255, 0.92) 42%, rgba(255, 246, 248, 0.86) 100%),
    #f8fafc;
  color: #20252d;
}
.staff-photo-wrap {
  position: relative;
  height: 100vh;
  min-height: 0;
}
.staff-photo {
  width: 100%;
  height: 100%;
  overflow: hidden;
  border-radius: 0;
  background: #e5e7eb;
  box-shadow: 0 28px 80px rgba(32, 37, 45, 0.16);
}
.staff-photo img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.staff-photo div {
  display: flex;
  width: 100%;
  height: 100%;
  align-items: center;
  justify-content: center;
  font-size: 120px;
  font-weight: 700;
  color: #94a3b8;
}
.staff-info {
  display: grid;
  grid-template-rows: 28vh 18vh 16vh 26vh;
  align-content: stretch;
  min-width: 0;
  padding: 6vh 0 6vh;
}
.staff-top { min-height: 0; }
.staff-kicker {
  color: #8c97a8;
  font-size: clamp(17px, 1.05vw, 22px);
  font-weight: 900;
  letter-spacing: 3px;
}
.staff-header {
  display: flex;
  align-items: flex-end;
  gap: 20px;
  margin-top: 14px;
}
.staff-header h1 {
  margin: 0;
  color: #20252d;
  font-size: clamp(64px, 5.6vw, 112px);
  line-height: 0.98;
  font-weight: 950;
}
.staff-header span {
  margin-bottom: 10px;
  border-radius: 999px;
  background: #2f3744;
  color: #fff;
  padding: 9px 18px;
  font-size: clamp(18px, 1.2vw, 26px);
  font-weight: 800;
}
.staff-subtitle {
  margin-top: 20px;
  color: #697386;
  font-size: clamp(24px, 1.65vw, 34px);
}
.staff-subtitle strong {
  color: #ff5876;
  font-size: 1.22em;
}
.staff-line {
  width: 100%;
  height: 1px;
  margin: 34px 0 0;
  background: linear-gradient(90deg, rgba(255, 88, 118, 0.5), rgba(148, 163, 184, 0.15));
}
.staff-section { min-height: 0; overflow: hidden; }
.section-title {
  color: #2f3744;
  font-size: clamp(23px, 1.55vw, 32px);
  font-weight: 900;
  margin-bottom: 18px;
}
.specialty-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
}
.specialty-tags span {
  border-radius: 7px;
  background: #fff0f3;
  color: #ff5876;
  padding: 12px 18px;
  font-size: clamp(20px, 1.22vw, 26px);
  font-weight: 800;
  line-height: 1.2;
}
.tags { display: flex; flex-wrap: wrap; gap: 14px; }
.tags b {
  border-radius: 7px;
  background: #f3f5f8;
  color: #697386;
  padding: 12px 18px;
  font-size: clamp(20px, 1.22vw, 26px);
}
.tags b.tag-color-0 { background: #ffe7ed; color: #df6270; }
.tags b.tag-color-1 { background: #fff0dc; color: #d89142; }
.tags b.tag-color-2 { background: #e9f8ec; color: #4fa765; }
.tags b.tag-color-3 { background: #fff1f4; color: #d65b6a; }
.tags b.tag-color-4 { background: #fff3df; color: #de8a3f; }
.empty-mark {
  color: #a8b0bd;
  font-size: clamp(20px, 1.22vw, 26px);
}
.slogan-panel {
  border-radius: 10px;
  background: #f4f6f9;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 0;
  padding: 22px 36px;
}
.slogan-panel p {
  margin: 0;
  color: #2f3744;
  font-size: clamp(20px, 1.22vw, 26px);
  line-height: 1.5;
  text-align: center;
  white-space: pre-line;
}
.progress {
  position: absolute;
  right: 42px;
  bottom: 34px;
  display: flex;
  gap: 8px;
}
.progress span {
  width: 28px;
  height: 5px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.42);
}
.progress span.active {
  width: 58px;
  background: #ff5876;
}
</style>
