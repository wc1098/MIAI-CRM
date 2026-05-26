<template>
  <div class="app-container service-workbench">
    <el-card shadow="never" class="filter-card">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane v-if="canManageService" label="待分配" name="pending" />
        <el-tab-pane label="我的服务" name="mine" />
        <el-tab-pane v-if="canManageService" label="全部服务" name="all" />
        <el-tab-pane v-if="canManageService" label="关单审核" name="closeReview" />
      </el-tabs>

      <el-form :model="query" inline>
        <el-form-item label="关键词">
          <el-input v-model="query.keyword" clearable placeholder="编号/姓名/手机号/合同号" style="width: 240px" @keyup.enter="fetchList" />
        </el-form-item>
        <el-form-item label="VIP等级">
          <el-select v-model="query.vip_level" clearable placeholder="全部" style="width: 130px">
            <el-option v-for="item in vipLevelOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value || ''" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="activeTab !== 'pending'" label="服务状态">
          <el-select v-model="query.vip_status" clearable placeholder="全部" style="width: 150px">
            <el-option v-for="item in caseStatusOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value || ''" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="canManageService" label="门店">
          <el-select v-model="query.store_id" clearable filterable placeholder="全部" style="width: 180px" @change="handleStoreFilterChange">
            <el-option v-for="item in deptOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="canManageService && activeTab !== 'pending'" label="服务红娘">
          <el-select v-model="query.service_owner_user_id" clearable filterable placeholder="全部" style="width: 180px" :disabled="!query.store_id">
            <el-option v-for="item in filterMatchmakers" :key="item.id" :label="`${item.name}${item.mobile ? `（${item.mobile}）` : ''}`" :value="item.id" />
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
            <div class="toolbar-title">{{ pageTitle }}</div>
            <div class="toolbar-note">以服务工单承载分配、深访、权益核销、关单审核</div>
          </div>
        </div>
      </template>

      <el-table v-loading="loading" :data="rows" border stripe row-key="id">
        <el-table-column prop="person_display_no" label="客户编号" width="110" show-overflow-tooltip />
        <el-table-column prop="person_name" label="姓名" width="110" show-overflow-tooltip />
        <el-table-column label="性别/年龄" width="110">
          <template #default="{ row }">{{ genderText(row.person_gender) }} / {{ row.person_age ?? "-" }}</template>
        </el-table-column>
        <el-table-column prop="person_mobile" label="手机号" width="130" show-overflow-tooltip />
        <el-table-column label="VIP等级" width="100">
          <template #default="{ row }"><el-tag :type="dictTag(vipLevelOptions, row.vip_level)">{{ dictText(vipLevelOptions, row.vip_level) }}</el-tag></template>
        </el-table-column>
        <el-table-column label="服务状态" width="120">
          <template #default="{ row }"><el-tag :type="dictTag(caseStatusOptions, row.case_status || row.vip_status)">{{ dictText(caseStatusOptions, row.case_status || row.vip_status) }}</el-tag></template>
        </el-table-column>
        <el-table-column label="关单审核" width="110">
          <template #default="{ row }"><el-tag :type="dictTag(closeStatusOptions, row.close_review_status)">{{ dictText(closeStatusOptions, row.close_review_status) }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="contract_no" label="合同编号" min-width="150" show-overflow-tooltip />
        <el-table-column prop="service_owner_user_name" label="服务红娘" width="110" show-overflow-tooltip>
          <template #default="{ row }">{{ row.service_owner_user_name || "-" }}</template>
        </el-table-column>
        <el-table-column prop="store_name" label="门店" width="130" show-overflow-tooltip />
        <el-table-column label="权益进度" min-width="180">
          <template #default="{ row }">
            <div class="quota-line">推 {{ quotaText(row, "recommendation") }} / 见 {{ quotaText(row, "meeting") }} / 课 {{ quotaText(row, "course") }}</div>
          </template>
        </el-table-column>
        <el-table-column label="深访/核销" width="110">
          <template #default="{ row }">{{ row.deep_interview_count || 0 }} / {{ row.usage_count || 0 }}</template>
        </el-table-column>
        <el-table-column v-if="activeTab === 'pending'" label="等待时长" width="110">
          <template #default="{ row }">{{ waitingText(row.waiting_hours) }}</template>
        </el-table-column>
        <el-table-column v-else label="剩余天数" width="100">
          <template #default="{ row }">{{ row.remaining_days ?? "-" }}</template>
        </el-table-column>
        <el-table-column fixed="right" label="操作" width="280" align="center">
          <template #default="{ row }">
            <div class="table-actions">
              <el-button v-hasPerm="['service:vip:detail']" link type="primary" icon="View" @click="openDetail(row.id)">详情</el-button>
              <el-button v-if="row.case_status === 'pending_assign'" v-hasPerm="['service:vip:assign']" link type="success" icon="UserFilled" @click="openAssign(row)">分配</el-button>
              <el-button v-else-if="['serving', 'reopened'].includes(row.case_status || '')" v-hasPerm="['service:vip:assign']" link type="warning" icon="Switch" @click="openTransfer(row)">改派</el-button>
              <el-button v-if="['serving', 'reopened'].includes(row.case_status || '')" v-hasPerm="['service:vip:close']" link type="danger" icon="CircleClose" @click="openClose(row)">关单</el-button>
              <el-button v-if="row.close_review_status === 'pending'" v-hasPerm="['service:vip:close']" link type="success" icon="Check" @click="openReview(row)">审核</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination v-model:current-page="query.page_no" v-model:page-size="query.page_size" :total="total" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next, jumper" @size-change="fetchList" @current-change="fetchList" />
      </div>
    </el-card>

    <el-dialog v-model="assignVisible" :title="assignMode === 'assign' ? '分配服务红娘' : '改派服务红娘'" width="620px" destroy-on-close>
      <el-descriptions v-if="currentRow" :column="2" border class="summary">
        <el-descriptions-item label="客户">{{ currentRow.person_name || "-" }}</el-descriptions-item>
        <el-descriptions-item label="门店">{{ currentRow.store_name || "-" }}</el-descriptions-item>
        <el-descriptions-item label="VIP等级">{{ dictText(vipLevelOptions, currentRow.vip_level) }}</el-descriptions-item>
        <el-descriptions-item label="合同编号">{{ currentRow.contract_no || "-" }}</el-descriptions-item>
      </el-descriptions>
      <el-form ref="assignFormRef" :model="assignForm" :rules="assignRules" label-width="110px">
        <el-form-item label="服务红娘" prop="service_owner_user_id">
          <el-select v-model="assignForm.service_owner_user_id" filterable placeholder="请选择同门店服务红娘" style="width: 100%">
            <el-option v-for="item in matchmakerOptions" :key="item.id" :label="`${item.name}${item.mobile ? `（${item.mobile}）` : ''}`" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="assignForm.remark" type="textarea" :rows="3" maxlength="1000" show-word-limit /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="assignVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="submitAssign">确认</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="interviewVisible" title="新增深访" width="720px" destroy-on-close>
      <el-form ref="interviewFormRef" :model="interviewForm" :rules="interviewRules" label-width="100px">
        <el-form-item label="深访类型" prop="interview_type">
          <el-select v-model="interviewForm.interview_type" style="width: 100%">
            <el-option v-for="item in interviewTypeOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value || ''" />
          </el-select>
        </el-form-item>
        <el-form-item label="深访时间"><el-date-picker v-model="interviewForm.interviewed_at" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width: 100%" /></el-form-item>
        <el-form-item label="关键词"><el-select v-model="interviewForm.keywords" multiple filterable allow-create default-first-option style="width: 100%" /></el-form-item>
        <el-form-item label="深访内容" prop="content"><el-input v-model="interviewForm.content" type="textarea" :rows="6" maxlength="20000" show-word-limit /></el-form-item>
        <el-form-item label="摘要"><el-input v-model="interviewForm.summary" type="textarea" :rows="3" maxlength="5000" show-word-limit /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="interviewVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="submitInterview">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="usageVisible" title="新增权益核销" width="720px" destroy-on-close>
      <el-form ref="usageFormRef" :model="usageForm" :rules="usageRules" label-width="110px">
        <el-form-item label="核销权益" prop="entitlement_id">
          <el-select v-model="usageForm.entitlement_id" style="width: 100%" @change="handleUsageEntitlementChange">
            <el-option v-for="item in manualUsageEntitlements" :key="item.id" :label="`${dictText(entitlementTypeOptions, item.entitlement_type)}：剩余 ${item.remaining_quota}/${item.total_quota}${item.unit}`" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="核销数量" prop="quantity"><el-input-number v-model="usageForm.quantity" :min="1" :precision="0" style="width: 180px" /></el-form-item>
        <el-form-item label="发生时间"><el-date-picker v-model="usageForm.occurred_at" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width: 100%" /></el-form-item>
        <el-form-item label="标题"><el-input v-model="usageForm.title" maxlength="128" show-word-limit /></el-form-item>
        <el-form-item v-if="selectedEntitlement?.entitlement_type !== 'course'" label="候选资源">
          <el-select v-model="usageForm.candidate_person_id" filterable remote reserve-keyword clearable :remote-method="searchCandidates" :loading="candidateLoading" placeholder="搜索备选库候选" style="width: 100%">
            <el-option v-for="item in candidateOptions" :key="item.person_id" :label="`${item.name} ${item.mobile || ''}`" :value="item.person_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="核销内容"><el-input v-model="usageForm.content" type="textarea" :rows="4" maxlength="5000" show-word-limit /></el-form-item>
        <el-form-item label="超额原因"><el-input v-model="usageForm.overuse_reason" type="textarea" :rows="2" maxlength="1000" show-word-limit placeholder="超额核销时必填" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="usageVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="submitUsage">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="closeVisible" title="申请关单" width="560px" destroy-on-close>
      <el-form ref="closeFormRef" :model="closeForm" :rules="closeRules" label-width="90px">
        <el-form-item label="关单原因" prop="reason"><el-input v-model="closeForm.reason" type="textarea" :rows="4" maxlength="2000" show-word-limit /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeVisible = false">取消</el-button>
        <el-button type="danger" :loading="submitLoading" @click="submitClose">提交审核</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="reviewVisible" title="关单审核" width="560px" destroy-on-close>
      <el-form :model="reviewForm" label-width="90px">
        <el-form-item label="审核意见"><el-input v-model="reviewForm.review_remark" type="textarea" :rows="4" maxlength="2000" show-word-limit /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reviewVisible = false">取消</el-button>
        <el-button type="danger" :loading="submitLoading" @click="submitReview(false)">驳回</el-button>
        <el-button type="primary" :loading="submitLoading" @click="submitReview(true)">通过</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="processVisible" title="新增过程记录" width="640px" destroy-on-close>
      <el-form ref="processFormRef" :model="processForm" :rules="processRules" label-width="110px">
        <el-form-item label="记录类型" prop="record_type">
          <el-select v-model="processForm.record_type" placeholder="请选择记录类型" filterable style="width: 100%">
            <el-option v-for="item in processRecordTypeOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value || ''" />
          </el-select>
        </el-form-item>
        <el-form-item label="沟通方式">
          <el-select v-model="processForm.method" placeholder="请选择沟通方式" clearable style="width: 100%">
            <el-option v-for="item in followMethodOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value || ''" />
          </el-select>
        </el-form-item>
        <el-form-item label="发生时间">
          <el-date-picker v-model="processForm.occurred_at" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" placeholder="默认当前时间" style="width: 100%" />
        </el-form-item>
        <el-form-item label="内容" prop="content">
          <el-input v-model="processForm.content" type="textarea" :rows="5" maxlength="20000" show-word-limit placeholder="填写服务沟通、需求确认、推荐说明、约见反馈、续费沟通等内容" />
        </el-form-item>
        <el-form-item label="需求摘要">
          <el-input v-model="processForm.need_summary" type="textarea" :rows="2" maxlength="5000" show-word-limit />
        </el-form-item>
        <el-form-item label="下次跟进">
          <el-date-picker v-model="processForm.next_follow_at" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" placeholder="请选择下次跟进时间" style="width: 100%" />
        </el-form-item>
        <el-form-item label="下一步动作">
          <el-input v-model="processForm.next_action" maxlength="255" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="processVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="submitProcessRecord">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="appointmentVisible" title="服务邀约到店" width="640px" destroy-on-close>
      <el-form ref="appointmentFormRef" :model="appointmentForm" :rules="appointmentRules" label-width="110px">
        <el-form-item label="预约日期" prop="scheduled_at">
          <el-date-picker v-model="appointmentForm.scheduled_at" type="date" value-format="YYYY-MM-DD 00:00:00" placeholder="请选择预约日期" style="width: 100%" />
        </el-form-item>
        <el-form-item label="预约时段">
          <el-select v-model="appointmentForm.appointment_slot" placeholder="请选择预约时段" clearable style="width: 100%">
            <el-option v-for="item in appointmentSlotOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value || ''" />
          </el-select>
        </el-form-item>
        <el-form-item label="到访目的">
          <el-select v-model="appointmentForm.visit_purpose" placeholder="请选择到访目的" clearable style="width: 100%">
            <el-option v-for="item in visitPurposeOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value || ''" />
          </el-select>
        </el-form-item>
        <el-form-item label="到店礼">
          <el-input v-model="appointmentForm.promised_gift" maxlength="255" show-word-limit />
        </el-form-item>
        <el-form-item label="邀约内容" prop="content">
          <el-input v-model="appointmentForm.content" type="textarea" :rows="4" maxlength="20000" show-word-limit placeholder="填写本次服务邀约说明" />
        </el-form-item>
        <el-form-item label="需求摘要">
          <el-input v-model="appointmentForm.need_summary" type="textarea" :rows="2" maxlength="5000" show-word-limit />
        </el-form-item>
        <el-form-item label="下次跟进">
          <el-date-picker v-model="appointmentForm.next_follow_at" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" placeholder="请选择下次跟进时间" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="appointmentVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="submitAppointment">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="profileEditVisible" title="编辑客户资料" width="980px" destroy-on-close>
      <el-tabs>
        <el-tab-pane label="基础资料">
          <el-form ref="profileFormRef" :model="profileForm" :rules="profileRules" label-width="92px">
            <person-profile-fields :form="profileForm" :dict-options="profileDictOptions" :show-id-card="false" mobile-disabled>
              <template #photo>
                <el-form-item label="本人照片">
                  <el-upload v-model:file-list="profilePhotoFileList" list-type="picture-card" accept="image/*" multiple :http-request="uploadProfilePhoto" :on-remove="removeProfilePhoto">
                    <el-icon><Plus /></el-icon>
                  </el-upload>
                </el-form-item>
              </template>
            </person-profile-fields>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="择偶要求">
          <partner-preference-form ref="preferenceFormRef" :model-value="profileForm.partner_preference" :dict-options="preferenceDictOptions" :region-options="[]" :show-actions="false" />
        </el-tab-pane>
      </el-tabs>
      <template #footer>
        <el-button @click="profileEditVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="submitProfileEdit">保存</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailVisible" title="服务详情" size="86%">
      <template v-if="detail">
        <div class="detail-actions">
          <template v-if="canOperateService">
            <el-button v-hasPerm="['service:vip:deep_interview']" type="primary" icon="ChatLineSquare" @click="openInterview">新增深访</el-button>
            <el-button v-hasPerm="['service:vip:appointment']" type="primary" plain icon="Calendar" @click="openAppointment">邀约到店</el-button>
            <el-button v-hasPerm="['service:vip:process_record']" type="warning" icon="EditPen" @click="openProcessRecord">新增过程</el-button>
          </template>
          <el-alert v-else type="info" show-icon :closable="false" title="服务工单分配给红娘后，才可以进行深访和权益核销。" />
        </div>
        <el-tabs v-model="detailTab" @tab-change="handleDetailTabChange">
          <el-tab-pane label="服务概览" name="overview">
            <el-row :gutter="12" class="summary">
              <el-col :span="6"><el-statistic title="深访次数" :value="workSummary?.deep_interview_count ?? detail.deep_interview_count ?? 0" /></el-col>
              <el-col :span="6"><el-statistic title="有效核销" :value="workSummary?.active_usage_count ?? detail.usage_count ?? 0" /></el-col>
              <el-col :span="6"><el-statistic title="过程记录" :value="workSummary?.process_record_count ?? 0" /></el-col>
              <el-col :span="6"><el-statistic title="剩余天数" :value="workSummary?.remaining_days ?? detail.remaining_days ?? 0" /></el-col>
            </el-row>
            <el-descriptions :column="3" border>
              <el-descriptions-item label="客户编号">{{ detail.person_display_no || "-" }}</el-descriptions-item>
              <el-descriptions-item label="姓名">{{ detail.person_name || "-" }}</el-descriptions-item>
              <el-descriptions-item label="手机号">{{ detail.person_mobile || "-" }}</el-descriptions-item>
              <el-descriptions-item label="VIP等级">{{ dictText(vipLevelOptions, detail.vip_level) }}</el-descriptions-item>
              <el-descriptions-item label="服务状态">{{ dictText(caseStatusOptions, detail.case_status || detail.vip_status) }}</el-descriptions-item>
              <el-descriptions-item label="关单审核">{{ dictText(closeStatusOptions, detail.close_review_status) }}</el-descriptions-item>
              <el-descriptions-item label="服务红娘">{{ detail.service_owner_user_name || "-" }}</el-descriptions-item>
              <el-descriptions-item label="成交销售">{{ detail.owner_user_name || "-" }}</el-descriptions-item>
              <el-descriptions-item label="门店">{{ detail.store_name || "-" }}</el-descriptions-item>
              <el-descriptions-item label="合同编号">{{ detail.contract_no || "-" }}</el-descriptions-item>
              <el-descriptions-item label="合同名称">{{ detail.contract_name || "-" }}</el-descriptions-item>
              <el-descriptions-item label="合同金额">{{ money(detail.contract_amount) }}</el-descriptions-item>
              <el-descriptions-item label="已收金额">{{ money(detail.received_amount) }}</el-descriptions-item>
              <el-descriptions-item label="待收金额">{{ money(detail.pending_amount) }}</el-descriptions-item>
              <el-descriptions-item label="服务期限">{{ dateOnly(detail.start_date) }} 至 {{ dateOnly(detail.end_date) }}</el-descriptions-item>
            </el-descriptions>

            <div class="section-title">服务权益</div>
            <el-table :data="entitlementSummaryRows" border stripe>
              <el-table-column label="类型" width="100"><template #default="{ row }">{{ dictText(entitlementTypeOptions, row.entitlement_type) }}</template></el-table-column>
              <el-table-column prop="total_quota" label="总量" width="90" />
              <el-table-column prop="used_quota" label="已核销" width="90" />
              <el-table-column prop="remaining_quota" label="剩余" width="90" />
              <el-table-column prop="unit" label="单位" width="80" />
              <el-table-column label="超额" width="90"><template #default="{ row }">{{ row.allow_overuse ? "允许" : "不允许" }}</template></el-table-column>
            </el-table>

            <div class="section-title">核销记录</div>
            <el-table :data="detail.usages || []" border stripe>
              <el-table-column prop="occurred_at" label="时间" min-width="160" show-overflow-tooltip />
              <el-table-column label="类型" width="90"><template #default="{ row }">{{ dictText(entitlementTypeOptions, row.usage_type) }}</template></el-table-column>
              <el-table-column prop="quantity" label="数量" width="70" />
              <el-table-column prop="candidate_name" label="候选" width="110" show-overflow-tooltip />
              <el-table-column prop="title" label="标题" min-width="140" show-overflow-tooltip />
              <el-table-column label="状态" width="90"><template #default="{ row }">{{ dictText(usageStatusOptions, row.usage_status) }}</template></el-table-column>
              <el-table-column prop="created_by_name" label="提交人" width="100" show-overflow-tooltip />
              <el-table-column fixed="right" label="操作" width="80">
                <template #default="{ row }"><el-button v-if="row.usage_status === 'active'" v-hasPerm="['service:meeting:rollback']" link type="danger" @click="voidUsage(row)">作废</el-button></template>
              </el-table-column>
            </el-table>

            <div class="section-title">深访记录</div>
            <el-table :data="detail.deep_interviews || []" border stripe>
              <el-table-column prop="interviewed_at" label="时间" min-width="160" show-overflow-tooltip />
              <el-table-column label="类型" width="100"><template #default="{ row }">{{ dictText(interviewTypeOptions, row.interview_type) }}</template></el-table-column>
              <el-table-column prop="summary" label="摘要" min-width="180" show-overflow-tooltip />
              <el-table-column prop="content" label="内容" min-width="260" show-overflow-tooltip />
              <el-table-column prop="matchmaker_name" label="红娘" width="110" show-overflow-tooltip />
            </el-table>
          </el-tab-pane>
          <el-tab-pane label="服务计划" name="plan">
            <div class="tab-toolbar">
              <el-tag v-if="servicePlan" type="primary">{{ dictText(planStatusOptions, servicePlan.plan_status) }}</el-tag>
              <el-button v-hasPerm="['service:plan:publish']" type="primary" icon="Promotion" :disabled="!servicePlan || servicePlan.plan_status !== 'draft'" @click="publishPlan">发布计划</el-button>
              <el-button v-hasPerm="['service:plan:update']" icon="Calendar" @click="autoSchedulePlan">自动排期未排节点</el-button>
              <el-button v-if="canAdminMaintainPlan" v-hasPerm="['service:plan:update']" icon="Refresh" @click="rebuildPlan">按权益重建</el-button>
            </div>
            <el-table :data="servicePlan?.items || []" border stripe>
              <el-table-column prop="sequence_no" label="#" width="60" />
              <el-table-column prop="title" label="节点" min-width="160" show-overflow-tooltip />
              <el-table-column label="类型" width="110"><template #default="{ row }">{{ dictText(planItemTypeOptions, row.item_type) }}</template></el-table-column>
              <el-table-column label="状态" width="110"><template #default="{ row }">{{ dictText(planItemStatusOptions, row.item_status) }}</template></el-table-column>
              <el-table-column prop="source_contract_no" label="来源合同" width="150" show-overflow-tooltip />
              <el-table-column label="候选" width="120" show-overflow-tooltip>
                <template #default="{ row }">
                  <span v-if="row.item_type === 'recommendation' && row.recommendation_count">{{ row.candidate_name }}</span>
                  <el-button v-else-if="row.candidate_person_id" link type="primary" @click="openServiceCandidateDetail(row.candidate_person_id)">{{ row.candidate_name || "-" }}</el-button>
                  <span v-else>-</span>
                </template>
              </el-table-column>
              <el-table-column label="计划区间" width="220" show-overflow-tooltip><template #default="{ row }">{{ planRangeText(row) }}</template></el-table-column>
              <el-table-column prop="remark" label="备注" min-width="160" show-overflow-tooltip />
              <el-table-column fixed="right" label="操作" width="300">
                <template #default="{ row }">
                  <el-button v-if="canMatchPlanItem(row)" v-hasPerm="['service:match:candidate']" link type="primary" @click="openMatch(row)">匹配候选</el-button>
                  <el-button v-if="row.item_type === 'meeting' && !row.related_meeting_id" v-hasPerm="['service:meeting:create']" link type="success" @click="openMeetingFromItem(row)">转约见</el-button>
                  <el-button v-if="row.item_type === 'course' && !row.related_usage_id && !['cancelled', 'skipped', 'completed'].includes(row.item_status)" v-hasPerm="['service:plan:item:update']" link type="success" @click="openCourseRecord(row)">登记课程</el-button>
                  <el-button v-if="canEditPlanItem(row)" v-hasPerm="['service:plan:item:update']" link @click="openPlanItemEdit(row)">编辑</el-button>
                  <el-button v-if="canSkipPlanItem(row)" v-hasPerm="['service:plan:item:update']" link @click="skipPlanItem(row)">放弃本次</el-button>
                  <el-button v-if="canRestorePlanItem(row)" v-hasPerm="['service:plan:item:update']" link type="warning" @click="restorePlanItem(row)">撤销</el-button>
                </template>
              </el-table-column>
            </el-table>

            <div class="section-title">推荐记录</div>
            <el-table :data="recommendationRows" border stripe>
              <el-table-column label="候选" width="120" show-overflow-tooltip>
                <template #default="{ row }">
                  <el-button link type="primary" @click="openServiceCandidateDetail(row.candidate_person_id)">{{ row.candidate_name || "-" }}</el-button>
                </template>
              </el-table-column>
              <el-table-column label="状态" width="110"><template #default="{ row }">{{ dictText(recommendStatusOptions, row.recommendation_status) }}</template></el-table-column>
              <el-table-column prop="match_score" label="匹配分" width="90" />
              <el-table-column prop="recommend_reason" label="推荐理由" min-width="180" show-overflow-tooltip />
              <el-table-column prop="matchmaker_remark" label="红娘备注" min-width="180" show-overflow-tooltip />
              <el-table-column fixed="right" label="操作" width="220">
                <template #default="{ row }">
                  <el-button v-if="canConsumeRecommendation(row)" v-hasPerm="['service:recommendation:update']" link type="primary" @click="consumeRecommendation(row)">核销推荐</el-button>
                  <el-button v-if="canCreateMeetingFromRecommendation(row)" v-hasPerm="['service:meeting:create']" link type="success" @click="openMeeting(row)">转约见</el-button>
                  <el-button v-if="row.recommendation_status === 'recommended' && !row.related_usage_id" v-hasPerm="['service:recommendation:update']" link type="warning" @click="revokeRecommendation(row)">撤销</el-button>
                </template>
              </el-table-column>
            </el-table>

            <div class="section-title">相亲约见</div>
            <el-table :data="meetingRows" border stripe>
              <el-table-column prop="target_name" label="对方" width="120" show-overflow-tooltip />
              <el-table-column label="状态" width="110"><template #default="{ row }">{{ dictText(meetingStatusOptions, row.meeting_status) }}</template></el-table-column>
              <el-table-column label="类型" width="110"><template #default="{ row }">{{ dictText(meetingTypeOptions, row.meeting_type) }}</template></el-table-column>
              <el-table-column prop="scheduled_at" label="约见日期" width="170" show-overflow-tooltip />
              <el-table-column label="时段" width="100"><template #default="{ row }">{{ dictText(appointmentSlotOptions, row.appointment_slot) }}</template></el-table-column>
              <el-table-column prop="location" label="地点" min-width="140" show-overflow-tooltip />
              <el-table-column prop="target_matchmaker_name" label="对方红娘" width="110" show-overflow-tooltip />
              <el-table-column fixed="right" label="操作" width="260">
                <template #default="{ row }">
                  <el-button v-if="row.meeting_status === 'pending_confirm'" v-hasPerm="['service:meeting:confirm']" link type="primary" @click="confirmMeeting(row)">确认</el-button>
                  <el-button v-if="['confirmed', 'pending_feedback', 'completed'].includes(row.meeting_status)" v-hasPerm="['service:meeting:feedback']" link @click="openFeedback(row)">反馈</el-button>
                  <el-button v-if="['pending_confirm', 'confirmed', 'pending_feedback'].includes(row.meeting_status)" v-hasPerm="['service:meeting:cancel']" link type="danger" @click="cancelMeeting(row)">撤销</el-button>
                </template>
              </el-table-column>
            </el-table>

            <div class="section-title">课程记录</div>
            <el-table :data="courseRows" border stripe>
              <el-table-column prop="course_title" label="课程主题" min-width="160" show-overflow-tooltip />
              <el-table-column label="形式" width="110"><template #default="{ row }">{{ dictText(courseModeOptions, row.course_mode) }}</template></el-table-column>
              <el-table-column prop="course_at" label="课程时间" width="170" show-overflow-tooltip />
              <el-table-column prop="quantity" label="课时" width="70" />
              <el-table-column label="确认" width="110"><template #default="{ row }">{{ dictText(courseConfirmOptions, row.customer_confirm_status) }}</template></el-table-column>
              <el-table-column label="状态" width="100"><template #default="{ row }">{{ dictText(courseRecordStatusOptions, row.record_status) }}</template></el-table-column>
              <el-table-column prop="content" label="课程内容" min-width="180" show-overflow-tooltip />
              <el-table-column prop="customer_feedback" label="客户反馈" min-width="180" show-overflow-tooltip />
              <el-table-column prop="matchmaker_name" label="红娘" width="110" show-overflow-tooltip />
              <el-table-column fixed="right" label="操作" width="90">
                <template #default="{ row }">
                  <el-button v-if="row.record_status === 'active'" v-hasPerm="['service:plan:item:update']" link type="danger" @click="revokeCourseRecord(row)">撤销</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
          <el-tab-pane label="客户资料" name="profile">
            <template v-if="customerProfile">
              <div class="tab-toolbar">
                <el-button v-hasPerm="['service:vip:update']" type="primary" icon="Edit" :disabled="!canEditProfile" @click="openProfileEdit">编辑客户资料</el-button>
              </div>
              <div class="profile-grid">
                <div class="profile-side">
                  <el-carousel v-if="customerProfile.photo_urls?.length" class="avatar-carousel" indicator-position="outside" arrow="hover" trigger="click">
                    <el-carousel-item v-for="url in customerProfile.photo_urls" :key="url">
                      <el-image class="avatar-photo" :src="ossImage(url, { w: 360, h: 480 })" fit="cover" :preview-src-list="ossImageList(customerProfile.photo_urls, { w: 1600 })" preview-teleported />
                    </el-carousel-item>
                  </el-carousel>
                  <div v-else class="avatar-empty">暂无照片</div>
                </div>
                <el-descriptions :column="3" border class="profile-desc">
                  <el-descriptions-item label="客户编号">{{ customerProfile.display_no || "-" }}</el-descriptions-item>
                  <el-descriptions-item label="姓名">{{ customerProfile.name || "-" }}</el-descriptions-item>
                  <el-descriptions-item label="性别">{{ genderText(customerProfile.gender) }}</el-descriptions-item>
                  <el-descriptions-item label="手机号">{{ customerProfile.mobile || "-" }}</el-descriptions-item>
                  <el-descriptions-item label="微信">{{ customerProfile.wechat || "-" }}</el-descriptions-item>
                  <el-descriptions-item label="身份证号">{{ customerProfile.id_card_no || "-" }}</el-descriptions-item>
                  <el-descriptions-item label="出生日期">{{ dateOnly(customerProfile.birth_date) }}</el-descriptions-item>
                  <el-descriptions-item label="年龄">{{ customerProfile.age ? `${customerProfile.age}岁` : "-" }}</el-descriptions-item>
                  <el-descriptions-item label="星座">{{ customerProfile.constellation || "-" }}</el-descriptions-item>
                  <el-descriptions-item label="生肖">{{ customerProfile.zodiac || "-" }}</el-descriptions-item>
                  <el-descriptions-item label="身高">{{ customerProfile.height_cm ? `${customerProfile.height_cm}cm` : "-" }}</el-descriptions-item>
                  <el-descriptions-item label="体重">{{ customerProfile.weight_kg ? `${customerProfile.weight_kg}kg` : "-" }}</el-descriptions-item>
                  <el-descriptions-item label="民族">{{ dictText(ethnicityOptions, customerProfile.ethnicity) }}</el-descriptions-item>
                  <el-descriptions-item label="认证等级">{{ certificationLevelText(customerProfile.certification_level) }}</el-descriptions-item>
                  <el-descriptions-item label="个人介绍" :span="3">{{ customerProfile.profile_intro || "-" }}</el-descriptions-item>
                </el-descriptions>
              </div>

              <div class="section-title">教育职业</div>
              <el-descriptions :column="3" border>
                <el-descriptions-item label="学历">{{ dictText(educationOptions, customerProfile.education) }}</el-descriptions-item>
                <el-descriptions-item label="毕业院校">{{ customerProfile.graduated_school || "-" }}</el-descriptions-item>
                <el-descriptions-item label="专业">{{ customerProfile.major || "-" }}</el-descriptions-item>
                <el-descriptions-item label="职业">{{ dictText(occupationOptions, customerProfile.occupation_code) || customerProfile.occupation || "-" }}</el-descriptions-item>
                <el-descriptions-item label="职业补充">{{ customerProfile.occupation || "-" }}</el-descriptions-item>
                <el-descriptions-item label="年收入">{{ dictText(annualIncomeOptions, customerProfile.annual_income) }}</el-descriptions-item>
                <el-descriptions-item label="单位类型">{{ dictText(unitTypeOptions, customerProfile.unit_type) }}</el-descriptions-item>
                <el-descriptions-item label="职务">{{ customerProfile.job_title || "-" }}</el-descriptions-item>
                <el-descriptions-item label="工作单位">{{ customerProfile.work_company || "-" }}</el-descriptions-item>
              </el-descriptions>

              <div class="section-title">地域资产与婚恋态度</div>
              <el-descriptions :column="3" border>
                <el-descriptions-item label="籍贯">{{ customerProfile.hometown || "-" }}</el-descriptions-item>
                <el-descriptions-item label="常驻地">{{ customerProfile.residence || "-" }}</el-descriptions-item>
                <el-descriptions-item label="婚况">{{ dictText(maritalStatusOptions, customerProfile.marital_status) }}</el-descriptions-item>
                <el-descriptions-item label="房产信息">{{ dictText(houseStatusOptions, customerProfile.house_status) }}</el-descriptions-item>
                <el-descriptions-item label="购车信息">{{ dictText(carStatusOptions, customerProfile.car_status) }}</el-descriptions-item>
                <el-descriptions-item label="结婚计划">{{ dictText(marriagePlanOptions, customerProfile.marriage_plan) }}</el-descriptions-item>
                <el-descriptions-item label="接受异地">{{ boolText(customerProfile.accept_long_distance_self) }}</el-descriptions-item>
                <el-descriptions-item label="接受闪婚">{{ boolText(customerProfile.accept_flash_marriage) }}</el-descriptions-item>
                <el-descriptions-item label="愿意搬家">{{ boolText(customerProfile.willing_relocate) }}</el-descriptions-item>
                <el-descriptions-item label="家庭情况" :span="3">{{ customerProfile.family_background || "-" }}</el-descriptions-item>
                <el-descriptions-item label="档案备注" :span="3">{{ customerProfile.profile_remark || "-" }}</el-descriptions-item>
              </el-descriptions>

              <div class="section-title">择偶要求</div>
              <partner-preference-form :model-value="customerProfile.partner_preference" :dict-options="preferenceDictOptions" :region-options="[]" read-only :show-actions="false" />

              <div class="section-title">客户经营</div>
              <el-descriptions :column="3" border>
                <el-descriptions-item label="门店">{{ customerProfile.store_name || "-" }}</el-descriptions-item>
                <el-descriptions-item label="成交销售">{{ customerProfile.owner_user_name || "-" }}</el-descriptions-item>
                <el-descriptions-item label="服务红娘">{{ customerProfile.service_owner_user_name || "-" }}</el-descriptions-item>
                <el-descriptions-item label="当前阶段">{{ dictText(customerStageOptions, customerProfile.current_stage) }}</el-descriptions-item>
                <el-descriptions-item label="最高进展">{{ dictText(customerStageOptions, customerProfile.max_stage) }}</el-descriptions-item>
                <el-descriptions-item label="转VIP时间">{{ customerProfile.converted_vip_at || "-" }}</el-descriptions-item>
                <el-descriptions-item label="最近跟进">{{ customerProfile.latest_follow_at || "-" }}</el-descriptions-item>
                <el-descriptions-item label="下次跟进">{{ customerProfile.next_follow_at || "-" }}</el-descriptions-item>
                <el-descriptions-item label="阶段结束">{{ customerProfile.ended_at || "-" }}</el-descriptions-item>
                <el-descriptions-item label="结束原因">{{ customerEndReasonText(customerProfile.end_reason) }}</el-descriptions-item>
                <el-descriptions-item label="建档时间">{{ customerProfile.created_time || "-" }}</el-descriptions-item>
              </el-descriptions>

              <div class="section-title">认证摘要</div>
              <pre class="json-block">{{ jsonText(customerProfile.certification_summary) }}</pre>
            </template>
          </el-tab-pane>
          <el-tab-pane label="认证资料" name="certification">
            <el-alert title="认证结果为认证事实，只读展示；服务红娘可在此收集和存档认证资料图片，不影响认证结果。" type="info" show-icon :closable="false" />
            <el-descriptions v-if="customerProfile" :column="3" border class="summary">
              <el-descriptions-item label="认证等级">{{ certificationLevelText(customerProfile.certification_level) }}</el-descriptions-item>
              <el-descriptions-item label="客户编号">{{ customerProfile.display_no || "-" }}</el-descriptions-item>
              <el-descriptions-item label="客户姓名">{{ customerProfile.name || "-" }}</el-descriptions-item>
            </el-descriptions>
            <div class="cert-material-grid">
              <div v-for="item in certificationArchiveItems" :key="item.item_code" class="cert-material-card">
                <div class="cert-material-head">
                  <div>
                    <div class="cert-material-title">{{ item.item_name }}</div>
                    <div class="cert-material-desc">{{ item.material_desc || "资料图片存档" }}</div>
                  </div>
                  <el-upload v-if="canUploadCertificationMaterial(item.item_code)" v-hasPerm="['service:vip:update']" :show-file-list="false" accept="image/*" :http-request="(options) => uploadCertificationMaterial(options, item)">
                    <el-button link type="primary" icon="Upload" :disabled="!canEditProfile">{{ uploadButtonText(item.item_code) }}</el-button>
                  </el-upload>
                  <el-tag v-else type="success">已通过</el-tag>
                </div>
                <div v-if="certificationMaterialsByItem(item.item_code).length" class="cert-material-list">
                  <div v-for="material in certificationMaterialsByItem(item.item_code)" :key="material.id" class="cert-material-item">
                    <el-image class="cert-material-image" :src="ossImage(material.file_url, { w: 160, h: 160 })" :preview-src-list="ossImageList([material.file_url], { w: 1600 })" fit="cover" preview-teleported />
                    <div class="cert-material-meta">
                      <span>{{ material.created_time || material.file_name || "已上传" }}</span>
                      <el-tag v-if="material.certification_record_status" :type="materialStatusType(material.certification_record_status)" size="small">{{ materialStatusLabel(material.certification_record_status) }}</el-tag>
                      <el-button v-if="canDeleteCertificationMaterial(material)" v-hasPerm="['service:vip:update']" link type="danger" :disabled="!canEditProfile" @click="deleteCertificationMaterial(material)">删除</el-button>
                    </div>
                    <div v-if="material.certification_record_status === 'rejected'" class="cert-review-result is-rejected">
                      <div>已驳回</div>
                      <div v-if="material.certification_reject_reason">原因：{{ material.certification_reject_reason }}</div>
                    </div>
                    <div v-if="idCardOcrResult(material)" class="cert-ocr-result" :class="`is-${idCardOcrResult(material)?.status}`">
                      <div>{{ idCardOcrResult(material)?.message }}</div>
                      <div v-if="idCardOcrResult(material)?.card_side">类型：{{ idCardSideLabel(idCardOcrResult(material)?.card_side) }}</div>
                      <div v-if="idCardOcrResult(material)?.id_card_no_masked">身份证号：{{ idCardOcrResult(material)?.id_card_no_masked }}</div>
                      <div v-if="idCardOcrResult(material)?.name">姓名：{{ idCardOcrResult(material)?.name }}</div>
                      <div v-if="idCardOcrResult(material)?.issue_authority">签发机关：{{ idCardOcrResult(material)?.issue_authority }}</div>
                      <div v-if="idCardOcrResult(material)?.valid_period">有效期：{{ idCardOcrResult(material)?.valid_period }}</div>
                    </div>
                  </div>
                </div>
                <el-empty v-else description="暂无资料" :image-size="48" />
              </div>
            </div>
          </el-tab-pane>
          <el-tab-pane label="过程时间轴" name="timeline">
            <el-table :data="timelineRows" border stripe>
              <el-table-column prop="occurred_at" label="时间" width="170" show-overflow-tooltip />
              <el-table-column label="来源" width="90"><template #default="{ row }">{{ dictText(timelineSourceOptions, row.source_type) }}</template></el-table-column>
              <el-table-column label="类型" width="160"><template #default="{ row }">{{ timelineRecordText(row) }}</template></el-table-column>
              <el-table-column prop="title" label="标题" width="120" show-overflow-tooltip />
              <el-table-column prop="content" label="内容" min-width="260" show-overflow-tooltip />
              <el-table-column prop="operator_user_name" label="操作人" width="110" show-overflow-tooltip />
            </el-table>
          </el-tab-pane>
          <el-tab-pane label="生命周期" name="lifecycle">
            <el-table :data="lifecycleRows" border stripe>
              <el-table-column prop="occurred_at" label="时间" width="170" show-overflow-tooltip />
              <el-table-column label="阶段域" width="100"><template #default="{ row }">{{ lifecycleStageText(row.stage_group) }}</template></el-table-column>
              <el-table-column label="节点" width="170" show-overflow-tooltip><template #default="{ row }">{{ lifecycleOperationText(row.operation_type) }}</template></el-table-column>
              <el-table-column prop="title" label="标题" width="130" show-overflow-tooltip />
              <el-table-column prop="remark" label="备注" min-width="240" show-overflow-tooltip />
              <el-table-column prop="operator_user_name" label="操作人" width="110" show-overflow-tooltip />
            </el-table>
          </el-tab-pane>
          <el-tab-pane label="合同收款" name="contracts">
            <el-table :data="contractRows" border stripe>
              <el-table-column prop="contract_no" label="合同编号" min-width="150" show-overflow-tooltip />
              <el-table-column prop="contract_name" label="合同名称" min-width="160" show-overflow-tooltip />
              <el-table-column label="状态" width="100"><template #default="{ row }">{{ dictText(contractStatusOptions, row.contract_status) }}</template></el-table-column>
              <el-table-column prop="owner_user_name" label="销售" width="110" show-overflow-tooltip />
              <el-table-column label="合同金额" width="120"><template #default="{ row }">{{ money(row.contract_amount) }}</template></el-table-column>
              <el-table-column label="已收" width="120"><template #default="{ row }">{{ money(row.received_amount) }}</template></el-table-column>
              <el-table-column label="待收" width="120"><template #default="{ row }">{{ money(row.pending_amount) }}</template></el-table-column>
              <el-table-column prop="effective_at" label="生效时间" width="170" show-overflow-tooltip />
              <el-table-column fixed="right" label="操作" width="100">
                <template #default="{ row }">
                  <el-button link type="primary" icon="View" @click="openContractDetail(row)">详情</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </template>
    </el-drawer>

    <el-dialog v-model="matchVisible" title="匹配候选" width="1280px" destroy-on-close>
      <div class="tab-toolbar">
        <el-radio-group v-model="matchQuery.search_mode">
          <el-radio-button label="score">系统推荐</el-radio-button>
          <el-radio-button label="filter">条件筛选</el-radio-button>
        </el-radio-group>
        <el-select v-model="matchQuery.scope" style="width: 140px">
          <el-option label="我的备选库" value="backup" />
          <el-option label="本门店" value="store" />
          <el-option label="品牌" value="brand" />
        </el-select>
        <el-input v-model="matchQuery.keyword" placeholder="姓名/手机号/编号/ID" clearable style="width: 240px" @keyup.enter="fetchMatchCandidates" />
        <el-button type="primary" :loading="matchLoading" @click="fetchMatchCandidates">搜索</el-button>
      </div>
      <el-alert
        v-if="matchQuery.search_mode === 'filter'"
        class="match-filter-tip"
        type="info"
        :closable="false"
        show-icon
        title="系统会自动结合当前 VIP 的择偶要求筛候选个人资料；下方“候选择偶”字段筛的是候选本人填写的择偶条件。"
      />
      <el-form v-if="matchQuery.search_mode === 'filter'" class="match-filter-form" label-width="122px">
        <div class="section-subtitle">个人资料筛选</div>
        <el-row :gutter="12">
          <el-col :span="6"><el-form-item label="年龄"><el-input-number v-model="matchQuery.age_min" :controls="false" :min="18" :max="120" placeholder="最小" /> <span class="range-sep">-</span> <el-input-number v-model="matchQuery.age_max" :controls="false" :min="18" :max="120" placeholder="最大" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="身高"><el-input-number v-model="matchQuery.height_min" :controls="false" :min="80" :max="260" placeholder="最小" /> <span class="range-sep">-</span> <el-input-number v-model="matchQuery.height_max" :controls="false" :min="80" :max="260" placeholder="最大" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="体重"><el-input-number v-model="matchQuery.weight_min" :controls="false" :min="20" :max="300" placeholder="最小" /> <span class="range-sep">-</span> <el-input-number v-model="matchQuery.weight_max" :controls="false" :min="20" :max="300" placeholder="最大" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="学历"><el-select v-model="matchQuery.education" clearable><el-option v-for="item in educationOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value || ''" /></el-select></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="年收入"><el-select v-model="matchQuery.annual_income" clearable><el-option v-for="item in annualIncomeOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value || ''" /></el-select></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="婚况"><el-select v-model="matchQuery.marital_status" clearable><el-option v-for="item in maritalStatusOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value || ''" /></el-select></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="单位类型"><el-select v-model="matchQuery.unit_type" clearable><el-option v-for="item in unitTypeOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value || ''" /></el-select></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="职业"><el-select v-model="matchQuery.occupation_code" clearable><el-option v-for="item in occupationOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value || ''" /></el-select></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="常驻地"><el-cascader v-model="matchResidenceValue" :options="addressOptions" :props="addressProps" clearable filterable style="width: 100%" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="籍贯"><el-cascader v-model="matchHometownValue" :options="addressOptions" :props="addressProps" clearable filterable style="width: 100%" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="房产"><el-select v-model="matchQuery.house_status" clearable><el-option v-for="item in houseStatusOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value || ''" /></el-select></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="车辆"><el-select v-model="matchQuery.car_status" clearable><el-option v-for="item in carStatusOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value || ''" /></el-select></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="接受异地"><el-select v-model="matchQuery.accept_long_distance_self" clearable><el-option label="是" :value="true" /><el-option label="否" :value="false" /></el-select></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="接受闪婚"><el-select v-model="matchQuery.accept_flash_marriage" clearable><el-option label="是" :value="true" /><el-option label="否" :value="false" /></el-select></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="愿意搬家"><el-select v-model="matchQuery.willing_relocate" clearable><el-option label="是" :value="true" /><el-option label="否" :value="false" /></el-select></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="结婚计划"><el-select v-model="matchQuery.marriage_plan" clearable><el-option v-for="item in marriagePlanOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value || ''" /></el-select></el-form-item></el-col>
        </el-row>
        <div class="section-subtitle">候选人的择偶条件筛选</div>
        <el-row :gutter="12">
          <el-col :span="6"><el-form-item label="期望年龄"><el-input-number v-model="matchQuery.pref_age_min" :controls="false" :min="18" :max="120" placeholder="最小" /> <span class="range-sep">-</span> <el-input-number v-model="matchQuery.pref_age_max" :controls="false" :min="18" :max="120" placeholder="最大" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="期望身高"><el-input-number v-model="matchQuery.pref_height_min" :controls="false" :min="80" :max="260" placeholder="最小" /> <span class="range-sep">-</span> <el-input-number v-model="matchQuery.pref_height_max" :controls="false" :min="80" :max="260" placeholder="最大" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="期望学历"><el-select v-model="matchQuery.preferred_education_codes" multiple collapse-tags clearable><el-option v-for="item in educationOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value || ''" /></el-select></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="期望婚况"><el-select v-model="matchQuery.preferred_marital_status_codes" multiple collapse-tags clearable><el-option v-for="item in maritalStatusOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value || ''" /></el-select></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="期望收入"><el-select v-model="matchQuery.preferred_annual_income_codes" multiple collapse-tags clearable><el-option v-for="item in annualIncomeOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value || ''" /></el-select></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="接受异地"><el-select v-model="matchQuery.pref_accept_long_distance" clearable><el-option label="是" :value="true" /><el-option label="否" :value="false" /></el-select></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="接受离异"><el-select v-model="matchQuery.pref_accept_divorced" clearable><el-option label="是" :value="true" /><el-option label="否" :value="false" /></el-select></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="接受带孩"><el-select v-model="matchQuery.pref_accept_children" clearable><el-option label="是" :value="true" /><el-option label="否" :value="false" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="择偶说明"><el-input v-model="matchQuery.preference_text" clearable /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="职业偏好"><el-input v-model="matchQuery.preferred_occupation_text" clearable /></el-form-item></el-col>
        </el-row>
      </el-form>
      <el-table :data="matchRows" border stripe>
        <el-table-column prop="display_no" label="编号" width="90" />
        <el-table-column label="姓名" width="100">
          <template #default="{ row }">
            <el-button link type="primary" @click="openServiceCandidateDetail(row.id)">{{ row.name || "-" }}</el-button>
          </template>
        </el-table-column>
        <el-table-column prop="mobile" label="手机号" width="130" />
        <el-table-column prop="store_name" label="门店" width="120" show-overflow-tooltip />
        <el-table-column prop="match_score" label="匹配分" width="80" />
        <el-table-column label="命中点" min-width="220">
          <template #default="{ row }">
            <el-tag v-for="item in row.matched_points || []" :key="item" class="match-point-tag" type="success">{{ item }}</el-tag>
            <span v-if="!row.matched_points?.length">-</span>
          </template>
        </el-table-column>
        <el-table-column label="风险点" min-width="200">
          <template #default="{ row }">
            <el-tag v-for="item in row.unmatched_points || []" :key="item" class="match-point-tag" type="warning">{{ item }}</el-tag>
            <span v-if="!row.unmatched_points?.length">-</span>
          </template>
        </el-table-column>
        <el-table-column label="身份标记" width="150">
          <template #default="{ row }">
            <el-tag v-if="row.in_backup" size="small" type="success">备选库</el-tag>
            <el-tag v-if="row.is_vip" size="small" type="warning">VIP</el-tag>
          </template>
        </el-table-column>
        <el-table-column fixed="right" label="操作" width="90">
          <template #default="{ row }">
            <el-button link type="primary" @click="openRecommendation(row)">确定</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination class="pager" v-model:current-page="matchQuery.page_no" v-model:page-size="matchQuery.page_size" :total="matchTotal" layout="total, prev, pager, next" @current-change="fetchMatchCandidates" />
    </el-dialog>

    <el-dialog v-model="recommendationVisible" title="创建推荐记录" width="640px" destroy-on-close>
      <el-form label-width="110px">
        <el-form-item label="候选">{{ currentCandidate?.name }} · {{ currentCandidate?.mobile }}</el-form-item>
        <el-form-item label="匹配分">
          <el-tag type="info">{{ recommendationForm.match_score ?? "-" }}</el-tag>
        </el-form-item>
        <el-form-item label="推荐理由"><el-input v-model="recommendationForm.recommend_reason" type="textarea" :rows="3" maxlength="5000" show-word-limit /></el-form-item>
        <el-form-item label="风险提示"><el-input v-model="recommendationForm.risk_notes" type="textarea" :rows="2" maxlength="2000" show-word-limit /></el-form-item>
        <el-form-item label="红娘备注"><el-input v-model="recommendationForm.matchmaker_remark" type="textarea" :rows="2" maxlength="2000" show-word-limit /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="recommendationVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="submitRecommendation">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="courseVisible" title="登记课程服务" width="720px" destroy-on-close>
      <el-form ref="courseFormRef" :model="courseForm" :rules="courseRules" label-width="110px">
        <el-form-item label="课程节点">{{ currentPlanItem?.title || "-" }}</el-form-item>
        <el-form-item label="课程时间" prop="course_at"><el-date-picker v-model="courseForm.course_at" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width: 100%" /></el-form-item>
        <el-form-item label="课程主题" prop="course_title"><el-input v-model="courseForm.course_title" maxlength="128" show-word-limit /></el-form-item>
        <el-form-item label="课程形式" prop="course_mode">
          <el-select v-model="courseForm.course_mode" style="width: 100%">
            <el-option v-for="item in courseModeOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value || ''" />
          </el-select>
        </el-form-item>
        <el-form-item label="课时数"><el-tag type="primary">1 课时</el-tag></el-form-item>
        <el-form-item label="确认状态" prop="customer_confirm_status">
          <el-select v-model="courseForm.customer_confirm_status" style="width: 100%">
            <el-option v-for="item in courseConfirmOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value || ''" />
          </el-select>
        </el-form-item>
        <el-form-item label="课程内容"><el-input v-model="courseForm.content" type="textarea" :rows="4" maxlength="5000" show-word-limit /></el-form-item>
        <el-form-item label="客户反馈"><el-input v-model="courseForm.customer_feedback" type="textarea" :rows="3" maxlength="5000" show-word-limit /></el-form-item>
        <el-form-item label="红娘备注"><el-input v-model="courseForm.matchmaker_remark" type="textarea" :rows="2" maxlength="2000" show-word-limit /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="courseVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="submitCourseRecord">保存并核销</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="serviceCandidateVisible" size="82%" destroy-on-close class="candidate-drawer">
      <template #header>
        <div class="drawer-head">
          <div>
            <div class="drawer-title">{{ serviceCandidateDetail?.person.name || "候选人详情" }}</div>
            <div class="drawer-subtitle">
              编号：{{ serviceCandidateDetail?.person.display_no || "-" }} ·
              {{ genderText(serviceCandidateDetail?.person.gender) }} ·
              {{ serviceCandidateDetail?.person.age ?? "-" }}岁 ·
              {{ serviceCandidateDetail?.person.store_name || "未归属门店" }}
            </div>
          </div>
          <div class="drawer-actions">
            <el-button
              v-if="serviceCandidateDetail && serviceCandidateDetail.backup.unlock_method === 'join_request'"
              type="primary"
              :loading="submitLoading"
              @click="requestCandidateUnlock"
            >
              申请加入备选库解锁
            </el-button>
            <el-button v-else-if="serviceCandidateDetail?.backup.unlock_method === 'pending_review'" disabled>加入申请待审核</el-button>
          </div>
        </div>
      </template>
      <template v-if="serviceCandidateDetail">
        <el-alert
          v-if="!serviceCandidateDetail.backup.contact_unmasked"
          type="warning"
          :closable="false"
          show-icon
          title="该候选联系方式未解锁。申请加入备选库并审核通过后，在当前红娘备选库上下文内可查看完整联系方式。"
        />
        <el-alert
          v-else
          type="success"
          :closable="false"
          show-icon
          title="该候选已授权，当前服务红娘可查看完整联系方式。"
        />
        <el-tabs v-model="serviceCandidateTab" class="lead-detail-tabs">
          <el-tab-pane label="资料信息" name="profile">
            <div class="candidate-profile-grid">
              <div class="profile-side">
                <el-carousel v-if="serviceCandidateDetail.person.photo_urls?.length" class="avatar-carousel" indicator-position="outside" arrow="hover" trigger="click">
                  <el-carousel-item v-for="url in serviceCandidateDetail.person.photo_urls" :key="url">
                    <el-image class="avatar-photo" :src="ossImage(url, { w: 360, h: 480 })" fit="cover" :preview-src-list="ossImageList(serviceCandidateDetail.person.photo_urls, { w: 1600 })" preview-teleported />
                  </el-carousel-item>
                </el-carousel>
                <div v-else class="avatar-empty">暂无照片</div>
              </div>
              <el-descriptions :column="3" border class="profile-desc">
                <el-descriptions-item label="编号">{{ serviceCandidateDetail.person.display_no || "-" }}</el-descriptions-item>
                <el-descriptions-item label="姓名">{{ serviceCandidateDetail.person.name || "-" }}</el-descriptions-item>
                <el-descriptions-item label="性别">{{ genderText(serviceCandidateDetail.person.gender) }}</el-descriptions-item>
                <el-descriptions-item label="手机号">{{ serviceCandidateDetail.person.mobile || "-" }}</el-descriptions-item>
                <el-descriptions-item label="微信">{{ serviceCandidateDetail.person.wechat || "-" }}</el-descriptions-item>
                <el-descriptions-item label="门店">{{ serviceCandidateDetail.person.store_name || "-" }}</el-descriptions-item>
                <el-descriptions-item label="年龄">{{ serviceCandidateDetail.person.age ?? "-" }}</el-descriptions-item>
                <el-descriptions-item label="出生日期">{{ serviceCandidateDetail.person.birth_date || "-" }}</el-descriptions-item>
                <el-descriptions-item label="身高">{{ serviceCandidateDetail.person.height_cm ? `${serviceCandidateDetail.person.height_cm}cm` : "-" }}</el-descriptions-item>
                <el-descriptions-item label="体重">{{ serviceCandidateDetail.person.weight_kg ? `${serviceCandidateDetail.person.weight_kg}kg` : "-" }}</el-descriptions-item>
                <el-descriptions-item label="民族">{{ dictText(ethnicityOptions, serviceCandidateDetail.person.ethnicity) }}</el-descriptions-item>
                <el-descriptions-item label="学历">{{ dictText(educationOptions, serviceCandidateDetail.person.education) }}</el-descriptions-item>
                <el-descriptions-item label="年收入">{{ dictText(annualIncomeOptions, serviceCandidateDetail.person.annual_income) }}</el-descriptions-item>
                <el-descriptions-item label="婚况">{{ dictText(maritalStatusOptions, serviceCandidateDetail.person.marital_status) }}</el-descriptions-item>
                <el-descriptions-item label="职业">{{ dictText(occupationOptions, serviceCandidateDetail.person.occupation_code) || serviceCandidateDetail.person.occupation || "-" }}</el-descriptions-item>
                <el-descriptions-item label="单位类型">{{ dictText(unitTypeOptions, serviceCandidateDetail.person.unit_type) }}</el-descriptions-item>
                <el-descriptions-item label="职务">{{ serviceCandidateDetail.person.job_title || "-" }}</el-descriptions-item>
                <el-descriptions-item label="工作单位">{{ serviceCandidateDetail.person.work_company || "-" }}</el-descriptions-item>
                <el-descriptions-item label="常驻地">{{ serviceCandidateDetail.person.residence || "-" }}</el-descriptions-item>
                <el-descriptions-item label="籍贯">{{ serviceCandidateDetail.person.hometown || "-" }}</el-descriptions-item>
                <el-descriptions-item label="房产">{{ dictText(houseStatusOptions, serviceCandidateDetail.person.house_status) }}</el-descriptions-item>
                <el-descriptions-item label="车辆">{{ dictText(carStatusOptions, serviceCandidateDetail.person.car_status) }}</el-descriptions-item>
                <el-descriptions-item label="接受异地">{{ boolText(serviceCandidateDetail.person.accept_long_distance_self) }}</el-descriptions-item>
                <el-descriptions-item label="接受闪婚">{{ boolText(serviceCandidateDetail.person.accept_flash_marriage) }}</el-descriptions-item>
                <el-descriptions-item label="愿意搬家">{{ boolText(serviceCandidateDetail.person.willing_relocate) }}</el-descriptions-item>
                <el-descriptions-item label="结婚计划">{{ dictText(marriagePlanOptions, serviceCandidateDetail.person.marriage_plan) }}</el-descriptions-item>
                <el-descriptions-item label="个人介绍" :span="3">{{ serviceCandidateDetail.person.profile_intro || "-" }}</el-descriptions-item>
                <el-descriptions-item label="备注" :span="3">{{ serviceCandidateDetail.person.profile_remark || "-" }}</el-descriptions-item>
              </el-descriptions>
            </div>
          </el-tab-pane>

          <el-tab-pane label="择偶要求" name="preference">
            <PartnerPreferenceForm
              :model-value="serviceCandidateDetail.partner_preference || undefined"
              :dict-options="preferenceDictOptions"
              :region-options="addressOptions"
              read-only
              :show-actions="false"
            />
            <div class="section-title">择偶摘要</div>
            <el-descriptions :column="3" border>
              <el-descriptions-item label="年龄">{{ preferenceRangeText("age") }}</el-descriptions-item>
              <el-descriptions-item label="身高">{{ preferenceRangeText("height") }}</el-descriptions-item>
              <el-descriptions-item label="体重">{{ preferenceRangeText("weight") }}</el-descriptions-item>
              <el-descriptions-item label="接受异地">{{ boolText(serviceCandidateDetail.partner_preference?.accept_long_distance) }}</el-descriptions-item>
              <el-descriptions-item label="接受离异">{{ boolText(serviceCandidateDetail.partner_preference?.accept_divorced) }}</el-descriptions-item>
              <el-descriptions-item label="接受带孩">{{ boolText(serviceCandidateDetail.partner_preference?.accept_children) }}</el-descriptions-item>
            </el-descriptions>
          </el-tab-pane>

          <el-tab-pane label="认证情况" name="certification">
            <el-alert title="认证结果为认证事实，只读展示；候选资料图片仍以 Person 当前资料为准。" type="info" show-icon :closable="false" />
            <el-descriptions :column="2" border class="mt12">
              <el-descriptions-item label="认证等级">{{ serviceCandidateDetail.person.certification_level || "none" }}</el-descriptions-item>
              <el-descriptions-item label="认证记录">{{ serviceCandidateDetail.person_center?.relations.certification ? "有认证摘要" : "暂无认证摘要" }}</el-descriptions-item>
              <el-descriptions-item label="认证摘要" :span="2">{{ relationFieldText("certification", "certification_summary", serviceCandidateDetail.person_center?.relations.certification?.certification_summary, serviceCandidateDetail.person_center?.relations.certification) }}</el-descriptions-item>
            </el-descriptions>
            <div class="photo-list">
              <el-image v-for="url in serviceCandidateDetail.person.photo_urls || []" :key="url" class="photo-item" :src="ossImage(url, { w: 120, h: 120 })" :preview-src-list="ossImageList(serviceCandidateDetail.person.photo_urls || [], { w: 1600 })" fit="cover" preview-teleported />
              <el-empty v-if="!serviceCandidateDetail.person.photo_urls?.length" description="暂无资料图片" :image-size="64" />
            </div>
          </el-tab-pane>

          <el-tab-pane label="系统信息" name="system">
            <div class="quality-inline">
              <el-progress
                type="dashboard"
                :percentage="serviceCandidateDetail.person_center?.quality.score || 0"
                :status="qualityStatus(serviceCandidateDetail.person_center?.quality.quality_level)"
              />
              <div class="quality-meta">
                <div>基础资料：{{ serviceCandidateDetail.person_center?.quality.basic_score || 0 }}%</div>
                <div>展示资料：{{ serviceCandidateDetail.person_center?.quality.display_score || 0 }}%</div>
                <div>服务资料：{{ serviceCandidateDetail.person_center?.quality.service_score || 0 }}%</div>
                <div class="muted">缺失项：{{ candidateMissingText }}</div>
              </div>
            </div>
            <div class="risk-list">
              <el-tag v-for="risk in serviceCandidateDetail.person_center?.quality.risk_flags || []" :key="risk.type" class="tag" :type="risk.level === 'danger' ? 'danger' : 'warning'">
                {{ risk.title }}
              </el-tag>
            </div>
            <div class="relation-grid">
              <div v-for="group in candidateRelationGroups" :key="group.title" class="relation-card">
                <div class="section-subtitle">{{ group.title }}</div>
                <el-descriptions v-if="group.data" :column="1" border size="small">
                  <el-descriptions-item v-for="field in group.fields" :key="field.key" :label="field.label">
                    {{ relationFieldText(group.kind, field.key, group.data[field.key], group.data) }}
                  </el-descriptions-item>
                </el-descriptions>
                <el-empty v-else description="暂无数据" :image-size="48" />
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="过程记录" name="process">
            <el-timeline>
              <el-timeline-item v-for="item in candidateProcessTimeline" :key="item.id" :timestamp="item.occurred_at">
                <div class="timeline-title">{{ timelineSourceText(item.source_type) }} · {{ candidateTimelineTitleText(item) }}</div>
                <div class="timeline-content">{{ item.content || "-" }}</div>
                <div class="muted">操作人：{{ item.operator_user_name || item.operator_user_id || "-" }}</div>
              </el-timeline-item>
            </el-timeline>
            <el-empty v-if="!candidateProcessTimeline.length" description="暂无过程记录" :image-size="64" />
          </el-tab-pane>

          <el-tab-pane label="生命周期" name="lifecycle">
            <el-timeline>
              <el-timeline-item v-for="item in candidateLifecycleTimeline" :key="item.id" :timestamp="item.occurred_at">
                <div class="timeline-title">{{ timelineSourceText(item.source_type) }} · {{ candidateTimelineTitleText(item) }}</div>
                <div class="timeline-content">{{ item.content || "-" }}</div>
                <div class="muted">操作人：{{ item.operator_user_name || item.operator_user_id || "-" }}</div>
              </el-timeline-item>
            </el-timeline>
            <el-empty v-if="!candidateLifecycleTimeline.length" description="暂无生命周期记录" :image-size="64" />
          </el-tab-pane>

          <el-tab-pane label="候选/备选" name="backup">
            <div class="section-subtitle">备选库归属</div>
            <el-table :data="serviceCandidateDetail.person_center?.relations.backup_items || []" border stripe size="small">
              <el-table-column prop="matchmaker_name" label="服务红娘" min-width="120" />
              <el-table-column prop="store_name" label="门店" min-width="140" />
              <el-table-column label="来源" min-width="130"><template #default="{ row }">{{ dictText(candidateSourceTypeOptions, row.source_type) }}</template></el-table-column>
              <el-table-column prop="approved_at" label="审批时间" min-width="170" />
            </el-table>
            <div class="section-subtitle">加入申请</div>
            <el-table :data="serviceCandidateDetail.person_center?.relations.join_requests || []" border stripe size="small">
              <el-table-column prop="request_matchmaker_name" label="申请红娘" min-width="120" />
              <el-table-column prop="request_store_name" label="申请门店" min-width="140" />
              <el-table-column label="范围" width="100"><template #default="{ row }">{{ dictText(candidateSearchScopeOptions, row.request_scope) }}</template></el-table-column>
              <el-table-column label="状态" width="110"><template #default="{ row }">{{ dictText(candidateJoinRequestStatusOptions, row.review_status) }}</template></el-table-column>
              <el-table-column prop="created_time" label="申请时间" min-width="170" />
            </el-table>
          </el-tab-pane>

          <el-tab-pane label="画像" name="portrait">
            <div class="relation-grid">
              <div v-for="group in candidateProfileGroups" :key="group.title" class="relation-card">
                <div class="section-subtitle">{{ group.title }}</div>
                <el-descriptions v-if="group.data" :column="1" border size="small">
                  <el-descriptions-item v-for="field in group.fields" :key="field.key" :label="field.label">
                    {{ relationFieldText(group.kind, field.key, group.data[field.key], group.data) }}
                  </el-descriptions-item>
                </el-descriptions>
                <el-empty v-else description="暂无数据" :image-size="48" />
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </template>
      <template #footer>
        <el-button @click="serviceCandidateVisible = false">关闭</el-button>
        <el-button
          v-if="serviceCandidateDetail && serviceCandidateDetail.backup.unlock_method === 'join_request'"
          type="primary"
          :loading="submitLoading"
          @click="requestCandidateUnlock"
        >
          申请加入备选库解锁
        </el-button>
        <el-button v-else-if="serviceCandidateDetail?.backup.unlock_method === 'pending_review'" disabled>加入申请待审核</el-button>
      </template>
    </el-drawer>

    <el-dialog v-model="meetingVisible" title="创建相亲约见" width="560px" destroy-on-close>
      <el-form label-width="110px">
        <el-form-item label="约见人">
          <el-select v-model="meetingForm.recommendation_id" filterable style="width: 100%" @change="handleMeetingRecommendationChange">
            <el-option v-for="item in availableRecommendationRows" :key="item.id" :label="recommendationOptionLabel(item)" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="绑定约见计划">
          <el-select v-model="meetingForm.plan_item_id" filterable style="width: 100%">
            <el-option v-for="item in availableMeetingPlanItems" :key="item.id" :label="meetingPlanItemOptionLabel(item)" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="约见类型">
          <el-select v-model="meetingForm.meeting_type" style="width: 100%">
            <el-option v-for="item in meetingTypeOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value || ''" />
          </el-select>
        </el-form-item>
        <el-form-item label="约见日期"><el-date-picker v-model="meetingForm.scheduled_at" type="date" value-format="YYYY-MM-DD 00:00:00" style="width: 100%" /></el-form-item>
        <el-form-item label="约见时段">
          <el-select v-model="meetingForm.appointment_slot" clearable style="width: 100%">
            <el-option v-for="item in appointmentSlotOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value || ''" />
          </el-select>
        </el-form-item>
        <el-form-item label="约见地点"><el-input v-model="meetingForm.location" maxlength="255" show-word-limit /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="meetingVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="submitMeeting">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="feedbackVisible" title="填写双方反馈" width="820px" destroy-on-close>
      <el-table :data="feedbackRows" border size="small" class="mb12">
        <el-table-column prop="feedback_person_name" label="反馈归属" width="110" />
        <el-table-column label="意向" width="90"><template #default="{ row }">{{ dictText(feedbackInterestOptions, row.interest_level) }}</template></el-table-column>
        <el-table-column prop="feedback_content" label="内容" min-width="220" show-overflow-tooltip />
        <el-table-column prop="feedback_matchmaker_name" label="填写人" width="110" />
      </el-table>
      <el-form label-width="110px">
        <el-form-item :label="feedbackSideLabel('male')">
          <el-input v-model="feedbackPairForm.male.feedback_content" type="textarea" :rows="3" maxlength="10000" show-word-limit />
        </el-form-item>
        <el-form-item :label="`${feedbackSideLabel('male')}意向`">
          <el-select v-model="feedbackPairForm.male.interest_level" clearable style="width: 100%">
            <el-option v-for="item in feedbackInterestOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value || ''" />
          </el-select>
        </el-form-item>
        <el-form-item :label="feedbackSideLabel('female')">
          <el-input v-model="feedbackPairForm.female.feedback_content" type="textarea" :rows="3" maxlength="10000" show-word-limit />
        </el-form-item>
        <el-form-item :label="`${feedbackSideLabel('female')}意向`">
          <el-select v-model="feedbackPairForm.female.interest_level" clearable style="width: 100%">
            <el-option v-for="item in feedbackInterestOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value || ''" />
          </el-select>
        </el-form-item>
        <el-form-item label="约见结果">
          <el-select v-model="feedbackPairForm.meeting_result" clearable style="width: 100%">
            <el-option v-for="item in meetingResultOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value || ''" />
          </el-select>
        </el-form-item>
        <el-form-item label="红娘意见"><el-input v-model="feedbackPairForm.matchmaker_opinion" type="textarea" :rows="3" maxlength="10000" show-word-limit /></el-form-item>
        <el-form-item label="下一步动作"><el-input v-model="feedbackPairForm.next_action" maxlength="255" show-word-limit /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="feedbackVisible = false">关闭</el-button>
        <el-button type="primary" :loading="submitLoading" @click="submitFeedback">保存反馈</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="planItemEditVisible" title="编辑计划节点" width="560px" destroy-on-close>
      <el-form label-width="110px">
        <el-form-item label="节点标题">
          <el-input v-model="planItemForm.title" :disabled="servicePlan?.plan_status === 'published'" maxlength="128" show-word-limit />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="planItemForm.sequence_no" :disabled="servicePlan?.plan_status === 'published'" :min="1" :max="9999" style="width: 180px" />
        </el-form-item>
        <el-form-item label="计划开始">
          <el-date-picker v-model="planItemForm.planned_start_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="计划结束">
          <el-date-picker v-model="planItemForm.planned_end_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="planItemForm.remark" type="textarea" :rows="3" maxlength="2000" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="planItemEditVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="submitPlanItemEdit">保存</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="contractDetailVisible" size="72%" destroy-on-close>
      <template #header>
        <div class="drawer-title">{{ selectedContract?.contract_name || "合同详情" }} · {{ selectedContract?.contract_no || "" }}</div>
      </template>
      <template v-if="selectedContract">
        <el-descriptions :column="3" border>
          <el-descriptions-item label="合同编号">{{ selectedContract.contract_no }}</el-descriptions-item>
          <el-descriptions-item label="合同状态">{{ dictText(contractStatusOptions, selectedContract.contract_status) }}</el-descriptions-item>
          <el-descriptions-item label="VIP等级">{{ dictText(vipLevelOptions, selectedContract.vip_level) }}</el-descriptions-item>
          <el-descriptions-item label="应收价款">{{ money(selectedContract.original_amount) }}</el-descriptions-item>
          <el-descriptions-item label="合同金额">{{ money(selectedContract.contract_amount) }}</el-descriptions-item>
          <el-descriptions-item label="已收金额">{{ money(selectedContract.received_amount) }} / {{ money(selectedContract.contract_amount) }}</el-descriptions-item>
          <el-descriptions-item label="支付状态">{{ paymentStatusText(selectedContract.payment_status) }}</el-descriptions-item>
          <el-descriptions-item label="折扣金额">{{ money(selectedContract.discount_amount) }}</el-descriptions-item>
          <el-descriptions-item label="有效期限">{{ selectedContract.validity_period || `${dateOnly(selectedContract.start_date)} 至 ${dateOnly(selectedContract.end_date)}` }}</el-descriptions-item>
          <el-descriptions-item label="签署人">{{ selectedContract.signer_name || "-" }}</el-descriptions-item>
          <el-descriptions-item label="销售">{{ selectedContract.owner_user_name || "-" }}</el-descriptions-item>
          <el-descriptions-item label="生效时间">{{ selectedContract.effective_at || "-" }}</el-descriptions-item>
          <el-descriptions-item label="提交审核时间">{{ selectedContract.review_submitted_at || "-" }}</el-descriptions-item>
          <el-descriptions-item label="审核时间">{{ selectedContract.reviewed_at || "-" }}</el-descriptions-item>
          <el-descriptions-item label="审核备注">{{ selectedContract.review_remark || "-" }}</el-descriptions-item>
          <el-descriptions-item label="折扣原因" :span="3">{{ selectedContract.discount_reason || "-" }}</el-descriptions-item>
          <el-descriptions-item label="备注" :span="3">{{ selectedContract.remark || "-" }}</el-descriptions-item>
        </el-descriptions>

        <div class="section-title">产品快照</div>
        <el-table :data="selectedContract.items" border size="small">
          <el-table-column prop="product_name_snapshot" label="产品" min-width="160" />
          <el-table-column label="价格" width="110"><template #default="{ row }">{{ money(row.price_snapshot) }}</template></el-table-column>
          <el-table-column prop="service_days_snapshot" label="时长(天)" width="90" />
          <el-table-column prop="recommendation_quota_snapshot" label="推荐" width="80" />
          <el-table-column prop="meeting_quota_snapshot" label="约见" width="80" />
          <el-table-column prop="course_quota_snapshot" label="课程" width="80" />
          <el-table-column label="线上约见" width="100"><template #default="{ row }">{{ row.supports_online_meeting_snapshot ? "支持" : "不支持" }}</template></el-table-column>
        </el-table>

        <div class="section-title">合同影像</div>
        <div v-if="selectedContract.attachments?.length" class="attachment-list">
          <div v-for="file in selectedContract.attachments" :key="String(file.id)" class="attachment-item">
            <el-image v-if="isContractImageAttachment(file)" class="attachment-thumb" :src="String(file.file_url || '')" :preview-src-list="contractAttachmentPreviewList" fit="cover" preview-teleported />
            <div v-else class="attachment-file"><el-icon><Document /></el-icon></div>
            <div class="attachment-meta">
              <el-link :href="String(file.file_url || '')" target="_blank" type="primary" :underline="false">{{ file.file_name || file.file_url }}</el-link>
              <div class="muted">{{ file.file_type || "file" }}</div>
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无合同影像" :image-size="64" />

        <div class="section-title">收款记录</div>
        <el-table :data="selectedContract.receipts" border size="small">
          <el-table-column prop="receipt_no" label="收款单号" min-width="160" />
          <el-table-column label="类型" width="100"><template #default="{ row }">{{ receiptTypeText(row.receipt_type) }}</template></el-table-column>
          <el-table-column label="方式" width="100"><template #default="{ row }">{{ payMethodText(row.pay_method) }}</template></el-table-column>
          <el-table-column label="金额" width="110"><template #default="{ row }">{{ money(row.amount) }}</template></el-table-column>
          <el-table-column label="状态" width="100"><template #default="{ row }">{{ dictText(receiptStatusOptions, row.receipt_status) }}</template></el-table-column>
          <el-table-column prop="submitted_at" label="提交时间" min-width="160" />
        </el-table>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { ElMessage, ElMessageBox, type FormInstance, type FormRules, type UploadFile, type UploadRequestOptions, type UploadUserFile } from "element-plus";
