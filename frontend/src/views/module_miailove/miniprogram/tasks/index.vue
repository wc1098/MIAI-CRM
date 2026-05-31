<template>
  <div class="app-container mp-admin-page">
    <el-card shadow="never">
      <template #header>
        <div class="toolbar">
          <div>
            <div class="toolbar-title">解锁任务配置</div>
            <div class="toolbar-subtitle">任务类型决定系统如何判定完成，运营选择中文类型即可，不需要填写技术编码。</div>
          </div>
          <el-button type="primary" @click="open()">新增任务</el-button>
        </div>
      </template>
      <el-table :data="rows" border>
        <el-table-column prop="task_name" label="任务名称" min-width="160" />
        <el-table-column label="分组" width="120">
          <template #default="{ row }">{{ groupLabel(row.task_group) }}</template>
        </el-table-column>
        <el-table-column label="完成方式" width="150">
          <template #default="{ row }">{{ typeLabel(row.task_type) }}</template>
        </el-table-column>
        <el-table-column prop="score" label="加分" width="90" />
        <el-table-column prop="daily_limit" label="每日限制" width="100" />
        <el-table-column label="作用范围" width="130">
          <template #default="{ row }">{{ scopeLabel(row) }}</template>
        </el-table-column>
        <el-table-column prop="sort" label="排序" width="90" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === '0' ? 'success' : 'info'">{{ row.status === "0" ? "启用" : "停用" }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }"><el-button link type="primary" @click="open(row)">编辑</el-button></template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="visible" title="解锁任务" width="640px">
      <el-form :model="form" label-width="120px">
        <el-form-item label="任务名称"><el-input v-model="form.task_name" placeholder="例如：喜欢TA" /></el-form-item>
        <el-form-item label="任务编码">
          <el-input v-model="form.task_code" :disabled="isBuiltInTask" placeholder="系统唯一编码，新增自定义任务时自动生成也可以" />
          <div class="form-tip">内置任务编码用于和详情页按钮绑定，不建议修改。</div>
        </el-form-item>
        <el-form-item label="任务分组">
          <el-select v-model="form.task_group" style="width: 260px">
            <el-option v-for="item in groupOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="完成方式">
          <el-select v-model="form.task_type" style="width: 260px" @change="applyTypeDefaults">
            <el-option v-for="item in typeOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
          <div class="form-tip">{{ currentTypeTip }}</div>
        </el-form-item>
        <el-form-item label="加分"><el-input-number v-model="form.score" :min="0" /></el-form-item>
        <el-form-item label="每日限制"><el-input-number v-model="form.daily_limit" :min="0" /></el-form-item>
        <el-form-item label="作用范围">
          <el-checkbox v-model="form.is_target">当前目标心动值</el-checkbox>
          <el-checkbox v-model="form.is_global">全局真诚度</el-checkbox>
        </el-form-item>
        <el-form-item label="排序"><el-input-number v-model="form.sort" :min="0" /></el-form-item>
        <el-form-item label="状态"><el-switch v-model="enabled" active-text="启用" inactive-text="停用" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import MpUserAPI, { type MpUnlockTask } from "@/api/module_mp/user";

const groupOptions = [
  { label: "快速靠近", value: "quick" },
  { label: "提升真诚度", value: "trust" },
  { label: "默契度挑战", value: "question" },
  { label: "每日任务", value: "daily" },
];
const typeOptions = [
  { label: "查看资料自动完成", value: "view", tip: "用户打开详情页后自动完成，不在任务页单独点击。" },
  { label: "喜欢按钮完成", value: "like", tip: "和详情页照片上的心形喜欢按钮是同一个动作。" },
  { label: "收藏按钮完成", value: "favorite", tip: "和详情页底部收藏按钮是同一个动作。" },
  { label: "转发名片完成", value: "share", tip: "用户点击转发并唤起微信分享后记录任务。" },
  { label: "每日登录", value: "daily_login", tip: "进入小程序后按每日任务记录。" },
  { label: "自定义预留", value: "custom", tip: "给后续认证、资料完善、认证套餐等独立入口预留。" },
];
const builtInCodes = new Set(["view_profile", "like_profile", "favorite_profile", "share_card", "daily_login"]);

const rows = ref<MpUnlockTask[]>([]);
const visible = ref(false);
const editingId = ref<number>();
const form = reactive<MpUnlockTask>({ task_code: "", task_name: "", task_type: "custom", task_group: "quick", score: 0, is_global: false, is_target: true, daily_limit: 1, sort: 0, status: "0" });
const enabled = computed({ get: () => form.status === "0", set: (value: boolean) => (form.status = value ? "0" : "1") });
const isBuiltInTask = computed(() => Boolean(editingId.value && builtInCodes.has(form.task_code)));
const currentTypeTip = computed(() => typeOptions.find((item) => item.value === form.task_type)?.tip || "");

async function load() { rows.value = (await MpUserAPI.listTasks()).data.data || []; }
function open(row?: MpUnlockTask) {
  editingId.value = row?.id;
  Object.assign(form, row || { task_code: "", task_name: "", task_type: "custom", task_group: "quick", score: 0, is_global: false, is_target: true, daily_limit: 1, sort: 0, status: "0" });
  visible.value = true;
}
function applyTypeDefaults() {
  if (!form.task_code) form.task_code = `custom_${Date.now()}`;
  if (form.task_type === "daily_login") {
    form.task_group = "daily";
    form.is_global = true;
    form.is_target = false;
  }
}
function groupLabel(value?: string) { return groupOptions.find((item) => item.value === value)?.label || value || "-"; }
function typeLabel(value?: string) { return typeOptions.find((item) => item.value === value)?.label || value || "-"; }
function scopeLabel(row: MpUnlockTask) {
  if (row.is_global && row.is_target) return "全局+目标";
  if (row.is_global) return "全局";
  if (row.is_target) return "目标";
  return "-";
}
async function save() {
  if (!form.task_name.trim()) return ElMessage.warning("请填写任务名称");
  if (!form.task_code.trim()) form.task_code = `custom_${Date.now()}`;
  await MpUserAPI.saveTask(form, editingId.value);
  ElMessage.success("保存成功");
  visible.value = false;
  load();
}
onMounted(load);
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; gap: 16px; }
.toolbar-title { font-size: 16px; font-weight: 600; }
.toolbar-subtitle, .form-tip { margin-top: 4px; color: var(--el-text-color-secondary); font-size: 12px; line-height: 1.5; }
</style>
