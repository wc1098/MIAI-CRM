<template>
  <div class="app-container person-page">
    <el-card shadow="never" class="filter-card">
      <el-form :model="query" inline>
        <el-form-item label="关键词">
          <el-input
            v-model="query.keyword"
            clearable
            placeholder="编号/姓名/手机号"
            style="width: 220px"
            @keyup.enter="fetchList"
          />
        </el-form-item>
        <el-form-item label="门店">
          <el-select
            v-model="query.store_id"
            clearable
            filterable
            placeholder="全部"
            style="width: 180px"
          >
            <el-option
              v-for="item in deptOptions"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="销售">
          <el-select
            v-model="query.owner_sales_id"
            clearable
            filterable
            placeholder="全部"
            style="width: 160px"
          >
            <el-option
              v-for="item in userOptions"
              :key="item.id"
              :label="item.name || item.username"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="红娘">
          <el-select
            v-model="query.service_owner_user_id"
            clearable
            filterable
            placeholder="全部"
            style="width: 160px"
          >
            <el-option
              v-for="item in userOptions"
              :key="item.id"
              :label="item.name || item.username"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="身份">
          <el-select v-model="query.identity_tag" clearable placeholder="全部" style="width: 150px">
            <el-option
              v-for="item in identityOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="认证">
          <el-select
            v-model="query.certification_level"
            clearable
            placeholder="全部"
            style="width: 140px"
          >
            <el-option
              v-for="item in certificationOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="完整度">
          <el-select
            v-model="query.quality_level"
            clearable
            placeholder="全部"
            style="width: 130px"
          >
            <el-option label="高" value="good" />
            <el-option label="中" value="medium" />
            <el-option label="低" value="poor" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <ElButton type="primary" icon="Search" @click="fetchList">查询</ElButton>
          <ElButton icon="Refresh" @click="resetQuery">重置</ElButton>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="toolbar">
          <div>
            <div class="toolbar-title">用户资源中心</div>
            <div class="toolbar-note">
              全量 Person 综合查询与生命周期总览，只读展示，不处理业务流转
            </div>
          </div>
        </div>
      </template>

      <el-table v-loading="loading" :data="rows" border stripe row-key="person.id">
        <el-table-column label="编号" width="110">
          <template #default="{ row }">{{ row.person.display_no || "-" }}</template>
        </el-table-column>
        <el-table-column label="姓名" min-width="120">
          <template #default="{ row }">
            <ElButton link type="primary" @click="openDetail(row.person.id)">
              {{ row.person.name || "-" }}
            </ElButton>
          </template>
        </el-table-column>
        <el-table-column label="性别/年龄" width="110">
          <template #default="{ row }">
            {{ genderLabel(row.person.gender) }} / {{ row.person.age ?? "-" }}
          </template>
        </el-table-column>
        <el-table-column label="手机号" min-width="130">
          <template #default="{ row }">
            {{ row.person.mobile_masked || row.person.primary_mobile || "-" }}
          </template>
        </el-table-column>
        <el-table-column label="门店" min-width="130">
          <template #default="{ row }">{{ row.store?.name || "-" }}</template>
        </el-table-column>
        <el-table-column label="销售" min-width="110">
          <template #default="{ row }">{{ row.owner_sales?.name || "-" }}</template>
        </el-table-column>
        <el-table-column label="红娘" min-width="110">
          <template #default="{ row }">{{ row.service_owner?.name || "-" }}</template>
        </el-table-column>
        <el-table-column label="身份" min-width="220">
          <template #default="{ row }">
            <el-tag
              v-for="tag in row.identity_tags"
              :key="tag"
              class="tag"
              size="small"
              :type="identityType(tag)"
            >
              {{ identityLabel(tag) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="认证" width="110">
          <template #default="{ row }">
            {{ certificationLabel(row.person.certification_level) }}
          </template>
        </el-table-column>
        <el-table-column label="完整度" width="130">
          <template #default="{ row }">
            <el-progress
              :percentage="row.quality.score"
              :stroke-width="8"
              :status="qualityStatus(row.quality.quality_level)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="latest_activity_at" label="最近活动" min-width="170" />
        <el-table-column fixed="right" label="操作" width="120">
          <template #default="{ row }">
            <ElButton
              v-hasPerm="['crm:person:detail']"
              link
              type="primary"
              icon="View"
              @click="openDetail(row.person.id)"
            >
              详情
            </ElButton>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination
          v-model:current-page="query.page_no"
          v-model:page-size="query.page_size"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchList"
          @current-change="fetchList"
        />
      </div>
    </el-card>

    <el-drawer v-model="detailVisible" size="86%" destroy-on-close class="person-drawer">
      <template #header>
        <div class="drawer-head">
          <div>
            <div class="drawer-title">{{ detail?.person.name || "资源详情" }}</div>
            <div class="drawer-subtitle">
              编号：{{ detail?.person.display_no || "-" }} ·
              {{ genderLabel(detail?.person.gender) }} · {{ detail?.person.age ?? "-" }}岁
            </div>
          </div>
          <div class="drawer-actions">
            <ElButton v-hasPerm="['crm:person:view_phone']" icon="Phone" @click="viewPhone">
              查看手机号
            </ElButton>
            <ElButton v-hasPerm="['crm:person:view_id_card']" icon="Postcard" @click="viewIdCard">
              查看身份证
            </ElButton>
            <ElButton v-hasPerm="['crm:person:interview:create']" type="primary" icon="ChatLineSquare" @click="openInterview">
              新增深访
            </ElButton>
          </div>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="总览" name="overview">
          <div class="overview-grid">
            <section class="profile-panel">
              <el-carousel
                v-if="detail?.person.photo_urls?.length"
                height="260px"
                indicator-position="outside"
              >
                <el-carousel-item v-for="url in detail.person.photo_urls" :key="url">
                  <el-image
                    class="profile-photo"
                    :src="url"
                    fit="cover"
                    :preview-src-list="detail.person.photo_urls"
                    preview-teleported
                  />
                </el-carousel-item>
              </el-carousel>
              <div v-else class="photo-empty">暂无照片</div>
            </section>
            <section class="profile-panel">
              <h3>基础资料</h3>
              <ElDescriptions :column="2" border>
                <ElDescriptionsItem label="姓名">
                  {{ detail?.person.name || "-" }}
                </ElDescriptionsItem>
                <ElDescriptionsItem label="手机号">
                  {{ fullPhone || detail?.person.mobile_masked || "-" }}
                </ElDescriptionsItem>
                <ElDescriptionsItem label="微信">
                  {{ detail?.person.wechat || "-" }}
                </ElDescriptionsItem>
                <ElDescriptionsItem label="身份证">
                  {{ fullIdCard || detail?.person.id_card_no_masked || "-" }}
                </ElDescriptionsItem>
                <ElDescriptionsItem label="身高">
                  {{ detail?.person.height_cm ? `${detail.person.height_cm} cm` : "-" }}
                </ElDescriptionsItem>
                <ElDescriptionsItem label="学历">
                  {{ optionLabel(dictOptions.education, detail?.person.education) }}
                </ElDescriptionsItem>
                <ElDescriptionsItem label="年收入">
                  {{ optionLabel(dictOptions.annualIncome, detail?.person.annual_income) }}
                </ElDescriptionsItem>
                <ElDescriptionsItem label="婚况">
                  {{ optionLabel(dictOptions.maritalStatus, detail?.person.marital_status) }}
                </ElDescriptionsItem>
                <ElDescriptionsItem label="职业">
                  {{
                    optionLabel(dictOptions.occupation, detail?.person.occupation_code) ||
                    detail?.person.occupation ||
                    "-"
                  }}
                </ElDescriptionsItem>
                <ElDescriptionsItem label="常驻地">
                  {{ detail?.person.residence || "-" }}
                </ElDescriptionsItem>
              </ElDescriptions>
            </section>
            <section class="profile-panel quality-panel">
              <h3>资料质量</h3>
              <el-progress
                type="dashboard"
                :percentage="detail?.quality.score || 0"
                :status="qualityStatus(detail?.quality.quality_level)"
              />
              <div class="score-parts">
                <span>基础 {{ detail?.quality.basic_score || 0 }}%</span>
                <span>展示 {{ detail?.quality.display_score || 0 }}%</span>
                <span>服务 {{ detail?.quality.service_score || 0 }}%</span>
              </div>
              <div class="risk-list">
                <el-tag
                  v-for="risk in detail?.quality.risk_flags || []"
                  :key="risk.type"
                  :type="risk.level === 'danger' ? 'danger' : 'warning'"
                  class="tag"
                >
                  {{ risk.title }}
                </el-tag>
              </div>
            </section>
          </div>
        </el-tab-pane>

        <el-tab-pane label="销售链路" name="sales">
          <RelationBlock title="线索" kind="lead" :data="detail?.relations.lead" />
          <RelationBlock title="建档客户" kind="customer" :data="detail?.relations.customer" />
        </el-tab-pane>

        <el-tab-pane label="服务链路" name="service">
          <RelationBlock title="VIP" kind="vip" :data="detail?.relations.vip" />
          <RelationBlock
            title="服务工单"
            kind="serviceCase"
            :data="detail?.relations.service_case"
          />
        </el-tab-pane>

        <el-tab-pane label="候选/备选" name="candidate">
          <RelationBlock title="候选身份" kind="candidate" :data="detail?.relations.candidate" />
          <h3>备选库归属</h3>
          <el-table :data="detail?.relations.backup_items || []" border stripe>
            <el-table-column prop="matchmaker_name" label="服务红娘" min-width="120" />
            <el-table-column prop="store_name" label="门店" min-width="140" />
            <el-table-column label="来源" min-width="140">
              <template #default="{ row }">
                {{ optionLabel(dictOptions.candidateSourceType, row.source_type) }}
              </template>
            </el-table-column>
            <el-table-column prop="approved_at" label="审批时间" min-width="170" />
          </el-table>
          <h3>加入申请</h3>
          <el-table :data="detail?.relations.join_requests || []" border stripe>
            <el-table-column prop="request_matchmaker_name" label="申请红娘" min-width="120" />
            <el-table-column prop="request_store_name" label="申请门店" min-width="140" />
            <el-table-column label="范围" width="100">
              <template #default="{ row }">
                {{ optionLabel(dictOptions.candidateSearchScope, row.request_scope) }}
              </template>
            </el-table-column>
            <el-table-column label="状态" width="110">
              <template #default="{ row }">
                {{ optionLabel(dictOptions.candidateJoinRequestStatus, row.review_status) }}
              </template>
            </el-table-column>
            <el-table-column prop="created_time" label="申请时间" min-width="170" />
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="小程序/订阅" name="mp">
          <RelationBlock
            title="小程序用户"
            kind="miniprogramUser"
            :data="detail?.relations.miniprogram_user"
          />
          <RelationBlock
            title="订阅服务"
            kind="subscription"
            :data="detail?.relations.subscription"
          />
        </el-tab-pane>

        <el-tab-pane label="认证/画像" name="profile">
          <h3>当前画像</h3>
          <person-profile-insight-panel :insight="detail?.profile_insight" />
          <RelationBlock
            title="认证摘要"
            kind="certification"
            :data="detail?.relations.certification"
          />
          <RelationBlock
            title="择偶要求"
            kind="partnerPreference"
            :data="detail?.relations.partner_preference"
          />
          <RelationBlock title="AI画像" kind="aiProfile" :data="detail?.relations.ai_profile" />
          <h3>缺失项</h3>
          <el-alert :title="missingText" type="info" show-icon :closable="false" />
        </el-tab-pane>

        <el-tab-pane label="深访记录" name="interviews">
          <el-table :data="interviewRows" border stripe>
            <el-table-column prop="interviewed_at" label="时间" min-width="160" show-overflow-tooltip />
            <el-table-column prop="interview_type" label="类型" width="110" />
            <el-table-column prop="interview_method" label="方式" width="110" />
            <el-table-column label="当前来源" width="90">
              <template #default="{ row }">
                <el-tag v-if="row.is_current_source" type="success">是</el-tag>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column prop="summary" label="摘要" min-width="220" show-overflow-tooltip />
            <el-table-column prop="content" label="内容" min-width="260" show-overflow-tooltip />
            <el-table-column prop="matchmaker_name" label="红娘" width="120" show-overflow-tooltip />
            <el-table-column prop="interview_status" label="状态" width="100" />
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="生命周期" name="timeline">
          <el-timeline>
            <el-timeline-item v-for="item in timeline" :key="item.id" :timestamp="item.occurred_at">
              <div class="timeline-title">
                {{ timelineLabel(item.source_type) }} · {{ timelineTitle(item) }}
              </div>
              <div class="timeline-content">{{ item.content || "-" }}</div>
              <div class="muted">
                操作人：{{ item.operator_user_name || item.operator_user_id || "-" }}
              </div>
            </el-timeline-item>
          </el-timeline>
        </el-tab-pane>

        <el-tab-pane label="敏感审计" name="sensitive">
          <el-table :data="sensitiveLogs" border stripe>
            <el-table-column label="类型" width="140">
              <template #default="{ row }">{{ sensitiveTypeLabel(row.access_type) }}</template>
            </el-table-column>
            <el-table-column prop="operator_name" label="查看人" width="120" />
            <el-table-column prop="reason" label="原因" min-width="220" show-overflow-tooltip />
            <el-table-column prop="accessed_at" label="查看时间" min-width="170" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-drawer>

    <el-dialog v-model="interviewVisible" title="新增深访" width="980px" destroy-on-close>
      <person-insight-interview-form ref="interviewFormRef" v-model="interviewForm" />
      <template #footer>
        <ElButton @click="interviewVisible = false">取消</ElButton>
        <ElButton type="primary" :loading="submitLoading" @click="submitInterview">保存深访</ElButton>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, onMounted, reactive, ref } from "vue";
import {
  ElButton,
  ElDescriptions,
  ElDescriptionsItem,
  ElEmpty,
  ElMessage,
  ElMessageBox,
} from "element-plus";
import PersonAPI, {
  type PersonDetail,
  type PersonInterview,
  type PersonInterviewForm,
  type PersonPageQuery,
  type PersonRecord,
  type PersonTimelineItem,
  type PersonUserOption,
  type SensitiveLogRecord,
} from "@/api/module_crm/person";
import DictAPI, { type DictDataTable } from "@/api/module_system/dict";
import LeadAPI from "@/api/module_crm/lead";
import PersonInsightInterviewForm from "@/views/module_miailove/components/PersonInsightInterviewForm.vue";
import PersonProfileInsightPanel from "@/views/module_miailove/components/PersonProfileInsightPanel.vue";

const loading = ref(false);
const submitLoading = ref(false);
const detailVisible = ref(false);
const activeTab = ref("overview");
const rows = ref<PersonRecord[]>([]);
const total = ref(0);
const detail = ref<PersonDetail>();
const timeline = ref<PersonTimelineItem[]>([]);
const interviewRows = ref<PersonInterview[]>([]);
const sensitiveLogs = ref<SensitiveLogRecord[]>([]);
const fullPhone = ref("");
const fullIdCard = ref("");
const deptOptions = ref<Array<{ id: number; name?: string }>>([]);
const userOptions = ref<PersonUserOption[]>([]);
const channelOptions = ref<Array<{ label: string; value: string }>>([]);
const interviewVisible = ref(false);
const interviewFormRef = ref<InstanceType<typeof PersonInsightInterviewForm>>();
const interviewForm = ref<PersonInterviewForm>({
  interview_scope: "general",
  interview_type: "first",
  interview_method: "offline",
  content: "",
  structured_payload: {},
  keywords: [],
});

const query = reactive<PersonPageQuery>({
  page_no: 1,
  page_size: 10,
});

const dictOptions = reactive({
  gender: [] as Array<{ label: string; value: string }>,
  education: [] as Array<{ label: string; value: string }>,
  annualIncome: [] as Array<{ label: string; value: string }>,
  maritalStatus: [] as Array<{ label: string; value: string }>,
  occupation: [] as Array<{ label: string; value: string }>,
  leadType: [] as Array<{ label: string; value: string }>,
  leadPoolType: [] as Array<{ label: string; value: string }>,
  leadProcessAction: [] as Array<{ label: string; value: string }>,
  customerStage: [] as Array<{ label: string; value: string }>,
  customerReturnReason: [] as Array<{ label: string; value: string }>,
  customerProcessRecordType: [] as Array<{ label: string; value: string }>,
  vipLevel: [] as Array<{ label: string; value: string }>,
  vipStatus: [] as Array<{ label: string; value: string }>,
  serviceCaseStatus: [] as Array<{ label: string; value: string }>,
  servicePoolType: [] as Array<{ label: string; value: string }>,
  closeReviewStatus: [] as Array<{ label: string; value: string }>,
  candidateSourceType: [] as Array<{ label: string; value: string }>,
  candidateSearchScope: [] as Array<{ label: string; value: string }>,
  candidateJoinRequestStatus: [] as Array<{ label: string; value: string }>,
});

type RelationKind =
  | "lead"
  | "customer"
  | "vip"
  | "serviceCase"
  | "candidate"
  | "miniprogramUser"
  | "subscription"
  | "certification"
  | "partnerPreference"
  | "aiProfile";

interface RelationField {
  key: string;
  label: string;
}

const relationFields: Record<RelationKind, RelationField[]> = {
  lead: [
    { key: "id", label: "线索ID" },
    { key: "store_id", label: "归属门店" },
    { key: "owner_sales_id", label: "归属销售" },
    { key: "pool_type", label: "归属池" },
    { key: "lead_type", label: "线索类型" },
    { key: "source_channel_code", label: "来源渠道" },
    { key: "latest_follow_at", label: "最近跟进" },
    { key: "next_follow_at", label: "下次跟进" },
    { key: "assigned_at", label: "分配时间" },
    { key: "converted_customer_at", label: "转客户时间" },
    { key: "created_time", label: "创建时间" },
    { key: "updated_time", label: "更新时间" },
  ],
  customer: [
    { key: "id", label: "客户ID" },
    { key: "lead_id", label: "来源线索ID" },
    { key: "store_id", label: "归属门店" },
    { key: "owner_user_id", label: "归属销售" },
    { key: "current_stage", label: "当前阶段" },
    { key: "max_stage", label: "最高阶段" },
    { key: "latest_follow_at", label: "最近跟进" },
    { key: "next_follow_at", label: "下次跟进" },
    { key: "converted_vip_at", label: "转VIP时间" },
    { key: "ended_at", label: "结束时间" },
    { key: "end_reason", label: "结束原因" },
  ],
  vip: [
    { key: "id", label: "VIP ID" },
    { key: "customer_id", label: "客户ID" },
    { key: "contract_id", label: "合同ID" },
    { key: "store_id", label: "服务门店" },
    { key: "service_owner_user_id", label: "服务红娘" },
    { key: "vip_level", label: "VIP等级" },
    { key: "vip_status", label: "VIP状态" },
    { key: "started_at", label: "开始时间" },
    { key: "ended_at", label: "结束时间" },
    { key: "assigned_at", label: "分配时间" },
  ],
  serviceCase: [
    { key: "id", label: "工单ID" },
    { key: "vip_id", label: "VIP ID" },
    { key: "customer_id", label: "客户ID" },
    { key: "contract_id", label: "合同ID" },
    { key: "store_id", label: "服务门店" },
    { key: "owner_matchmaker_id", label: "服务红娘" },
    { key: "pool_type", label: "服务池" },
    { key: "case_status", label: "工单状态" },
    { key: "close_review_status", label: "关单审核" },
  ],
  candidate: [
    { key: "id", label: "候选ID" },
    { key: "candidate_status", label: "候选状态" },
    { key: "created_time", label: "创建时间" },
    { key: "updated_time", label: "更新时间" },
  ],
  miniprogramUser: [
    { key: "id", label: "小程序用户ID" },
    { key: "mobile", label: "手机号" },
    { key: "nickname", label: "昵称" },
    { key: "registered_at", label: "注册时间" },
    { key: "last_login_at", label: "最近登录" },
    { key: "is_invisible", label: "隐身状态" },
    { key: "allow_user_wall", label: "允许上墙" },
  ],
  subscription: [
    { key: "id", label: "订阅ID" },
    { key: "plan_id", label: "套餐ID" },
    { key: "started_at", label: "开始时间" },
    { key: "expired_at", label: "过期时间" },
    { key: "total_quota", label: "总名额" },
    { key: "used_quota", label: "已使用名额" },
    { key: "subscription_status", label: "订阅状态" },
    { key: "last_unlock_at", label: "最近解锁" },
  ],
  certification: [
    { key: "id", label: "认证申请ID" },
    { key: "level_code", label: "认证等级编码" },
    { key: "level_name", label: "认证等级" },
    { key: "certification_level", label: "认证等级" },
    { key: "application_status", label: "申请状态" },
    { key: "paid_at", label: "支付时间" },
    { key: "approved_at", label: "通过时间" },
    { key: "certification_summary", label: "认证摘要" },
  ],
  partnerPreference: [
    { key: "profile_summary", label: "择偶摘要" },
    { key: "strictness_level", label: "严格程度" },
    { key: "is_final", label: "最终版本" },
    { key: "version_no", label: "版本号" },
    { key: "source_type", label: "来源类型" },
    { key: "updated_time", label: "更新时间" },
  ],
  aiProfile: [
    { key: "profile_type", label: "画像类型" },
    { key: "source_type", label: "来源类型" },
    { key: "content", label: "画像内容" },
    { key: "generation_status", label: "生成状态" },
    { key: "model_name", label: "模型" },
    { key: "generated_at", label: "生成时间" },
  ],
};

const identityOptions = [
  { label: "小程序用户", value: "mp_user" },
  { label: "线索", value: "lead" },
  { label: "建档客户", value: "customer" },
  { label: "VIP", value: "vip" },
  { label: "服务工单", value: "service" },
  { label: "候选资源", value: "candidate" },
  { label: "备选库", value: "backup" },
  { label: "订阅", value: "subscription" },
];

const certificationOptions = [
  { label: "未认证", value: "none" },
  { label: "基础认证", value: "basic" },
  { label: "增强认证", value: "enhanced" },
  { label: "尊享认证", value: "premium" },
];

const RelationBlock = defineComponent({
  props: {
    title: { type: String, required: true },
    kind: { type: String as () => RelationKind, default: "lead" },
    data: { type: Object, default: null },
  },
  setup(props) {
    return () =>
      h("section", { class: "relation-block" }, [
        h("div", { class: "relation-head" }, [h("h3", props.title)]),
        props.data
          ? h(ElDescriptions, { column: 2, border: true }, () =>
              relationDisplayFields(props.kind, props.data as Record<string, unknown>).map(
                (field) =>
                  h(ElDescriptionsItem, { label: field.label }, () =>
                    displayFieldValue(field.key, (props.data as Record<string, unknown>)[field.key])
                  )
              )
            )
          : h(ElEmpty, { description: "暂无数据" }),
      ]);
  },
});

const missingText = computed(() => {
  const quality = detail.value?.quality;
  if (!quality) return "暂无资料质量信息";
  const items = [...quality.missing_basic, ...quality.missing_display, ...quality.missing_service];
  return items.length ? `缺失：${items.join("、")}` : "资料完整度较好";
});

onMounted(async () => {
  await Promise.all([loadOptions(), loadDictOptions()]);
  await fetchList();
});

async function fetchList() {
  loading.value = true;
  try {
    const res = await PersonAPI.listPerson(query);
    rows.value = res.data.data.items || [];
    total.value = res.data.data.total || 0;
  } finally {
    loading.value = false;
  }
}

function resetQuery() {
  Object.assign(query, { page_no: 1, page_size: query.page_size });
  delete query.keyword;
  delete query.store_id;
  delete query.owner_sales_id;
  delete query.service_owner_user_id;
  delete query.identity_tag;
  delete query.certification_level;
  delete query.quality_level;
  fetchList();
}

async function openDetail(personId: number) {
  activeTab.value = "overview";
  fullPhone.value = "";
  fullIdCard.value = "";
  const [detailRes, timelineRes, logRes] = await Promise.all([
    PersonAPI.detailPerson(personId),
    PersonAPI.timelinePerson(personId),
    PersonAPI.sensitiveLog(personId),
  ]);
  detail.value = detailRes.data.data;
  timeline.value = timelineRes.data.data || [];
  sensitiveLogs.value = logRes.data.data || [];
  await loadInterviews(personId);
  detailVisible.value = true;
}

async function loadInterviews(personId: number) {
  try {
    const res = await PersonAPI.listInterviews(personId);
    interviewRows.value = res.data.data || [];
  } catch {
    interviewRows.value = [];
  }
}

function openInterview() {
  if (!detail.value) return;
  interviewForm.value = {
    interview_scope: "general",
    interview_type: "first",
    interview_method: "offline",
    interviewed_at: undefined,
    content: "",
    structured_payload: {},
    keywords: [],
    summary: undefined,
    manual_notes: undefined,
  };
  interviewVisible.value = true;
}

async function submitInterview() {
  if (!detail.value) return;
  const valid = await interviewFormRef.value?.validate();
  if (!valid) return;
  submitLoading.value = true;
  try {
    await PersonAPI.createInterview(detail.value.person.id, interviewForm.value);
    ElMessage.success("深访记录已保存");
    interviewVisible.value = false;
    const detailRes = await PersonAPI.detailPerson(detail.value.person.id);
    detail.value = detailRes.data.data;
    await loadInterviews(detail.value.person.id);
  } finally {
    submitLoading.value = false;
  }
}

async function viewPhone() {
  if (!detail.value) return;
  const reason = await promptReason("查看完整手机号");
  if (!reason) return;
  const res = await PersonAPI.viewPhone(detail.value.person.id, reason);
  fullPhone.value = res.data.data.primary_mobile || "";
  await reloadSensitiveLog();
  ElMessage.success("已记录敏感查看审计");
}

async function viewIdCard() {
  if (!detail.value) return;
  const reason = await promptReason("查看完整身份证");
  if (!reason) return;
  const res = await PersonAPI.viewIdCard(detail.value.person.id, reason);
  fullIdCard.value = res.data.data.id_card_no || "";
  await reloadSensitiveLog();
  ElMessage.success("已记录敏感查看审计");
}

async function promptReason(title: string) {
  try {
    const res = await ElMessageBox.prompt("请输入查看原因", title, {
      inputType: "textarea",
      inputValidator: (value) => !!value?.trim() || "查看原因不能为空",
    });
    return res.value.trim();
  } catch {
    return "";
  }
}

async function reloadSensitiveLog() {
  if (!detail.value) return;
  const res = await PersonAPI.sensitiveLog(detail.value.person.id);
  sensitiveLogs.value = res.data.data || [];
}

async function loadOptions() {
  const [storeRes, userRes, channelRes] = await Promise.all([
    PersonAPI.storeOptions(),
    PersonAPI.userOptions(),
    LeadAPI.sourceOptions(),
  ]);
  deptOptions.value = storeRes.data.data || [];
  userOptions.value = userRes.data.data || [];
  channelOptions.value = (channelRes.data.data || []).map((item) => ({
    label: item.name || item.code || "",
    value: item.code || "",
  }));
}

async function loadDictOptions() {
  const dictMap = {
    gender: "sys_user_sex",
    education: "crm_education",
    annualIncome: "crm_annual_income",
    maritalStatus: "crm_marital_status",
    occupation: "crm_occupation",
    leadType: "crm_lead_type",
    leadPoolType: "crm_lead_pool_type",
    leadProcessAction: "crm_lead_process_action",
    customerStage: "crm_customer_stage",
    customerReturnReason: "crm_customer_return_reason",
    customerProcessRecordType: "crm_customer_process_record_type",
    vipLevel: "crm_vip_level",
    vipStatus: "crm_vip_status",
    serviceCaseStatus: "service_case_status",
    servicePoolType: "service_pool_type",
    closeReviewStatus: "close_review_status",
    candidateSourceType: "candidate_source_type",
    candidateSearchScope: "candidate_search_scope",
    candidateJoinRequestStatus: "candidate_join_request_status",
  };
  await Promise.all(
    Object.entries(dictMap).map(async ([key, type]) => {
      const res = await DictAPI.getInitDict(type);
      dictOptions[key as keyof typeof dictOptions] = ((res.data.data as DictDataTable[]) || []).map(
        (item) => ({
          label: item.dict_label || item.dict_value || "",
          value: item.dict_value || "",
        })
      );
    })
  );
}

function genderLabel(value?: string) {
  const normalized = normalizeGenderValue(value);
  const label = dictOptions.gender.find((item) => item.value === normalized)?.label;
  return label || fallbackGenderLabel(normalized || value);
}

function identityLabel(value: string) {
  return identityOptions.find((item) => item.value === value)?.label || value;
}

function identityType(value: string) {
  return (
    (
      {
        vip: "danger",
        service: "success",
        customer: "warning",
        lead: "primary",
        backup: "success",
      } as Record<string, any>
    )[value] || "info"
  );
}

function certificationLabel(value?: string) {
  return certificationOptions.find((item) => item.value === value)?.label || value || "-";
}

function qualityStatus(value?: string) {
  if (value === "good") return "success";
  if (value === "poor") return "exception";
  return undefined;
}

function optionLabel(options: Array<{ label: string; value: string }>, value?: string) {
  if (!value) return "-";
  return options.find((item) => item.value === value)?.label || value;
}

function fallbackGenderLabel(value?: string) {
  return (
    (
      { "0": "男", "1": "女", "2": "未知", male: "男", female: "女", unknown: "未知" } as Record<
        string,
        string
      >
    )[value || ""] ||
    value ||
    "-"
  );
}

function normalizeGenderValue(value?: string) {
  return ({ male: "0", female: "1", unknown: "2" } as Record<string, string>)[value || ""] || value;
}

function relationDisplayFields(kind: RelationKind, data: Record<string, unknown>) {
  const configured = relationFields[kind] || [];
  const used = new Set(configured.map((item) => item.key));
  const extras = Object.keys(data)
    .filter((key) => !used.has(key))
    .map((key) => ({ key, label: fieldFallbackLabel(key) }));
  return [...configured, ...extras];
}

function displayFieldValue(field: string, value: unknown) {
  if (value === null || value === undefined || value === "") return "-";
  if (field === "store_id") return deptName(value) || `ID ${value}`;
  if (
    ["owner_sales_id", "owner_user_id", "service_owner_user_id", "owner_matchmaker_id"].includes(
      field
    )
  ) {
    return userName(value) || `ID ${value}`;
  }
  if (field === "gender") return genderLabel(String(value));
  if (field === "source_channel_code") return channelLabel(String(value));
  if (field === "lead_type") return optionLabel(dictOptions.leadType, String(value));
  if (field === "pool_type") return serviceOrLeadPoolLabel(String(value));
  if (["current_stage", "max_stage"].includes(field))
    return optionLabel(dictOptions.customerStage, String(value));
  if (field === "end_reason") return customerEndReasonLabel(String(value));
  if (field === "vip_level") return optionLabel(dictOptions.vipLevel, String(value));
  if (field === "vip_status") return optionLabel(dictOptions.vipStatus, String(value));
  if (field === "case_status") return optionLabel(dictOptions.serviceCaseStatus, String(value));
  if (field === "close_review_status")
    return optionLabel(dictOptions.closeReviewStatus, String(value));
  if (field === "candidate_status") return candidateStatusLabel(String(value));
  if (field === "subscription_status") return subscriptionStatusLabel(String(value));
  if (["application_status", "record_status"].includes(field))
    return certificationStatusLabel(String(value));
  if (field === "certification_level") return certificationLabel(String(value));
  if (field === "strictness_level") return strictnessLabel(String(value));
  if (field === "source_type") return sourceTypeLabel(String(value));
  if (field === "generation_status") return aiStatusLabel(String(value));
  if (typeof value === "boolean") return boolLabel(value);
  return displayValue(value);
}

function displayValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "-";
  if (Array.isArray(value)) return value.length ? value.join("、") : "-";
  if (typeof value === "boolean") return boolLabel(value);
  if (typeof value === "object") return JSON.stringify(value, null, 2);
  return String(value);
}