import { Document, Plus } from "@element-plus/icons-vue";
import DictAPI, { type DictDataTable } from "@/api/module_system/dict";
import DeptAPI, { type DeptTable } from "@/api/module_system/dept";
import type { PartnerPreference } from "@/api/module_crm/lead";
import CandidateAPI, { type CandidateRecord } from "@/api/module_service/candidate";
import { ROLE_ROOT } from "@/constants";
import { useUserStore } from "@/store";
import { ossImage, ossImageList } from "@/utils/ossImage";
import { uploadImageDirect } from "@/utils/upload";
import { addressOptions } from "@/views/module_miailove/components/addressOptions";
import PartnerPreferenceForm from "@/views/module_miailove/components/PartnerPreferenceForm.vue";
import PersonProfileFields from "@/views/module_miailove/components/PersonProfileFields.vue";
import VipServiceAPI, {
  type InterviewForm,
  type IdCardOcrResult,
  type MatchCandidate,
  type MatchCandidateQuery,
  type MatchmakerOption,
  type MeetingFeedbackForm,
  type MeetingForm,
  type RecommendationForm,
  type ServiceCertification,
  type ServiceCertificationArchiveItem,
  type ServiceCaseDetail,
  type ServiceCaseTable,
  type ServiceCandidateDetail,
  type ServiceContractRecord,
  type ServiceCourseRecord,
  type ServiceCustomerProcessForm,
  type ServiceCustomerProfile,
  type ServiceCustomerProfileForm,
  type ServiceEntitlement,
  type ServiceLifecycleItem,
  type ServiceMeeting,
  type ServiceMeetingFeedback,
  type ServicePlan,
  type ServicePlanItem,
  type ServicePlanItemForm,
  type ServiceRecommendation,
  type ServiceTimelineItem,
  type ServiceWorkSummary,
  type UsageForm,
  type CourseRecordForm,
  type UsageRecord,
  type VipAssignForm,
} from "@/api/module_service/vip";

