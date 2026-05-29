<template>
  <div class="app-container workbench-page">
    <el-card class="workbench-hero" shadow="never">
      <div class="workbench-hero__main">
        <div>
          <div class="workbench-hero__title">角色工作台</div>
          <div class="workbench-hero__meta">
            {{ summary?.role_name || "工作台" }} · {{ currentDate }} · {{ scopeText }}
          </div>
        </div>
        <div class="workbench-hero__actions">
          <el-segmented v-model="range" :options="rangeOptions" @change="loadSummary" />
          <el-button :loading="loading" @click="reloadAll">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </div>
    </el-card>

    <div class="metric-grid mt-4">
      <div v-for="metric in summaryMetrics" :key="metric.key">
        <button class="metric-card" type="button" @click="go(metric.route_path, metric.query)">
          <div class="metric-card__head">
            <span>{{ metric.title }}</span>
            <el-tag :type="tagType(metric.priority)" size="small" effect="plain">{{ rangeLabel }}</el-tag>
          </div>
          <div class="metric-card__value">
            {{ formatMetric(metric.value) }}
            <span v-if="metric.unit" class="metric-card__unit">{{ metric.unit }}</span>
          </div>
          <div class="metric-card__hint">{{ metric.hint || "点击查看明细" }}</div>
        </button>
      </div>
    </div>

    <div class="task-grid mt-4">
      <TaskPanel title="今日待办" subtitle="今天必须处理的事项" bucket="today" :tasks="taskMap.today" :total="taskTotal.today" :loading="taskLoading.today" @reload="loadTasks('today')" @open="openTask" @view-all="openTaskDrawer" />
      <TaskPanel title="遗留事项" subtitle="超时、驳回、待补充事项" bucket="overdue" :tasks="taskMap.overdue" :total="taskTotal.overdue" :loading="taskLoading.overdue" @reload="loadTasks('overdue')" @open="openTask" @view-all="openTaskDrawer" />
      <TaskPanel title="未来日程" subtitle="未来 7 天即将处理" bucket="upcoming" :tasks="taskMap.upcoming" :total="taskTotal.upcoming" :loading="taskLoading.upcoming" @reload="loadTasks('upcoming')" @open="openTask" @view-all="openTaskDrawer" />
    </div>

    <el-card class="mt-4 node-card" shadow="never" v-loading="nodeLoading">
      <template #header>
        <div class="section-head">
          <div>
            <span class="section-title">业务节点状态</span>
            <div class="section-sub">按功能节点汇总积压和推进状态，点击节点进入对应列表</div>
          </div>
          <el-segmented v-model="nodeScope" :options="scopeOptions" @change="loadNodes" />
        </div>
      </template>
      <el-empty v-if="nodeGroups.length === 0" :image-size="72" description="暂无节点数据" />
      <div v-else class="node-groups">
        <section v-for="group in nodeGroups" :key="group.key" class="node-group">
          <div class="node-group__title">{{ group.title }}</div>
          <div class="node-grid">
            <button v-for="node in group.nodes" :key="node.key" type="button" class="node-item" @click="go(node.route_path, node.query)">
              <span class="node-item__title">{{ node.title }}</span>
              <span class="node-item__count" :class="`is-${node.priority || 'primary'}`">{{ node.count }}</span>
            </button>
          </div>
        </section>
      </div>
    </el-card>

    <el-drawer v-model="taskDrawerVisible" :title="taskDrawerTitle" size="520px" append-to-body>
      <div v-loading="taskDrawerLoading" class="task-drawer">
        <el-empty v-if="taskDrawerItems.length === 0" :image-size="72" description="暂无事项" />
        <div v-else class="task-list task-list--drawer">
          <button v-for="task in taskDrawerItems" :key="task.id" type="button" class="task-item" @click="openTask(task)">
            <div class="task-item__main">
              <span class="task-item__title">{{ task.title }}</span>
              <el-tag :type="tagType(task.priority)" size="small" effect="plain">{{ statusText(task.status) }}</el-tag>
            </div>
            <div class="task-item__name">{{ task.object_name || `#${task.object_id}` }}</div>
            <div class="task-item__meta">
              <span>{{ task.due_at || "无截止时间" }}</span>
              <span>{{ task.owner_user_name || "未分配" }}</span>
            </div>
            <div class="task-item__action">{{ task.action_text }}</div>
          </button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
defineOptions({
  name: "MiailoveWorkbenchOverview",
});

