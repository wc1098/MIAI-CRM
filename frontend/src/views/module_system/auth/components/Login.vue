<template>
  <div class="miai-login">
    <div class="miai-login__header">
      <p class="miai-login__eyebrow">STAFF LOGIN</p>
      <h2>员工登录</h2>
      <p class="miai-login__desc">请使用后台账号进入会员服务工作台。</p>
      <div class="miai-login__status">
        <span>会员资料库正常</span>
        <span>AI 匹配引擎在线</span>
      </div>
    </div>

    <el-tabs v-model="activeTab" class="login-tabs">
      <!-- 账号登录 -->
      <el-tab-pane label="账号登录" name="password">
        <el-form
          ref="loginFormRef"
          :model="loginForm"
          :rules="loginRules"
          size="large"
          :validate-on-rule-change="false"
        >
          <!-- 用户名 -->
          <el-form-item prop="username">
            <el-input
              v-model.trim="loginForm.username"
              placeholder="员工账号"
              clearable
            >
              <template #prefix>
                <el-icon><User /></el-icon>
              </template>
            </el-input>
          </el-form-item>

          <!-- 密码 -->
          <el-tooltip :visible="isCapsLock" :content="t('login.capsLock')" placement="right">
            <el-form-item prop="password">
              <el-input
                v-model.trim="loginForm.password"
                placeholder="登录密码"
                type="password"
                show-password
                clearable
                @keyup="checkCapsLock"
                @keyup.enter="handleLoginSubmit"
              >
                <template #prefix>
                  <el-icon><Lock /></el-icon>
                </template>
              </el-input>
            </el-form-item>
          </el-tooltip>

          <!-- 验证码 -->
          <el-form-item v-if="captchaState.enable" prop="captcha">
            <div flex items-center gap-10px class="flex-1">
              <el-input
                v-model.trim="loginForm.captcha"
                :placeholder="t('login.captchaCode')"
                clearable
                class="flex-1"
                @keyup.enter="handleLoginSubmit"
              >
                <template #prefix>
                  <div class="i-svg:captcha" />
                </template>
              </el-input>
              <div cursor-pointer flex-center h-40px w-100px>
                <el-icon v-if="codeLoading" class="is-loading" size="20">
                  <Loading />
                </el-icon>
                <el-image
                  v-else-if="captchaState.img_base"
                  border-rd-4px
                  object-cover
                  shadow="[0_0_0_1px_var(--el-border-color)_inset]"
                  :src="captchaState.img_base"
                  class="w-full h-full"
                  @click="getCaptcha"
                />
                <el-text v-else type="info" size="small">点击获取验证码</el-text>
              </div>
            </div>
          </el-form-item>

          <div class="flex-x-between w-full">
            <el-checkbox v-model="loginForm.remember">{{ t("login.rememberMe") }}</el-checkbox>
          </div>

          <!-- 登录按钮 -->
          <el-form-item>
            <el-button
              :loading="loading"
              type="primary"
              class="miai-login__submit"
              @click="handleLoginSubmit"
            >
              进入员工工作台
            </el-button>
          </el-form-item>

          <div class="miai-login__note">安全连接已启用，请妥善保管账号凭证。</div>
        </el-form>

        <!-- <div flex-center gap-10px>
          <el-text size="default">{{ t("login.noAccount") }}</el-text>
          <el-link type="primary" underline="never" @click="toOtherForm('register')">
            {{ t("login.reg") }}
          </el-link>
        </div> -->
      </el-tab-pane>

      <!-- 快速登录 -->
      <el-tab-pane v-if="autoLoginUsers.length > 0" label="快速登录" name="quick">
        <div class="quick-login-section">
          <div class="quick-login-tip">
            {{ t("login.quickLoginTip") }}
          </div>
          <!-- 当用户数量大于4个时使用下拉选择，否则使用网格展示 -->
          <template v-if="autoLoginUsers.length > 3">
            <el-select
              v-model="selectedUserId"
              class="miai-quick-select"
              :placeholder="t('login.selectUser')"
              size="large"
              @change="handleAutoLogin"
            >
              <el-option
                v-for="user in autoLoginUsers"
                :key="user.user_id"
                :label="`${user.username}@${user.name}`"
                :value="user.user_id"
              />
            </el-select>
          </template>
          <template v-else>
            <div class="auto-login-users">
              <div
                v-for="user in autoLoginUsers"
                :key="user.user_id"
                class="auto-login-user-item"
                @click="handleAutoLogin(user.user_id)"
              >
                <el-button
                  class="remove-quick-login"
                  :icon="Close"
                  circle
                  text
                  size="small"
                  @click.stop="removeQuickLoginAccount(user.user_id)"
                />
                <el-avatar :size="60" :src="user.avatar || ''" class="user-avatar">
                  <el-icon size="24"><User /></el-icon>
                </el-avatar>
                <span class="user-name">{{ user.name }}</span>
                <span class="user-username">{{ user.username }}</span>
              </div>
            </div>
          </template>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 第三方登录 -->
    <!-- <div class="third-party-login">
      <div class="divider-container">
        <div class="divider-line"></div>
        <span class="divider-text">{{ t("login.otherLoginMethods") }}</span>
        <div class="divider-line"></div>
      </div>
      <div class="flex-center gap-x-5 w-full text-[var(--el-text-color-secondary)]">
        <CommonWrapper>
          <div text-20px class="i-svg:wechat" />
        </CommonWrapper>
        <CommonWrapper>
          <div text-20px cursor-pointer class="i-svg:qq" />
        </CommonWrapper>
        <CommonWrapper>
          <div text-20px cursor-pointer class="i-svg:github" />
        </CommonWrapper>
        <CommonWrapper>
          <div text-20px cursor-pointer class="i-svg:gitee" />
        </CommonWrapper>
      </div>
    </div> -->
  </div>