defineOptions({ name: "MiailoveServiceWorkbench", inheritAttrs: false });

const route = useRoute();
const userStore = useUserStore();
const loading = ref(false);
const submitLoading = ref(false);
const rows = ref<ServiceCaseTable[]>([]);
const total = ref(0);
const activeTab = ref<"pending" | "mine" | "all" | "closeReview">("all");
const vipLevelOptions = ref<DictDataTable[]>([]);
const caseStatusOptions = ref<DictDataTable[]>([]);
const closeStatusOptions = ref<DictDataTable[]>([]);
const entitlementTypeOptions = ref<DictDataTable[]>([]);
const usageStatusOptions = ref<DictDataTable[]>([]);
const interviewTypeOptions = ref<DictDataTable[]>([]);
const processRecordTypeOptions = ref<DictDataTable[]>([]);
const followMethodOptions = ref<DictDataTable[]>([]);
const timelineSourceOptions = ref<DictDataTable[]>([]);
const appointmentSlotOptions = ref<DictDataTable[]>([]);
const visitPurposeOptions = ref<DictDataTable[]>([]);
const planStatusOptions = ref<DictDataTable[]>([]);
const planItemTypeOptions = ref<DictDataTable[]>([]);
const planItemStatusOptions = ref<DictDataTable[]>([]);
const recommendStatusOptions = ref<DictDataTable[]>([]);
const meetingTypeOptions = ref<DictDataTable[]>([]);
const meetingStatusOptions = ref<DictDataTable[]>([]);
const meetingResultOptions = ref<DictDataTable[]>([]);
const feedbackInterestOptions = ref<DictDataTable[]>([]);
const courseModeOptions = ref<DictDataTable[]>([]);
const courseConfirmOptions = ref<DictDataTable[]>([]);
const courseRecordStatusOptions = ref<DictDataTable[]>([]);
const ethnicityOptions = ref<DictDataTable[]>([]);
const occupationOptions = ref<DictDataTable[]>([]);
const annualIncomeOptions = ref<DictDataTable[]>([]);
const maritalStatusOptions = ref<DictDataTable[]>([]);
const educationOptions = ref<DictDataTable[]>([]);
const unitTypeOptions = ref<DictDataTable[]>([]);
const houseStatusOptions = ref<DictDataTable[]>([]);
const carStatusOptions = ref<DictDataTable[]>([]);
const marriagePlanOptions = ref<DictDataTable[]>([]);
const customerStageOptions = ref<DictDataTable[]>([]);
const contractStatusOptions = ref<DictDataTable[]>([]);
const receiptStatusOptions = ref<DictDataTable[]>([]);
const candidateSourceTypeOptions = ref<DictDataTable[]>([]);
const candidateSearchScopeOptions = ref<DictDataTable[]>([]);
const candidateJoinRequestStatusOptions = ref<DictDataTable[]>([]);
const leadTypeOptions = ref<DictDataTable[]>([]);
const leadPoolTypeOptions = ref<DictDataTable[]>([]);
const servicePoolOptions = ref<DictDataTable[]>([]);
const deptOptions = ref<Array<{ label: string; value: number }>>([]);
const filterMatchmakers = ref<MatchmakerOption[]>([]);
const matchmakerOptions = ref<MatchmakerOption[]>([]);
const candidateOptions = ref<CandidateRecord[]>([]);
const candidateLoading = ref(false);
const detailVisible = ref(false);
const detailTab = ref("overview");
const detail = ref<ServiceCaseDetail>();
const workSummary = ref<ServiceWorkSummary>();
const customerProfile = ref<ServiceCustomerProfile>();
const certificationArchiveItems = ref<ServiceCertificationArchiveItem[]>([]);
const certifications = ref<ServiceCertification[]>([]);
const timelineRows = ref<ServiceTimelineItem[]>([]);
const lifecycleRows = ref<ServiceLifecycleItem[]>([]);
const contractRows = ref<ServiceContractRecord[]>([]);
const servicePlan = ref<ServicePlan>();
const recommendationRows = ref<ServiceRecommendation[]>([]);
const meetingRows = ref<ServiceMeeting[]>([]);
const feedbackRows = ref<ServiceMeetingFeedback[]>([]);
const courseRows = ref<ServiceCourseRecord[]>([]);
const availableRecommendationRows = computed(() => recommendationRows.value.filter((item) => canCreateMeetingFromRecommendation(item)));
const availableMeetingPlanItems = computed(() =>
  (servicePlan.value?.items || []).filter(
    (item) =>
      item.item_type === "meeting"
      && !item.related_meeting_id
      && !item.related_usage_id
      && ["pending", "in_progress"].includes(item.item_status),
  ),
);
const contractDetailVisible = ref(false);
const selectedContract = ref<ServiceContractRecord>();
const contractAttachmentPreviewList = computed(() => (selectedContract.value?.attachments || []).filter((item) => isContractImageAttachment(item)).map((item) => String(item.file_url || "")));
const assignVisible = ref(false);
const assignMode = ref<"assign" | "transfer">("assign");
const currentRow = ref<ServiceCaseTable>();
const assignFormRef = ref<FormInstance>();
const interviewFormRef = ref<FormInstance>();
const usageFormRef = ref<FormInstance>();
const closeFormRef = ref<FormInstance>();
const processFormRef = ref<FormInstance>();
const appointmentFormRef = ref<FormInstance>();
const courseFormRef = ref<FormInstance>();
const profileFormRef = ref<FormInstance>();
const preferenceFormRef = ref<{ getValue: () => PartnerPreference }>();
const interviewVisible = ref(false);
const usageVisible = ref(false);
const closeVisible = ref(false);
const reviewVisible = ref(false);
const processVisible = ref(false);
const appointmentVisible = ref(false);
const profileEditVisible = ref(false);
const matchVisible = ref(false);
const recommendationVisible = ref(false);
const serviceCandidateVisible = ref(false);
const serviceCandidateTab = ref("profile");
const meetingVisible = ref(false);
const feedbackVisible = ref(false);
const courseVisible = ref(false);
const planItemEditVisible = ref(false);
const profilePhotoFileList = ref<UploadUserFile[]>([]);
const currentPlanItem = ref<ServicePlanItem>();
const currentCandidate = ref<MatchCandidate>();
const serviceCandidateDetail = ref<ServiceCandidateDetail>();
const currentRecommendation = ref<ServiceRecommendation>();
const currentMeeting = ref<ServiceMeeting>();
const matchRows = ref<MatchCandidate[]>([]);
const matchTotal = ref(0);
const matchLoading = ref(false);