import { dayjs } from "element-plus";
import { Refresh, RefreshRight } from "@element-plus/icons-vue";
import { defineComponent, h, type PropType } from "vue";
import { ElButton, ElCard, ElEmpty, ElIcon, ElTag } from "element-plus";
import WorkbenchAPI, {
  type WorkbenchBucket,
  type WorkbenchMetric,
  type WorkbenchNodeGroup,
  type WorkbenchRange,
  type WorkbenchScope,
  type WorkbenchSummary,
  type WorkbenchTask,
} from "@/api/module_workbench/workbench";

const router = useRouter();

const range = ref<WorkbenchRange>("today");
const nodeScope = ref<WorkbenchScope>("mine");
const loading = ref(false);
const nodeLoading = ref(false);
const summary = ref<WorkbenchSummary>();
const nodeGroups = ref<WorkbenchNodeGroup[]>([]);
const taskMap = reactive<Record<WorkbenchBucket, WorkbenchTask[]>>({
  today: [],
  overdue: [],
  upcoming: [],
});
const taskTotal = reactive<Record<WorkbenchBucket, number>>({
  today: 0,
  overdue: 0,
  upcoming: 0,
});
const taskLoading = reactive<Record<WorkbenchBucket, boolean>>({
  today: false,
  overdue: false,
  upcoming: false,
});
const taskDrawerVisible = ref(false);
const taskDrawerLoading = ref(false);
const taskDrawerBucket = ref<WorkbenchBucket>("today");
const taskDrawerItems = ref<WorkbenchTask[]>([]);

const TASK_PREVIEW_LIMIT = 8;
const TASK_DRAWER_LIMIT = 100;

const rangeOptions = [
  { label: "今日", value: "today" },
  { label: "本周", value: "week" },
  { label: "本月", value: "month" },
];
const scopeOptions = [
  { label: "我的", value: "mine" },
  { label: "本门店", value: "store" },
];

const STATUS_TEXT_MAP: Record<string, string> = {
  active: "启用",
  approved: "已通过",
  cancelled: "已取消",
  checked_in: "已到店",
  closed: "已关单",
  completed: "已完成",
  consulted: "已面谈",
  confirmed: "已确认",
  converted_customer: "已转建档",
  draft: "草稿",
  effective: "已生效",
  expired: "已过期",
  hq_pool: "品牌池",
  in_progress: "进行中",
  invalid: "无效",
  meeting_confirmed: "约见已确认",
  meeting_created: "已转约见",
  new: "新线索",
  no_show: "爽约",
  none: "无",
  pending: "待处理",
  pending_assign: "待分配",
  pending_close_review: "关单待审",
  pending_feedback: "待反馈",
  pending_meeting: "待约见",
  pending_review: "待审核",
  recommended: "已推荐",
  rejected: "已驳回",
  reopened: "已重开",
  sales_private: "销售私海",
  second_hand: "二手线索",
  serving: "服务中",
  skipped: "已放弃",
  store_pool: "门店公海",
  voided: "已作废",
};

const currentDate = computed(() => dayjs().format("YYYY年MM月DD日"));
const rangeLabel = computed(() => rangeOptions.find((item) => item.value === range.value)?.label || "今日");
const scopeText = computed(() => (summary.value?.scope === "store" ? "本门店视角" : "我的视角"));
const summaryMetrics = computed<WorkbenchMetric[]>(() => summary.value?.metrics || []);
const taskDrawerTitle = computed(() => `${bucketTitle(taskDrawerBucket.value)}（共 ${taskTotal[taskDrawerBucket.value]} 条）`);

function tagType(priority?: string) {
  return ["success", "warning", "danger", "info"].includes(priority || "") ? (priority as any) : "primary";
}

function formatMetric(value: number | string) {
  if (typeof value !== "number") return value;
  return value.toLocaleString("zh-CN", { maximumFractionDigits: 2 });
}

function statusText(value?: string) {
  if (!value) return "待处理";
  return STATUS_TEXT_MAP[value] || value;
}

function bucketTitle(bucket: WorkbenchBucket) {
  const titleMap: Record<WorkbenchBucket, string> = {
    today: "今日待办",
    overdue: "遗留事项",
    upcoming: "未来日程",
  };
  return titleMap[bucket];
}

function go(path?: string, query?: Record<string, unknown>) {
  if (!path) return;
  router.push({ path, query: sanitizeQuery(query || {}) });
}

function sanitizeQuery(query: Record<string, unknown>) {
  return Object.fromEntries(
    Object.entries(query)
      .filter(([, value]) => value !== undefined && value !== null && value !== "")
      .map(([key, value]) => [key, typeof value === "boolean" ? String(value) : value as any])
  );
}

