<template>
  <div class="auth-view" :style="{ '--login-background-url': `url(${loginBackgroundUrl})` }">
    <div class="auth-view__wrapper">
      <section class="auth-feature">
        <div class="auth-feature__brand">
          <div class="auth-feature__mark">觅</div>
          <div>
            <p>高端婚恋会员运营系统</p>
            <span>MI AI MEMBER CARE</span>
          </div>
        </div>
        <div class="auth-feature__badge">STAFF PORTAL · MEMBER CARE</div>
        <h1 class="auth-feature__title">把每一次相遇，交给更专业的服务流程。</h1>
        <p class="auth-feature__subtitle">
          会员画像、匹配线索、红娘跟进与实名认证统一沉淀，让门店服务节奏清晰、客户经营更稳。
        </p>

        <div class="auth-orbit" aria-hidden="true">
          <span class="auth-orbit__ring auth-orbit__ring--one" />
          <span class="auth-orbit__ring auth-orbit__ring--two" />
          <span class="auth-orbit__dot auth-orbit__dot--one" />
          <span class="auth-orbit__dot auth-orbit__dot--two" />
          <span class="auth-orbit__core">AI</span>
        </div>

        <div class="auth-feature__insights">
          <article>
            <span>全链路会员运营</span>
            <p>线索、建档、合同、服务计划与跟进记录统一沉淀。</p>
          </article>
          <article>
            <span>智能匹配辅助</span>
            <p>结合会员画像与择偶偏好，帮助红娘更快筛选候选人。</p>
          </article>
          <article>
            <span>门店协同管控</span>
            <p>围绕门店、角色和权限管理客户资源与服务流程。</p>
          </article>
        </div>
      </section>

      <section class="auth-panel">
        <transition name="fade-slide" mode="out-in">
          <component
            :is="formComponents[component]"
            v-model="component"
            v-model:preset-username="loginPreset.username"
            v-model:preset-password="loginPreset.password"
            class="auth-panel__form"
          />
        </transition>

        <footer class="auth-panel__footer">
          <el-text size="small">
            <a :href="configStore.configData?.sys_git_code?.config_value || ''" target="_blank">
              {{ configStore.configData?.sys_web_copyright?.config_value || "" }}
            </a>
            |
            <a :href="configStore.configData?.sys_help_doc?.config_value || ''" target="_blank">
              帮助
            </a>
            |
            <a :href="configStore.configData?.sys_web_privacy?.config_value || ''" target="_blank">
              隐私
            </a>
            |
            <a :href="configStore.configData?.sys_web_clause?.config_value || ''" target="_blank">
              条款
            </a>
            {{ configStore.configData?.sys_keep_record?.config_value || "" }}
          </el-text>
        </footer>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
// import logo from "@/assets/logo.png";
// import { defaultSettings } from "@/settings";
import { useConfigStore } from "@/store";

const configStore = useConfigStore();

// 添加计算属性处理背景图片URL
const loginBackgroundUrl = computed(() => {
  // 使用可选链操作符确保安全访问
  return (
    configStore.configData?.sys_login_background?.config_value ||
    new URL("@/assets/images/login-bg.svg", import.meta.url).href
  );
});

type LayoutMap = "login" | "register" | "resetPwd";

const component = ref<LayoutMap>("login"); // 切换显示的组件
const formComponents = {
  login: defineAsyncComponent(() => import("./components/Login.vue")),
  register: defineAsyncComponent(() => import("./components/Register.vue")),
  resetPwd: defineAsyncComponent(() => import("./components/ResetPwd.vue")),
};

// 预填登录信息（通过具名 v-model 双向绑定传递）
const loginPreset = reactive<{ username: string; password: string }>({
  username: "admin",
  password: "123456",
});

let notificationInstance: ReturnType<typeof ElNotification> | null = null;

const showVoteNotification = () => {
  notificationInstance = ElNotification({
    title: "⭐ FastapiAdmin 完全开源 · 期待您的 Star 支持 🙏",
    message: `项目持续迭代中，若对您有所帮助，欢迎点亮 Star 支持！
    <br/><a href="https://github.com/fastapiadmin/FastapiAdmin" target="_blank" style="color: var(--el-color-primary); text-decoration: none; font-weight: 500;">Github仓库 →</a>
    <br/><a href="https://gitee.com/fastapiadmin/FastapiAdmin" target="_blank" style="color: var(--el-color-warning); text-decoration: none; font-weight: 500;">Gitee仓库 →</a>`,
    type: "success",
    position: "bottom-left",
    duration: 0,
    dangerouslyUseHTMLString: true,
  });
};

// onMounted(() => {
//   setTimeout(showVoteNotification, 500);
// });

onBeforeUnmount(() => {
  if (notificationInstance) {
    notificationInstance.close();
    notificationInstance = null;
  }
});
</script>