const query = reactive({
  page_no: 1,
  page_size: 10,
  keyword: undefined as string | undefined,
  vip_level: undefined as string | undefined,
  vip_status: undefined as string | undefined,
  store_id: undefined as number | undefined,
  service_owner_user_id: undefined as number | undefined,
});

const assignForm = reactive<VipAssignForm>({ service_owner_user_id: undefined, remark: undefined });
const interviewForm = reactive<InterviewForm>({ interview_type: undefined, interviewed_at: undefined, content: "", keywords: [], summary: undefined });
const usageForm = reactive<UsageForm>({ entitlement_id: undefined, quantity: 1, occurred_at: undefined, title: undefined, content: undefined, candidate_person_id: undefined, overuse_reason: undefined });
const closeForm = reactive({ reason: "" });
const reviewForm = reactive({ review_remark: "" });
const processForm = reactive<ServiceCustomerProcessForm>({ record_type: undefined, occurred_at: undefined, method: undefined, content: "", need_summary: undefined, next_follow_at: undefined, next_action: undefined });
const appointmentForm = reactive<ServiceCustomerProcessForm>({ record_type: "appointment", scheduled_at: undefined, appointment_slot: undefined, visit_purpose: undefined, promised_gift: undefined, content: "", need_summary: undefined, next_follow_at: undefined });
const matchQuery = reactive<MatchCandidateQuery>({
  page_no: 1,
  page_size: 10,
  search_mode: "score",
  scope: "backup",
  keyword: undefined,
  preferred_education_codes: [],
  preferred_marital_status_codes: [],
  preferred_annual_income_codes: [],
});
const recommendationForm = reactive<RecommendationForm>({ plan_item_id: 0, candidate_person_id: 0, recommend_reason: "", match_score: undefined, matched_points: [], unmatched_points: [], risk_notes: "", matchmaker_remark: "" });
const courseForm = reactive<CourseRecordForm>({ course_at: undefined, course_title: "", course_mode: "offline", content: "", customer_feedback: "", matchmaker_remark: "", customer_confirm_status: "matchmaker_confirmed" });
const meetingForm = reactive<MeetingForm>({ recommendation_id: undefined, meeting_type: "store", scheduled_at: undefined, appointment_slot: undefined, location: "" });
const feedbackPairForm = reactive({
  male: { person_id: 0, feedback_content: "", interest_level: undefined as string | undefined },
  female: { person_id: 0, feedback_content: "", interest_level: undefined as string | undefined },
  meeting_result: undefined as string | undefined,
  next_action: undefined as string | undefined,
  matchmaker_opinion: "",
});
const planItemForm = reactive({ title: "", sequence_no: 1, planned_start_date: "", planned_end_date: "", remark: "" });
const profileForm = reactive<ServiceCustomerProfileForm>({
  mobile: "",
  name: "",
  gender: "2",
  photo_urls: [],
  partner_preference: null,
});