function openTask(task: WorkbenchTask) {
  go(task.route_path, task.query);
}

async function openTaskDrawer(bucket: WorkbenchBucket) {
  taskDrawerBucket.value = bucket;
  taskDrawerVisible.value = true;
  taskDrawerLoading.value = true;
  try {
    const res = await WorkbenchAPI.tasks({ bucket, days: 7, limit: TASK_DRAWER_LIMIT });
    taskTotal[bucket] = res.data.data.total || 0;
    taskDrawerItems.value = res.data.data.items || [];
  } finally {
    taskDrawerLoading.value = false;
  }
}

async function loadSummary() {
  loading.value = true;
  try {
    const res = await WorkbenchAPI.summary({ range: range.value });
    summary.value = res.data.data;
    nodeScope.value = summary.value?.scope === "store" ? "store" : "mine";
  } finally {
    loading.value = false;
  }
}

async function loadTasks(bucket: WorkbenchBucket) {
  taskLoading[bucket] = true;
  try {
    const res = await WorkbenchAPI.tasks({ bucket, days: 7, limit: TASK_PREVIEW_LIMIT });
    taskTotal[bucket] = res.data.data.total || 0;
    taskMap[bucket] = res.data.data.items || [];
  } finally {
    taskLoading[bucket] = false;
  }
}

async function loadNodes() {
  nodeLoading.value = true;
  try {
    const res = await WorkbenchAPI.nodes({ scope: nodeScope.value });
    nodeGroups.value = res.data.data.groups || [];
  } finally {
    nodeLoading.value = false;
  }
}

async function reloadAll() {
  await Promise.all([loadSummary(), loadTasks("today"), loadTasks("overdue"), loadTasks("upcoming"), loadNodes()]);
}

const TaskPanel = defineComponent({
  name: "TaskPanel",
  props: {
    title: { type: String, required: true },
    subtitle: { type: String, required: true },
    bucket: { type: String as PropType<WorkbenchBucket>, required: true },
    tasks: { type: Array as PropType<WorkbenchTask[]>, required: true },
    total: { type: Number, default: 0 },
    loading: { type: Boolean, default: false },
  },
  emits: ["reload", "open", "view-all"],
  setup(props, { emit }) {
    const priorityType = (priority?: string) => (["success", "warning", "danger", "info"].includes(priority || "") ? priority : "primary") as any;
    const hiddenCount = () => Math.max(props.total - props.tasks.length, 0);
    return () =>
      h(
        ElCard,
        { class: "task-card", shadow: "never", loading: props.loading },
        {
          header: () =>
            h("div", { class: "section-head" }, [
              h("div", [
                h("span", { class: "section-title" }, [
                  props.title,
                  h("span", { class: "section-count" }, `共 ${props.total} 条`),
                ]),
                h("div", { class: "section-sub" }, props.subtitle),
              ]),
              h("div", { class: "task-card__actions" }, [
                h(
                  ElButton,
                  { link: true, type: "primary", onClick: () => emit("view-all", props.bucket) },
                  { default: () => "查看全部" }
                ),
                h(
                  ElButton,
                  { link: true, type: "primary", onClick: () => emit("reload") },
                  { default: () => [h(ElIcon, null, { default: () => h(RefreshRight) }), "刷新"] }
                ),
              ]),
            ]),
          default: () =>
            h("div", { class: "task-card__body" }, [
              props.tasks.length === 0
                ? h(ElEmpty, { imageSize: 64, description: "暂无事项" })
                : h(
                    "div",
                    { class: "task-list" },
                    props.tasks.map((task) =>
                      h(
                        "button",
                        { key: task.id, type: "button", class: "task-item", onClick: () => emit("open", task) },
                        [
                          h("div", { class: "task-item__main" }, [
                            h("span", { class: "task-item__title" }, task.title),
                            h(ElTag, { type: priorityType(task.priority), size: "small", effect: "plain" }, { default: () => statusText(task.status) }),
                          ]),
                          h("div", { class: "task-item__name" }, task.object_name || `#${task.object_id}`),
                          h("div", { class: "task-item__meta" }, [h("span", task.due_at || "无截止时间"), h("span", task.owner_user_name || "未分配")]),
                          h("div", { class: "task-item__action" }, task.action_text),
                        ]
                      )
                    )
                  ),
              hiddenCount() > 0
                ? h("button", { type: "button", class: "task-more", onClick: () => emit("view-all", props.bucket) }, `还有 ${hiddenCount()} 条，查看全部`)
                : null,
            ]),
        }
      );
  },
});

