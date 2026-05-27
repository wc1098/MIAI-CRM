<template>
  <el-empty v-if="!insight" description="暂无当前画像" :image-size="72" />
  <el-descriptions v-else :column="2" border>
    <el-descriptions-item label="画像状态">{{ statusText }}</el-descriptions-item>
    <el-descriptions-item label="来源深访">{{ insight.source_interview_id || "-" }}</el-descriptions-item>
    <el-descriptions-item label="关键词" :span="2">{{ listText(insight.keywords) }}</el-descriptions-item>
    <el-descriptions-item label="性格标签" :span="2">{{ listText(insight.personality_tags) }}</el-descriptions-item>
    <el-descriptions-item label="家庭背景" :span="2">{{ insight.family_background || "-" }}</el-descriptions-item>
    <el-descriptions-item label="情感经历" :span="2">{{ insight.relationship_history || "-" }}</el-descriptions-item>
    <el-descriptions-item label="婚恋观" :span="2">{{ insight.marriage_view || "-" }}</el-descriptions-item>
    <el-descriptions-item label="沟通方式" :span="2">{{ insight.communication_style || "-" }}</el-descriptions-item>
    <el-descriptions-item label="建议新增一票否决" :span="2">{{ listText(insight.hard_reject_items) }}</el-descriptions-item>
    <el-descriptions-item label="建议重点偏好" :span="2">{{ listText(insight.soft_preference_items) }}</el-descriptions-item>
    <el-descriptions-item label="建议放宽条件" :span="2">{{ listText(insight.compromise_items) }}</el-descriptions-item>
    <el-descriptions-item label="风险提示" :span="2">{{ insight.risk_notes || "-" }}</el-descriptions-item>
    <el-descriptions-item label="推荐策略" :span="2">{{ insight.recommendation_strategy || "-" }}</el-descriptions-item>
    <el-descriptions-item label="红娘印象" :span="2">{{ insight.public_matchmaker_impression || "-" }}</el-descriptions-item>
  </el-descriptions>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{ insight?: Record<string, any> | null }>();

const statusText = computed(() => {
  if (props.insight?.profile_status === "stale") return "来源已作废，请重新深访";
  if (props.insight?.profile_status === "active") return "有效";
  return props.insight?.profile_status || "-";
});

function listText(value?: unknown) {
  return Array.isArray(value) && value.length ? value.join("、") : "-";
}
</script>