const assignRules = reactive<FormRules<VipAssignForm>>({ service_owner_user_id: [{ required: true, message: "请选择服务红娘", trigger: "change" }] });
const interviewRules = reactive<FormRules<InterviewForm>>({
  interview_type: [{ required: true, message: "请选择深访类型", trigger: "change" }],
  content: [{ required: true, message: "请填写深访内容", trigger: "blur" }],
});
const usageRules = reactive<FormRules<UsageForm>>({
  entitlement_id: [{ required: true, message: "请选择核销权益", trigger: "change" }],
  quantity: [{ required: true, message: "请输入核销数量", trigger: "blur" }],
});
const courseRules = reactive<FormRules<CourseRecordForm>>({
  course_at: [{ required: true, message: "请选择课程时间", trigger: "change" }],
  course_title: [{ required: true, message: "请填写课程主题", trigger: "blur" }],
  course_mode: [{ required: true, message: "请选择课程形式", trigger: "change" }],
  customer_confirm_status: [{ required: true, message: "请选择确认状态", trigger: "change" }],
});
const closeRules = reactive<FormRules<typeof closeForm>>({ reason: [{ required: true, message: "请填写关单原因", trigger: "blur" }] });
const processRules = reactive<FormRules<ServiceCustomerProcessForm>>({
  record_type: [{ required: true, message: "请选择记录类型", trigger: "change" }],
  content: [{ required: true, message: "请填写过程内容", trigger: "blur" }],
});
const appointmentRules = reactive<FormRules<ServiceCustomerProcessForm>>({
  scheduled_at: [{ required: true, message: "请选择预约日期", trigger: "change" }],
  content: [{ required: true, message: "请填写邀约内容", trigger: "blur" }],
});
const profileRules = reactive<FormRules<ServiceCustomerProfileForm>>({
  mobile: [{ required: true, message: "请填写手机号", trigger: "blur" }],
  name: [{ required: true, message: "请填写姓名", trigger: "blur" }],
  gender: [{ required: true, message: "请选择性别", trigger: "change" }],
});

