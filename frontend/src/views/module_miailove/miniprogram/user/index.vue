<template>
  <div class="app-container mp-user-page">
    <el-card shadow="never" class="filter-card">
      <el-form :model="query" inline>
        <el-form-item label="关键词">
          <el-input v-model="query.keyword" clearable placeholder="昵称/手机号/姓名/微信号" @keyup.enter="fetchList" />
        </el-form-item>
        <el-form-item label="注册状态">
          <el-select v-model="query.is_registered" clearable placeholder="全部" style="width: 150px">
            <el-option label="已注册" :value="true" />
            <el-option label="未完成" :value="false" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" icon="Search" @click="fetchList">查询</el-button>
          <el-button icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="toolbar">
          <div class="toolbar-title">小程序注册用户</div>
          <el-button icon="Refresh" @click="fetchList">刷新</el-button>
        </div>
      </template>

      <el-table v-loading="loading" :data="rows" border stripe row-key="id">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column label="微信资料" min-width="220">
          <template #default="{ row }">
            <div class="wx-profile">
              <el-avatar :size="38" :src="ossImage(row.avatar_url, { w: 76, h: 76 })">
                {{ row.nickname?.slice(0, 1) || "微" }}
              </el-avatar>
              <div>
                <div class="nickname">{{ row.nickname || "-" }}</div>
                <div class="sub-text">{{ row.mobile || "-" }}</div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="姓名" min-width="110">
          <template #default="{ row }">{{ row.person?.name || "-" }}</template>
        </el-table-column>
        <el-table-column label="性别" width="90">
          <template #default="{ row }">{{ genderLabel(row.person?.gender) }}</template>
        </el-table-column>
        <el-table-column label="微信号" min-width="130">
          <template #default="{ row }">{{ row.person?.wechat || "-" }}</template>
        </el-table-column>
        <el-table-column label="线索ID" width="100">
          <template #default="{ row }">{{ row.lead_id || "-" }}</template>
        </el-table-column>
        <el-table-column label="来源事件" width="100">
          <template #default="{ row }">{{ eventCountLabel(row.source_event_count) }}</template>
        </el-table-column>
        <el-table-column label="注册状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.is_registered ? 'success' : 'info'">
              {{ row.is_registered ? "已注册" : "未完成" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="允许上墙" width="110">
          <template #default="{ row }">
            <el-switch
              v-model="row.allow_user_wall"
              v-hasPerm="['operation:miniprogram:update']"
              :disabled="row.is_invisible"
              @change="(value: boolean | string | number) => updateUserWall(row, Boolean(value))"
            />
          </template>
        </el-table-column>
        <el-table-column prop="registered_at" label="注册时间" min-width="170" />
        <el-table-column prop="last_login_at" label="最近登录" min-width="170" />
        <el-table-column fixed="right" label="操作" width="180">
          <template #default="{ row }">
            <el-button v-hasPerm="['operation:miniprogram:detail']" link type="primary" icon="View" @click="openDetail(row.id)">详情</el-button>
            <el-button v-hasPerm="['operation:miniprogram:update']" link type="primary" icon="Edit" :disabled="!row.person_id" @click="openEdit(row)">编辑</el-button>
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

    <el-drawer v-model="detailVisible" size="64%" title="小程序注册用户详情" destroy-on-close>
      <template v-if="detail">
        <el-descriptions title="微信资料" :column="2" border>
          <el-descriptions-item label="头像">
            <el-avatar :size="46" :src="ossImage(detail.avatar_url, { w: 92, h: 92 })">{{ detail.nickname?.slice(0, 1) || "微" }}</el-avatar>
          </el-descriptions-item>
          <el-descriptions-item label="昵称">{{ detail.nickname || "-" }}</el-descriptions-item>
          <el-descriptions-item label="微信手机号">{{ detail.mobile || "-" }}</el-descriptions-item>
          <el-descriptions-item label="openid">{{ detail.openid || "-" }}</el-descriptions-item>
          <el-descriptions-item label="注册时间">{{ detail.registered_at || "-" }}</el-descriptions-item>
          <el-descriptions-item label="最近登录">{{ detail.last_login_at || "-" }}</el-descriptions-item>
          <el-descriptions-item label="隐身状态">{{ detail.is_invisible ? "已隐身" : "未隐身" }}</el-descriptions-item>
          <el-descriptions-item label="允许上墙">{{ detail.allow_user_wall ? "是" : "否" }}</el-descriptions-item>
          <el-descriptions-item label="当前线索ID">{{ detail.lead_id || "-" }}</el-descriptions-item>
          <el-descriptions-item label="来源事件数">{{ eventCountLabel(detail.source_event_count) }}</el-descriptions-item>
        </el-descriptions>

        <div class="detail-section section-toolbar">
          <div class="section-title">CRM资料</div>
          <el-button v-hasPerm="['operation:miniprogram:update']" type="primary" icon="Edit" :disabled="!detail.person_id" @click="openEdit(detail)">编辑资料</el-button>
        </div>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="姓名">{{ detail.person?.name || "-" }}</el-descriptions-item>
          <el-descriptions-item label="性别">{{ genderLabel(detail.person?.gender) }}</el-descriptions-item>
          <el-descriptions-item label="手机号">{{ detail.person?.primary_mobile || "-" }}</el-descriptions-item>
          <el-descriptions-item label="身份证">{{ detail.person?.id_card_no_masked || "-" }}</el-descriptions-item>
          <el-descriptions-item label="认证等级">{{ certificationLevelLabel(detail.person?.certification_level) }}</el-descriptions-item>
          <el-descriptions-item label="微信号">{{ detail.person?.wechat || "-" }}</el-descriptions-item>
          <el-descriptions-item label="出生日期">{{ detail.person?.birth_date || "-" }}</el-descriptions-item>
          <el-descriptions-item label="身高">{{ detail.person?.height_cm ? `${detail.person.height_cm} cm` : "-" }}</el-descriptions-item>
          <el-descriptions-item label="民族">{{ dictLabel("ethnicity", detail.person?.ethnicity) }}</el-descriptions-item>
          <el-descriptions-item label="职业">{{ detail.person?.occupation || "-" }}</el-descriptions-item>
          <el-descriptions-item label="年收入">{{ dictLabel("annualIncome", detail.person?.annual_income) }}</el-descriptions-item>
          <el-descriptions-item label="婚况">{{ dictLabel("maritalStatus", detail.person?.marital_status) }}</el-descriptions-item>
          <el-descriptions-item label="学历">{{ dictLabel("education", detail.person?.education) }}</el-descriptions-item>
          <el-descriptions-item label="籍贯">{{ detail.person?.hometown || "-" }}</el-descriptions-item>
          <el-descriptions-item label="常住地">{{ detail.person?.residence || "-" }}</el-descriptions-item>
          <el-descriptions-item label="房产信息">{{ dictLabel("houseStatus", detail.person?.house_status) }}</el-descriptions-item>
          <el-descriptions-item label="购车信息">{{ dictLabel("carStatus", detail.person?.car_status) }}</el-descriptions-item>
        </el-descriptions>

        <el-descriptions class="detail-section" title="互动摘要" :column="3" border>
          <el-descriptions-item label="被喜欢">{{ detail.interaction_stats?.liked_count || 0 }} 次</el-descriptions-item>
          <el-descriptions-item label="被收藏">{{ detail.interaction_stats?.favorited_count || 0 }} 次</el-descriptions-item>
          <el-descriptions-item label="被解锁">{{ detail.interaction_stats?.unlocked_count || 0 }} 次</el-descriptions-item>
          <el-descriptions-item label="可用免费券">{{ detail.coupon_summary?.unused_count || 0 }} 张</el-descriptions-item>
        </el-descriptions>

        <div class="detail-section">
          <div class="section-title">择偶要求</div>
          <el-descriptions v-if="detail.partner_preference" :column="2" border>
            <el-descriptions-item label="年龄范围">{{ rangeLabel(detail.partner_preference.age_min, detail.partner_preference.age_max, "岁") }}</el-descriptions-item>
            <el-descriptions-item label="身高范围">{{ rangeLabel(detail.partner_preference.height_min_cm, detail.partner_preference.height_max_cm, "cm") }}</el-descriptions-item>
            <el-descriptions-item label="常住地">{{ listLabel(detail.partner_preference.preferred_residence_region_codes) }}</el-descriptions-item>
            <el-descriptions-item label="籍贯">{{ listLabel(detail.partner_preference.preferred_hometown_region_codes) }}</el-descriptions-item>
            <el-descriptions-item label="学历">{{ dictLabels("education", detail.partner_preference.preferred_education_codes) }}</el-descriptions-item>
            <el-descriptions-item label="婚况">{{ dictLabels("maritalStatus", detail.partner_preference.preferred_marital_status_codes) }}</el-descriptions-item>
            <el-descriptions-item label="年收入">{{ dictLabels("annualIncome", detail.partner_preference.preferred_annual_income_codes) }}</el-descriptions-item>
            <el-descriptions-item label="房产">{{ dictLabels("houseStatus", detail.partner_preference.preferred_house_status_codes) }}</el-descriptions-item>
            <el-descriptions-item label="车辆">{{ dictLabels("carStatus", detail.partner_preference.preferred_car_status_codes) }}</el-descriptions-item>
            <el-descriptions-item label="接受异地">{{ boolLabel(detail.partner_preference.accept_long_distance) }}</el-descriptions-item>
            <el-descriptions-item label="接受离异">{{ boolLabel(detail.partner_preference.accept_divorced) }}</el-descriptions-item>
            <el-descriptions-item label="接受有子女">{{ boolLabel(detail.partner_preference.accept_children) }}</el-descriptions-item>
            <el-descriptions-item label="子女说明">{{ detail.partner_preference.children_requirement || "-" }}</el-descriptions-item>
            <el-descriptions-item label="来源">{{ preferenceSourceLabel(detail.partner_preference.source_type) }}</el-descriptions-item>
          </el-descriptions>
          <el-empty v-else description="暂无择偶要求" :image-size="72" />
        </div>

        <div class="detail-section">
          <div class="section-title">最近行为</div>
          <el-table :data="detail.recent_actions || []" border size="small">
            <el-table-column label="行为" min-width="120">
              <template #default="{ row }">{{ actionLabel(row.action_type) }}</template>
            </el-table-column>
            <el-table-column prop="viewer_user_id" label="操作用户ID" width="120" />
            <el-table-column prop="occurred_at" label="时间" min-width="170" />
          </el-table>
        </div>

        <div class="detail-section">
          <div class="section-title">觅AI印象</div>
          <div class="ai-profile-box">
            <div class="ai-profile-head">
              <el-tag :type="aiStatusTag(detail.ai_profile?.latest_task?.status || detail.ai_profile?.profile?.generation_status)">
                {{ aiStatusLabel(detail.ai_profile?.latest_task?.status || detail.ai_profile?.profile?.generation_status) }}
              </el-tag>
              <span v-if="detail.ai_profile?.profile?.source_type" class="ai-profile-meta">
                来源：{{ aiSourceLabel(detail.ai_profile.profile.source_type) }}
              </span>
              <span v-if="detail.ai_profile?.latest_task?.retry_count" class="ai-profile-meta">
                重试：{{ detail.ai_profile.latest_task.retry_count }} 次
              </span>
            </div>
            <div v-if="detail.ai_profile?.profile?.content" class="ai-profile-content">
              {{ detail.ai_profile.profile.content }}
            </div>
            <el-empty v-else description="暂无觅AI印象" :image-size="72" />
            <div v-if="detail.ai_profile?.latest_task?.last_error" class="ai-profile-error">
              最近错误：{{ detail.ai_profile.latest_task.last_error }}
            </div>
          </div>
        </div>

        <div class="detail-section">
          <div class="section-title">照片相册</div>
          <div v-if="detail.person?.photo_urls?.length" class="photo-list">
            <el-image
              v-for="url in detail.person.photo_urls"
              :key="url"
              :src="ossImage(url, { w: 120, h: 120 })"
              :preview-src-list="ossImageList(detail.person.photo_urls, { w: 1600 })"
              fit="cover"
              preview-teleported
              class="photo-item"
            />
          </div>
          <el-empty v-else description="暂无照片" />
        </div>
      </template>
    </el-drawer>

    <el-dialog v-model="editVisible" title="编辑小程序用户资料" width="760px" destroy-on-close>
      <el-form :model="profileForm" label-width="86px">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="姓名"><el-input v-model="profileForm.name" /></el-form-item></el-col>
          <el-col :span="12">
            <el-form-item label="性别">
              <el-radio-group v-model="profileForm.gender">
                <el-radio-button value="0">男</el-radio-button>
                <el-radio-button value="1">女</el-radio-button>
                <el-radio-button value="2">未知</el-radio-button>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="12"><el-form-item label="微信号"><el-input v-model="profileForm.wechat" clearable /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="出生日期"><el-date-picker v-model="profileForm.birth_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="身高"><el-input-number v-model="profileForm.height_cm" :min="80" :max="260" controls-position="right" style="width: 100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="民族"><el-select v-model="profileForm.ethnicity" clearable style="width: 100%"><el-option v-for="item in dictOptions.ethnicity" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="职业"><el-input v-model="profileForm.occupation" clearable /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="年收入"><el-select v-model="profileForm.annual_income" clearable style="width: 100%"><el-option v-for="item in dictOptions.annualIncome" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="婚况"><el-select v-model="profileForm.marital_status" clearable style="width: 100%"><el-option v-for="item in dictOptions.maritalStatus" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="学历"><el-select v-model="profileForm.education" clearable style="width: 100%"><el-option v-for="item in dictOptions.education" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="籍贯"><el-input v-model="profileForm.hometown" clearable /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="常住地"><el-input v-model="profileForm.residence" clearable /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="房产"><el-select v-model="profileForm.house_status" clearable style="width: 100%"><el-option v-for="item in dictOptions.houseStatus" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="车辆"><el-select v-model="profileForm.car_status" clearable style="width: 100%"><el-option v-for="item in dictOptions.carStatus" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item></el-col>
          <el-col :span="24">
            <el-form-item label="照片">
              <el-upload v-model:file-list="photoFileList" list-type="picture-card" accept="image/*" multiple :http-request="uploadPhoto" :on-remove="syncPhotoUrls" :on-preview="previewUploadedPhoto">
                <el-icon><Plus /></el-icon>
              </el-upload>
            </el-form-item>
          </el-col>
          <el-col :span="24"><el-form-item label="备注"><el-input v-model="profileForm.description" type="textarea" :rows="3" resize="none" /></el-form-item></el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveProfile">保存</el-button>
      </template>
    </el-dialog>
    <ElImageViewer
      v-if="photoPreviewVisible"
      :url-list="photoPreviewUrls"
      :initial-index="photoPreviewIndex"
      :z-index="4000"
      @close="photoPreviewVisible = false"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { Plus } from "@element-plus/icons-vue";
import { ElImageViewer, ElMessage, type UploadFile, type UploadRequestOptions, type UploadUserFile } from "element-plus";

import DictAPI, { type DictDataTable } from "@/api/module_system/dict";
import MpUserAPI, { type MpUserPageQuery, type MpUserProfileForm, type MpUserTable } from "@/api/module_mp/user";
import { ossImage, ossImageList } from "@/utils/ossImage";
import { uploadImageDirect } from "@/utils/upload";

const query = reactive<MpUserPageQuery>({
  page_no: 1,
  page_size: 10,
  keyword: "",
  is_registered: undefined,
});
const loading = ref(false);
const rows = ref<MpUserTable[]>([]);
const total = ref(0);
const detailVisible = ref(false);
const detail = ref<MpUserTable>();
const editVisible = ref(false);
const saving = ref(false);
const editingUserId = ref<number>();
const photoFileList = ref<UploadUserFile[]>([]);
const photoPreviewVisible = ref(false);
const photoPreviewUrls = ref<string[]>([]);
const photoPreviewIndex = ref(0);
const profileForm = reactive<MpUserProfileForm>({
  name: "",
  gender: "2",
  photo_urls: [],
});
const dictOptions = reactive({
  ethnicity: [] as Array<{ label: string; value: string }>,
  annualIncome: [] as Array<{ label: string; value: string }>,
  maritalStatus: [] as Array<{ label: string; value: string }>,
  education: [] as Array<{ label: string; value: string }>,
  houseStatus: [] as Array<{ label: string; value: string }>,
  carStatus: [] as Array<{ label: string; value: string }>,
});
function genderLabel(value?: string) {
  const map: Record<string, string> = { "0": "男", "1": "女", "2": "未知" };
  return value ? map[value] || value : "-";
}

function certificationLevelLabel(value?: string) {
  const map: Record<string, string> = { none: "未认证", basic: "基础认证", advanced: "高级认证", premium: "尊享认证" };
  return map[value || "none"] || value || "未认证";
}

function eventCountLabel(value?: number) {
  return `${value || 0} 次`;
}

function dictLabel(type: keyof typeof dictOptions, value?: string) {
  if (!value) return "-";
  return dictOptions[type].find((item) => item.value === value)?.label || value;
}

function dictLabels(type: keyof typeof dictOptions, values?: string[]) {
  if (!values?.length) return "不限";
  return values.map((value) => dictLabel(type, value)).join("、");
}

function listLabel(values?: string[]) {
  return values?.length ? values.join("、") : "不限";
}

function rangeLabel(min?: number, max?: number, unit = "") {
  if (!min && !max) return "不限";
  if (min && max) return `${min}-${max}${unit}`;
  if (min) return `${min}${unit}以上`;
  return `${max}${unit}以下`;
}

function boolLabel(value?: boolean | null) {
  if (value === true) return "接受";
  if (value === false) return "不接受";
  return "不限";
}

function preferenceSourceLabel(value?: string) {
  return (
    {
      miniapp: "小程序",
      admin: "后台",
      matchmaker: "红娘",
      deep_interview: "深访",
      import: "导入",
    } as Record<string, string>
  )[value || ""] || value || "-";
}

function aiStatusLabel(value?: string) {
  return (
    {
      pending: "等待生成",
      processing: "生成中",
      success: "已生成",
      failed: "生成失败，等待重试",
      cancelled: "已取消",
    } as Record<string, string>
  )[value || ""] || "暂无任务";
}

function aiStatusTag(value?: string) {
  return (
    {
      pending: "info",
      processing: "warning",
      success: "success",
      failed: "danger",
      cancelled: "info",
    } as const
  )[value || ""] || "info";
}

function aiSourceLabel(value?: string) {
  return (
    {
      register: "小程序注册",
      admin_update: "后台资料维护",
      deep_interview: "红娘深访",
    } as Record<string, string>
  )[value || ""] || value || "-";
}

function actionLabel(value?: string) {
  return (
    {
      view: "浏览详情",
      view_invisible: "浏览隐身资料",
      like: "喜欢",
      cancel_like: "取消喜欢",
      favorite: "收藏",
      cancel_favorite: "取消收藏",
      unlock_heartbeat_attempt: "尝试心动值解锁",
      unlock_coupon_attempt: "尝试免费券解锁",
      unlock_pay_attempt: "尝试付费解锁",
      unlock_success: "解锁成功",
    } as Record<string, string>
  )[value || ""] || value || "-";
}

async function fetchList() {
  loading.value = true;
  try {
    const res = await MpUserAPI.listUser(query);
    rows.value = res.data.data.items || [];
    total.value = res.data.data.total || 0;
  } finally {
    loading.value = false;
  }
}

function resetQuery() {
  query.page_no = 1;
  query.page_size = 10;
  query.keyword = "";
  query.is_registered = undefined;
  fetchList();
}

async function openDetail(id: number) {
  await loadDictOptions();
  const res = await MpUserAPI.detailUser(id);
  detail.value = res.data.data;
  detailVisible.value = true;
}

async function updateUserWall(row: MpUserTable, allowUserWall: boolean) {
  const previous = !allowUserWall;
  if (!row.id) {
    row.allow_user_wall = previous;
    return;
  }
  if (allowUserWall && row.is_invisible) {
    row.allow_user_wall = false;
    ElMessage.warning("隐身用户不能开启上墙");
    return;
  }
  try {
    const res = await MpUserAPI.updateUserWall(row.id, allowUserWall);
    Object.assign(row, res.data.data);
    if (detail.value?.id === row.id) {
      detail.value = res.data.data;
    }
  } catch {
    row.allow_user_wall = previous;
  }
}

async function openEdit(row: MpUserTable) {
  await loadDictOptions();
  if (!row.id) return;
  const target = row.person ? row : (await MpUserAPI.detailUser(row.id)).data.data;
  if (!target.person) {
    ElMessage.warning("该小程序用户尚未完成注册，不能编辑资料");
    return;
  }
  editingUserId.value = target.id;
  Object.assign(profileForm, {
    name: target.person.name || "",
    gender: target.person.gender || "2",
    wechat: target.person.wechat || undefined,
    birth_date: target.person.birth_date || undefined,
    height_cm: target.person.height_cm,
    ethnicity: target.person.ethnicity || undefined,
    occupation: target.person.occupation || undefined,
    annual_income: target.person.annual_income || undefined,
    marital_status: target.person.marital_status || undefined,
    education: target.person.education || undefined,
    hometown: target.person.hometown || undefined,
    residence: target.person.residence || undefined,
    house_status: target.person.house_status || undefined,
    car_status: target.person.car_status || undefined,
    photo_urls: target.person.photo_urls || [],
    description: target.person.description || undefined,
  });
  photoFileList.value = profileForm.photo_urls.map((url) => ({ name: url.split("/").pop() || "image", url }));
  editVisible.value = true;
}

function syncPhotoUrls() {
  profileForm.photo_urls = photoFileList.value.map((item) => item.url).filter((url): url is string => Boolean(url));
}

function previewUploadedPhoto(file: UploadFile) {
  const urls = photoFileList.value.map((item) => item.url).filter((url): url is string => Boolean(url));
  if (!urls.length) return;
  photoPreviewUrls.value = ossImageList(urls, { w: 1600 });
  photoPreviewIndex.value = Math.max(urls.findIndex((url) => url === file.url), 0);
  photoPreviewVisible.value = true;
}

async function uploadPhoto(options: UploadRequestOptions) {
  const fileInfo = await uploadImageDirect(options.file, "crm_lead_photo");
  const current = photoFileList.value.find((item) => item.uid === options.file.uid);
  if (current) {
    current.name = fileInfo.file_name || options.file.name;
    current.url = fileInfo.file_url;
  }
  syncPhotoUrls();
  options.onSuccess?.(fileInfo);
}

async function saveProfile() {
  if (!editingUserId.value) return;
  if (!profileForm.name.trim()) {
    ElMessage.warning("请填写姓名");
    return;
  }
  saving.value = true;
  try {
    const res = await MpUserAPI.updateProfile(editingUserId.value, {
      ...profileForm,
      name: profileForm.name.trim(),
      photo_urls: profileForm.photo_urls || [],
    });
    detail.value = res.data.data;
    editVisible.value = false;
    await fetchList();
  } finally {
    saving.value = false;
  }
}

let dictPromise: Promise<void> | null = null;

async function loadDictOptions() {
  if (dictPromise) return dictPromise;
  const dictMap = {
    ethnicity: "crm_ethnicity",
    annualIncome: "crm_annual_income",
    maritalStatus: "crm_marital_status",
    education: "crm_education",
    houseStatus: "crm_house_status",
    carStatus: "crm_car_status",
  } as const;
  dictPromise = Promise.all(
    Object.entries(dictMap).map(async ([key, type]) => {
      const res = await DictAPI.getInitDict(type);
      dictOptions[key as keyof typeof dictOptions] = ((res.data.data as DictDataTable[]) || []).map((item) => ({
        label: item.dict_label || item.dict_value || "",
        value: item.dict_value || "",
      }));
    })
  ).then(() => undefined);
  return dictPromise;
}

onMounted(() => {
  loadDictOptions();
  fetchList();
});
</script>

<style scoped>
.mp-user-page .filter-card {
  margin-bottom: 12px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.toolbar-title {
  font-size: 16px;
  font-weight: 600;
}

.wx-profile {
  display: flex;
  align-items: center;
  gap: 10px;
}

.nickname {
  font-weight: 600;
  line-height: 20px;
}

.sub-text {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 18px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.detail-section {
  margin-top: 18px;
}

.section-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.section-toolbar .section-title {
  margin-bottom: 0;
}

.section-title {
  margin-bottom: 12px;
  color: var(--el-text-color-primary);
  font-size: 16px;
  font-weight: 600;
}

.ai-profile-box {
  padding: 16px 18px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  background: var(--el-fill-color-blank);
}

.ai-profile-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.ai-profile-meta {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.ai-profile-content {
  min-height: 132px;
  max-height: 420px;
  overflow-y: auto;
  padding: 14px 16px;
  border-radius: 8px;
  background: var(--el-fill-color-light);
  color: var(--el-text-color-primary);
  font-size: 14px;
  line-height: 1.9;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
  word-break: break-word;
}

.ai-profile-error {
  margin-top: 10px;
  color: var(--el-color-danger);
  font-size: 12px;
  line-height: 1.6;
}

.photo-list {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.photo-item {
  width: 112px;
  height: 112px;
  border-radius: 6px;
}
</style>
