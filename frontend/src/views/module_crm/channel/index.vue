<!-- CRM渠道管理 -->
<template>
  <div class="app-container">
    <PageSearch
      ref="searchRef"
      :search-config="searchConfig"
      @query-click="handleQueryClick"
      @reset-click="handleResetClick"
    />

    <PageContent ref="contentRef" :content-config="contentConfig">
      <template #toolbar="{ toolbarRight, onToolbar, removeIds, cols }">
        <CrudToolbarLeft
          :remove-ids="removeIds"
          :perm-create="['crm:channel:create']"
          :perm-delete="['crm:channel:delete']"
          :perm-patch="['crm:channel:patch']"
          @add="handleOpenDialog('create')"
          @delete="onToolbar('delete')"
          @more="handleMoreClick"
        />
        <div class="data-table__toolbar--right">
          <CrudToolbarRight :buttons="toolbarRight" :cols="cols" :on-toolbar="onToolbar">
            <template #prepend>
              <el-tooltip content="导出">
                <el-button
                  v-hasPerm="['crm:channel:export']"
                  type="warning"
                  icon="download"
                  circle
                  @click="handleOpenExportsModal"
                />
              </el-tooltip>
            </template>
          </CrudToolbarRight>
        </div>
      </template>

      <template #table="{ data, loading, tableRef, onSelectionChange, pagination }">
        <div class="data-table__content">
          <el-table
            :ref="tableRef as any"
            v-loading="loading"
            row-key="id"
            :data="data"
            height="100%"
            border
            stripe
            @selection-change="onSelectionChange"
          >
            <template #empty>
              <el-empty :image-size="80" description="暂无数据" />
            </template>
            <el-table-column
              v-if="contentCols.find((col) => col.prop === 'selection')?.show"
              type="selection"
              min-width="55"
              align="center"
            />
            <el-table-column
              v-if="contentCols.find((col) => col.prop === 'index')?.show"
              fixed
              label="序号"
              min-width="60"
            >
              <template #default="scope">
                {{ (pagination.currentPage - 1) * pagination.pageSize + scope.$index + 1 }}
              </template>
            </el-table-column>
            <el-table-column
              v-if="contentCols.find((col) => col.prop === 'channel_name')?.show"
              label="渠道名称"
              prop="channel_name"
              min-width="130"
            />
            <el-table-column
              v-if="contentCols.find((col) => col.prop === 'channel_code')?.show"
              label="渠道编码"
              prop="channel_code"
              min-width="160"
              show-overflow-tooltip
            />
            <el-table-column
              v-if="contentCols.find((col) => col.prop === 'channel_type')?.show"
              label="渠道类型"
              prop="channel_type"
              min-width="110"
            >
              <template #default="scope">
                {{ channelTypeLabel(scope.row.channel_type) }}
              </template>
            </el-table-column>
            <el-table-column
              v-if="contentCols.find((col) => col.prop === 'source_system')?.show"
              label="来源系统"
              prop="source_system"
              min-width="120"
              show-overflow-tooltip
            />
            <el-table-column
              v-if="contentCols.find((col) => col.prop === 'external_code')?.show"
              label="外部编码"
              prop="external_code"
              min-width="130"
              show-overflow-tooltip
            />
            <el-table-column
              v-if="contentCols.find((col) => col.prop === 'landing_url')?.show"
              label="落地页"
              prop="landing_url"
              min-width="180"
              show-overflow-tooltip
            />
            <el-table-column
              v-if="contentCols.find((col) => col.prop === 'status')?.show"
              label="状态"
              prop="status"
              min-width="80"
            >
              <template #default="scope">
                <el-tag :type="scope.row.status === '0' ? 'success' : 'danger'">
                  {{ scope.row.status === "0" ? "启用" : "停用" }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column
              v-if="contentCols.find((col) => col.prop === 'sort')?.show"
              label="排序"
              prop="sort"
              min-width="80"
            />
            <el-table-column
              v-if="contentCols.find((col) => col.prop === 'updated_time')?.show"
              label="更新时间"
              prop="updated_time"
              min-width="180"
              sortable
            />
            <el-table-column
              v-if="contentCols.find((col) => col.prop === 'operation')?.show"
              fixed="right"
              label="操作"
              align="center"
              min-width="200"
            >
              <template #default="scope">
                <el-button
                  v-hasPerm="['crm:channel:detail']"
                  type="info"
                  size="small"
                  link
                  icon="View"
                  @click="handleOpenDialog('detail', scope.row.id)"
                >
                  详情
                </el-button>
                <el-button
                  v-hasPerm="['crm:channel:update']"
                  type="primary"
                  size="small"
                  link
                  icon="edit"
                  @click="handleOpenDialog('update', scope.row.id)"
                >
                  编辑
                </el-button>
                <el-button
                  v-hasPerm="['crm:channel:delete']"
                  type="danger"
                  size="small"
                  link
                  icon="delete"
                  @click="handleRowDelete(scope.row.id)"
                >
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </template>
    </PageContent>

    <EnhancedDialog
      v-model="dialogVisible.visible"
      :title="dialogVisible.title"
      @close="handleCloseDialog"
    >
      <template v-if="dialogVisible.type === 'detail'">
        <el-descriptions :column="4" border>
          <el-descriptions-item label="渠道名称" :span="2">
            {{ detailFormData.channel_name }}
          </el-descriptions-item>
          <el-descriptions-item label="渠道编码" :span="2">
            {{ detailFormData.channel_code }}
          </el-descriptions-item>
          <el-descriptions-item label="渠道类型" :span="2">
            {{ channelTypeLabel(detailFormData.channel_type) }}
          </el-descriptions-item>
          <el-descriptions-item label="来源系统" :span="2">
            {{ detailFormData.source_system }}
          </el-descriptions-item>
          <el-descriptions-item label="外部编码" :span="2">
            {{ detailFormData.external_code }}
          </el-descriptions-item>
          <el-descriptions-item label="排序" :span="2">
            {{ detailFormData.sort }}
          </el-descriptions-item>
          <el-descriptions-item label="状态" :span="2">
            <el-tag :type="detailFormData.status === '0' ? 'success' : 'danger'">
              {{ detailFormData.status === "0" ? "启用" : "停用" }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="更新时间" :span="2">
            {{ detailFormData.updated_time }}
          </el-descriptions-item>
          <el-descriptions-item label="落地页" :span="4">
            {{ detailFormData.landing_url }}
          </el-descriptions-item>
          <el-descriptions-item label="描述" :span="4">
            {{ detailFormData.description }}
          </el-descriptions-item>
        </el-descriptions>
      </template>
      <template v-else>
        <el-form
          ref="dataFormRef"
          :model="formData"
          :rules="rules"
          label-suffix=":"
          label-width="auto"
          label-position="right"
        >
          <el-form-item label="渠道名称" prop="channel_name">
            <el-input
              v-model="formData.channel_name"
              placeholder="请输入渠道名称"
              :maxlength="64"
              show-word-limit
            />
          </el-form-item>
          <el-form-item label="渠道编码" prop="channel_code">
            <el-input
              v-model="formData.channel_code"
              placeholder="1-64位字母/数字/下划线/中划线"
              :maxlength="64"
              show-word-limit
            />
          </el-form-item>
          <el-form-item label="渠道类型" prop="channel_type">
            <el-select
              v-model="formData.channel_type"
              placeholder="请选择渠道类型"
              style="width: 100%"
            >
              <el-option
                v-for="item in channelTypeOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="来源系统" prop="source_system">
            <el-input
              v-model="formData.source_system"
              placeholder="例如 miniapp、third_crm"
              :maxlength="64"
            />
          </el-form-item>
          <el-form-item label="外部编码" prop="external_code">
            <el-input
              v-model="formData.external_code"
              placeholder="外部系统渠道编码，可为空"
              :maxlength="128"
            />
          </el-form-item>
          <el-form-item label="落地页" prop="landing_url">
            <el-input
              v-model="formData.landing_url"
              placeholder="投放页/落地页链接，可为空"
              :maxlength="500"
            />
          </el-form-item>
          <el-form-item label="排序" prop="sort">
            <el-input-number
              v-model="formData.sort"
              controls-position="right"
              :min="1"
              :max="999"
            />
          </el-form-item>
          <el-form-item label="状态" prop="status">
            <el-radio-group v-model="formData.status">
              <el-radio value="0">启用</el-radio>
              <el-radio value="1">停用</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="描述" prop="description">
            <el-input
              v-model="formData.description"
              :rows="4"
              :maxlength="255"
              show-word-limit
              type="textarea"
              placeholder="请输入描述"
            />
          </el-form-item>
        </el-form>
      </template>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="handleCloseDialog">取消</el-button>
          <el-button
            v-if="dialogVisible.type !== 'detail'"
            type="primary"
            :loading="submitLoading"
            @click="handleSubmit"
          >
            确定
          </el-button>
          <el-button v-else type="primary" @click="handleCloseDialog">确定</el-button>
        </div>
      </template>
    </EnhancedDialog>

    <ExportModal
      v-model="exportsDialogVisible"
      :content-config="curdContentConfig"
      :query-params="exportQueryParams"
      :page-data="exportPageData"
      :selection-data="exportSelectionData"
    />
  </div>
</template>

<script setup lang="ts">
defineOptions({
  name: "CrmChannel",
  inheritAttrs: false,
});

import { computed, onMounted, reactive, ref, unref } from "vue";
import ChannelAPI, { ChannelForm, ChannelPageQuery, ChannelTable } from "@/api/module_crm/channel";
import { fetchAllPages } from "@/utils/fetchAllPages";
import { useDictStore, useUserStore } from "@/store";
import CrudToolbarLeft from "@/components/CURD/CrudToolbarLeft.vue";
import CrudToolbarRight from "@/components/CURD/CrudToolbarRight.vue";
import PageSearch from "@/components/CURD/PageSearch.vue";
import PageContent from "@/components/CURD/PageContent.vue";
import EnhancedDialog from "@/components/CURD/EnhancedDialog.vue";
import ExportModal from "@/components/CURD/ExportModal.vue";
import { useCrudList } from "@/components/CURD/useCrudList";
import type { IContentConfig, ISearchConfig } from "@/components/CURD/types";

const { searchRef, contentRef, handleQueryClick, handleResetClick, refreshList } = useCrudList();
const dataFormRef = ref();
const submitLoading = ref(false);

const FALLBACK_CHANNEL_TYPE_OPTIONS = [
  { label: "小程序", value: "miniprogram" },
  { label: "人工录入", value: "manual" },
  { label: "批量导入", value: "import" },
  { label: "外部系统", value: "external" },
  { label: "广告投放", value: "ad" },
  { label: "线下渠道", value: "offline" },
  { label: "其他", value: "other" },
];
const dictStore = useDictStore();
const channelTypeOptions = ref<OptionType[]>([...FALLBACK_CHANNEL_TYPE_OPTIONS]);

function channelTypeLabel(value?: string) {
  return channelTypeOptions.value.find((item) => item.value === value)?.label ?? value ?? "";
}

const searchConfig = reactive<ISearchConfig>({
  permPrefix: "crm:channel",
  colon: true,
  isExpandable: true,
  showNumber: 3,
  form: { labelWidth: "auto" },
  formItems: [
    {
      prop: "channel_name",
      label: "渠道名称",
      type: "input",
      attrs: { placeholder: "请输入渠道名称", clearable: true },
    },
    {
      prop: "channel_code",
      label: "渠道编码",
      type: "input",
      attrs: { placeholder: "请输入渠道编码", clearable: true },
    },
    {
      prop: "channel_type",
      label: "渠道类型",
      type: "select",
      options: channelTypeOptions.value,
      attrs: { placeholder: "请选择渠道类型", clearable: true, style: { width: "167.5px" } },
    },
    {
      prop: "source_system",
      label: "来源系统",
      type: "input",
      attrs: { placeholder: "请输入来源系统", clearable: true },
    },
    {
      prop: "status",
      label: "状态",
      type: "select",
      options: [
        { label: "启用", value: "0" },
        { label: "停用", value: "1" },
      ],
      attrs: { placeholder: "请选择状态", clearable: true, style: { width: "167.5px" } },
    },
    {
      prop: "created_time",
      label: "创建时间",
      type: "date-picker",
      initialValue: [],
      attrs: {
        type: "datetimerange",
        valueFormat: "YYYY-MM-DD HH:mm:ss",
        rangeSeparator: "至",
        startPlaceholder: "开始日期",
        endPlaceholder: "结束日期",
        style: { width: "340px" },
      },
    },
  ],
});

const contentCols = reactive<
  Array<{
    prop?: string;
    label?: string;
    show?: boolean;
  }>
>([
  { prop: "selection", label: "选择框", show: true },
  { prop: "index", label: "序号", show: true },
  { prop: "channel_name", label: "渠道名称", show: true },
  { prop: "channel_code", label: "渠道编码", show: true },
  { prop: "channel_type", label: "渠道类型", show: true },
  { prop: "source_system", label: "来源系统", show: true },
  { prop: "external_code", label: "外部编码", show: true },
  { prop: "landing_url", label: "落地页", show: true },
  { prop: "status", label: "状态", show: true },
  { prop: "sort", label: "排序", show: true },
  { prop: "updated_time", label: "更新时间", show: true },
  { prop: "operation", label: "操作", show: true },
]);

const contentConfig = reactive<IContentConfig<ChannelPageQuery>>({
  permPrefix: "crm:channel",
  pk: "id",
  cols: contentCols as IContentConfig["cols"],
  hideColumnFilter: false,
  toolbar: [],
  defaultToolbar: ["refresh", "filter"],
  pagination: {
    pageSize: 10,
    pageSizes: [10, 20, 30, 50],
  },
  request: { page_no: "page_no", page_size: "page_size" },
  indexAction: async (params) => {
    const res = await ChannelAPI.listChannel(params as ChannelPageQuery);
    return {
      total: res.data.data.total,
      list: res.data.data.items,
    };
  },
  deleteAction: async (ids) => {
    await ChannelAPI.deleteChannel(
      ids
        .split(",")
        .map((s) => Number(s.trim()))
        .filter((n) => !Number.isNaN(n))
    );
    const userStore = useUserStore();
    await userStore.getUserInfo();
  },
  deleteConfirm: {
    title: "警告",
    message: "确认删除该项数据?",
    type: "warning",
  },
});

const detailFormData = ref<ChannelTable>({});
const formData = reactive<ChannelForm>({
  id: undefined,
  channel_code: undefined,
  channel_name: undefined,
  channel_type: "miniprogram",
  source_system: undefined,
  external_code: undefined,
  landing_url: undefined,
  sort: 1,
  status: "0",
  description: undefined,
});

const initialFormData: ChannelForm = {
  id: undefined,
  channel_code: undefined,
  channel_name: undefined,
  channel_type: "miniprogram",
  source_system: undefined,
  external_code: undefined,
  landing_url: undefined,
  sort: 1,
  status: "0",
  description: undefined,
};

const dialogVisible = reactive({
  title: "",
  visible: false,
  type: "create" as "create" | "update" | "detail",
});

const CODE_PATTERN = /^[A-Za-z0-9_-]{1,64}$/;

const rules = reactive({
  channel_name: [{ required: true, message: "请输入渠道名称", trigger: "blur" }],
  channel_code: [
    { required: true, message: "请输入渠道编码", trigger: "blur" },
    {
      pattern: CODE_PATTERN,
      message: "1-64位字母/数字/下划线/中划线",
      trigger: "blur",
    },
  ],
  channel_type: [{ required: true, message: "请选择渠道类型", trigger: "change" }],
  sort: [{ required: true, message: "请输入排序", trigger: "blur" }],
  status: [{ required: true, message: "请选择状态", trigger: "change" }],
});

async function resetForm() {
  if (dataFormRef.value) {
    dataFormRef.value.resetFields();
    dataFormRef.value.clearValidate();
  }
  Object.assign(formData, initialFormData);
}

async function handleCloseDialog() {
  dialogVisible.visible = false;
  await resetForm();
}

async function handleOpenDialog(type: "create" | "update" | "detail", id?: number) {
  dialogVisible.type = type;
  if (id) {
    const response = await ChannelAPI.detailChannel(id);
    if (type === "detail") {
      dialogVisible.title = "渠道详情";
      Object.assign(detailFormData.value, response.data.data);
    } else {
      dialogVisible.title = "修改渠道";
      Object.assign(formData, response.data.data);
    }
  } else {
    dialogVisible.title = "新增渠道";
    Object.assign(formData, initialFormData);
  }
  dialogVisible.visible = true;
}

function handleRowDelete(id: number) {
  contentRef.value?.handleDelete(id);
}

async function handleSubmit() {
  dataFormRef.value.validate(async (valid: boolean) => {
    if (valid) {
      submitLoading.value = true;
      const id = formData.id;
      try {
        const payload = {
          ...formData,
          channel_code: formData.channel_code?.toUpperCase(),
        };
        if (id) {
          await ChannelAPI.updateChannel(id, { id, ...payload });
        } else {
          await ChannelAPI.createChannel(payload);
        }
        dialogVisible.visible = false;
        await resetForm();
        refreshList();
        const userStore = useUserStore();
        await userStore.getUserInfo();
      } catch (error: unknown) {
        console.error(error);
      } finally {
        submitLoading.value = false;
      }
    }
  });
}

async function handleMoreClick(status: string) {
  const rows = contentRef.value?.getSelectionData() as ChannelTable[] | undefined;
  const ids = (rows ?? []).map((r) => r.id).filter((id): id is number => id != null);
  if (!ids.length) {
    ElMessage.warning("请先选择要操作的数据");
    return;
  }
  ElMessageBox.confirm(`确认${status === "0" ? "启用" : "停用"}该项数据?`, "警告", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning",
  })
    .then(async () => {
      try {
        await ChannelAPI.batchChannel({ ids, status });
        refreshList();
        const userStore = useUserStore();
        await userStore.getUserInfo();
      } catch (error: unknown) {
        console.error(error);
      }
    })
    .catch(() => {
      ElMessageBox.close();
    });
}

const exportsDialogVisible = ref(false);
const exportQueryParams = computed(() => searchRef.value?.getQueryParams() ?? {});
const exportPageData = computed(() => (unref(contentRef.value?.pageData) ?? []) as ChannelTable[]);
const exportSelectionData = computed(
  () => (contentRef.value?.getSelectionData() ?? []) as ChannelTable[]
);

const exportColumns = [
  { prop: "channel_name", label: "渠道名称" },
  { prop: "channel_code", label: "渠道编码" },
  { prop: "channel_type", label: "渠道类型" },
  { prop: "source_system", label: "来源系统" },
  { prop: "external_code", label: "外部编码" },
  { prop: "landing_url", label: "落地页" },
  { prop: "sort", label: "排序" },
  { prop: "status", label: "状态" },
  { prop: "description", label: "描述" },
  { prop: "updated_time", label: "更新时间" },
];

const curdContentConfig = {
  permPrefix: "crm:channel",
  cols: exportColumns as unknown as IContentConfig["cols"],
  exportsAction: async (params: Record<string, unknown>) => {
    return fetchAllPages<ChannelTable>({
      initialQuery: { ...params },
      fetchPage: async (q) => {
        const res = await ChannelAPI.listChannel(q as unknown as ChannelPageQuery);
        return {
          total: res.data?.data?.total ?? 0,
          list: res.data?.data?.items ?? [],
        };
      },
    });
  },
} as unknown as IContentConfig;

function handleOpenExportsModal() {
  exportsDialogVisible.value = true;
}

onMounted(async () => {
  await dictStore.getDict(["crm_channel_type"]);
  const dictOptions = dictStore.getDictArray("crm_channel_type").map((item) => ({
    label: item.dict_label,
    value: item.dict_value,
  }));
  if (dictOptions.length) {
    channelTypeOptions.value = dictOptions;
    const typeItem = searchConfig.formItems?.find((item) => item.prop === "channel_type");
    if (typeItem) {
      typeItem.options = dictOptions;
    }
  }
});
</script>