const pageTitle = computed(() => {
  if (activeTab.value === "pending") return "待分配服务池";
  if (activeTab.value === "mine") return "我的服务";
  if (activeTab.value === "closeReview") return "关单审核";
  return "全部服务";
});
const selectedEntitlement = computed<ServiceEntitlement | undefined>(() => detail.value?.entitlements?.find((item) => item.id === usageForm.entitlement_id));
const manualUsageEntitlements = computed(() => (detail.value?.entitlements || []).filter((item) => item.entitlement_type !== "course"));
const entitlementSummaryRows = computed<ServiceEntitlement[]>(() => {
  const rows = new Map<string, ServiceEntitlement>();
  for (const item of detail.value?.entitlements || []) {
    const current = rows.get(item.entitlement_type);
    if (!current) {
      rows.set(item.entitlement_type, { ...item });
      continue;
    }
    current.total_quota += item.total_quota;
    current.used_quota += item.used_quota;
    current.remaining_quota += item.remaining_quota;
    current.allow_overuse = current.allow_overuse || item.allow_overuse;
    if (current.unit !== item.unit) current.unit = "";
  }
  return Array.from(rows.values());
});
const canOperateService = computed(() => ["serving", "reopened"].includes(detail.value?.case_status || ""));
const canEditProfile = computed(() => ["serving", "reopened", "pending_close_review"].includes(detail.value?.case_status || ""));
const roleCodes = computed(() => (userStore.basicInfo.roles || []).map((role) => role.code));
const canManageService = computed(() => roleCodes.value.includes(ROLE_ROOT) || userStore.prems.includes("service:vip:assign"));
const canAdminMaintainPlan = computed(() => roleCodes.value.includes(ROLE_ROOT));
const profileDictOptions = computed(() => ({
  ethnicity: ethnicityOptions.value,
  occupation: occupationOptions.value,
  annualIncome: annualIncomeOptions.value,
  maritalStatus: maritalStatusOptions.value,
  education: educationOptions.value,
  unitType: unitTypeOptions.value,
  houseStatus: houseStatusOptions.value,
  carStatus: carStatusOptions.value,
  marriagePlan: marriagePlanOptions.value,
}));
const preferenceDictOptions = computed(() => ({
  annualIncome: dictDataToOptions(annualIncomeOptions.value),
  maritalStatus: dictDataToOptions(maritalStatusOptions.value),
  education: dictDataToOptions(educationOptions.value),
  houseStatus: dictDataToOptions(houseStatusOptions.value),
  carStatus: dictDataToOptions(carStatusOptions.value),
}));
const addressProps = { emitPath: true, checkStrictly: true };
const splitAddress = (value?: string) => (value ? value.split("/").filter(Boolean).slice(0, 2) : []);
const matchResidenceValue = computed<string[]>({
  get: () => splitAddress(matchQuery.residence),
  set: (value) => {
    matchQuery.residence = value?.join("/") || undefined;
  },
});
const matchHometownValue = computed<string[]>({
  get: () => splitAddress(matchQuery.hometown),
  set: (value) => {
    matchQuery.hometown = value?.join("/") || undefined;
  },
});
const candidateMissingText = computed(() => {
  const quality = serviceCandidateDetail.value?.person_center?.quality;
  if (!quality) return "暂无";
  const items = [...quality.missing_basic, ...quality.missing_display, ...quality.missing_service];
  return items.length ? items.join("、") : "资料完整度较好";
});
const relationFields = {
  lead: [
    { key: "id", label: "线索ID" },
    { key: "store_id", label: "归属门店" },
    { key: "owner_sales_id", label: "归属销售" },
    { key: "pool_type", label: "归属池" },
    { key: "lead_type", label: "线索类型" },
    { key: "source_channel_code", label: "来源渠道" },
    { key: "latest_follow_at", label: "最近跟进" },
    { key: "next_follow_at", label: "下次跟进" },
  ],
  customer: [
    { key: "id", label: "客户ID" },
    { key: "store_id", label: "归属门店" },
    { key: "owner_user_id", label: "归属销售" },
    { key: "current_stage", label: "当前阶段" },
    { key: "max_stage", label: "最高阶段" },
    { key: "latest_follow_at", label: "最近跟进" },
    { key: "converted_vip_at", label: "转VIP时间" },
  ],
  vip: [
    { key: "id", label: "VIP ID" },
    { key: "contract_id", label: "合同ID" },
    { key: "store_id", label: "服务门店" },
    { key: "service_owner_user_id", label: "服务红娘" },
    { key: "vip_level", label: "VIP等级" },
    { key: "vip_status", label: "VIP状态" },
    { key: "started_at", label: "开始时间" },
  ],
  serviceCase: [
    { key: "id", label: "工单ID" },
    { key: "store_id", label: "服务门店" },
    { key: "owner_matchmaker_id", label: "服务红娘" },
    { key: "pool_type", label: "服务池" },
    { key: "case_status", label: "工单状态" },
    { key: "close_review_status", label: "关单审核" },
  ],
  certification: [
    { key: "level_name", label: "认证等级" },
    { key: "certification_level", label: "认证等级" },
    { key: "application_status", label: "申请状态" },
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
} as const;
type CandidateRelationKind = keyof typeof relationFields;
const candidateRelationGroups = computed(() => {
  const relations = serviceCandidateDetail.value?.person_center?.relations;
  return [
    { title: "线索", kind: "lead" as CandidateRelationKind, data: relations?.lead, fields: relationFields.lead },
    { title: "建档客户", kind: "customer" as CandidateRelationKind, data: relations?.customer, fields: relationFields.customer },
    { title: "VIP", kind: "vip" as CandidateRelationKind, data: relations?.vip, fields: relationFields.vip },
    { title: "服务工单", kind: "serviceCase" as CandidateRelationKind, data: relations?.service_case, fields: relationFields.serviceCase },
  ];
});
const candidateProfileGroups = computed(() => {
  const relations = serviceCandidateDetail.value?.person_center?.relations;
  return [
    { title: "认证摘要", kind: "certification" as CandidateRelationKind, data: relations?.certification, fields: relationFields.certification },
    { title: "择偶要求", kind: "partnerPreference" as CandidateRelationKind, data: relations?.partner_preference, fields: relationFields.partnerPreference },
    { title: "AI画像", kind: "aiProfile" as CandidateRelationKind, data: relations?.ai_profile, fields: relationFields.aiProfile },
  ];
});
const candidateProcessTimeline = computed(() =>
  (serviceCandidateDetail.value?.timeline || []).filter((item) => ["source_event", "service_log", "candidate_join_request", "certification"].includes(item.source_type))
);
const candidateLifecycleTimeline = computed(() => serviceCandidateDetail.value?.timeline || []);

function syncTabByRoute() {
  if (!canManageService.value) {
    activeTab.value = "mine";
    return;
  }
  activeTab.value = route.path.includes("/pending") ? "pending" : "all";
}

function handleTabChange() {
  query.page_no = 1;
  fetchList();
}

async function loadDicts() {
  const [levelRes, caseRes, closeRes, entitlementRes, usageRes, interviewRes, processRes, methodRes, sourceRes, appointmentSlotRes, visitPurposeRes, planStatusRes, planItemTypeRes, planItemStatusRes, recommendStatusRes, meetingTypeRes, meetingStatusRes, meetingResultRes, feedbackInterestRes, courseModeRes, courseConfirmRes, courseRecordStatusRes, ethnicityRes, occupationRes, annualIncomeRes, maritalRes, educationRes, unitTypeRes, houseRes, carRes, marriagePlanRes, customerStageRes, contractStatusRes, receiptStatusRes, candidateSourceRes, candidateScopeRes, candidateRequestStatusRes, leadTypeRes, leadPoolRes, servicePoolRes] = await Promise.all([
    DictAPI.getInitDict("crm_vip_level"),
    DictAPI.getInitDict("service_case_status"),
    DictAPI.getInitDict("close_review_status"),
    DictAPI.getInitDict("service_entitlement_type"),
    DictAPI.getInitDict("service_usage_status"),
    DictAPI.getInitDict("deep_interview_type"),
    DictAPI.getInitDict("crm_customer_process_record_type"),
    DictAPI.getInitDict("crm_customer_follow_method"),
    DictAPI.getInitDict("unified_timeline_source"),
    DictAPI.getInitDict("crm_customer_appointment_slot"),
    DictAPI.getInitDict("crm_customer_visit_purpose"),
    DictAPI.getInitDict("service_plan_status"),
    DictAPI.getInitDict("service_plan_item_type"),
    DictAPI.getInitDict("service_plan_item_status"),
    DictAPI.getInitDict("service_recommend_status"),
    DictAPI.getInitDict("service_meeting_type"),
    DictAPI.getInitDict("service_meeting_status"),
    DictAPI.getInitDict("service_meeting_result"),
    DictAPI.getInitDict("service_feedback_interest_level"),
    DictAPI.getInitDict("service_course_mode"),
    DictAPI.getInitDict("service_course_confirm_status"),
    DictAPI.getInitDict("service_course_record_status"),
    DictAPI.getInitDict("crm_ethnicity"),
    DictAPI.getInitDict("crm_occupation"),
    DictAPI.getInitDict("crm_annual_income"),
    DictAPI.getInitDict("crm_marital_status"),
    DictAPI.getInitDict("crm_education"),
    DictAPI.getInitDict("crm_unit_type"),
    DictAPI.getInitDict("crm_house_status"),
    DictAPI.getInitDict("crm_car_status"),
    DictAPI.getInitDict("crm_marriage_plan"),
    DictAPI.getInitDict("crm_customer_stage"),
    DictAPI.getInitDict("crm_contract_status"),
    DictAPI.getInitDict("crm_contract_receipt_status"),
    DictAPI.getInitDict("candidate_source_type"),
    DictAPI.getInitDict("candidate_search_scope"),
    DictAPI.getInitDict("candidate_join_request_status"),
    DictAPI.getInitDict("crm_lead_type"),
    DictAPI.getInitDict("crm_lead_pool_type"),
    DictAPI.getInitDict("service_pool_type"),
  ]);
  vipLevelOptions.value = levelRes.data.data || [];
  caseStatusOptions.value = caseRes.data.data || [];
  closeStatusOptions.value = closeRes.data.data || [];
  entitlementTypeOptions.value = entitlementRes.data.data || [];
  usageStatusOptions.value = usageRes.data.data || [];
  interviewTypeOptions.value = interviewRes.data.data || [];
  processRecordTypeOptions.value = processRes.data.data || [];
  followMethodOptions.value = methodRes.data.data || [];
  timelineSourceOptions.value = sourceRes.data.data || [];
  appointmentSlotOptions.value = appointmentSlotRes.data.data || [];
  visitPurposeOptions.value = visitPurposeRes.data.data || [];
  planStatusOptions.value = planStatusRes.data.data || [];
  planItemTypeOptions.value = planItemTypeRes.data.data || [];
  planItemStatusOptions.value = planItemStatusRes.data.data || [];
  recommendStatusOptions.value = recommendStatusRes.data.data || [];
  meetingTypeOptions.value = meetingTypeRes.data.data || [];
  meetingStatusOptions.value = meetingStatusRes.data.data || [];
  meetingResultOptions.value = meetingResultRes.data.data || [];
  feedbackInterestOptions.value = feedbackInterestRes.data.data || [];
  courseModeOptions.value = courseModeRes.data.data || [];
  courseConfirmOptions.value = courseConfirmRes.data.data || [];
  courseRecordStatusOptions.value = courseRecordStatusRes.data.data || [];
  ethnicityOptions.value = ethnicityRes.data.data || [];
  occupationOptions.value = occupationRes.data.data || [];
  annualIncomeOptions.value = annualIncomeRes.data.data || [];
  maritalStatusOptions.value = maritalRes.data.data || [];
  educationOptions.value = educationRes.data.data || [];
  unitTypeOptions.value = unitTypeRes.data.data || [];
  houseStatusOptions.value = houseRes.data.data || [];
  carStatusOptions.value = carRes.data.data || [];
  marriagePlanOptions.value = marriagePlanRes.data.data || [];
  customerStageOptions.value = customerStageRes.data.data || [];
  contractStatusOptions.value = contractStatusRes.data.data || [];
  receiptStatusOptions.value = receiptStatusRes.data.data || [];
  candidateSourceTypeOptions.value = candidateSourceRes.data.data || [];
  candidateSearchScopeOptions.value = candidateScopeRes.data.data || [];
  candidateJoinRequestStatusOptions.value = candidateRequestStatusRes.data.data || [];
  leadTypeOptions.value = leadTypeRes.data.data || [];
  leadPoolTypeOptions.value = leadPoolRes.data.data || [];
  servicePoolOptions.value = servicePoolRes.data.data || [];
}

function flattenDept(list: DeptTable[], prefix = ""): Array<{ label: string; value: number }> {
  return list.flatMap((item) => {
    const label = `${prefix}${item.name}`;
    const current = item.id ? [{ label, value: item.id }] : [];
    return [...current, ...flattenDept(item.children || [], `${label}/`)];
  });
}

async function loadDeptOptions() {
  if (!canManageService.value) {
    const deptId = userStore.basicInfo.dept_id;
    deptOptions.value = deptId ? [{ label: userStore.basicInfo.dept_name || "当前门店", value: deptId }] : [];
    return;
  }
  const res = await DeptAPI.listDept();
  deptOptions.value = flattenDept(res.data.data || []);
}

async function handleStoreFilterChange() {
  query.service_owner_user_id = undefined;
  filterMatchmakers.value = [];
  if (query.store_id) {
    const response = await VipServiceAPI.listMatchmakers(query.store_id);
    filterMatchmakers.value = response.data.data || [];
  }
}

async function fetchList() {
  loading.value = true;
  try {
    const params = {
      ...query,
      vip_status: activeTab.value === "pending" ? undefined : activeTab.value === "closeReview" ? "pending_close_review" : query.vip_status,
      close_review_status: activeTab.value === "closeReview" ? "pending" : undefined,
      service_owner_user_id: activeTab.value === "pending" ? undefined : query.service_owner_user_id,
      mine: activeTab.value === "mine" ? true : undefined,
    };
    const response = activeTab.value === "pending" ? await VipServiceAPI.listPendingAssign(params) : await VipServiceAPI.listVip(params);
    rows.value = response.data.data.items || [];
    total.value = response.data.data.total || 0;
  } finally {
    loading.value = false;
  }
}

function resetQuery() {
  Object.assign(query, { page_no: 1, keyword: undefined, vip_level: undefined, vip_status: undefined, store_id: undefined, service_owner_user_id: undefined });
  filterMatchmakers.value = [];
  fetchList();
}

function money(value?: string | number) {
  const amount = Number(value ?? 0);
  return Number.isFinite(amount) ? `¥${amount.toFixed(2)}` : "¥0.00";
}

function dictText(options: DictDataTable[], value?: string) {
  const normalized = normalizeCode(value);
  return options.find((item) => item.dict_value === normalized)?.dict_label || normalized || "-";
}

function dictDataToOptions(options: DictDataTable[]) {
  return options.map((item) => ({ label: item.dict_label || String(item.dict_value || ""), value: String(item.dict_value || "") }));
}

function dictListText(options: DictDataTable[], values?: string[]) {
  if (!values?.length) return "-";
  return values.map((value) => dictText(options, value)).join("、");
}

function dictTag(options: DictDataTable[], value?: string): "primary" | "success" | "warning" | "info" | "danger" {
  const tag = options.find((item) => item.dict_value === value)?.list_class;
  return ["primary", "success", "warning", "info", "danger"].includes(tag || "") ? (tag as "primary" | "success" | "warning" | "info" | "danger") : "info";
}

function genderText(value?: string) {
  const map: Record<string, string> = { "0": "男", "1": "女", "2": "未知", male: "男", female: "女", unknown: "未知" };
  return value ? map[value] || value : "-";
}

function boolText(value?: boolean | null) {
  if (value === true) return "是";
  if (value === false) return "否";
  return "-";
}

function qualityStatus(value?: string): "success" | "warning" | "exception" | undefined {
  if (value === "good") return "success";
  if (value === "medium") return "warning";
  if (value === "poor") return "exception";
  return undefined;
}

function jsonText(value?: Record<string, unknown>) {
  if (!value || Object.keys(value).length === 0) return "暂无";
  return JSON.stringify(value, null, 2);
}

function relationFieldText(kind: CandidateRelationKind, key: string, value: unknown, relationData?: Record<string, unknown> | null) {
  if (value === undefined || value === null || value === "") return "-";
  const current = relationData || {};
  const text = String(value);
  if (key === "store_id") return String(current?.store_name || deptName(Number(value)));
  if (key === "owner_sales_id") return String(current?.owner_sales_id_name || userName(Number(value)));
  if (key === "owner_user_id") return String(current?.owner_user_id_name || userName(Number(value)));
  if (key === "service_owner_user_id") return String(current?.service_owner_user_id_name || userName(Number(value)));
  if (key === "owner_matchmaker_id") return String(current?.owner_matchmaker_id_name || userName(Number(value)));
  if (key === "source_channel_code") return String(current?.source_channel_name || channelText(text));
  if (key === "pool_type" && kind === "lead") return dictText(leadPoolTypeOptions.value, text);
  if (key === "pool_type" && kind === "serviceCase") return dictText(servicePoolOptions.value, text) === text ? servicePoolText(text) : dictText(servicePoolOptions.value, text);
  if (key === "lead_type") return dictText(leadTypeOptions.value, text);
  if (key === "vip_level") return dictText(vipLevelOptions.value, text);
  if (key === "vip_status") return dictText(caseStatusOptions.value, text);
  if (key === "case_status") return dictText(caseStatusOptions.value, text);
  if (key === "close_review_status") return dictText(closeStatusOptions.value, text);
  if (key === "current_stage" || key === "max_stage") return dictText(customerStageOptions.value, text);
  if (key === "candidate_status") return candidateStatusText(text);
  if (key === "application_status") return applicationStatusText(text);
  if (key === "strictness_level") return strictnessText(text);
  if (key === "is_final") return boolText(Boolean(value));
  if (key === "source_type" && kind === "partnerPreference") return preferenceSourceText(text);
  if (key === "source_type" && kind === "aiProfile") return aiSourceText(text);
  if (key === "generation_status") return generationStatusText(text);
  if (typeof value === "boolean") return boolText(value);
  if (Array.isArray(value)) return value.length ? value.join("、") : "-";
  if (typeof value === "object") return JSON.stringify(value);
  return text;
}

function deptName(id?: number) {
  if (!id) return "-";
  return deptOptions.value.find((item) => item.value === id)?.label || String(id);
}

function userName(id?: number) {
  if (!id) return "-";
  const user = [...filterMatchmakers.value, ...matchmakerOptions.value].find((item) => item.id === id);
  return user?.name || String(id);
}

function channelText(value?: string) {
  const fallback: Record<string, string> = {
    MINIAPP_REGISTER: "小程序注册",
    MANUAL_CREATE: "人工录入",
    IMPORT: "批量导入",
    EXTERNAL_PUSH: "外部推送",
  };
  return value ? fallback[value] || value : "-";
}

function servicePoolText(value?: string) {
  const map: Record<string, string> = {
    pending_assign: "待分配",
    private: "红娘私有",
    close: "关单",
    public_reserved: "服务公海预留",
  };
  return value ? map[value] || value : "-";
}

function candidateStatusText(value?: string) {
  const map: Record<string, string> = { active: "有效", inactive: "停用" };
  return value ? map[value] || value : "-";
}

function applicationStatusText(value?: string) {
  const map: Record<string, string> = { pending: "待处理", pending_pay: "待支付", paid: "已支付", reviewing: "审核中", approved: "已通过", rejected: "已驳回", cancelled: "已取消" };
  return value ? map[value] || value : "-";
}

function strictnessText(value?: string) {
  const map: Record<string, string> = { loose: "宽松", normal: "正常", strict: "严格" };
  return value ? map[value] || value : "-";
}

function preferenceSourceText(value?: string) {
  const map: Record<string, string> = { admin: "后台维护", matchmaker: "红娘维护", customer: "客户填写", system: "系统生成" };
  return value ? map[value] || value : "-";
}

function aiSourceText(value?: string) {
  const map: Record<string, string> = { system: "系统生成", profile: "资料画像", deep_interview: "深访画像", manual: "人工维护" };
  return value ? map[value] || value : "-";
}

function generationStatusText(value?: string) {
  const map: Record<string, string> = { pending: "待生成", running: "生成中", success: "已生成", failed: "生成失败" };
  return value ? map[value] || value : "-";
}

function timelineSourceText(value?: string) {
  const map: Record<string, string> = {
    source_event: "来源事件",
    lead_lifecycle: "线索",
    customer_lifecycle: "客户",
    service_log: "服务",
    candidate_join_request: "备选申请",
    certification: "认证",
  };
  return (value && (map[value] || dictText(timelineSourceOptions.value, value))) || "-";
}

function candidateTimelineTitleText(item: { source_type?: string; title?: string }) {
  const title = normalizeCode(item.title);
  if (!title) return "-";
  if (item.source_type === "service_log") return serviceOperationText(title);
  if (item.source_type === "lead_lifecycle" || item.source_type === "customer_lifecycle") return lifecycleOperationText(title);
  if (item.source_type === "candidate_join_request") {
    const status = title.replace("备选加入申请-", "");
    return `备选加入申请-${dictText(candidateJoinRequestStatusOptions.value, status)}`;
  }
  if (item.source_type === "certification") {
    const [name, status] = title.split("-");
    return status ? `${name}-${certificationRecordStatusText(status)}` : title;
  }
  return lifecycleOperationText(title);
}

function certificationRecordStatusText(value?: string) {
  const map: Record<string, string> = { pending: "待提交", submitted: "已提交", reviewing: "审核中", verified: "已通过", rejected: "已驳回", expired: "已过期" };
  return value ? map[value] || value : "-";
}

function preferenceRangeText(type: "age" | "height" | "weight") {
  const pref = serviceCandidateDetail.value?.partner_preference;
  if (!pref) return "-";
  const config = {
    age: { min: pref.age_min, max: pref.age_max, unit: "岁" },
    height: { min: pref.height_min_cm, max: pref.height_max_cm, unit: "cm" },
    weight: { min: pref.weight_min_kg, max: pref.weight_max_kg, unit: "kg" },
  }[type];
  if (!config.min && !config.max) return "-";
  return `${config.min ?? "不限"} - ${config.max ?? "不限"}${config.unit}`;
}

function certificationLevelText(value?: string) {
  const map: Record<string, string> = { none: "未认证", basic: "基础认证", enhanced: "增强认证" };
  return value ? map[value] || value : "-";
}

function paymentStatusText(value?: string) {
  const map: Record<string, string> = { unpaid: "未支付", partial: "部分支付", settled: "已结清" };
  return value ? map[value] || value : "-";
}

function receiptTypeText(value?: string) {
  const map: Record<string, string> = { deposit: "首付款", full: "全款", balance: "尾款", installment: "分期款", refund: "退款" };
  return value ? map[value] || value : "-";
}

function payMethodText(value?: string) {
  const map: Record<string, string> = { cash: "现金", bank_transfer: "银行转账", alipay: "支付宝", wechat: "微信", cloudpay: "云支付", other: "其他" };
  return value ? map[value] || value : "-";
}

function customerEndReasonText(value?: string) {
  const map: Record<string, string> = { converted_vip: "已转VIP", return_lead: "退回线索", closed: "结束服务" };
  return value ? map[value] || lifecycleOperationText(value) : "-";
}

function timelineRecordText(row: ServiceTimelineItem) {
  const value = normalizeCode(row.record_type);
  const map: Record<string, string> = {
    visit_checkin: "登记到店",
    convert_customer: "转建档客户",
    converted_customer: "已转建档客户",
    customer_convert: "线索转建档客户",
  };
  if (map[value]) return map[value];
  if (value.startsWith("deep_interview_")) {
    return `深访-${dictText(interviewTypeOptions.value, value.replace("deep_interview_", ""))}`;
  }
  if (value.startsWith("usage_")) {
    return `核销-${dictText(entitlementTypeOptions.value, value.replace("usage_", ""))}`;
  }
  if (value.startsWith("service_")) {
    return serviceOperationText(value.replace("service_", ""));
  }
  if (value.startsWith("contract_")) {
    return `合同-${dictText(contractStatusOptions.value, value.replace("contract_", ""))}`;
  }
  if (value.startsWith("receipt_")) {
    return `收款-${dictText(receiptStatusOptions.value, value.replace("receipt_", ""))}`;
  }
  return dictText(processRecordTypeOptions.value, value);
}

function serviceOperationText(value?: string) {
  const code = normalizeCode(value);
  const map: Record<string, string> = {
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
  };
  return code ? map[code] || code : "-";
}

function lifecycleStageText(value?: string) {
  const code = normalizeCode(value);
  const map: Record<string, string> = { lead: "线索", customer: "客户", contract: "合同", receipt: "收款", service: "服务", system: "系统" };
  return code ? map[code] || code : "-";
}

function lifecycleOperationText(value?: string) {
  const code = normalizeCode(value);
  const map: Record<string, string> = {
    create_from_lead: "线索转客户",
    edit: "编辑资料",
    transfer_owner: "同店转派",
    transfer_store: "跨店转交",
    return_lead: "退回线索",
    service_profile_update: "服务阶段编辑VIP资料",
    convert_customer: "线索转建档客户",
    converted_customer: "已转建档客户",
    customer_convert: "线索转建档客户",
    customer_return: "客户退回线索",
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
    service_assign: "服务分配",
    service_transfer: "服务改派",
    service_close_apply: "申请关单",
    service_close_review: "审核关单",
    service_reopen: "服务重开",
  };
  if (!code) return "-";
  return map[code] || dictText(contractStatusOptions.value, code);
}

function normalizeCode(value?: string) {
  return String(value || "").trim();
}

function dateOnly(value?: string) {
  return value ? value.slice(0, 10) : "-";
}

function dateValue(value?: string) {
  return value ? value.slice(0, 10) : "";
}

function planRangeText(row: ServicePlanItem) {
  const start = dateOnly(row.planned_start_at || row.planned_at);
  const end = dateOnly(row.planned_end_at || row.due_at);
  if (start === "-" && end === "-") return "-";
  return `${start} 至 ${end}`;
}

function canEditPlanItem(row: ServicePlanItem) {
  if (["cancelled", "skipped"].includes(row.item_status)) return false;
  if (servicePlan.value?.plan_status === "draft") return true;
  if (servicePlan.value?.plan_status === "published") {
    return !row.related_recommendation_id && !row.related_meeting_id && !row.related_usage_id && ["pending", "in_progress"].includes(row.item_status);
  }
  return false;
}

function canSkipPlanItem(row: ServicePlanItem) {
  return !row.related_recommendation_id && !row.related_meeting_id && !row.related_usage_id && ["pending", "in_progress"].includes(row.item_status);
}

function canRestorePlanItem(row: ServicePlanItem) {
  return !row.related_recommendation_id && !row.related_meeting_id && !row.related_usage_id && row.item_status === "skipped";
}

function canMatchPlanItem(row: ServicePlanItem) {
  return (
    row.item_type === "recommendation"
    && !row.related_usage_id
    && !row.recommendation_count
    && ["pending", "in_progress"].includes(row.item_status)
  );
}

function canConsumeRecommendation(row: ServiceRecommendation) {
  return !row.related_usage_id && ["recommended", "meeting_created", "completed"].includes(row.recommendation_status);
}

function canCreateMeetingFromRecommendation(row: ServiceRecommendation) {
  return ["recommended", "completed"].includes(row.recommendation_status);
}

function ensurePlanPublished() {
  if (servicePlan.value?.plan_status === "published") return true;
  ElMessage.warning("请先发布服务计划");
  return false;
}

function waitingText(hours?: number) {
  if (hours === undefined || hours === null) return "-";
  if (hours < 24) return `${hours}小时`;
  return `${Math.floor(hours / 24)}天${hours % 24}小时`;
}

function quotaText(row: ServiceCaseTable, type: string) {
  const item = row.entitlement_summary?.[type];
  return item ? `${item.used}/${item.total}` : "0/0";
}

function operationText(value?: string) {
  const map: Record<string, string> = { assign: "分配", transfer: "改派", close_apply: "申请关单", close_review: "审核关单", reopen: "重开" };
  return value ? map[value] || value : "-";
}

async function openDetail(id?: number) {
  if (!id) return;
  const response = await VipServiceAPI.detailVip(id);
  detail.value = response.data.data;
  detailTab.value = "overview";
  workSummary.value = undefined;
  customerProfile.value = undefined;
  certificationArchiveItems.value = [];
  certifications.value = [];
  timelineRows.value = [];
  lifecycleRows.value = [];
  contractRows.value = [];
  servicePlan.value = undefined;
  recommendationRows.value = [];
  meetingRows.value = [];
  courseRows.value = [];
  await loadWorkSummary(id);
  detailVisible.value = true;
}

async function loadWorkSummary(id: number) {
  const response = await VipServiceAPI.getWorkSummary(id);
  workSummary.value = response.data.data;
}

async function handleDetailTabChange(tabName: string | number) {
  if (!detail.value?.id) return;
  const id = detail.value.id;
  if (tabName === "profile" && !customerProfile.value) {
    const response = await VipServiceAPI.getCustomerProfile(id);
    customerProfile.value = response.data.data;
  }
  if (tabName === "certification" && certifications.value.length === 0) {
    const [profileRes, itemRes, materialRes] = await Promise.all([
      customerProfile.value ? Promise.resolve(undefined) : VipServiceAPI.getCustomerProfile(id),
      VipServiceAPI.getCertificationArchiveItems(id),
      VipServiceAPI.getCertification(id),
    ]);
    if (profileRes) {
      customerProfile.value = profileRes.data.data;
    }
    certificationArchiveItems.value = itemRes.data.data || [];
    certifications.value = materialRes.data.data || [];
  }
  if (tabName === "timeline" && timelineRows.value.length === 0) {
    const response = await VipServiceAPI.getTimeline(id);
    timelineRows.value = response.data.data || [];
  }
  if (tabName === "lifecycle" && lifecycleRows.value.length === 0) {
    const response = await VipServiceAPI.getLifecycle(id);
    lifecycleRows.value = response.data.data || [];
  }
  if (tabName === "contracts" && contractRows.value.length === 0) {
    const response = await VipServiceAPI.getContracts(id);
    contractRows.value = response.data.data || [];
  }
  if (tabName === "plan" && !servicePlan.value) {
    await loadServicePlan(id);
  }
}

async function loadServicePlan(id = detail.value?.id) {
  if (!id) return;
  const [planRes, recommendRes, meetingRes, courseRes] = await Promise.all([
    VipServiceAPI.getPlan(id),
    VipServiceAPI.listRecommendations(id),
    VipServiceAPI.listMeetings(id),
    VipServiceAPI.listCourseRecords(id),
  ]);
  servicePlan.value = planRes.data.data;
  recommendationRows.value = recommendRes.data.data || [];
  meetingRows.value = meetingRes.data.data || [];
  courseRows.value = courseRes.data.data || [];
}

async function publishPlan() {
  if (!detail.value?.id) return;
  await VipServiceAPI.publishPlan(detail.value.id);
  ElMessage.success("服务计划已发布");
  await loadServicePlan(detail.value.id);
}

async function rebuildPlan() {
  if (!detail.value?.id) return;
  await ElMessageBox.confirm("将按当前权益重新生成未执行的计划节点，确认继续？", "重建服务计划", { type: "warning" });
  await VipServiceAPI.rebuildPlan(detail.value.id);
  ElMessage.success("服务计划已重建");
  await loadServicePlan(detail.value.id);
}

async function autoSchedulePlan() {
  if (!detail.value?.id) return;
  await VipServiceAPI.autoSchedulePlan(detail.value.id);
  ElMessage.success("未排期节点已自动排期");
  await loadServicePlan(detail.value.id);
}

function openMatch(row: ServicePlanItem) {
  if (!ensurePlanPublished()) return;
  currentPlanItem.value = row;
  Object.assign(matchQuery, {
    page_no: 1,
    page_size: 10,
    search_mode: "score",
    scope: "backup",
    keyword: undefined,
    person_id: undefined,
    display_no: undefined,
    mobile: undefined,
    name: undefined,
    gender: undefined,
    age_min: undefined,
    age_max: undefined,
    height_min: undefined,
    height_max: undefined,
    weight_min: undefined,
    weight_max: undefined,
    education: undefined,
    annual_income: undefined,
    marital_status: undefined,
    ethnicity: undefined,
    occupation_code: undefined,
    unit_type: undefined,
    residence: undefined,
    hometown: undefined,
    house_status: undefined,
    car_status: undefined,
    accept_long_distance_self: undefined,
    accept_flash_marriage: undefined,
    willing_relocate: undefined,
    marriage_plan: undefined,
    has_photo: undefined,
    certification_level: undefined,
    pref_age_min: undefined,
    pref_age_max: undefined,
    pref_height_min: undefined,
    pref_height_max: undefined,
    pref_weight_min: undefined,
    pref_weight_max: undefined,
    preferred_education_codes: [],
    preferred_marital_status_codes: [],
    preferred_annual_income_codes: [],
    preferred_house_status_codes: [],
    preferred_car_status_codes: [],
    pref_accept_long_distance: undefined,
    pref_accept_divorced: undefined,
    pref_accept_children: undefined,
    preference_text: undefined,
    preferred_occupation_text: undefined,
  });
  matchRows.value = [];
  matchTotal.value = 0;
  matchVisible.value = true;
  fetchMatchCandidates();
}

async function fetchMatchCandidates() {
  if (!detail.value?.id || !currentPlanItem.value?.id) return;
  matchLoading.value = true;
  try {
    const response = await VipServiceAPI.matchCandidates(detail.value.id, currentPlanItem.value.id, matchQuery);
    matchRows.value = response.data.data.items || [];
    matchTotal.value = response.data.data.total || 0;
  } finally {
    matchLoading.value = false;
  }
}

function openRecommendation(row: MatchCandidate) {
  if (!currentPlanItem.value) return;
  currentCandidate.value = row;
  Object.assign(recommendationForm, {
    plan_item_id: currentPlanItem.value.id,
    candidate_person_id: row.id,
    recommend_reason: "",
    match_score: row.match_score,
    matched_points: row.matched_points || [],
    unmatched_points: row.unmatched_points || [],
    risk_notes: "",
    matchmaker_remark: "",
  });
  recommendationVisible.value = true;
}

async function submitRecommendation() {
  if (!detail.value?.id) return;
  submitLoading.value = true;
  try {
    await VipServiceAPI.createRecommendation(detail.value.id, recommendationForm);
    ElMessage.success("推荐记录已创建");
    recommendationVisible.value = false;
    matchVisible.value = false;
    await loadServicePlan(detail.value.id);
  } finally {
    submitLoading.value = false;
  }
}

async function revokeRecommendation(row: ServiceRecommendation) {
  if (!detail.value?.id) return;
  await ElMessageBox.confirm("确认撤销这条推荐记录？撤销后对应候选不会进入约见，可重新推荐或重新选择约见人。", "撤销推荐记录", { type: "warning" });
  await VipServiceAPI.revokeRecommendation(detail.value.id, row.id, { reason: "红娘撤销推荐记录" });
  ElMessage.success("推荐记录已撤销");
  await loadServicePlan(detail.value.id);
}

async function consumeRecommendation(row: ServiceRecommendation) {
  if (!detail.value?.id) return;
  const serviceCaseId = detail.value.id;
  await ElMessageBox.confirm("确认核销这条推荐服务？核销后会扣减推荐权益，推荐记录仍可继续转约见。", "核销推荐服务", { type: "warning" });
  await VipServiceAPI.consumeRecommendation(serviceCaseId, row.id, { reason: "红娘确认推荐服务已交付" });
  ElMessage.success("推荐权益已核销");
  await loadServicePlan(serviceCaseId);
  detail.value = (await VipServiceAPI.detailVip(serviceCaseId)).data.data;
  await loadWorkSummary(serviceCaseId);
  await fetchList();
}

function openCourseRecord(row: ServicePlanItem) {
  if (!ensurePlanPublished()) return;
  currentPlanItem.value = row;
  Object.assign(courseForm, {
    course_at: undefined,
    course_title: row.title || "课程服务",
    course_mode: "offline",
    content: "",
    customer_feedback: "",
    matchmaker_remark: "",
    customer_confirm_status: "matchmaker_confirmed",
    customer_signature_url: undefined,
    customer_signed_at: undefined,
  });
  courseVisible.value = true;
}

async function submitCourseRecord() {
  const valid = await courseFormRef.value?.validate();
  if (!valid || !detail.value?.id || !currentPlanItem.value?.id) return;
  const serviceCaseId = detail.value.id;
  const planItemId = currentPlanItem.value.id;
  submitLoading.value = true;
  try {
    await VipServiceAPI.createCourseRecord(serviceCaseId, planItemId, courseForm);
    ElMessage.success("课程已登记并核销");
    courseVisible.value = false;
    await loadServicePlan(serviceCaseId);
    detail.value = (await VipServiceAPI.detailVip(serviceCaseId)).data.data;
    await loadWorkSummary(serviceCaseId);
    await fetchList();
  } finally {
    submitLoading.value = false;
  }
}

async function revokeCourseRecord(row: ServiceCourseRecord) {
  if (!detail.value?.id) return;
  const serviceCaseId = detail.value.id;
  const { value } = await ElMessageBox.prompt("请填写撤销原因，撤销后会恢复课程权益并回退课程节点。", "撤销课程记录", {
    inputType: "textarea",
    inputValidator: (val) => !!val || "撤销原因必填",
  });
  await VipServiceAPI.revokeCourseRecord(serviceCaseId, row.id, { reason: value });
  ElMessage.success("课程记录已撤销");
  await loadServicePlan(serviceCaseId);
  detail.value = (await VipServiceAPI.detailVip(serviceCaseId)).data.data;
  await loadWorkSummary(serviceCaseId);
  await fetchList();
}

async function openServiceCandidateDetail(personId?: number) {
  if (!detail.value?.id || !personId) return;
  const response = await VipServiceAPI.getServiceCandidateDetail(detail.value.id, personId);
  serviceCandidateDetail.value = response.data.data;
  serviceCandidateTab.value = "profile";
  serviceCandidateVisible.value = true;
}

async function requestCandidateUnlock() {
  if (!detail.value || !serviceCandidateDetail.value) return;
  const { value } = await ElMessageBox.prompt("请输入申请原因", "申请加入备选库解锁联系方式", {
    inputType: "textarea",
    inputPlaceholder: "例如：服务计划推荐候选，需要纳入当前红娘备选库跟进",
    inputValidator: (value) => Boolean(value && value.trim()),
    inputErrorMessage: "请填写申请原因",
  });
  submitLoading.value = true;
  try {
    const person = serviceCandidateDetail.value.person;
    await CandidateAPI.createJoinRequest({
      person_id: person.id,
      scope: serviceCandidateDetail.value.backup.request_scope,
      matchmaker_id: detail.value.owner_matchmaker_id || detail.value.service_owner_user_id,
      request_reason: value,
    });
    ElMessage.success("加入申请已提交");
    await openServiceCandidateDetail(person.id);
  } finally {
    submitLoading.value = false;
  }
}

function openMeeting(row: ServiceRecommendation) {
  if (!ensurePlanPublished()) return;
  if (!availableMeetingPlanItems.value.length) {
    ElMessage.warning("没有可用的相亲约见计划节点");
    return;
  }
  currentRecommendation.value = row;
  currentPlanItem.value = availableMeetingPlanItems.value.length === 1 ? availableMeetingPlanItems.value[0] : undefined;
  Object.assign(meetingForm, {
    recommendation_id: row.id,
    plan_item_id: currentPlanItem.value?.id,
    meeting_type: "store",
    scheduled_at: undefined,
    appointment_slot: undefined,
    location: "",
  });
  meetingVisible.value = true;
}

function openMeetingFromItem(row: ServicePlanItem) {
  if (!ensurePlanPublished()) return;
  if (!availableRecommendationRows.value.length) {
    ElMessage.warning("请先创建可转约见的推荐记录");
    return;
  }
  currentPlanItem.value = row;
  currentRecommendation.value = undefined;
  Object.assign(meetingForm, { recommendation_id: undefined, plan_item_id: row.id, meeting_type: "store", scheduled_at: undefined, appointment_slot: undefined, location: "" });
  meetingVisible.value = true;
}

function recommendationOptionLabel(row: ServiceRecommendation) {
  const score = row.match_score === undefined || row.match_score === null ? "" : ` / ${row.match_score}分`;
  return `${row.candidate_name || `候选${row.candidate_person_id}`}${score}`;
}

function meetingPlanItemOptionLabel(row: ServicePlanItem) {
  return `${row.title || `约见节点${row.sequence_no}`} · ${planRangeText(row)} · ${dictText(planItemStatusOptions.value, row.item_status)}`;
}

function handleMeetingRecommendationChange(value: number) {
  currentRecommendation.value = availableRecommendationRows.value.find((item) => item.id === value);
}

async function submitMeeting() {
  if (!detail.value?.id) return;
  if (!meetingForm.recommendation_id) {
    ElMessage.warning("请选择约见人");
    return;
  }
  if (!meetingForm.plan_item_id) {
    ElMessage.warning("请选择绑定的相亲约见计划节点");
    return;
  }
  submitLoading.value = true;
  try {
    await VipServiceAPI.createMeeting(detail.value.id, meetingForm);
    ElMessage.success("相亲约见已创建");
    meetingVisible.value = false;
    await loadServicePlan(detail.value.id);
  } finally {
    submitLoading.value = false;
  }
}

async function confirmMeeting(row: ServiceMeeting) {
  if (!detail.value?.id) return;
  await VipServiceAPI.confirmMeeting(detail.value.id, row.id);
  ElMessage.success("相亲约见已确认");
  await loadServicePlan(detail.value.id);
}

async function cancelMeeting(row: ServiceMeeting) {
  if (!detail.value?.id) return;
  await ElMessageBox.confirm("确认撤销该相亲约见？撤销后约见计划节点会回退为待处理。", "撤销相亲约见", { type: "warning" });
  await VipServiceAPI.cancelMeeting(detail.value.id, row.id, { reason: "红娘撤销约见" });
  ElMessage.success("相亲约见已撤销");
  await loadServicePlan(detail.value.id);
}

async function openFeedback(row: ServiceMeeting) {
  if (!detail.value?.id) return;
  currentMeeting.value = row;
  const response = await VipServiceAPI.listMeetingFeedback(detail.value.id, row.id);
  feedbackRows.value = response.data.data || [];
  hydrateFeedbackPair(row);
  feedbackVisible.value = true;
}

async function submitFeedback() {
  if (!detail.value?.id || !currentMeeting.value?.id) return;
  if (!feedbackPairForm.male.feedback_content || !feedbackPairForm.female.feedback_content || !feedbackPairForm.matchmaker_opinion) {
    ElMessage.warning("请填写男方意见、女方意见和红娘意见");
    return;
  }
  submitLoading.value = true;
  try {
    await saveOneMeetingFeedback(feedbackPairForm.male.person_id, feedbackPairForm.male.feedback_content, feedbackPairForm.male.interest_level);
    await saveOneMeetingFeedback(feedbackPairForm.female.person_id, feedbackPairForm.female.feedback_content, feedbackPairForm.female.interest_level);
    ElMessage.success("反馈已保存");
    await openFeedback(currentMeeting.value);
    await loadServicePlan(detail.value.id);
  } finally {
    submitLoading.value = false;
  }
}

function feedbackPeople(row: ServiceMeeting) {
  const people = [
    { id: row.initiator_person_id, name: row.initiator_name || "发起方", gender: row.initiator_gender },
    { id: row.target_person_id, name: row.target_name || "对方", gender: row.target_gender },
  ];
  const male = people.find((item) => item.gender === "1") || people[0];
  const female = people.find((item) => item.gender === "0") || people.find((item) => item.id !== male.id) || people[1];
  return { male, female };
}

function feedbackSideLabel(side: "male" | "female") {
  if (!currentMeeting.value) return side === "male" ? "男方意见" : "女方意见";
  const people = feedbackPeople(currentMeeting.value);
  const person = people[side];
  const label = side === "male" ? "男方意见" : "女方意见";
  return `${label}(${person.name})`;
}

function hydrateFeedbackPair(row: ServiceMeeting) {
  const people = feedbackPeople(row);
  const maleFeedback = feedbackRows.value.find((item) => item.feedback_person_id === people.male.id);
  const femaleFeedback = feedbackRows.value.find((item) => item.feedback_person_id === people.female.id);
  Object.assign(feedbackPairForm.male, {
    person_id: people.male.id,
    feedback_content: maleFeedback?.feedback_content || "",
    interest_level: maleFeedback?.interest_level,
  });
  Object.assign(feedbackPairForm.female, {
    person_id: people.female.id,
    feedback_content: femaleFeedback?.feedback_content || "",
    interest_level: femaleFeedback?.interest_level,
  });
  feedbackPairForm.meeting_result = maleFeedback?.meeting_result || femaleFeedback?.meeting_result || row.meeting_result;
  feedbackPairForm.next_action = maleFeedback?.next_action || femaleFeedback?.next_action || row.next_action;
  feedbackPairForm.matchmaker_opinion = row.matchmaker_opinion || "";
}

async function saveOneMeetingFeedback(personId: number, content: string, interestLevel?: string) {
  if (!detail.value?.id || !currentMeeting.value?.id) return;
  const body: MeetingFeedbackForm = {
    feedback_person_id: personId,
    feedback_content: content,
    interest_level: interestLevel,
    meeting_result: feedbackPairForm.meeting_result,
    next_action: feedbackPairForm.next_action,
    matchmaker_opinion: feedbackPairForm.matchmaker_opinion,
  };
  const existing = feedbackRows.value.find((item) => item.feedback_person_id === personId);
  if (existing) {
    await VipServiceAPI.updateMeetingFeedback(detail.value.id, currentMeeting.value.id, existing.id, body);
  } else {
    await VipServiceAPI.createMeetingFeedback(detail.value.id, currentMeeting.value.id, body);
  }
}

function openPlanItemEdit(row: ServicePlanItem) {
  currentPlanItem.value = row;
  Object.assign(planItemForm, {
    title: row.title,
    sequence_no: row.sequence_no,
    planned_start_date: dateValue(row.planned_start_at || row.planned_at),
    planned_end_date: dateValue(row.planned_end_at || row.due_at),
    remark: row.remark || "",
  });
  planItemEditVisible.value = true;
}

async function submitPlanItemEdit() {
  if (!detail.value?.id || !currentPlanItem.value?.id) return;
  submitLoading.value = true;
  try {
    const body: ServicePlanItemForm = {
      planned_start_at: planItemForm.planned_start_date ? `${planItemForm.planned_start_date} 00:00:00` : undefined,
      planned_end_at: planItemForm.planned_end_date ? `${planItemForm.planned_end_date} 23:59:59` : undefined,
      remark: planItemForm.remark,
    };
    if (servicePlan.value?.plan_status !== "published") {
      body.title = planItemForm.title;
      body.sequence_no = planItemForm.sequence_no;
    }
    await VipServiceAPI.updatePlanItem(detail.value.id, currentPlanItem.value.id, body);
    ElMessage.success("计划节点已更新");
    planItemEditVisible.value = false;
    await loadServicePlan(detail.value.id);
  } finally {
    submitLoading.value = false;
  }
}

async function skipPlanItem(row: ServicePlanItem) {
  if (!detail.value?.id) return;
  await ElMessageBox.confirm("确认放弃本次服务安排？放弃后不会扣减权益、不会生成核销，只会在服务计划中保留一条记录。", "放弃本次服务", { type: "warning" });
  await VipServiceAPI.skipPlanItem(detail.value.id, row.id, { reason: "放弃本次服务安排" });
  ElMessage.success("已放弃本次服务安排");
  await loadServicePlan(detail.value.id);
}

async function restorePlanItem(row: ServicePlanItem) {
  if (!detail.value?.id) return;
  await ElMessageBox.confirm(
    "确认撤销该节点的放弃状态？撤销后节点会恢复为待处理，可继续推进服务。",
    "撤销放弃",
    { type: "warning" }
  );
  await VipServiceAPI.restorePlanItem(detail.value.id, row.id, { reason: "撤销放弃" });
  ElMessage.success("已撤销，节点恢复为待处理");
  await loadServicePlan(detail.value.id);
}

function openContractDetail(row: ServiceContractRecord) {
  selectedContract.value = row;
  contractDetailVisible.value = true;
}

function certificationMaterialsByItem(itemCode: string) {
  return certifications.value.filter((item) => item.item_code === itemCode);
}

function latestCertificationMaterial(itemCode: string) {
  return certificationMaterialsByItem(itemCode)[0];
}

function uploadButtonText(itemCode: string) {
  return latestCertificationMaterial(itemCode)?.certification_record_status === "rejected" ? "重新上传" : "上传";
}

function canUploadCertificationMaterial(itemCode: string) {
  return latestCertificationMaterial(itemCode)?.certification_record_status !== "approved";
}

function materialStatusLabel(value?: string) {
  return ({ pending_review: "审核中", approved: "已通过", rejected: "已驳回", not_submitted: "未提交" } as Record<string, string>)[value || ""] || value || "-";
}

function materialStatusType(value?: string) {
  if (value === "approved") return "success";
  if (value === "rejected") return "danger";
  return "warning";
}

function canDeleteCertificationMaterial(material: ServiceCertification) {
  return material.certification_record_status !== "approved";
}

function idCardOcrResult(material: ServiceCertification): IdCardOcrResult | undefined {
  return material.ocr_result || (material.payload?.ocr_result as IdCardOcrResult | undefined);
}

function idCardSideLabel(value?: string) {
  return ({ front: "人像面", back: "国徽面", unknown: "未识别" } as Record<string, string>)[value || ""] || value || "-";
}

function isContractImageAttachment(file: Record<string, unknown>) {
  const type = String(file.file_type || "").toLowerCase();
  const url = String(file.file_url || "").split("?")[0].toLowerCase();
  return type === "image" || /\.(png|jpe?g|gif|webp|bmp|svg)$/.test(url);
}

async function uploadCertificationMaterial(options: UploadRequestOptions, item: ServiceCertificationArchiveItem) {
  if (!detail.value?.id) return;
  const fileInfo = await uploadImageDirect(options.file, "certification_material");
  const response = await VipServiceAPI.saveCertificationMaterial(detail.value.id, {
    item_code: item.item_code,
    item_name: item.item_name,
    material_type: "image",
    file_name: options.file.name,
    file_path: fileInfo.file_path,
    file_url: fileInfo.file_url,
  });
  certifications.value = [response.data.data, ...certifications.value];
  const ocr = idCardOcrResult(response.data.data);
  ElMessage.success(ocr?.message || "认证资料已存档");
}

async function deleteCertificationMaterial(material?: ServiceCertification) {
  if (!detail.value?.id || !material?.id) return;
  if (material.certification_record_status === "approved") {
    ElMessage.warning("已通过审核的认证资料不能删除");
    return;
  }
  await ElMessageBox.confirm("确认删除这张认证资料图片？未通过前删除会同步撤销该认证审核。", "删除认证资料", { type: "warning" });
  await VipServiceAPI.deleteCertificationMaterial(detail.value.id, material.id);
  certifications.value = certifications.value.filter((item) => item.id !== material.id);
  ElMessage.success("认证资料已删除，相关审核已撤销");
}

async function uploadProfilePhoto(options: UploadRequestOptions) {
  const fileInfo = await uploadImageDirect(options.file, "crm_lead_photo");
  const current = profilePhotoFileList.value.find((item) => item.uid === options.file.uid);
  if (current) {
    current.name = fileInfo.file_name || fileInfo.origin_name || options.file.name;
    current.url = fileInfo.file_url;
  }
  options.onSuccess?.(fileInfo);
}

function removeProfilePhoto(file: UploadFile) {
  profilePhotoFileList.value = profilePhotoFileList.value.filter((item) => item.uid !== file.uid && item.url !== file.url);
}

async function loadMatchmakers(storeId?: number) {
  matchmakerOptions.value = [];
  if (!storeId) return;
  const response = await VipServiceAPI.listMatchmakers(storeId);
  matchmakerOptions.value = response.data.data || [];
}

async function openAssign(row: ServiceCaseTable) {
  currentRow.value = row;
  assignMode.value = "assign";
  Object.assign(assignForm, { service_owner_user_id: undefined, remark: undefined });
  await loadMatchmakers(row.store_id);
  assignVisible.value = true;
}

async function openTransfer(row: ServiceCaseTable) {
  currentRow.value = row;
  assignMode.value = "transfer";
  Object.assign(assignForm, { service_owner_user_id: undefined, remark: undefined });
  await loadMatchmakers(row.store_id);
  assignVisible.value = true;
}

async function submitAssign() {
  const valid = await assignFormRef.value?.validate();
  if (!valid || !currentRow.value?.id) return;
  await ElMessageBox.confirm(`确认${assignMode.value === "assign" ? "分配" : "改派"}该服务工单？`, "操作确认", { type: "warning" });
  submitLoading.value = true;
  try {
    if (assignMode.value === "assign") {
      await VipServiceAPI.assignVip(currentRow.value.id, assignForm);
      ElMessage.success("服务工单已分配");
    } else {
      await VipServiceAPI.transferVip(currentRow.value.id, assignForm);
      ElMessage.success("服务工单已改派");
    }
    assignVisible.value = false;
    await fetchList();
  } finally {
    submitLoading.value = false;
  }
}

function openInterview() {
  if (!canOperateService.value) {
    ElMessage.warning("服务工单分配后才可以新增深访");
    return;
  }
  Object.assign(interviewForm, { interview_type: "first", interviewed_at: undefined, content: "", keywords: [], summary: undefined });
  interviewVisible.value = true;
}

async function submitInterview() {
  const valid = await interviewFormRef.value?.validate();
  if (!valid || !detail.value?.id) return;
  submitLoading.value = true;
  try {
    await VipServiceAPI.createInterview(detail.value.id, interviewForm);
    ElMessage.success("深访记录已保存");
    interviewVisible.value = false;
    await openDetail(detail.value.id);
  } finally {
    submitLoading.value = false;
  }
}

function openUsage() {
  if (!canOperateService.value) {
    ElMessage.warning("服务工单分配后才可以新增核销");
    return;
  }
  Object.assign(usageForm, { entitlement_id: undefined, quantity: 1, occurred_at: undefined, title: undefined, content: undefined, candidate_person_id: undefined, overuse_reason: undefined });
  candidateOptions.value = [];
  usageVisible.value = true;
}

function openProcessRecord() {
  if (!canOperateService.value) {
    ElMessage.warning("服务工单分配后才可以新增过程记录");
    return;
  }
  Object.assign(processForm, {
    record_type: "service_communication",
    occurred_at: undefined,
    method: undefined,
    result: undefined,
    content: "",
    next_follow_at: undefined,
    scheduled_at: undefined,
    appointment_slot: undefined,
    visit_purpose: undefined,
    need_summary: undefined,
    intention_level: undefined,
    next_action: undefined,
    enter_signing: undefined,
  });
  processVisible.value = true;
}

function openAppointment() {
  if (!canOperateService.value) {
    ElMessage.warning("服务工单分配后才可以邀约到店");
    return;
  }
  Object.assign(appointmentForm, {
    record_type: "appointment",
    scheduled_at: undefined,
    appointment_slot: undefined,
    visit_purpose: undefined,
    promised_gift: undefined,
    content: "",
    need_summary: undefined,
    next_follow_at: undefined,
  });
  appointmentVisible.value = true;
}

async function openProfileEdit() {
  if (!canEditProfile.value) {
    ElMessage.warning("当前服务状态不能编辑客户资料");
    return;
  }
  if (!detail.value?.id) return;
  if (!customerProfile.value) {
    const response = await VipServiceAPI.getCustomerProfile(detail.value.id);
    customerProfile.value = response.data.data;
  }
  const profile = customerProfile.value;
  if (!profile) return;
  Object.assign(profileForm, {
    mobile: profile.mobile || "",
    name: profile.name || "",
    gender: profile.gender || "2",
    wechat: profile.wechat || undefined,
    birth_date: profile.birth_date || undefined,
    height_cm: profile.height_cm,
    weight_kg: profile.weight_kg,
    ethnicity: profile.ethnicity || undefined,
    occupation: profile.occupation || undefined,
    occupation_code: profile.occupation_code || undefined,
    annual_income: profile.annual_income || undefined,
    marital_status: profile.marital_status || undefined,
    education: profile.education || undefined,
    graduated_school: profile.graduated_school || undefined,
    major: profile.major || undefined,
    unit_type: profile.unit_type || undefined,
    job_title: profile.job_title || undefined,
    work_company: profile.work_company || undefined,
    hometown: profile.hometown || undefined,
    residence: profile.residence || undefined,
    house_status: profile.house_status || undefined,
    car_status: profile.car_status || undefined,
    accept_long_distance_self: profile.accept_long_distance_self ?? null,
    accept_flash_marriage: profile.accept_flash_marriage ?? null,
    willing_relocate: profile.willing_relocate ?? null,
    marriage_plan: profile.marriage_plan || undefined,
    family_background: profile.family_background || undefined,
    profile_remark: profile.profile_remark || undefined,
    photo_urls: profile.photo_urls || [],
    profile_intro: profile.profile_intro || undefined,
    id_card_no: profile.id_card_no || undefined,
    current_stage: profile.current_stage || undefined,
    next_follow_at: profile.next_follow_at || undefined,
    partner_preference: profile.partner_preference || null,
  });
  profilePhotoFileList.value = (profile.photo_urls || []).map((url, index) => ({
    name: url.split("/").pop() || `photo-${index + 1}`,
    url,
  }));
  profileEditVisible.value = true;
}

async function submitProfileEdit() {
  const valid = await profileFormRef.value?.validate();
  if (!valid || !detail.value?.id) return;
  submitLoading.value = true;
  try {
    profileForm.partner_preference = preferenceFormRef.value?.getValue() || profileForm.partner_preference || null;
    profileForm.photo_urls = profilePhotoFileList.value.map((item) => item.url).filter((url): url is string => Boolean(url));
    const response = await VipServiceAPI.updateCustomerProfile(detail.value.id, profileForm);
    customerProfile.value = response.data.data;
    profileEditVisible.value = false;
    lifecycleRows.value = [];
    timelineRows.value = [];
    await loadWorkSummary(detail.value.id);
    ElMessage.success("客户资料已保存");
  } finally {
    submitLoading.value = false;
  }
}

async function submitProcessRecord() {
  const valid = await processFormRef.value?.validate();
  if (!valid || !detail.value?.id) return;
  submitLoading.value = true;
  try {
    await VipServiceAPI.createCustomerProcessRecord(detail.value.id, processForm);
    ElMessage.success("过程记录已保存");
    processVisible.value = false;
    timelineRows.value = [];
    await loadWorkSummary(detail.value.id);
    if (detailTab.value === "timeline") {
      await handleDetailTabChange("timeline");
    }
  } finally {
    submitLoading.value = false;
  }
}

async function submitAppointment() {
  const valid = await appointmentFormRef.value?.validate();
  if (!valid || !detail.value?.id) return;
  submitLoading.value = true;
  try {
    const serviceCaseId = detail.value.id;
    await VipServiceAPI.createAppointment(serviceCaseId, appointmentForm);
    ElMessage.success("服务邀约已保存");
    appointmentVisible.value = false;
    timelineRows.value = [];
    const response = await VipServiceAPI.detailVip(serviceCaseId);
    detail.value = response.data.data;
    await loadWorkSummary(serviceCaseId);
    if (detailTab.value === "timeline") {
      await handleDetailTabChange("timeline");
    }
  } finally {
    submitLoading.value = false;
  }
}

function handleUsageEntitlementChange() {
  usageForm.candidate_person_id = undefined;
}

async function searchCandidates(keyword: string) {
  candidateLoading.value = true;
  try {
    const res = await CandidateAPI.listCandidate({ page_no: 1, page_size: 20, keyword, mine: true });
    candidateOptions.value = res.data.data.items || [];
  } finally {
    candidateLoading.value = false;
  }
}

async function submitUsage() {
  const valid = await usageFormRef.value?.validate();
  if (!valid || !detail.value?.id) return;
  const entitlement = selectedEntitlement.value;
  if (entitlement && entitlement.remaining_quota - usageForm.quantity < 0 && !usageForm.overuse_reason) {
    ElMessage.warning("超额核销必须填写超额原因");
    return;
  }
  submitLoading.value = true;
  try {
    await VipServiceAPI.createUsage(detail.value.id, usageForm);
    ElMessage.success("权益核销已保存");
    usageVisible.value = false;
    await openDetail(detail.value.id);
    await fetchList();
  } finally {
    submitLoading.value = false;
  }
}

async function voidUsage(row: UsageRecord) {
  if (!detail.value?.id) return;
  const { value } = await ElMessageBox.prompt("请填写作废原因", "作废核销", { inputType: "textarea", inputValidator: (val) => !!val || "作废原因必填" });
  await VipServiceAPI.voidUsage(detail.value.id, row.id, { reason: value });
  ElMessage.success("核销记录已作废");
  await openDetail(detail.value.id);
  await fetchList();
}

function openClose(row: ServiceCaseTable) {
  currentRow.value = row;
  closeForm.reason = "";
  closeVisible.value = true;
}

async function submitClose() {
  const valid = await closeFormRef.value?.validate();
  if (!valid || !currentRow.value?.id) return;
  submitLoading.value = true;
  try {
    await VipServiceAPI.applyClose(currentRow.value.id, closeForm);
    ElMessage.success("关单申请已提交");
    closeVisible.value = false;
    await fetchList();
  } finally {
    submitLoading.value = false;
  }
}

function openReview(row: ServiceCaseTable) {
  currentRow.value = row;
  reviewForm.review_remark = "";
  reviewVisible.value = true;
}

async function submitReview(approved: boolean) {
  if (!currentRow.value?.id) return;
  submitLoading.value = true;
  try {
    await VipServiceAPI.reviewClose(currentRow.value.id, { approved, review_remark: reviewForm.review_remark });
    ElMessage.success("关单审核已处理");
    reviewVisible.value = false;
    await fetchList();
  } finally {
    submitLoading.value = false;
  }
}

watch(
  () => route.path,
  () => {
    syncTabByRoute();
    fetchList();
  }
);

onMounted(async () => {
  syncTabByRoute();
  if (canManageService.value) {
    await Promise.all([loadDicts(), loadDeptOptions()]);
  } else {
    await loadDicts();
  }
  await fetchList();
});
</script>

<style scoped>
.service-workbench {
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

.table-actions,
.detail-actions {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  white-space: nowrap;
}

.detail-actions {
  margin-bottom: 12px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  padding-top: 16px;
}

.match-point-tag {
  margin: 2px 4px 2px 0;
}

.summary {
  margin-bottom: 18px;
}

.tab-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

.profile-grid {
  display: grid;
  grid-template-columns: minmax(180px, 240px) 1fr;
  gap: 16px;
  align-items: stretch;
}

.candidate-profile-grid {
  display: grid;
  grid-template-columns: minmax(220px, 280px) 1fr;
  gap: 16px;
  align-items: start;
}

.profile-side {
  min-height: 260px;
}

.avatar-carousel,
.avatar-photo,
.avatar-empty {
  width: 100%;
  height: 260px;
  border-radius: 6px;
}

.avatar-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px dashed var(--el-border-color);
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color-light);
}