function boolLabel(value?: boolean | null) {
  if (value === true) return "是";
  if (value === false) return "否";
  return "-";
}

function deptName(value: unknown) {
  const id = Number(value);
  if (!Number.isFinite(id)) return "";
  return deptOptions.value.find((item) => item.id === id)?.name || "";
}

function userName(value: unknown) {
  const id = Number(value);
  if (!Number.isFinite(id)) return "";
  return (
    userOptions.value.find((item) => item.id === id)?.name ||
    userOptions.value.find((item) => item.id === id)?.username ||
    ""
  );
}

function channelLabel(value: string) {
  return (
    channelOptions.value.find((item) => item.value === value)?.label ||
    (
      {
        MINIAPP_REGISTER: "小程序注册",
        MANUAL_CREATE: "后台手动创建",
        IMPORT: "批量导入",
        EXTERNAL_PUSH: "外部推送",
      } as Record<string, string>
    )[value] ||
    value ||
    "-"
  );
}

function serviceOrLeadPoolLabel(value: string) {
  return optionLabel(dictOptions.leadPoolType, value) !== value
    ? optionLabel(dictOptions.leadPoolType, value)
    : optionLabel(dictOptions.servicePoolType, value);
}

function candidateStatusLabel(value: string) {
  return (
    ({ active: "有效", inactive: "停用", disabled: "停用" } as Record<string, string>)[value] ||
    value ||
    "-"
  );
}