</template>
<script setup lang="ts">
import type { FormInstance } from "element-plus";
import { LocationQuery, RouteLocationRaw, useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { onActivated, onMounted, watch } from "vue";
import AuthAPI, { type LoginFormData, type CaptchaInfo } from "@/api/module_system/auth";
import { useAppStore, useUserStore, useSettingsStore } from "@/store";
import { User, Loading, Lock, Close } from "@element-plus/icons-vue";
import { Auth } from "@/utils/auth";
import { QuickLoginStorage, type QuickLoginAccount } from "@/utils/quickLogin";

const { t } = useI18n();
const userStore = useUserStore();
const appStore = useAppStore();
const settingsStore = useSettingsStore();

// 激活的标签页
const activeTab = ref("password");

// 选择的用户ID（用于下拉选择）
const selectedUserId = ref<number | null>(null);

// 来自父容器的预填用户名和密码
const props = defineProps<{ presetUsername?: string; presetPassword?: string }>();

const route = useRoute();
const router = useRouter();

// 组件挂载时获取验证码和免登录用户列表
onMounted(() => {
  getCaptcha();
  loadQuickLoginAccounts();
});

// 组件激活时获取验证码（适用于KeepAlive缓存的情况）
onActivated(() => {
  getCaptcha();
  // 重置登录表单
  loginForm.captcha = "";
});

// 监听路由变化，确保每次进入登录页面都有最新验证码
watch(
  () => route.fullPath,
  () => {
    getCaptcha();
    loginForm.captcha = "";
  }
);

const loginFormRef = ref<FormInstance>();
const loading = ref(false);
// 是否大写锁定
const isCapsLock = ref(false);

const loginForm = reactive<LoginFormData>({
  username: "",
  password: "",
  captcha: "",
  captcha_key: "",
  remember: true,
  login_type: "PC端",
});

// 监听父组件传入的预填信息，立即填充到登录表单
watch(
  () => [props.presetUsername, props.presetPassword],
  ([presetUsername, presetPassword]) => {
    if (typeof presetUsername === "string") {
      loginForm.username = presetUsername;
    }
    if (typeof presetPassword === "string") {
      loginForm.password = presetPassword;
    }
  },
  { immediate: true }
);

const captchaState = reactive<CaptchaInfo>({
  enable: true,
  key: "",
  img_base: "",
});

// 本机快速登录账号列表
const autoLoginUsers = ref<QuickLoginAccount[]>([]);
const autoLoginLoading = ref(false);

function loadQuickLoginAccounts() {
  autoLoginUsers.value = QuickLoginStorage.getAccounts();
}

function removeQuickLoginAccount(userId: number) {
  QuickLoginStorage.removeAccount(userId);
  if (selectedUserId.value === userId) {
    selectedUserId.value = null;
  }
  loadQuickLoginAccounts();
}

// 免登录
async function handleAutoLogin(userId: number) {
  if (autoLoginLoading.value) return;

  try {
    autoLoginLoading.value = true;

    const account = autoLoginUsers.value.find((item) => item.user_id === userId);
    if (!account) {
      ElMessage.warning("本机快速登录账号已不存在");
      return;
    }

    await userStore.resetAllState();

    // 1. 使用本机凭证登录
    const loginResponse = await AuthAPI.autoLogin({
      user_id: account.user_id,
      device_token: account.device_token,
    });
    const loginData = loginResponse.data.data;

    // 2. 设置登录状态
    userStore.rememberMe = true;
    Auth.setTokens(loginData.access_token, loginData.refresh_token, true);

    // 3. 获取用户信息
    await userStore.getUserInfo();

    // 4. 跳转
    const redirect = resolveRedirectTarget(route.query);
    await router.replace(redirect);

    // 5. 显示引导
    if (settingsStore.showGuide) {
      appStore.showGuide(true);
    }

    ElMessage.success("登录成功");
  } catch (error: any) {
    console.error("免登录失败:", error);
    QuickLoginStorage.removeAccount(userId);
    loadQuickLoginAccounts();
    ElMessage.error(error?.response?.data?.msg || "快速登录失败，请重新账号密码登录");
  } finally {
    autoLoginLoading.value = false;
  }
}

const loginRules = computed(() => {
  const rules: any = {
    username: [
      {
        required: true,
        trigger: "blur",
        message: t("login.message.username.required"),
      },
    ],
    password: [
      {
        required: true,
        trigger: "blur",
        message: t("login.message.password.required"),
      },
      {
        min: 6,
        message: t("login.message.password.min"),
        trigger: "blur",
      },
    ],
  };

  // 只有在验证码开启时才添加验证码验证规则
  if (captchaState.enable) {
    rules.captcha = [
      {
        required: true,
        trigger: "blur",
        message: t("login.message.captchaCode.required"),
      },
    ];
  }

  return rules;
});

// 获取验证码
const codeLoading = ref(false);
async function getCaptcha() {
  try {
    codeLoading.value = true;
    const response = await AuthAPI.getCaptcha();
    loginForm.captcha_key = response.data.data.key;
    captchaState.img_base = response.data.data.img_base;
    captchaState.enable = response.data.data.enable;
  } catch (error: any) {
    // 验证码获取失败时，默认关闭验证码功能
    console.error("获取验证码失败:", error);
    captchaState.enable = false;
    // 清空验证码相关字段，避免影响登录
    loginForm.captcha = "";
    loginForm.captcha_key = "";
  } finally {
    codeLoading.value = false;
  }
}

/**
 * 登录提交
 */
async function handleLoginSubmit() {
  try {
    // 1. 表单验证
    const valid = await loginFormRef.value?.validate();
    if (!valid) return;

    loading.value = true;

    // 2. 执行登录
    await userStore.login(loginForm);
    await userStore.getUserInfo();
    try {
      const deviceResponse = await AuthAPI.createQuickLoginDevice();
      QuickLoginStorage.saveDevice(deviceResponse.data.data);
      loadQuickLoginAccounts();
    } catch (error) {
      console.error("创建本机快速登录凭证失败:", error);
    }

    // 4. 登录成功，让路由守卫处理跳转逻辑
    // 解析目标地址，但不直接跳转
    const redirect = resolveRedirectTarget(route.query);

    // 通过替换当前路由触发路由守卫，让守卫处理后续的路由生成和跳转
    await router.replace(redirect);

    // 5. 记住我功能已实现，根据用户选择决定token的存储方式:
    // - 选中"记住我": token存储在localStorage中，浏览器关闭后仍然有效
    // - 未选中"记住我": token存储在sessionStorage中，浏览器关闭后失效

    // 登录成功后自动开启项目引导
    if (settingsStore.showGuide) {
      appStore.showGuide(true);
    }
  } catch (error: any) {
    if (error) {
      getCaptcha(); // 刷新验证码
    }
  } finally {
    loading.value = false;
  }
}

/**
 * 解析重定向目标
 *
 * @param query 路由查询参数
 * @returns 标准化后的路由地址
 */
function resolveRedirectTarget(query: LocationQuery): RouteLocationRaw {
  // 默认跳转路径
  const defaultPath = "/";

  // 获取原始重定向路径
  const rawRedirect = (query.redirect as string) || defaultPath;

  try {
    // 6. 使用Vue Router解析路径
    const resolved = router.resolve(rawRedirect);
    return {
      path: resolved.path,
      query: resolved.query,
    };
  } catch {
    // 7. 异常处理：返回安全路径
    return { path: defaultPath };
  }
}

// 检查输入大小写
function checkCapsLock(event: KeyboardEvent) {
  // 防止浏览器密码自动填充时报错
  if (event instanceof KeyboardEvent) {
    isCapsLock.value = event.getModifierState("CapsLock");
  }
}

const emit = defineEmits(["update:modelValue"]);
function toOtherForm(type: "register" | "resetPwd") {
  emit("update:modelValue", type);
}
</script>

<style lang="scss" scoped>
.miai-login {
  color: var(--miai-fg, oklch(22% 0.028 255));
}

.miai-login__header {
  margin-bottom: 18px;

  h2 {
    margin: 0;
    font-size: 30px;
    font-weight: 800;
    line-height: 1.2;
    letter-spacing: 0;
    color: var(--miai-fg, oklch(22% 0.028 255));
  }
}

.miai-login__eyebrow {
  margin: 0 0 8px;
  font-size: 11px;
  font-weight: 800;
  color: var(--miai-rose-deep, oklch(42% 0.09 18));
  letter-spacing: 0;
}

.miai-login__desc {
  margin: 10px 0 0;
  font-size: 14px;
  line-height: 1.7;
  color: var(--miai-muted, oklch(50% 0.018 255));
}

.miai-login__status {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;

  span {
    display: inline-flex;
    align-items: center;
    height: 30px;
    padding: 0 12px;
    font-size: 12px;
    font-weight: 700;
    color: var(--miai-muted, oklch(50% 0.018 255));
    background: white;
    border: 1px solid var(--miai-border, oklch(90% 0.016 55));
    border-radius: 999px;

    &::before {
      width: 8px;
      height: 8px;
      margin-right: 8px;
      content: "";
      background: oklch(58% 0.12 155);
      border-radius: 50%;
    }
  }
}

.login-tabs {
  margin-bottom: 20px;

  :deep(.el-tabs__header) {
    margin-bottom: 18px;
  }

  :deep(.el-tabs__nav-wrap::after) {
    height: 1px;
    background-color: var(--miai-border, oklch(90% 0.016 55));
  }

  :deep(.el-tabs__active-bar) {
    height: 3px;
    background-color: var(--miai-accent, oklch(63% 0.14 18));
    border-radius: 999px;
  }

  :deep(.el-tabs__item) {
    height: 38px;
    padding: 0 18px 0 0;
    font-weight: 700;
    color: var(--miai-muted, oklch(50% 0.018 255));

    &.is-active,
    &:hover {
      color: var(--miai-rose-deep, oklch(42% 0.09 18));
    }
  }

  :deep(.el-tabs__content) {
    min-height: 360px;
    overflow: visible;
  }

  :deep(.el-tab-pane) {
    position: relative;
    min-height: 360px;
    overflow: visible;
  }

  :deep(.el-form-item__error) {
    padding-left: 6px;
  }

  :deep(.el-checkbox__label),
  :deep(.el-link__inner) {
    font-size: 13px;
  }

  :deep(.el-checkbox) {
    --el-checkbox-checked-bg-color: var(--miai-accent, oklch(63% 0.14 18));
    --el-checkbox-checked-input-border-color: var(--miai-accent, oklch(63% 0.14 18));
    --el-checkbox-checked-text-color: var(--miai-rose-deep, oklch(42% 0.09 18));
    --el-checkbox-input-border-color-hover: var(--miai-accent, oklch(63% 0.14 18));
    color: var(--miai-muted, oklch(50% 0.018 255));
  }

  :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
    background-color: var(--miai-accent, oklch(63% 0.14 18));
    border-color: var(--miai-accent, oklch(63% 0.14 18));
  }

  :deep(.el-checkbox__input.is-focus .el-checkbox__inner) {
    border-color: var(--miai-accent, oklch(63% 0.14 18));
  }

  :deep(.el-link.el-link--primary) {
    --el-link-text-color: var(--miai-rose-deep, oklch(42% 0.09 18));
    --el-link-hover-text-color: var(--miai-accent, oklch(63% 0.14 18));
  }
}