.profile-desc {
  min-width: 0;
}

.section-title {
  margin: 20px 0 12px;
  color: var(--el-text-color-primary);
  font-size: 15px;
  font-weight: 600;
}

.quota-line {
  font-size: 13px;
  white-space: nowrap;
}

.json-block {
  margin: 0;
  padding: 12px;
  overflow: auto;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  color: var(--el-text-color-regular);
  background: var(--el-fill-color-light);
  font-size: 13px;
  line-height: 1.6;
}

.cert-material-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 14px;
  margin-top: 14px;
}

.cert-material-card {
  padding: 14px;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
}

.cert-material-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.cert-material-title {
  color: var(--el-text-color-primary);
  font-weight: 600;
}

.cert-material-desc,
.cert-material-meta {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.cert-material-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.cert-material-image {
  width: 96px;
  height: 96px;
  border-radius: 6px;
}

.cert-material-meta {
  width: 96px;
  line-height: 1.5;
}

.cert-ocr-result {
  width: 96px;
  margin-top: 8px;
  padding: 8px;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.6;
  overflow-wrap: anywhere;
  background: var(--el-fill-color-light);
  color: var(--el-text-color-regular);
}

.cert-ocr-result.is-success {
  background: var(--el-color-success-light-9);
  color: var(--el-color-success-dark-2);
}

.cert-ocr-result.is-failed {
  background: var(--el-color-warning-light-9);
  color: var(--el-color-warning-dark-2);
}

.cert-review-result {
  width: 96px;
  margin-top: 8px;
  padding: 8px;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.6;
  overflow-wrap: anywhere;
}

.cert-review-result.is-rejected {
  background: var(--el-color-danger-light-9);
  color: var(--el-color-danger-dark-2);
}

.attachment-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 10px;
  margin-top: 10px;
}