function subscriptionStatusLabel(value: string) {
  return (
    ({ active: "生效中", expired: "已过期", void: "作废" } as Record<string, string>)[value] ||
    value ||
    "-"
  );
}

function customerEndReasonLabel(value: string) {
  return (
    {
      converted_vip: "已转VIP",
      return_lead: "退回线索",
      returned_lead: "退回线索",
      closed: "结束服务",
    }[value] ||
    optionLabel(dictOptions.customerReturnReason, value) ||
    value ||
    "-"
  );
}

function certificationStatusLabel(value: string) {
  return (
    (
      {
        pending_payment: "待支付",
        paid_pending_submit: "待提交",
        in_progress: "进行中",
        not_submitted: "未提交",
        submitted: "已提交",
        verifying: "核验中",
        pending_review: "待审核",
        approved: "已通过",
        rejected: "已驳回",
        expired: "已过期",
        void: "已作废",
      } as Record<string, string>
    )[value] ||
    value ||
    "-"
  );
}

function strictnessLabel(value: string) {
  return (
    ({ loose: "宽松", normal: "正常", strict: "严格" } as Record<string, string>)[value] ||
    value ||
    "-"
  );
}

function sourceTypeLabel(value: string) {
  return (
    (
      {
        register: "小程序注册",
        admin_update: "后台维护",
        deep_interview: "红娘深访",
        manual: "手动维护",
        ai: "AI生成",
      } as Record<string, string>
    )[value] ||
    value ||
    "-"
  );
}