.miai-login__submit {
  width: 100%;
  min-height: 50px;
  margin-top: 8px;
  font-size: 15px;
  font-weight: 800;
  color: white;
  background: linear-gradient(
    135deg,
    var(--miai-rose-deep, oklch(42% 0.09 18)),
    var(--miai-accent, oklch(63% 0.14 18))
  );
  border: 0;
  border-radius: 18px;
  box-shadow: 0 18px 38px color-mix(in oklch, var(--miai-accent, oklch(63% 0.14 18)), transparent 74%);

  &:hover,
  &:focus {
    background: linear-gradient(
      135deg,
      color-mix(in oklch, var(--miai-rose-deep, oklch(42% 0.09 18)), black 8%),
      color-mix(in oklch, var(--miai-accent, oklch(63% 0.14 18)), black 5%)
    );
  }
}

.miai-login__note {
  padding: 12px 14px;
  margin-top: 2px;
  font-size: 12px;
  line-height: 1.7;
  color: var(--miai-muted, oklch(50% 0.018 255));
  background: color-mix(in oklch, var(--miai-accent-soft, oklch(94% 0.04 18)), white 55%);
  border: 1px solid color-mix(in oklch, var(--miai-border, oklch(90% 0.016 55)), white 10%);
  border-radius: 18px;
}

