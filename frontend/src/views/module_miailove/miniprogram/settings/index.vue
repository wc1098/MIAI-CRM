<template>
  <div class="app-container">
    <el-card shadow="never">
      <template #header>
        <div class="toolbar">
          <div>
            <div class="toolbar-title">小程序设置</div>
            <div class="toolbar-subtitle">解锁价格、每日上限、免费券和小程序文案都在这里统一维护。</div>
          </div>
          <el-button type="primary" :loading="saving" @click="save">保存</el-button>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="广场设置" name="plaza">
          <el-form :model="form" label-width="170px" class="setting-form">
            <el-form-item label="展示待绑定用户">
              <el-switch v-model="form.plaza_show_pending_users" />
              <span class="form-tip">开启后，后台同步进小程序但尚未微信绑定的会员也会进入广场列表。</span>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="解锁设置" name="unlock">
          <el-alert
            class="setting-alert"
            type="info"
            show-icon
            :closable="false"
            title="联系方式解锁价格在本页第一项设置；修改后小程序详情页和解锁流程立即按新价格展示。"
          />
          <el-form :model="form" label-width="150px" class="setting-form">
            <el-form-item label="联系方式解锁价格">
              <el-input v-model="form.contact_price" style="width: 220px">
                <template #prepend>¥</template>
              </el-input>
            </el-form-item>
            <el-form-item label="允许免费券解锁">
              <el-switch v-model="form.allow_coupon" />
            </el-form-item>
            <el-form-item label="允许付费补足">
              <el-switch v-model="form.allow_paid_boost" />
            </el-form-item>
            <el-form-item label="允许任务免费解锁">
              <el-switch v-model="form.allow_task_free" />
            </el-form-item>
            <el-form-item label="每日解锁上限">
              <el-input-number v-model="form.daily_unlock_limit" :min="0" :max="999" />
            </el-form-item>
            <el-form-item label="默认收款门店">
              <el-tree-select
                v-model="form.default_store_id"
                :data="deptOptions"
                :props="{ label: 'name', children: 'children' }"
                node-key="id"
                check-strictly
                clearable
                filterable
                style="width: 320px"
                placeholder="默认第一个门店"
              />
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="心动值" name="heartbeat">
          <el-form :model="form" label-width="150px" class="setting-form">
            <el-form-item label="初始心动值">
              <el-input-number v-model="form.heartbeat_initial_min" :min="0" :max="999" />
              <span class="range-sep">至</span>
              <el-input-number v-model="form.heartbeat_initial_max" :min="0" :max="999" />
            </el-form-item>
            <el-form-item label="浏览加分"><el-input-number v-model="form.heartbeat_view_score" :min="0" :max="999" /></el-form-item>
            <el-form-item label="喜欢加分"><el-input-number v-model="form.heartbeat_like_score" :min="0" :max="999" /></el-form-item>
            <el-form-item label="收藏加分"><el-input-number v-model="form.heartbeat_favorite_score" :min="0" :max="999" /></el-form-item>
            <el-form-item label="资料完整加分"><el-input-number v-model="form.heartbeat_profile_score" :min="0" :max="999" /></el-form-item>
            <el-form-item label="解锁阈值"><el-input-number v-model="form.heartbeat_unlock_score" :min="1" :max="9999" /></el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="免费券" name="coupon">
          <el-form :model="form" label-width="150px" class="setting-form">
            <el-form-item label="启用免费券"><el-switch v-model="form.coupon_enabled" /></el-form-item>
            <el-form-item label="券名称"><el-input v-model="form.coupon_name" style="width: 320px" /></el-form-item>
            <el-form-item label="有效天数"><el-input-number v-model="form.coupon_valid_days" :min="1" :max="3650" /></el-form-item>
            <el-form-item label="连续任务周期"><el-input-number v-model="form.coupon_cycle_days" :min="1" :max="30" /></el-form-item>
            <el-form-item label="持有上限"><el-input-number v-model="form.coupon_hold_limit" :min="1" :max="99" /></el-form-item>
            <el-form-item label="说明"><el-input v-model="form.coupon_description" type="textarea" :rows="3" style="width: 520px" /></el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="文案配置" name="copy">
          <el-form :model="form" label-width="150px" class="setting-form">
            <el-form-item label="进度页文案"><el-input v-model="form.copy_progress" type="textarea" :rows="2" /></el-form-item>
            <el-form-item label="最后一步文案"><el-input v-model="form.copy_final" type="textarea" :rows="2" /></el-form-item>
            <el-form-item label="支付说明文案"><el-input v-model="form.copy_pay" type="textarea" :rows="2" /></el-form-item>
            <el-form-item label="手机号提示"><el-input v-model="form.copy_contact" type="textarea" :rows="2" /></el-form-item>
            <el-form-item label="风控提示"><el-input v-model="form.copy_risk" type="textarea" :rows="2" /></el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";

import MpUserAPI, { type MpOperationSettings } from "@/api/module_mp/user";
import DeptAPI, { type DeptTable } from "@/api/module_system/dept";

const activeTab = ref("unlock");
const saving = ref(false);
const deptOptions = ref<DeptTable[]>([]);
const form = reactive<MpOperationSettings>({
  plaza_show_pending_users: false,
  contact_price: "19.90",
  allow_coupon: true,
  allow_paid_boost: true,
  allow_task_free: true,
  daily_unlock_limit: 5,
  default_store_id: undefined,
  heartbeat_initial_min: 35,
  heartbeat_initial_max: 55,
  heartbeat_view_score: 1,
  heartbeat_like_score: 8,
  heartbeat_favorite_score: 5,
  heartbeat_profile_score: 0,
  heartbeat_unlock_score: 100,
  coupon_enabled: true,
  coupon_name: "联系方式解锁券",
  coupon_valid_days: 7,
  coupon_cycle_days: 2,
  coupon_hold_limit: 1,
  coupon_description: "可免费解锁一次心仪用户手机号",
  copy_progress: "完成互动任务提升心动值，达到目标后即可查看手机号。",
  copy_final: "解锁后可查看对方手机号，本次解锁后可重复查看，不重复收费。",
  copy_pay: "付费补足会直接加满当前心动值并解锁手机号。",
  copy_contact: "请真诚沟通，尊重对方意愿；若对方明确拒绝，请停止打扰。",
  copy_risk: "今日解锁次数已用完，请明天再试。",
});

async function load() {
  const [settingsRes, deptRes] = await Promise.all([MpUserAPI.getSettings(), DeptAPI.listDept()]);
  Object.assign(form, settingsRes.data.data);
  deptOptions.value = deptRes.data.data || [];
}

async function save() {
  saving.value = true;
  try {
    const res = await MpUserAPI.updateSettings(form);
    Object.assign(form, res.data.data);
    ElMessage.success("保存成功");
  } finally {
    saving.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.toolbar-title {
  font-size: 16px;
  font-weight: 600;
}
.toolbar-subtitle {
  margin-top: 4px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.setting-form {
  max-width: 760px;
  padding-top: 8px;
}
.setting-alert {
  max-width: 760px;
  margin-bottom: 12px;
}
.range-sep {
  margin: 0 12px;
  color: var(--el-text-color-secondary);
}
.form-tip {
  margin-left: 12px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
</style>