function aiStatusLabel(value: string) {
  return (
    (
      {
        pending: "等待生成",
        processing: "生成中",
        success: "已生成",
        failed: "生成失败",
        cancelled: "已取消",
      } as Record<string, string>
    )[value] ||
    value ||
    "-"
  );
}

function fieldFallbackLabel(key: string) {
  return (
    (
      {
        id: "ID",
        created_time: "创建时间",
        updated_time: "更新时间",
      } as Record<string, string>
    )[key] || key
  );
}

function timelineLabel(value: string) {
  return (
    (
      {
        source_event: "来源事件",
        lead_lifecycle: "线索",
        customer_lifecycle: "客户",
        service_log: "服务",
        candidate_join_request: "备选申请",
        certification: "认证",
      } as Record<string, string>
    )[value] || value
  );
}

function timelineTitle(item: PersonTimelineItem) {
  const title = item.title || "";
  if (item.source_type === "source_event") return eventTypeLabel(title);
  if (item.source_type === "lead_lifecycle") {
    return lifecycleOperationLabel(title);
  }
  if (["customer_lifecycle", "service_log"].includes(item.source_type)) {
    return lifecycleOperationLabel(title, item.source_type);
  }
  if (item.source_type === "candidate_join_request") {
    const status = String(item.payload?.review_status || title.replace("备选加入申请-", ""));
    return `备选加入申请-${optionLabel(dictOptions.candidateJoinRequestStatus, status)}`;
  }
  if (item.source_type === "certification") {
    const status = String(item.payload?.record_status || title.split("-").pop() || "");
    const itemName = title.includes("-") ? title.slice(0, title.lastIndexOf("-")) : title;
    return `${itemName || "认证资料"}-${certificationStatusLabel(status)}`;
  }
  return title || "-";
}