onMounted(reloadAll);
</script>

<style scoped lang="scss">
.workbench-page {
  display: flex;
  flex-direction: column;
  min-width: 0;
  height: auto;
  min-height: 100%;
  overflow: visible;
}

.workbench-hero,
.node-card,
:deep(.task-card) {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
}

.workbench-hero :deep(.el-card__body) {
  padding: 18px 20px;
}

.workbench-hero__main,
.section-head {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: flex-start;
  justify-content: space-between;
}

.workbench-hero__title {
  font-size: 22px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.workbench-hero__meta,
.section-sub {
  margin-top: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.workbench-hero__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(178px, 1fr));
  gap: 12px;
}

.metric-card {
  width: 100%;
  min-width: 0;
  min-height: 126px;
  padding: 14px;
  text-align: left;
  cursor: pointer;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  transition: border-color 0.2s, box-shadow 0.2s;

  &:hover,
  &:focus-visible {
    border-color: var(--el-color-primary-light-5);
    box-shadow: var(--el-box-shadow-light);
    outline: none;
  }
}

.metric-card__head {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
  min-width: 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);

  > span:first-child {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.metric-card__value {
  margin-top: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: clamp(20px, 2vw, 26px);
  font-weight: 700;
  line-height: 1.1;
  color: var(--el-color-primary);
  white-space: nowrap;
}

.metric-card__unit {
  margin-left: 4px;
  font-size: 12px;
  font-weight: 400;
  color: var(--el-text-color-secondary);
}

.metric-card__hint {
  margin-top: 10px;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 12px;
  color: var(--el-text-color-placeholder);
  white-space: nowrap;
}

.section-title {
  font-size: 16px;
  font-weight: 650;
  color: var(--el-text-color-primary);
}

.section-count {
  margin-left: 8px;
  font-size: 12px;
  font-weight: 400;
  color: var(--el-text-color-secondary);
}

.task-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  align-items: start;
}

.task-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;
  justify-content: flex-end;
}

:deep(.task-card) {
  width: 100%;
  min-width: 0;
  margin-bottom: 16px;

  .el-card__body {
    padding: 12px;
  }
}

.task-card__body {
  min-height: 260px;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.task-list--drawer {
  gap: 10px;
}

.task-item {
  width: 100%;
  padding: 12px;
  text-align: left;
  cursor: pointer;
  background: var(--el-fill-color-blank);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;

  &:hover {
    border-color: var(--el-color-primary-light-5);
  }
}

.task-item__main,
.task-item__meta {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  justify-content: space-between;
  min-width: 0;
}

.task-item__title {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 14px;
  font-weight: 650;
  color: var(--el-text-color-primary);
  white-space: nowrap;
}

.task-item__name {
  margin-top: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 13px;
  color: var(--el-text-color-regular);
  white-space: nowrap;
}

.task-item__meta {
  flex-wrap: wrap;
  margin-top: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.task-item__action {
  margin-top: 8px;
  font-size: 12px;
  color: var(--el-color-primary);
}

.task-more {
  width: 100%;
  padding: 10px 12px;
  margin-top: 10px;
  font-size: 13px;
  color: var(--el-color-primary);
  cursor: pointer;
  background: var(--el-color-primary-light-9);
  border: 1px solid var(--el-color-primary-light-7);
  border-radius: 8px;

  &:hover {
    background: var(--el-color-primary-light-8);
  }
}

.task-drawer {
  min-height: 220px;
}

.node-groups {
  display: flex;
  flex-direction: column;
  gap: 22px;
  padding-bottom: 8px;
}

.node-group__title {
  margin-bottom: 10px;
  font-size: 14px;
  font-weight: 650;
}

.node-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
}

.node-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
  min-height: 54px;
  padding: 10px 12px;
  cursor: pointer;
  background: var(--el-fill-color-blank);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;

  &:hover {
    border-color: var(--el-color-primary-light-5);
  }
}

.node-item__title {
  min-width: 0;
  font-size: 13px;
  line-height: 1.35;
  color: var(--el-text-color-regular);
  white-space: normal;
  word-break: break-word;
}

.node-item__count {
  flex: 0 0 auto;
  font-size: 18px;
  font-weight: 700;
  color: var(--el-color-primary);

  &.is-warning {
    color: var(--el-color-warning);
  }

  &.is-danger {
    color: var(--el-color-danger);
  }

  &.is-success {
    color: var(--el-color-success);
  }
}

@media (max-width: 1280px) {
  .task-grid {
    grid-template-columns: 1fr;
  }
}
</style>