<style lang="scss" scoped>
.auth-view {
  --miai-bg: oklch(98% 0.012 55);
  --miai-surface: oklch(100% 0 0);
  --miai-fg: oklch(22% 0.028 255);
  --miai-muted: oklch(50% 0.018 255);
  --miai-border: oklch(90% 0.016 55);
  --miai-accent: oklch(63% 0.14 18);
  --miai-accent-soft: oklch(94% 0.04 18);
  --miai-gold: oklch(75% 0.09 78);
  --miai-rose-deep: oklch(42% 0.09 18);
  --miai-ink-soft: oklch(33% 0.025 255);
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  min-height: 100vh;
  padding: clamp(18px, 4vw, 48px);
  overflow: hidden;
  color: var(--miai-fg);
  font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", "Segoe UI",
    system-ui, sans-serif;
  background:
    radial-gradient(circle at 14% 18%, oklch(95% 0.045 18) 0 18rem, transparent 31rem),
    radial-gradient(circle at 86% 12%, oklch(95% 0.035 78) 0 14rem, transparent 28rem),
    linear-gradient(135deg, var(--miai-bg), oklch(96% 0.018 45));

  &::before {
    position: fixed;
    inset: 0;
    z-index: -2;
    content: "";
    background: var(--login-background-url) center/cover no-repeat;
    opacity: 0.05;
  }

  &::after {
    position: fixed;
    inset: 0;
    z-index: -1;
    pointer-events: none;
    content: "";
    background: transparent;
  }
}

.auth-view__wrapper {
  display: grid;
  flex: 1;
  grid-template-columns: minmax(0, 1.05fr) minmax(360px, 0.78fr);
  gap: 0;
  align-items: stretch;
  width: min(1180px, 100%);
  min-height: min(760px, calc(100vh - 48px));
  margin: auto;
  overflow: hidden;
  background: color-mix(in oklch, var(--miai-surface), transparent 4%);
  border: 1px solid color-mix(in oklch, var(--miai-border), white 25%);
  border-radius: 32px;
  box-shadow: 0 30px 80px color-mix(in oklch, var(--miai-fg), transparent 88%);
}

.auth-feature {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: auto;
  padding: clamp(32px, 5vw, 64px);
  color: var(--miai-fg);
  background:
    linear-gradient(
      160deg,
      color-mix(in oklch, var(--miai-surface), transparent 5%),
      color-mix(in oklch, var(--miai-accent-soft), transparent 18%)
    ),
    radial-gradient(
      circle at 70% 34%,
      color-mix(in oklch, var(--miai-accent), transparent 84%),
      transparent 24rem
    );
  border-inline-end: 1px solid var(--miai-border);
  isolation: isolate;
  animation: featureFade 0.8s ease-out;

  &::before {
    position: absolute;
    inset: 9%;
    z-index: -1;
    content: "";
    border: 1px solid color-mix(in oklch, var(--miai-accent), transparent 72%);
    border-radius: 999px;
    transform: rotate(-10deg);
  }
}

@media (max-width: 768px) {
  .auth-view__wrapper {
    display: flex;
    align-items: center;
    justify-content: center;
    padding-top: 54px;
  }

  .auth-feature {
    display: none;
  }

  .auth-panel {
    width: 100%;
    margin-inline: 0;
  }
}

.auth-feature__brand {
  display: flex;
  gap: 14px;
  align-items: center;
  margin-bottom: 0;
  color: var(--miai-ink-soft);

  p {
    margin: 0 0 4px;
    font-size: 20px;
    font-weight: 700;
  }

  span {
    font-size: 13px;
    color: var(--miai-muted);
    letter-spacing: 0;
  }
}

.auth-feature__mark {
  display: grid;
  width: 48px;
  height: 48px;
  place-items: center;
  font-family: "Noto Serif SC", "Songti SC", "STSong", Georgia, serif;
  font-size: 22px;
  font-weight: 800;
  color: white;
  background: linear-gradient(135deg, var(--miai-rose-deep), var(--miai-accent));
  border-radius: 16px;
  box-shadow: inset 0 1px 0 color-mix(in oklch, white, transparent 65%);
}

.auth-feature__badge {
  display: inline-flex;
  width: fit-content;
  padding: 8px 12px;
  margin-bottom: 18px;
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
  font-size: 12px;
  font-weight: 500;
  color: var(--miai-rose-deep);
  text-transform: uppercase;
  letter-spacing: 0;
  background: color-mix(in oklch, var(--miai-accent-soft), white 22%);
  border: 1px solid color-mix(in oklch, var(--miai-accent), transparent 55%);
  border-radius: 999px;
}

.auth-feature__title {
  max-width: 670px;
  margin: 0;
  font-family: "Noto Serif SC", "Songti SC", "STSong", Georgia, serif;
  font-size: clamp(42px, 6vw, 82px);
  font-weight: 700;
  line-height: 1.03;
  letter-spacing: 0;
}