.quick-login-section {
  position: relative;
  min-height: 200px;
  padding: 0;

  .quick-login-tip {
    padding: 12px 14px;
    margin-bottom: 18px;
    font-size: 12px;
    line-height: 1.7;
    color: var(--miai-muted, oklch(50% 0.018 255));
    background: color-mix(in oklch, var(--miai-accent-soft, oklch(94% 0.04 18)), white 55%);
    border: 1px solid color-mix(in oklch, var(--miai-border, oklch(90% 0.016 55)), white 10%);
    border-radius: 18px;
  }

  .miai-quick-select {
    width: 100%;

    :deep(.el-select__wrapper) {
      min-height: 54px;
      background: oklch(99% 0.004 55);
      border-radius: 16px;
      box-shadow: 0 0 0 1px var(--miai-border, oklch(90% 0.016 55)) inset;
      transition: all 0.2s ease;

      &:hover,
      &.is-focused {
        background: white;
        box-shadow:
          0 0 0 1px color-mix(in oklch, var(--miai-accent, oklch(63% 0.14 18)), white 5%) inset,
          0 0 0 4px color-mix(in oklch, var(--miai-accent, oklch(63% 0.14 18)), transparent 84%);
      }
    }
  }

  // 下拉菜单样式
  .user-dropdown {
    .user-dropdown-btn {
      display: flex;
      align-items: center;
      justify-content: space-between;
      width: 100%;
      height: 48px;
      padding: 0 16px;

      .btn-text {
        font-size: 14px;
        color: var(--el-text-color-regular);
      }
    }
  }

  :deep(.user-dropdown-menu) {
    max-height: 320px;
    overflow-y: auto;

    .el-dropdown-menu__item {
      display: flex !important;
      gap: 20px !important;
      align-items: center !important;
      padding: 14px 24px !important;
    }
  }

  .user-option {
    display: flex;
    gap: 16px;
    align-items: center;
    padding: 10px 0;

    .user-info {
      display: flex;
      flex: 1;
      flex-direction: column;
      gap: 4px;
      min-width: 0;

      .user-option-name {
        overflow: hidden;
        text-overflow: ellipsis;
        font-size: 14px;
        font-weight: 600;
        white-space: nowrap;
      }

      .user-option-username {
        overflow: hidden;
        text-overflow: ellipsis;
        font-size: 12px;
        font-weight: 500;
        white-space: nowrap;
      }
    }
  }

  .user-option-avatar {
    flex-shrink: 0;
    border: 2px solid var(--el-border-color-light);
    transition: all 0.3s ease;

    &:hover {
      border-color: var(--el-color-primary);
    }
  }

  .auto-login-users {
    display: grid;
    grid-template-columns: 1fr;
    gap: 12px;
    padding: 0;

    .auto-login-user-item {
      position: relative;
      display: flex;
      flex-direction: row;
      gap: 12px;
      align-items: center;
      justify-content: flex-start;
      width: 100%;
      min-height: 64px;
      padding: 10px 44px 10px 12px;
      cursor: pointer;
      background-color: oklch(99% 0.004 55);
      border: 1px solid var(--miai-border, oklch(90% 0.016 55));
      border-radius: 16px;
      box-shadow: none;
      transition: all 0.3s ease;

      .remove-quick-login {
        position: absolute;
        top: 50%;
        right: 10px;
        color: var(--miai-muted, oklch(50% 0.018 255));
        opacity: 0.75;
        transform: translateY(-50%);
        transition: opacity 0.2s ease;
      }

      &:hover {
        background: white;
        border-color: color-mix(in oklch, var(--miai-accent, oklch(63% 0.14 18)), white 5%);
        box-shadow: 0 0 0 4px color-mix(in oklch, var(--miai-accent, oklch(63% 0.14 18)), transparent 84%);
        transform: none;

        .remove-quick-login {
          opacity: 1;
        }
      }

      .user-avatar {
        flex-shrink: 0;
        border: 1px solid var(--miai-border, oklch(90% 0.016 55));
        transition: all 0.3s ease;

        &:hover {
          border-color: var(--miai-accent, oklch(63% 0.14 18));
        }
      }

      .user-name {
        max-width: none;
        overflow: hidden;
        text-overflow: ellipsis;
        font-size: 14px;
        font-weight: 700;
        color: var(--miai-ink-soft, oklch(33% 0.025 255));
        text-align: left;
        white-space: nowrap;
      }

      .user-username {
        max-width: none;
        overflow: hidden;
        text-overflow: ellipsis;
        font-size: 12px;
        color: var(--miai-muted, oklch(50% 0.018 255));
        text-align: left;
        white-space: nowrap;
      }
    }
  }
}

.third-party-login {
  .divider-container {
    display: flex;
    align-items: center;
    margin: 20px 0;

    .divider-line {
      flex: 1;
      height: 1px;
      background: linear-gradient(to right, transparent, var(--el-border-color-light), transparent);
    }

    .divider-text {
      padding: 0 16px;
      font-size: 12px;
      color: var(--el-text-color-regular);
      white-space: nowrap;
    }
  }
}
</style>