function lifecycleOperationLabel(value: string, sourceType?: string) {
  const code = value.trim();
  if (!code) return "-";
  if (sourceType === "service_log") return serviceOperationLabel(code);
  if (code.startsWith("service_")) return serviceOperationLabel(code.replace("service_", ""));
  return optionLabel(dictOptions.leadProcessAction, code) !== code
    ? optionLabel(dictOptions.leadProcessAction, code)
    : optionLabel(dictOptions.customerProcessRecordType, code) !== code
      ? optionLabel(dictOptions.customerProcessRecordType, code)
      : lifecycleStaticLabel(code);
}

function lifecycleStaticLabel(value: string) {
  return (
    (
      {
        create_from_lead: "线索转客户",
        edit: "编辑资料",
        transfer_owner: "同店转派",
        transfer_store: "跨店转交",
        return_lead: "退回线索",
        returned_lead: "退回线索",
        service_profile_update: "服务阶段编辑VIP资料",
        convert_customer: "线索转建档客户",
        converted_customer: "已转建档客户",
        customer_convert: "线索转建档客户",
        customer_return: "客户退回线索",
        converted_vip: "已转VIP",
        create: "新增线索",
        assign: "分配线索",
        claim: "领取线索",
        auto_reclaim: "自动回公海",
        sync_mp_user: "同步小程序用户",
        source_event: "来源事件",
        register: "小程序注册",
        event_register: "活动报名",
        event_checkin: "活动签到",
        contact_unlock: "联系方式解锁",
        follow: "普通跟进",
        invalid: "标记无效",
        release: "释放线索",
        contract_create: "创建合同草稿",
        contract_update: "编辑合同草稿",
        contract_attachment: "上传合同影像",
        contract_attachment_delete: "删除合同影像",
        contract_sign: "合同已签",
        contract_submit_review: "合同提交审核",
        contract_review: "合同审核",
        contract_review_skipped: "合同免审通过",
        contract_void: "合同作废",
        contract_receipt_submit: "提交收款",
        contract_receipt_confirm: "确认收款",
        contract_receipt_review: "审核收款",
        contract_receipt_void: "作废收款",
        contract_receipt_reverse: "收款冲正",
        contract_receipt_refund_register: "登记退款",
        contract_first_payment_effective: "首款到账生效",
      } as Record<string, string>
    )[value] || value
  );
}