.auth-feature__subtitle {
  max-width: 560px;
  margin: 22px 0 0;
  font-size: clamp(17px, 1.45vw, 21px);
  line-height: 1.75;
  color: var(--miai-muted);
}

.auth-orbit {
  position: absolute;
  inset-block-start: 142px;
  inset-inline-end: clamp(22px, 5vw, 72px);
  width: clamp(180px, 22vw, 280px);
  aspect-ratio: 1;
  margin-top: 0;
  pointer-events: none;
  opacity: 0.92;
}

.auth-orbit__ring,
.auth-orbit__dot,
.auth-orbit__core {
  position: absolute;
  display: block;
}

.auth-orbit__ring {
  border: 1px solid color-mix(in oklch, var(--miai-accent), transparent 62%);
  border-radius: 50%;
}

.auth-orbit__ring--one {
  inset: 0;
}

.auth-orbit__ring--two {
  inset: 15%;
  border-color: color-mix(in oklch, var(--miai-gold), transparent 42%);
  transform: translate(-5%, 6%);
}

.auth-orbit__dot {
  width: 16px;
  height: 16px;
  background: var(--miai-accent);
  border: 0;
  border-radius: 50%;
  box-shadow: 0 0 0 8px color-mix(in oklch, var(--miai-accent), transparent 82%);
}

.auth-orbit__dot--one {
  top: 13%;
  right: 26%;
}

.auth-orbit__dot--two {
  bottom: 22%;
  right: 9%;
  left: auto;
  width: 12px;
  height: 12px;
  background: var(--miai-gold);
}

.auth-orbit__core {
  inset: 31%;
  display: grid;
  place-items: center;
  font-size: 26px;
  font-weight: 800;
  color: var(--miai-rose-deep);
  background: color-mix(in oklch, var(--miai-surface), transparent 12%);
  border: 1px solid color-mix(in oklch, var(--miai-accent), transparent 62%);
  border-radius: 50%;
  box-shadow: 0 12px 40px color-mix(in oklch, var(--miai-accent), transparent 86%);
}

.auth-feature__insights {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin: 0;

  article {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-width: 0;
    min-height: 126px;
    padding: 18px;
    background: color-mix(in oklch, var(--miai-surface), transparent 14%);
    border: 1px solid color-mix(in oklch, var(--miai-border), white 15%);
    border-radius: 22px;
  }

  span {
    display: block;
    font-size: 17px;
    font-weight: 800;
    color: var(--miai-fg);
  }

  p {
    margin: 12px 0 0;
    font-size: 13px;
    line-height: 1.55;
    color: var(--miai-muted);
  }
}

.auth-panel {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  justify-content: flex-start;
  justify-self: end;
  width: 100%;
  padding: clamp(28px, 4vw, 56px);
  background: color-mix(in oklch, var(--miai-surface), transparent 0%);
  animation: panelLift 0.7s ease;
}

.auth-panel__form {
  width: 100%;
  max-width: 100%;
  margin-inline: auto;

  :deep(.el-form-item) {
    margin-bottom: 1rem;
  }

  :deep(.el-input__wrapper) {
    min-height: 54px;
    background: oklch(99% 0.004 55);
    border-radius: 16px;
    box-shadow: 0 0 0 1px var(--miai-border) inset;
    transition: all 0.2s ease;

    &:hover {
      box-shadow: 0 0 0 1px color-mix(in oklch, var(--miai-accent), white 5%) inset;
    }

    &.is-focus {
      box-shadow:
        0 0 0 1px color-mix(in oklch, var(--miai-accent), white 5%) inset,
        0 0 0 4px color-mix(in oklch, var(--miai-accent), transparent 84%);
      background: white;
    }
  }

  :deep(.el-card) {
    background: transparent;
    box-shadow: none;
  }
}

.auth-panel__footer {
  padding-top: 0.875rem;
  margin-top: 0.125rem;
  font-size: 0.78rem;
  text-align: center;
  border-top: 1px solid var(--miai-border);

  a {
    margin-left: 0.1rem;
    color: var(--miai-muted);
    text-decoration: none;
    transition: color 0.2s ease;

    &:hover {
      color: var(--miai-rose-deep);
    }
  }
}

@media (max-width: 1100px) {
  .auth-view__wrapper {
    grid-template-columns: 1fr;
  }

  .auth-feature {
    display: none;
  }

  .auth-panel {
    justify-self: center;
  }
}

@keyframes featureFade {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes panelLift {
  from {
    opacity: 0;
    transform: translateY(30px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateX(-40px) scale(0.95);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateX(40px) scale(0.95);
}

.fade-slide-enter-to,
.fade-slide-leave-from {
  opacity: 1;
  transform: translateX(0) scale(1);
}
</style>
