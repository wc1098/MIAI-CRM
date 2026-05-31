<template>
  <div class="app-container mp-admin-page">
    <el-card shadow="never">
      <template #header>
        <div class="toolbar">
          <div>
            <div class="toolbar-title">默契题配置</div>
            <div class="toolbar-subtitle">运营只需要填写题目、选项和分值，系统会按选中的正确答案自动保存配置。</div>
          </div>
          <el-button type="primary" @click="open()">新增题目</el-button>
        </div>
      </template>

      <el-table :data="rows" border>
        <el-table-column prop="question" label="题目" min-width="260" />
        <el-table-column label="分类" width="130">
          <template #default="{ row }">{{ categoryLabel(row.category) }}</template>
        </el-table-column>
        <el-table-column label="正确答案" min-width="150">
          <template #default="{ row }">{{ answerLabel(row) }}</template>
        </el-table-column>
        <el-table-column prop="correct_score" label="答对加分" width="100" />
        <el-table-column prop="wrong_score" label="答错加分" width="100" />
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

    <el-dialog v-model="visible" title="默契题" width="760px">
      <el-form :model="form" label-width="110px">
        <el-form-item label="题目">
          <el-input v-model="form.question" maxlength="255" show-word-limit placeholder="例如：TA 周末更喜欢怎样安排？" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="form.category" placeholder="请选择分类" style="width: 260px">
            <el-option v-for="item in categoryOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="选项">
          <div class="option-editor">
            <div v-for="(item, index) in form.options" :key="item.value || index" class="option-row">
              <el-radio v-model="form.recommended_answer" :label="item.value">正确</el-radio>
              <el-input v-model="item.label" placeholder="选项内容" @blur="syncRecommendedAnswer" />
              <el-button link type="danger" :disabled="form.options.length <= 2" @click="removeOption(index)">删除</el-button>
            </div>
            <el-button plain @click="addOption">添加选项</el-button>
          </div>
        </el-form-item>
        <el-form-item label="答案标签">
          <el-select v-model="form.match_tags" multiple allow-create filterable default-first-option placeholder="可选，用于后续匹配画像" style="width: 100%">
            <el-option label="沟通观念" value="communication" />
            <el-option label="生活方式" value="lifestyle" />
            <el-option label="约会偏好" value="dating" />
            <el-option label="长期关系" value="relationship" />
          </el-select>
        </el-form-item>
        <el-form-item label="答对/答错">
          <el-input-number v-model="form.correct_score" :min="0" />
          <span class="sep">/</span>
          <el-input-number v-model="form.wrong_score" :min="0" />
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
import MpUserAPI, { type MpUnlockQuestion } from "@/api/module_mp/user";

const categoryOptions = [
  { label: "约会偏好", value: "dating" },
  { label: "相处观念", value: "relationship" },
  { label: "生活方式", value: "lifestyle" },
  { label: "沟通表达", value: "communication" },
];

const rows = ref<MpUnlockQuestion[]>([]);
const visible = ref(false);
const editingId = ref<number>();
const form = reactive<MpUnlockQuestion>({
  question: "",
  options: [],
  recommended_answer: "",
  match_tags: [],
  correct_score: 10,
  wrong_score: 3,
  category: "dating",
  sort: 0,
  status: "0",
});
const enabled = computed({ get: () => form.status === "0", set: (value: boolean) => (form.status = value ? "0" : "1") });

async function load() {
  rows.value = (await MpUserAPI.listQuestions()).data.data || [];
}

function makeOptions(row?: MpUnlockQuestion) {
  const options = row?.options?.length ? row.options : [
    { label: "更喜欢安静聊天", value: "a" },
    { label: "更喜欢一起体验新鲜事", value: "b" },
  ];
  return options.map((item, index) => ({ label: item.label || "", value: item.value || String.fromCharCode(97 + index) }));
}

function open(row?: MpUnlockQuestion) {
  editingId.value = row?.id;
  Object.assign(form, {
    question: row?.question || "",
    options: makeOptions(row),
    recommended_answer: row?.recommended_answer || "a",
    match_tags: row?.match_tags || [],
    correct_score: row?.correct_score ?? 10,
    wrong_score: row?.wrong_score ?? 3,
    category: row?.category || "dating",
    sort: row?.sort ?? 0,
    status: row?.status || "0",
  });
  syncRecommendedAnswer();
  visible.value = true;
}

function addOption() {
  const value = String.fromCharCode(97 + form.options.length);
  form.options.push({ label: "", value });
  syncRecommendedAnswer();
}

function removeOption(index: number) {
  const removed = form.options[index];
  form.options.splice(index, 1);
  form.options.forEach((item, optionIndex) => (item.value = String.fromCharCode(97 + optionIndex)));
  if (removed?.value === form.recommended_answer) form.recommended_answer = form.options[0]?.value || "";
  syncRecommendedAnswer();
}

function syncRecommendedAnswer() {
  if (!form.options.some((item) => item.value === form.recommended_answer)) {
    form.recommended_answer = form.options[0]?.value || "";
  }
}

function categoryLabel(value?: string) {
  return categoryOptions.find((item) => item.value === value)?.label || value || "-";
}

function answerLabel(row: MpUnlockQuestion) {
  return row.options?.find((item) => item.value === row.recommended_answer)?.label || row.recommended_answer || "-";
}

async function save() {
  form.options = form.options.map((item, index) => ({ label: item.label?.trim(), value: item.value || String.fromCharCode(97 + index) }));
  if (!form.question.trim()) return ElMessage.warning("请填写题目");
  if (form.options.length < 2 || form.options.some((item) => !item.label)) return ElMessage.warning("请至少填写两个完整选项");
  syncRecommendedAnswer();
  await MpUserAPI.saveQuestion(form, editingId.value);
  ElMessage.success("保存成功");
  visible.value = false;
  load();
}

onMounted(load);
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; gap: 16px; }
.toolbar-title { font-size: 16px; font-weight: 600; }
.toolbar-subtitle { margin-top: 4px; color: var(--el-text-color-secondary); font-size: 12px; }
.sep { margin: 0 10px; color: var(--el-text-color-secondary); }
.option-editor { width: 100%; display: flex; flex-direction: column; gap: 10px; }
.option-row { display: grid; grid-template-columns: 72px minmax(0, 1fr) 44px; gap: 10px; align-items: center; }
</style>
