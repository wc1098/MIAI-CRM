<template>
  <div class="app-container product-page">
    <el-card shadow="never" class="filter-card">
      <el-form :model="query" inline>
        <el-form-item label="关键词">
          <el-input
            v-model="query.keyword"
            clearable
            placeholder="套餐名称/说明/备注"
            style="width: 220px"
            @keyup.enter="fetchList"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" clearable placeholder="全部" style="width: 140px">
            <el-option label="启用" value="0" />
            <el-option label="停用" value="1" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" icon="Search" @click="fetchList">查询</el-button>
          <el-button icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="toolbar">
          <div>
            <div class="toolbar-title">产品管理</div>
            <div class="toolbar-note">维护品牌统一销售套餐，供后续合同创建选择</div>
          </div>
          <el-button v-hasPerm="['crm:product:create']" type="primary" icon="Plus" @click="openCreate">新增套餐</el-button>
        </div>
      </template>

      <el-table v-loading="loading" :data="rows" border stripe row-key="id">
        <el-table-column prop="package_name" label="套餐名称" min-width="180" show-overflow-tooltip />
        <el-table-column label="标准价" width="120" align="right">
          <template #default="{ row }">{{ money(row.standard_price) }}</template>
        </el-table-column>
        <el-table-column label="服务时长" width="110">
          <template #default="{ row }">{{ row.service_days ?? 0 }}天</template>
        </el-table-column>
        <el-table-column prop="recommendation_quota" label="推荐次数" width="100" />
        <el-table-column prop="meeting_quota" label="约见次数" width="100" />
        <el-table-column prop="course_quota" label="课程次数" width="100" />
        <el-table-column label="线上约见" width="100">
          <template #default="{ row }">
            <el-tag :type="row.supports_online_meeting ? 'success' : 'info'">
              {{ row.supports_online_meeting ? "支持" : "不支持" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sort" label="排序" width="80" />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === '0' ? 'success' : 'danger'">
              {{ row.status === "0" ? "启用" : "停用" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updated_time" label="更新时间" min-width="170" show-overflow-tooltip />
        <el-table-column fixed="right" label="操作" width="260" align="center">
          <template #default="{ row }">
            <div class="table-actions">
              <el-button v-hasPerm="['crm:product:detail']" link type="primary" icon="View" @click="openDetail(row.id)">详情</el-button>
              <el-button v-hasPerm="['crm:product:update']" link type="primary" icon="Edit" @click="openEdit(row.id)">编辑</el-button>
              <el-button
                v-hasPerm="['crm:product:change_status']"
                link
                :type="row.status === '0' ? 'warning' : 'success'"
                :icon="row.status === '0' ? 'VideoPause' : 'VideoPlay'"
                @click="toggleStatus(row)"
              >
                {{ row.status === "0" ? "禁用" : "启用" }}
              </el-button>
              <el-button v-hasPerm="['crm:product:delete']" link type="danger" icon="Delete" @click="deleteRow(row)">删除</el-button>
            </div>
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

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="720px" destroy-on-close @closed="resetForm">
      <template v-if="dialogMode === 'detail'">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="套餐名称">{{ detail?.package_name || "-" }}</el-descriptions-item>
          <el-descriptions-item label="标准价">{{ money(detail?.standard_price) }}</el-descriptions-item>
          <el-descriptions-item label="服务时长">{{ detail?.service_days ?? 0 }}天</el-descriptions-item>
          <el-descriptions-item label="推荐次数">{{ detail?.recommendation_quota ?? 0 }}</el-descriptions-item>
          <el-descriptions-item label="约见次数">{{ detail?.meeting_quota ?? 0 }}</el-descriptions-item>
          <el-descriptions-item label="课程次数">{{ detail?.course_quota ?? 0 }}</el-descriptions-item>
          <el-descriptions-item label="线上约见">
            {{ detail?.supports_online_meeting ? "支持" : "不支持" }}
          </el-descriptions-item>
          <el-descriptions-item label="排序">{{ detail?.sort ?? 0 }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="detail?.status === '0' ? 'success' : 'danger'">
              {{ detail?.status === "0" ? "启用" : "停用" }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ detail?.updated_time || "-" }}</el-descriptions-item>
          <el-descriptions-item label="套餐说明" :span="2">{{ detail?.description || "-" }}</el-descriptions-item>
          <el-descriptions-item label="内部备注" :span="2">{{ detail?.internal_remark || "-" }}</el-descriptions-item>
        </el-descriptions>
      </template>

      <el-form v-else ref="formRef" :model="form" :rules="rules" label-width="112px">
        <el-form-item label="套餐名称" prop="package_name">
          <el-input v-model="form.package_name" clearable maxlength="128" show-word-limit placeholder="请输入套餐名称" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="标准价" prop="standard_price">
              <el-input-number v-model="form.standard_price" :min="0" :precision="2" :step="100" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="服务时长天数" prop="service_days">
              <el-input-number v-model="form.service_days" :min="0" :precision="0" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="推荐次数" prop="recommendation_quota">
              <el-input-number v-model="form.recommendation_quota" :min="0" :precision="0" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="约见次数" prop="meeting_quota">
              <el-input-number v-model="form.meeting_quota" :min="0" :precision="0" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="课程次数" prop="course_quota">
              <el-input-number v-model="form.course_quota" :min="0" :precision="0" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="线上约见">
              <el-switch v-model="form.supports_online_meeting" active-text="支持" inactive-text="不支持" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="排序" prop="sort">
              <el-input-number v-model="form.sort" :min="0" :max="9999" :precision="0" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="form.status">
            <el-radio value="0">启用</el-radio>
            <el-radio value="1">停用</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="套餐说明">
          <el-input v-model="form.description" type="textarea" :rows="3" maxlength="1000" show-word-limit />
        </el-form-item>
        <el-form-item label="内部备注">
          <el-input v-model="form.internal_remark" type="textarea" :rows="3" maxlength="1000" show-word-limit />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button v-if="dialogMode !== 'detail'" type="primary" :loading="submitLoading" @click="submitForm">保存</el-button>
        <el-button v-else type="primary" @click="dialogVisible = false">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from "element-plus";
import ProductAPI, { ProductPackageForm, ProductPackageTable } from "@/api/module_crm/product";

defineOptions({
  name: "MiailoveProduct",
  inheritAttrs: false,
});

const loading = ref(false);
const submitLoading = ref(false);
const rows = ref<ProductPackageTable[]>([]);
const total = ref(0);
const detail = ref<ProductPackageTable>();
const dialogVisible = ref(false);
const dialogMode = ref<"create" | "update" | "detail">("create");
const dialogTitle = ref("新增套餐");
const formRef = ref<FormInstance>();

const query = reactive({
  page_no: 1,
  page_size: 10,
  keyword: undefined as string | undefined,
  status: undefined as string | undefined,
});

const initialForm: ProductPackageForm = {
  id: undefined,
  package_name: undefined,
  standard_price: 0,
  service_days: 0,
  recommendation_quota: 0,
  meeting_quota: 0,
  course_quota: 0,
  supports_online_meeting: false,
  description: undefined,
  internal_remark: undefined,
  sort: 0,
  status: "0",
};

const form = reactive<ProductPackageForm>({ ...initialForm });

const rules = reactive<FormRules<ProductPackageForm>>({
  package_name: [{ required: true, message: "请输入套餐名称", trigger: "blur" }],
  standard_price: [{ required: true, message: "请输入标准价", trigger: "blur" }],
  service_days: [{ required: true, message: "请输入服务时长天数", trigger: "blur" }],
  recommendation_quota: [{ required: true, message: "请输入推荐次数", trigger: "blur" }],
  meeting_quota: [{ required: true, message: "请输入约见次数", trigger: "blur" }],
  course_quota: [{ required: true, message: "请输入课程次数", trigger: "blur" }],
  sort: [{ required: true, message: "请输入排序", trigger: "blur" }],
  status: [{ required: true, message: "请选择状态", trigger: "change" }],
});

function money(value?: string | number) {
  const amount = Number(value ?? 0);
  return Number.isFinite(amount) ? `¥${amount.toFixed(2)}` : "¥0.00";
}

async function fetchList() {
  loading.value = true;
  try {
    const response = await ProductAPI.listProduct(query);
    rows.value = response.data.data.items || [];
    total.value = response.data.data.total || 0;
  } finally {
    loading.value = false;
  }
}

function resetQuery() {
  query.page_no = 1;
  query.keyword = undefined;
  query.status = undefined;
  fetchList();
}

function resetForm() {
  formRef.value?.clearValidate();
  Object.assign(form, { ...initialForm });
  detail.value = undefined;
}

function openCreate() {
  dialogMode.value = "create";
  dialogTitle.value = "新增套餐";
  Object.assign(form, { ...initialForm });
  dialogVisible.value = true;
}

async function openEdit(id?: number) {
  if (!id) return;
  const response = await ProductAPI.detailProduct(id);
  dialogMode.value = "update";
  dialogTitle.value = "编辑套餐";
  Object.assign(form, response.data.data);
  dialogVisible.value = true;
}

async function openDetail(id?: number) {
  if (!id) return;
  const response = await ProductAPI.detailProduct(id);
  detail.value = response.data.data;
  dialogMode.value = "detail";
  dialogTitle.value = "套餐详情";
  dialogVisible.value = true;
}

async function submitForm() {
  const valid = await formRef.value?.validate();
  if (!valid) return;
  submitLoading.value = true;
  try {
    const id = form.id;
    if (id) {
      await ProductAPI.updateProduct(id, form);
    } else {
      await ProductAPI.createProduct(form);
    }
    ElMessage.success("产品套餐已保存");
    dialogVisible.value = false;
    await fetchList();
  } finally {
    submitLoading.value = false;
  }
}

async function toggleStatus(row: ProductPackageTable) {
  if (!row.id) return;
  const nextStatus = row.status === "0" ? "1" : "0";
  await ElMessageBox.confirm(`确认${nextStatus === "0" ? "启用" : "禁用"}该套餐？`, "状态确认", { type: "warning" });
  await ProductAPI.changeProductStatus(row.id, nextStatus);
  ElMessage.success("状态已更新");
  await fetchList();
}

async function deleteRow(row: ProductPackageTable) {
  if (!row.id) return;
  await ElMessageBox.confirm("确认删除该产品套餐？删除后列表不可见。", "删除确认", { type: "warning" });
  await ProductAPI.deleteProduct(row.id);
  ElMessage.success("产品套餐已删除");
  await fetchList();
}

onMounted(fetchList);
</script>

<style scoped>
.product-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.filter-card :deep(.el-card__body) {
  padding-bottom: 0;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.toolbar-title {
  color: var(--el-text-color-primary);
  font-size: 16px;
  font-weight: 600;
}

.toolbar-note {
  margin-top: 4px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.table-actions {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  white-space: nowrap;
}

.pager {
  display: flex;
  justify-content: flex-end;
  padding-top: 16px;
}
</style>