function serviceOperationLabel(value: string) {
  const code = value.trim();
  return (
    (
      {
        assign: "服务分配",
        transfer: "服务改派",
        close_apply: "申请关单",
        close_review: "审核关单",
        reopen: "服务重开",
        communication: "服务沟通",
        requirement_confirm: "需求确认",
        recommendation_explain: "推荐说明",
        meeting_feedback: "约见反馈",
        renewal_communication: "续费沟通",
        close_communication: "关单沟通",
      } as Record<string, string>
    )[code] || lifecycleStaticLabel(code)
  );
}

function eventTypeLabel(value: string) {
  return (
    (
      {
        register: "小程序注册",
        miniapp_register: "小程序注册",
        manual_create: "后台手动创建",
        import: "批量导入",
        external_push: "外部推送",
        event_register: "活动报名",
        event_checkin: "活动签到",
        contact_unlock: "联系方式解锁",
      } as Record<string, string>
    )[value] ||
    value ||
    "-"
  );
}

function sensitiveTypeLabel(value: string) {
  return (
    ({ view_phone: "查看手机号", view_id_card: "查看身份证" } as Record<string, string>)[value] ||
    value
  );
}
</script>

<style scoped>
.person-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.filter-card,
.table-card {
  border-radius: 8px;
}

.toolbar,
.drawer-head,
.relation-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.toolbar-title,
.drawer-title {
  font-size: 18px;
  font-weight: 600;
}

.toolbar-note,
.drawer-subtitle,
.muted,
.timeline-content {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.tag {
  margin-right: 6px;
  margin-bottom: 4px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  padding-top: 16px;
}

.overview-grid {
  display: grid;
  grid-template-columns: 280px minmax(360px, 1fr);
  gap: 16px;
}

.profile-panel,
.relation-block {
  padding: 14px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
}

.quality-panel {
  grid-column: 1 / -1;
}

.profile-photo,
.photo-empty {
  width: 100%;
  height: 260px;
  border-radius: 8px;
}

.photo-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color-light);
}

.score-parts,
.risk-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.relation-block + .relation-block,
.relation-block + h3,
h3 + .el-table {
  margin-top: 16px;
}

.timeline-title {
  font-weight: 600;
}

@media (max-width: 960px) {
  .overview-grid {
    grid-template-columns: 1fr;
  }
}
</style>
