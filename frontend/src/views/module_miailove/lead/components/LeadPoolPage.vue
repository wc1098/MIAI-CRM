<template>
  <div class="app-container lead-page">
    <el-card shadow="never" class="lead-filter">
      <el-form :model="query" inline>
        <el-form-item label="关键词">
          <el-input v-model="query.keyword" clearable placeholder="姓名/手机号" @keyup.enter="fetchList" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="query.lead_type" clearable placeholder="全部" style="width: 150px">
            <el-option v-for="item in leadTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="来源">
          <el-select v-model="query.source_channel_code" clearable filterable placeholder="全部" style="width: 180px">
            <el-option v-for="item in channelOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="门店" v-if="view !== 'salesPrivate'">
          <el-select v-model="query.store_id" clearable filterable placeholder="全部" style="width: 180px">
            <el-option v-for="item in deptOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="归属人">
          <el-select v-model="query.owner_sales_id" clearable filterable placeholder="全部" style="width: 160px">
            <el-option v-for="item in userOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" icon="Search" @click="fetchList">查询</el-button>
          <el-button icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="lead-table">
      <template #header>
        <div class="toolbar">
          <div class="toolbar-title">{{ title }}</div>
          <div class="toolbar-actions">
            <el-button v-hasPerm="['crm:lead:create']" type="primary" icon="Plus" @click="openCreate">新增</el-button>
            <el-button v-hasPerm="['crm:lead:assign']" icon="UserFilled" :disabled="!selectedIds.length" @click="openAssign">分配</el-button>
            <el-button v-if="view === 'storePool'" v-hasPerm="['crm:lead:sales:claim']" icon="TakeawayBox" :disabled="!selectedIds.length" @click="claimSelected">领取</el-button>
            <el-button v-hasPerm="['crm:lead:import']" icon="Upload" @click="importVisible = true">导入</el-button>
          </div>
        </div>
      </template>

      <el-table v-loading="loading" :data="rows" border stripe row-key="id" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="48" />
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column label="姓名" min-width="110">
          <template #default="{ row }">{{ row.person?.name }}</template>
        </el-table-column>
        <el-table-column label="联系电话" min-width="140">
          <template #default="{ row }">{{ row.mobile_masked || row.person?.primary_mobile }}</template>
        </el-table-column>
        <el-table-column label="类型" min-width="120">
          <template #default="{ row }">
            <el-tag :type="leadTypeTag(row.lead_type)">{{ leadTypeLabel(row.lead_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="来源" min-width="140">
          <template #default="{ row }">{{ sourceLabel(row) }}</template>
        </el-table-column>
        <el-table-column prop="latest_follow_at" label="最后跟进时间" min-width="170" />
        <el-table-column label="归属人" min-width="120">
          <template #default="{ row }">{{ row.owner_sales?.name || "-" }}</template>
        </el-table-column>
        <el-table-column label="归属门店" min-width="140">
          <template #default="{ row }">{{ row.store?.name || "-" }}</template>
        </el-table-column>
        <el-table-column fixed="right" label="操作" width="220">
          <template #default="{ row }">
            <el-button v-hasPerm="['crm:lead:all:detail', 'crm:lead:store:detail', 'crm:lead:sales:detail']" link type="primary" icon="View" @click="openDetail(row.id)">详情</el-button>
            <el-button v-hasPerm="['crm:lead:update']" link type="primary" icon="Edit" @click="openEdit(row.id)">编辑</el-button>
            <el-button v-hasPerm="['crm:lead:process']" link type="warning" icon="ChatDotRound" @click="openProcess(row.id)">过程</el-button>
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

    <el-drawer v-model="detailVisible" size="72%" :title="drawerTitle" destroy-on-close>
      <el-tabs v-model="activeTab">
        <el-tab-pane label="个人信息" name="profile">
          <el-form ref="formRef" :model="form" :rules="rules" label-width="110px" class="lead-form">
            <el-row :gutter="16">
              <el-col :span="8">
                <el-form-item label="手机号" prop="mobile">
                  <el-input v-model="form.mobile" :disabled="Boolean(editingId)" @blur="checkMobile" />
                  <div v-if="mobileCheckMessage" class="form-tip form-tip--danger">{{ mobileCheckMessage }}</div>
                </el-form-item>
              </el-col>
              <el-col :span="8"><el-form-item label="姓名" prop="name"><el-input v-model="form.name" /></el-form-item></el-col>
              <el-col :span="8">
                <el-form-item label="性别" prop="gender">
                  <el-select v-model="form.gender" style="width: 100%">
                    <el-option label="男" value="0" />
                    <el-option label="女" value="1" />
                    <el-option label="未知" value="2" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8"><el-form-item label="微信号"><el-input v-model="form.wechat" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="出生日期"><el-date-picker v-model="form.birth_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="身高"><el-input-number v-model="form.height_cm" :min="80" :max="260" style="width: 100%" /></el-form-item></el-col>
              <el-col :span="8">
                <el-form-item label="民族">
                  <el-select v-model="form.ethnicity" clearable filterable style="width: 100%">
                    <el-option v-for="item in dictOptions.ethnicity" :key="item.value" :label="item.label" :value="item.value" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8"><el-form-item label="职业"><el-input v-model="form.occupation" /></el-form-item></el-col>
              <el-col :span="8">
                <el-form-item label="年收入">
                  <el-select v-model="form.annual_income" clearable style="width: 100%">
                    <el-option v-for="item in dictOptions.annualIncome" :key="item.value" :label="item.label" :value="item.value" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="婚况">
                  <el-select v-model="form.marital_status" clearable style="width: 100%">
                    <el-option v-for="item in dictOptions.maritalStatus" :key="item.value" :label="item.label" :value="item.value" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="学历">
                  <el-select v-model="form.education" clearable style="width: 100%">
                    <el-option v-for="item in dictOptions.education" :key="item.value" :label="item.label" :value="item.value" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="籍贯">
                  <el-cascader v-model="hometownValue" :options="addressOptions" clearable filterable :props="addressProps" style="width: 100%" @change="syncAddressFields" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="常驻地">
                  <el-cascader v-model="residenceValue" :options="addressOptions" clearable filterable :props="addressProps" style="width: 100%" @change="syncAddressFields" />
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="住房情况">
                  <el-select v-model="form.house_status" clearable style="width: 100%">
                    <el-option v-for="item in dictOptions.houseStatus" :key="item.value" :label="item.label" :value="item.value" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="购车情况">
                  <el-select v-model="form.car_status" clearable style="width: 100%">
                    <el-option v-for="item in dictOptions.carStatus" :key="item.value" :label="item.label" :value="item.value" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="来源渠道">
                  <el-select v-model="form.source_channel_code" clearable filterable style="width: 100%">
                    <el-option v-for="item in channelOptions" :key="item.value" :label="item.label" :value="item.value" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col v-if="!editingId" :span="8">
                <el-form-item>
                  <template #label>
                    <span class="label-with-tip">
                      同步小程序
                      <el-tooltip content="开启后创建待绑定小程序用户，用户后续用同手机号注册会自动关联。" placement="top">
                        <el-icon class="tip-icon"><QuestionFilled /></el-icon>
                      </el-tooltip>
                    </span>
                  </template>
                  <el-switch
                    v-model="form.sync_to_miniprogram"
                    active-text="是"
                    inactive-text="否"
                    inline-prompt
                  />
                </el-form-item>
              </el-col>
              <el-col :span="8"><el-form-item label="归属门店"><el-input :model-value="autoStoreName" disabled /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="归属人"><el-input :model-value="autoOwnerName" disabled /></el-form-item></el-col>
              <el-col :span="24">
                <el-form-item label="照片">
                  <el-upload
                    v-model:file-list="photoFileList"
                    list-type="picture-card"
                    accept="image/*"
                    multiple
                    :http-request="uploadPhoto"
                    :on-remove="removePhoto"
                  >
                    <el-icon><Plus /></el-icon>
                  </el-upload>
                </el-form-item>
              </el-col>
              <el-col :span="24">
                <el-form-item label="备注">
                  <el-input v-model="form.description" type="textarea" :rows="3" />
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>
          <div class="drawer-actions">
            <el-button @click="detailVisible = false">取消</el-button>
            <el-button v-hasPerm="['crm:lead:create', 'crm:lead:update']" type="primary" @click="submitForm">保存</el-button>
          </div>
        </el-tab-pane>

        <el-tab-pane label="系统信息" name="system" v-if="detail">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="线索ID">{{ detail.id }}</el-descriptions-item>
            <el-descriptions-item label="线索类型">{{ leadTypeLabel(detail.lead_type) }}</el-descriptions-item>
            <el-descriptions-item label="归属池">{{ poolTypeLabel(detail.pool_type) }}</el-descriptions-item>
            <el-descriptions-item label="来源">{{ sourceLabel(detail) }}</el-descriptions-item>
            <el-descriptions-item label="归属门店">{{ detail.store?.name || "-" }}</el-descriptions-item>
            <el-descriptions-item label="归属人">{{ detail.owner_sales?.name || "-" }}</el-descriptions-item>
            <el-descriptions-item label="最近跟进">{{ detail.latest_follow_at || "-" }}</el-descriptions-item>
            <el-descriptions-item label="下次跟进">{{ detail.next_follow_at || "-" }}</el-descriptions-item>
          </el-descriptions>
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
        </el-tab-pane>

        <el-tab-pane label="过程记录" name="process" v-if="detail">
          <el-timeline>
            <el-timeline-item v-for="item in detail.process_records" :key="item.id" :timestamp="item.created_time">
              <el-tag>{{ actionLabel(item.action_type) }}</el-tag>
              <span class="timeline-content">{{ item.content }}</span>
              <span v-if="item.next_follow_at" class="timeline-extra">下次跟进：{{ item.next_follow_at }}</span>
            </el-timeline-item>
          </el-timeline>
        </el-tab-pane>

        <el-tab-pane label="生命周期" name="lifecycle" v-if="detail">
          <el-timeline>
            <el-timeline-item v-for="item in detail.lifecycle_records" :key="item.id" :timestamp="item.created_time">
              <el-tag type="info">{{ actionLabel(item.operation_type) }}</el-tag>
              <span class="timeline-content">{{ item.remark || formatChange(item.change_detail) }}</span>
            </el-timeline-item>
          </el-timeline>
        </el-tab-pane>
      </el-tabs>
    </el-drawer>

    <el-dialog v-model="assignVisible" title="分配线索" width="520px">
      <el-form :model="assignForm" label-width="90px">
        <el-form-item label="目标门店">
          <el-select v-model="assignForm.store_id" clearable filterable style="width: 100%">
            <el-option v-for="item in deptOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标销售">
          <el-select v-model="assignForm.owner_sales_id" clearable filterable style="width: 100%">
            <el-option v-for="item in userOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="assignForm.remark" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="assignVisible = false">取消</el-button>
        <el-button type="primary" @click="submitAssign">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="processVisible" title="过程记录" width="560px">
      <el-form :model="processForm" label-width="100px">
        <el-form-item label="动作类型">
          <el-select v-model="processForm.action_type" style="width: 100%">
            <el-option v-for="item in actionOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="跟进方式" v-if="processForm.action_type === 'follow'">
          <el-select v-model="processForm.follow_method" clearable style="width: 100%">
            <el-option label="电话" value="phone" />
            <el-option label="微信" value="wechat" />
            <el-option label="面谈" value="meeting" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="常用语">
          <el-select placeholder="快捷输入" clearable style="width: 100%" @change="appendPhrase">
            <el-option v-for="item in phrases" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="内容/原因">
          <el-input v-model="processForm.content" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item label="下次跟进">
          <el-date-picker v-model="processForm.next_follow_at" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="processVisible = false">取消</el-button>
        <el-button type="primary" @click="submitProcess">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="importVisible" title="批量导入线索" width="620px">
      <el-alert type="info" show-icon :closable="false" title="请按模板填写，手机号重复会跳过并返回失败原因。" />
      <div class="import-actions">
        <el-button icon="Download" @click="downloadTemplate">下载模板</el-button>
        <el-upload :auto-upload="false" :limit="1" accept=".xlsx,.xls" :on-change="handleFileChange">
          <el-button type="primary" icon="Upload">选择文件</el-button>
        </el-upload>
      </div>
      <el-table v-if="importResult" :data="importResult.failed_rows" border size="small">
        <el-table-column prop="row" label="行号" width="90" />
        <el-table-column prop="reason" label="失败原因" />
      </el-table>
      <template #footer>
        <span v-if="importResult">成功 {{ importResult.success_count }} 条，失败 {{ importResult.failed_count }} 条</span>
        <el-button @click="importVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { Plus, QuestionFilled } from "@element-plus/icons-vue";
import { ElMessage, type FormInstance, type UploadFile, type UploadRequestOptions, type UploadUserFile } from "element-plus";
import LeadAPI, {
  type LeadDetail,
  type LeadForm,
  type LeadImportResult,
  type LeadPageQuery,
  type LeadTable,
  type LeadView,
} from "@/api/module_crm/lead";
import ChannelAPI from "@/api/module_crm/channel";
import DeptAPI, { type DeptTable } from "@/api/module_system/dept";
import DictAPI, { type DictDataTable } from "@/api/module_system/dict";
import ParamsAPI from "@/api/module_system/params";
import UserAPI, { type UserInfo } from "@/api/module_system/user";

const props = defineProps<{ view: LeadView; title: string }>();

const loading = ref(false);
const rows = ref<LeadTable[]>([]);
const total = ref(0);
const selectedIds = ref<number[]>([]);
const detailVisible = ref(false);
const assignVisible = ref(false);
const processVisible = ref(false);
const importVisible = ref(false);
const activeTab = ref("profile");
const detail = ref<LeadDetail>();
const editingId = ref<number>();
const processLeadId = ref<number>();
const formRef = ref<FormInstance>();
const importResult = ref<LeadImportResult>();
const currentUser = ref<UserInfo>();
const optionsLoaded = ref(false);
const mobileCheckMessage = ref("");
const photoFileList = ref<UploadUserFile[]>([]);
const hometownValue = ref<string[]>([]);
const residenceValue = ref<string[]>([]);

const query = reactive<LeadPageQuery>({
  page_no: 1,
  page_size: 10,
});

const defaultForm = (): LeadForm => ({
  mobile: "",
  name: "",
  gender: "0",
  photo_urls: [],
  source_channel_code: "MANUAL_CREATE",
  sync_to_miniprogram: false,
});

const form = reactive<LeadForm>(defaultForm());
const assignForm = reactive({ store_id: undefined as number | undefined, owner_sales_id: undefined as number | undefined, remark: "" });
const processForm = reactive({ action_type: "follow", follow_method: "phone", content: "", next_follow_at: "" });

const channelOptions = ref<Array<{ label: string; value: string }>>([]);
const deptOptions = ref<Array<{ label: string; value: number }>>([]);
const userOptions = ref<Array<{ label: string; value: number }>>([]);
const dictOptions = reactive({
  ethnicity: [] as Array<{ label: string; value: string }>,
  annualIncome: [] as Array<{ label: string; value: string }>,
  maritalStatus: [] as Array<{ label: string; value: string }>,
  education: [] as Array<{ label: string; value: string }>,
  houseStatus: [] as Array<{ label: string; value: string }>,
  carStatus: [] as Array<{ label: string; value: string }>,
});
const addressProps = { emitPath: true };
const addressOptions = [
  { label: "北京市", value: "北京市", children: [{ label: "北京市", value: "北京市" }] },
  { label: "上海市", value: "上海市", children: [{ label: "上海市", value: "上海市" }] },
  { label: "天津市", value: "天津市", children: [{ label: "天津市", value: "天津市" }] },
  { label: "重庆市", value: "重庆市", children: [{ label: "重庆市", value: "重庆市" }] },
  { label: "河北省", value: "河北省", children: ["石家庄市", "唐山市", "秦皇岛市", "邯郸市", "保定市", "张家口市"].map((city) => ({ label: city, value: city })) },
  { label: "山西省", value: "山西省", children: ["太原市", "大同市", "阳泉市", "长治市", "晋城市", "临汾市"].map((city) => ({ label: city, value: city })) },
  { label: "辽宁省", value: "辽宁省", children: ["沈阳市", "大连市", "鞍山市", "抚顺市", "锦州市"].map((city) => ({ label: city, value: city })) },
  { label: "吉林省", value: "吉林省", children: ["长春市", "吉林市", "四平市", "通化市"].map((city) => ({ label: city, value: city })) },
  { label: "黑龙江省", value: "黑龙江省", children: ["哈尔滨市", "齐齐哈尔市", "牡丹江市", "大庆市"].map((city) => ({ label: city, value: city })) },
  { label: "江苏省", value: "江苏省", children: ["南京市", "无锡市", "徐州市", "常州市", "苏州市", "南通市"].map((city) => ({ label: city, value: city })) },
  { label: "浙江省", value: "浙江省", children: ["杭州市", "宁波市", "温州市", "嘉兴市", "湖州市", "绍兴市"].map((city) => ({ label: city, value: city })) },
  { label: "安徽省", value: "安徽省", children: ["合肥市", "芜湖市", "蚌埠市", "淮南市", "安庆市"].map((city) => ({ label: city, value: city })) },
  { label: "福建省", value: "福建省", children: ["福州市", "厦门市", "泉州市", "漳州市", "莆田市"].map((city) => ({ label: city, value: city })) },
  { label: "江西省", value: "江西省", children: ["南昌市", "九江市", "赣州市", "宜春市", "上饶市"].map((city) => ({ label: city, value: city })) },
  { label: "山东省", value: "山东省", children: ["济南市", "青岛市", "淄博市", "烟台市", "潍坊市", "临沂市"].map((city) => ({ label: city, value: city })) },
  { label: "河南省", value: "河南省", children: ["郑州市", "洛阳市", "开封市", "新乡市", "南阳市"].map((city) => ({ label: city, value: city })) },
  { label: "湖北省", value: "湖北省", children: ["武汉市", "黄石市", "襄阳市", "宜昌市", "荆州市"].map((city) => ({ label: city, value: city })) },
  { label: "湖南省", value: "湖南省", children: ["长沙市", "株洲市", "湘潭市", "衡阳市", "岳阳市"].map((city) => ({ label: city, value: city })) },
  { label: "广东省", value: "广东省", children: ["广州市", "深圳市", "珠海市", "佛山市", "东莞市", "中山市"].map((city) => ({ label: city, value: city })) },
  { label: "海南省", value: "海南省", children: ["海口市", "三亚市", "儋州市"].map((city) => ({ label: city, value: city })) },
  { label: "四川省", value: "四川省", children: ["成都市", "绵阳市", "德阳市", "南充市", "宜宾市"].map((city) => ({ label: city, value: city })) },
  { label: "贵州省", value: "贵州省", children: ["贵阳市", "遵义市", "六盘水市", "安顺市"].map((city) => ({ label: city, value: city })) },
  { label: "云南省", value: "云南省", children: ["昆明市", "曲靖市", "玉溪市", "大理市"].map((city) => ({ label: city, value: city })) },
  { label: "陕西省", value: "陕西省", children: ["西安市", "咸阳市", "宝鸡市", "渭南市"].map((city) => ({ label: city, value: city })) },
  { label: "甘肃省", value: "甘肃省", children: ["兰州市", "天水市", "酒泉市", "庆阳市"].map((city) => ({ label: city, value: city })) },
  { label: "内蒙古自治区", value: "内蒙古自治区", children: ["呼和浩特市", "包头市", "赤峰市", "鄂尔多斯市"].map((city) => ({ label: city, value: city })) },
  { label: "广西壮族自治区", value: "广西壮族自治区", children: ["南宁市", "柳州市", "桂林市", "北海市"].map((city) => ({ label: city, value: city })) },
  { label: "宁夏回族自治区", value: "宁夏回族自治区", children: ["银川市", "石嘴山市", "吴忠市"].map((city) => ({ label: city, value: city })) },
  { label: "新疆维吾尔自治区", value: "新疆维吾尔自治区", children: ["乌鲁木齐市", "克拉玛依市", "喀什市"].map((city) => ({ label: city, value: city })) },
  { label: "西藏自治区", value: "西藏自治区", children: ["拉萨市", "日喀则市", "林芝市"].map((city) => ({ label: city, value: city })) },
  { label: "青海省", value: "青海省", children: ["西宁市", "海东市"].map((city) => ({ label: city, value: city })) },
  { label: "香港特别行政区", value: "香港特别行政区", children: [{ label: "香港特别行政区", value: "香港特别行政区" }] },
  { label: "澳门特别行政区", value: "澳门特别行政区", children: [{ label: "澳门特别行政区", value: "澳门特别行政区" }] },
  { label: "台湾省", value: "台湾省", children: ["台北市", "高雄市", "台中市", "台南市"].map((city) => ({ label: city, value: city })) },
];

const leadTypeOptions = [
  { label: "待分配", value: "pending" },
  { label: "新线索", value: "new" },
  { label: "二手线索", value: "second_hand" },
  { label: "无效线索", value: "invalid" },
  { label: "已转建档客户", value: "converted_customer" },
];
const actionOptions = [
  { label: "普通跟进", value: "follow" },
  { label: "标记无效", value: "invalid" },
  { label: "释放", value: "release" },
  { label: "转建档客户", value: "convert_customer" },
];
const phrases = ["已电话沟通，客户有初步意向。", "微信已添加，等待客户回复。", "客户暂时不方便，约定下次联系。", "客户无明确需求，后续观察。"];
const sourceFallbackLabels: Record<string, string> = {
  "1": "小程序注册用户",
  MINIAPP_REGISTER: "小程序注册",
  MINIAPP_EVENT: "小程序活动",
  MINIAPP_CONTACT_UNLOCK: "联系方式解锁",
  MANUAL_CREATE: "人工录入",
  IMPORT: "批量导入",
  EXTERNAL_PUSH: "外部推送",
};
const rules = {
  mobile: [{ required: true, message: "请输入手机号", trigger: "blur" }],
  name: [{ required: true, message: "请输入姓名", trigger: "blur" }],
  gender: [{ required: true, message: "请选择性别", trigger: "change" }],
};

const view = computed(() => props.view);
const title = computed(() => props.title);
const drawerTitle = computed(() => (editingId.value ? "线索详情" : "新增线索"));
const currentRoleCodes = computed(() => new Set((currentUser.value?.roles || []).map((role) => role.code)));
const autoStoreName = computed(() => {
  if (detail.value) return detail.value.store?.name || "-";
  if (currentRoleCodes.value.has("SALES") || currentRoleCodes.value.has("STORE_MGR")) return currentUser.value?.dept_name || "-";
  return "总部线索池";
});
const autoOwnerName = computed(() => {
  if (detail.value) return detail.value.owner_sales?.name || "-";
  if (currentRoleCodes.value.has("SALES")) return currentUser.value?.name || "-";
  return "未分配";
});

function resetForm() {
  Object.assign(form, defaultForm());
  detail.value = undefined;
  editingId.value = undefined;
  mobileCheckMessage.value = "";
  photoFileList.value = [];
  hometownValue.value = [];
  residenceValue.value = [];
  activeTab.value = "profile";
}

function fillForm(data: LeadDetail) {
  Object.assign(form, {
    mobile: data.person.primary_mobile,
    name: data.person.name,
    gender: data.person.gender,
    wechat: data.person.wechat,
    birth_date: data.person.birth_date,
    height_cm: data.person.height_cm,
    ethnicity: data.person.ethnicity,
    occupation: data.person.occupation,
    annual_income: data.person.annual_income,
    marital_status: data.person.marital_status,
    education: data.person.education,
    hometown: data.person.hometown,
    residence: data.person.residence,
    house_status: data.person.house_status,
    car_status: data.person.car_status,
    photo_urls: data.person.photo_urls || [],
    source_channel_code: data.source_channel_code,
    sync_to_miniprogram: false,
    description: data.description,
    store_id: data.store_id,
    owner_sales_id: data.owner_sales_id,
  });
  photoFileList.value = (data.person.photo_urls || []).map((url) => ({ name: url.split("/").pop() || "image", url }));
  hometownValue.value = splitAddress(data.person.hometown);
  residenceValue.value = splitAddress(data.person.residence);
}

async function fetchList() {
  loading.value = true;
  try {
    const res = await LeadAPI.listLead(props.view, query);
    rows.value = res.data.data.items || [];
    total.value = res.data.data.total || 0;
  } finally {
    loading.value = false;
  }
}

function resetQuery() {
  Object.assign(query, { page_no: 1, page_size: query.page_size, keyword: undefined, lead_type: undefined, source_channel_code: undefined, store_id: undefined, owner_sales_id: undefined });
  fetchList();
}

async function openDetail(id: number) {
  await ensureOptionsLoaded();
  resetForm();
  editingId.value = id;
  const res = await LeadAPI.detailLead(id);
  detail.value = res.data.data;
  fillForm(detail.value);
  detailVisible.value = true;
}

async function openEdit(id: number) {
  await openDetail(id);
}

async function openCreate() {
  await ensureOptionsLoaded();
  resetForm();
  detailVisible.value = true;
}

async function submitForm() {
  await formRef.value?.validate();
  await checkMobile();
  if (mobileCheckMessage.value) return;
  syncAddressFields();
  const payload = {
    ...form,
    photo_urls: photoFileList.value.map((item) => item.url).filter((url): url is string => Boolean(url)),
  };
  if (!editingId.value) {
    delete payload.store_id;
    delete payload.owner_sales_id;
  } else {
    delete payload.sync_to_miniprogram;
  }
  if (editingId.value) {
    await LeadAPI.updateLead(editingId.value, payload);
  } else {
    await LeadAPI.createLead(payload);
  }
  detailVisible.value = false;
  fetchList();
}

function handleSelectionChange(selection: LeadTable[]) {
  selectedIds.value = selection.map((item) => item.id).filter((id): id is number => typeof id === "number");
}

function openAssign() {
  Object.assign(assignForm, { store_id: undefined, owner_sales_id: undefined, remark: "" });
  assignVisible.value = true;
}

async function submitAssign() {
  await LeadAPI.assignLead({ lead_ids: selectedIds.value, ...assignForm });
  assignVisible.value = false;
  fetchList();
}

async function claimSelected() {
  await LeadAPI.claimLead({ lead_ids: selectedIds.value });
  fetchList();
}

function openProcess(id: number) {
  processLeadId.value = id;
  Object.assign(processForm, { action_type: "follow", follow_method: "phone", content: "", next_follow_at: "" });
  processVisible.value = true;
}

function appendPhrase(value: string) {
  if (!value) return;
  processForm.content = processForm.content ? `${processForm.content}\n${value}` : value;
}

async function submitProcess() {
  if (!processLeadId.value) return;
  await LeadAPI.processLead(processLeadId.value, {
    action_type: processForm.action_type,
    follow_method: processForm.action_type === "follow" ? processForm.follow_method : undefined,
    content: processForm.content,
    next_follow_at: processForm.next_follow_at || undefined,
  });
  processVisible.value = false;
  fetchList();
}

async function downloadTemplate() {
  const res = await LeadAPI.downloadTemplate();
  const url = URL.createObjectURL(res.data);
  const link = document.createElement("a");
  link.href = url;
  link.download = "crm_lead_import_template.xlsx";
  link.click();
  URL.revokeObjectURL(url);
}

async function handleFileChange(file: UploadFile) {
  if (!file.raw) return;
  const formData = new FormData();
  formData.append("file", file.raw);
  const res = await LeadAPI.importLead(formData);
  importResult.value = res.data.data;
  fetchList();
}

async function checkMobile() {
  mobileCheckMessage.value = "";
  if (editingId.value || !/^1[3-9]\d{9}$/.test(form.mobile)) return;
  const res = await LeadAPI.checkMobile(form.mobile);
  if (res.data.data.exists) {
    mobileCheckMessage.value = `手机号已存在：${res.data.data.name || ""}`;
  }
}

async function uploadPhoto(options: UploadRequestOptions) {
  const formData = new FormData();
  formData.append("file", options.file);
  const res = await ParamsAPI.uploadFile(formData);
  const fileInfo = res.data.data;
  const current = photoFileList.value.find((item) => item.uid === options.file.uid);
  if (current) {
    current.name = fileInfo.file_name || fileInfo.origin_name || options.file.name;
    current.url = fileInfo.file_url;
  }
  options.onSuccess?.(fileInfo);
}

function removePhoto(file: UploadFile) {
  photoFileList.value = photoFileList.value.filter((item) => item.uid !== file.uid && item.url !== file.url);
}

function splitAddress(value?: string) {
  return value ? value.split("/").filter(Boolean).slice(0, 2) : [];
}

function syncAddressFields() {
  form.hometown = hometownValue.value.join("/") || undefined;
  form.residence = residenceValue.value.join("/") || undefined;
}

let optionsPromise: Promise<void> | null = null;

async function ensureOptionsLoaded() {
  if (optionsLoaded.value) return;
  if (!optionsPromise) {
    optionsPromise = loadOptions();
  }
  await optionsPromise;
}

async function loadOptions() {
  const [channelRes, deptRes, userRes, currentUserRes] = await Promise.all([
    ChannelAPI.listChannel({ page_no: 1, page_size: 100 }),
    DeptAPI.listDept(),
    UserAPI.listUser({ page_no: 1, page_size: 100 } as any),
    UserAPI.getCurrentUserInfo(),
  ]);
  currentUser.value = currentUserRes.data.data;
  channelOptions.value = (channelRes.data.data.items || []).map((item) => ({ label: item.channel_name || item.channel_code || "", value: item.channel_code || "" }));
  deptOptions.value = flattenDept(deptRes.data.data || []);
  userOptions.value = (userRes.data.data.items || []).map((item: any) => ({ label: item.name || item.username || String(item.id), value: item.id }));
  await loadDictOptions();
  optionsLoaded.value = true;
}

async function loadDictOptions() {
  const dictMap = {
    ethnicity: "crm_ethnicity",
    annualIncome: "crm_annual_income",
    maritalStatus: "crm_marital_status",
    education: "crm_education",
    houseStatus: "crm_house_status",
    carStatus: "crm_car_status",
  } as const;
  await Promise.all(
    Object.entries(dictMap).map(async ([key, type]) => {
      const res = await DictAPI.getInitDict(type);
      dictOptions[key as keyof typeof dictOptions] = ((res.data.data as DictDataTable[]) || []).map((item) => ({
        label: item.dict_label || item.dict_value || "",
        value: item.dict_value || "",
      }));
    })
  );
}

function flattenDept(list: DeptTable[], prefix = ""): Array<{ label: string; value: number }> {
  return list.flatMap((item) => {
    const label = `${prefix}${item.name}`;
    const current = typeof item.id === "number" ? [{ label, value: item.id }] : [];
    return [...current, ...flattenDept(item.children || [], `${prefix}${item.name}/`)];
  });
}

function leadTypeLabel(value: string) {
  return leadTypeOptions.find((item) => item.value === value)?.label || value;
}

function sourceLabel(row?: Pick<LeadTable, "source_channel_name" | "source_channel_code">) {
  if (!row) return "-";
  if (row.source_channel_name) return row.source_channel_name;
  const code = row.source_channel_code || "";
  if (!code) return "-";
  return channelOptions.value.find((item) => item.value === code)?.label || sourceFallbackLabels[code] || code;
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

function leadTypeTag(value: string) {
  const tags = {
    pending: "info",
    new: "success",
    second_hand: "warning",
    invalid: "danger",
    converted_customer: "primary",
  } as const;
  return tags[value as keyof typeof tags] || "info";
}

function poolTypeLabel(value: string) {
  return ({ hq_pool: "总部池", store_pool: "门店公海", sales_private: "销售私海" } as Record<string, string>)[value] || value;
}

function actionLabel(value: string) {
  return (
    actionOptions.find((item) => item.value === value)?.label ||
    ({
      create: "新增线索",
      edit: "编辑资料",
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
      convert_customer: "转建档客户",
    } as Record<string, string>)[value] ||
    value
  );
}

function formatChange(value?: Record<string, unknown>) {
  return value ? JSON.stringify(value) : "-";
}

onMounted(() => {
  loadOptions();
  fetchList();
});
</script>

<style scoped>
.lead-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.lead-filter,
.lead-table {
  border-radius: 8px;
}

.toolbar,
.toolbar-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.toolbar-title {
  font-size: 16px;
  font-weight: 600;
}

.pager {
  display: flex;
  justify-content: flex-end;
  padding-top: 16px;
}

.lead-form {
  padding-right: 16px;
}

.drawer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 12px 0 4px;
}

.detail-section {
  margin-top: 18px;
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

.timeline-content {
  margin-left: 8px;
}

.timeline-extra {
  display: block;
  margin-top: 6px;
  color: var(--el-text-color-secondary);
}

.import-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 16px 0;
}

.label-with-tip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.tip-icon {
  color: var(--el-text-color-secondary);
  cursor: help;
}
</style>