.attachment-item {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  align-items: center;
  gap: 10px;
  padding: 8px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
}

.attachment-thumb,
.attachment-file {
  width: 72px;
  height: 72px;
  border-radius: 4px;
  background: var(--el-fill-color-light);
}

.attachment-file {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--el-text-color-secondary);
  font-size: 28px;
}

.attachment-meta {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.attachment-meta .el-link {
  justify-content: flex-start;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.match-filter-form {
  margin: 10px 0 12px;
  padding: 12px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  background: var(--el-fill-color-lighter);
}

.match-filter-tip {
  margin-top: 10px;
}

.match-filter-form .el-select,
.match-filter-form .el-input {
  width: 100%;
}

.match-filter-form .el-input-number {
  width: 92px;
}

.section-subtitle {
  margin: 4px 0 10px;
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.range-sep {
  display: inline-block;
  width: 12px;
  text-align: center;
  color: var(--el-text-color-secondary);
}

.drawer-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  gap: 16px;
}

.drawer-title {
  color: var(--el-text-color-primary);
  font-size: 18px;
  font-weight: 600;
}

.drawer-subtitle {
  margin-top: 4px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.drawer-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.quality-inline {
  display: flex;
  align-items: center;
  gap: 24px;
}

.quality-meta {
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: var(--el-text-color-regular);
}

.relation-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 14px;
}

.relation-card {
  min-width: 0;
}

.timeline-title {
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.timeline-content,
.muted {
  margin-top: 4px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.photo-list,
.risk-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 12px;
}

.photo-item {
  width: 120px;
  height: 120px;
  border-radius: 6px;
}

.mt12 {
  margin-top: 12px;
}

@media (max-width: 900px) {
  .profile-grid,
  .candidate-profile-grid {
    grid-template-columns: 1fr;
  }
}
</style>
