<template>
  <div class="app-container customer-page">
    <el-card shadow="never" class="filter-card">
      <el-form :model="query" inline>
        <el-form-item label="关键词">
          <el-input v-model="query.keyword" clearable placeholder="编号/姓名/手机号" @keyup.enter="fetchList" />
        </el-form-item>
        <el-form-item label="当前阶段">
          <el-select v-model="query.current_stage" clearable placeholder="全部" style="width: 150px">
            <el-option v-for="item in stageOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="最高进展">
          <el-select v-model="query.max_stage" clearable placeholder="全部" style="width: 150px">
            <el-option v-for="item in stageOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="门店">
          <el-select v-model="query.store_id" clearable filterable placeholder="全部" style="width: 180px">
            <el-option v-for="item in deptOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="归属人">
          <el-select v-model="query.owner_user_id" clearable filterable placeholder="全部" style="width: 160px">
            <el-option v-for="item in userOptions" :key="item.value" :label="item.label" :value="item.value" />
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
          <div class="toolbar-title">{{ isDealPage ? "成交客户" : "客户列表" }}</div>
          <div class="toolbar-note">{{ isDealPage ? "展示已成交并转入 VIP 的客户，支持后续续费和加购" : "仅展示当前处于客户运营阶段的建档客户" }}</div>
        </div>
      </template>

      <el-table v-loading="loading" :data="rows" border stripe row-key="id">
        <el-table-column label="客户编号" width="110">
          <template #default="{ row }">{{ row.person?.display_no || "-" }}</template>
        </el-table-column>
        <el-table-column label="姓名" min-width="110">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row.id)">{{ row.person?.name || "-" }}</el-button>
          </template>
        </el-table-column>
        <el-table-column label="性别" width="80">
          <template #default="{ row }">{{ genderLabel(row.person?.gender) }}</template>
        </el-table-column>
        <el-table-column prop="age" label="年龄" width="80" />
        <el-table-column label="手机号" min-width="140">
          <template #default="{ row }">{{ row.mobile_masked || row.person?.primary_mobile || "-" }}</template>
        </el-table-column>
        <el-table-column label="当前阶段" min-width="120">
          <template #default="{ row }"><el-tag>{{ stageLabel(row.current_stage) }}</el-tag></template>
        </el-table-column>
        <el-table-column label="最高进展" min-width="120">
          <template #default="{ row }"><el-tag type="success">{{ stageLabel(row.max_stage) }}</el-tag></template>
        </el-table-column>
        <el-table-column label="归属门店" min-width="140">
          <template #default="{ row }">{{ row.store?.name || "-" }}</template>
        </el-table-column>
        <el-table-column label="归属人" min-width="120">
          <template #default="{ row }">{{ row.owner_user?.name || "-" }}</template>
        </el-table-column>
        <el-table-column prop="latest_follow_at" label="最近跟进" min-width="170" />
        <el-table-column prop="next_follow_at" label="下次跟进" min-width="170" />
        <el-table-column prop="created_time" label="建档时间" min-width="170" />
        <el-table-column fixed="right" label="操作" width="290">
          <template #default="{ row }">
            <div class="table-actions">
              <el-button v-hasPerm="['crm:customer:detail']" link type="primary" icon="View" @click="openDetail(row.id)">详情</el-button>
              <el-button v-if="isDealPage" v-hasPerm="['crm:contract:create']" link type="success" icon="DocumentAdd" @click="createContract(row.id)">新增合同</el-button>
              <el-button v-else v-hasPerm="['crm:customer:follow']" link type="primary" icon="ChatDotRound" @click="openProcess(row.id, 'follow')">跟进</el-button>
              <el-dropdown v-if="!isDealPage" trigger="click">
                <el-button link type="primary" icon="ArrowDown">更多</el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item v-hasPerm="['crm:customer:transfer']" @click="openTransfer(row)">转派/转交</el-dropdown-item>
                    <el-dropdown-item v-hasPerm="['crm:customer:follow']" @click="openReturnLead(row)">退回线索</el-dropdown-item>
                    <el-dropdown-item v-hasPerm="['crm:customer:print']" @click="openPrint(row.id)">打印资料卡</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
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

    <el-drawer v-model="detailVisible" size="82%" destroy-on-close class="customer-drawer">
      <template #header>
        <div class="drawer-head">
          <div>
            <div class="drawer-title">{{ detail?.person?.name || "客户总档案" }}</div>
            <div class="drawer-subtitle">客户编号：{{ detail?.person?.display_no || "-" }} · {{ stageLabel(detail?.current_stage) }}</div>
          </div>
          <div class="drawer-actions">
            <el-button v-hasPerm="['crm:customer:print']" icon="Printer" @click="detail?.id && openPrint(detail.id)">打印资料卡</el-button>
            <el-button v-if="readOnly" v-hasPerm="['crm:customer:update']" type="primary" icon="Edit" @click="enableEdit">编辑资料</el-button>
            <el-button v-else icon="Close" @click="cancelEdit">取消编辑</el-button>
          </div>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="概览" name="overview">
          <div v-if="detail" class="overview-grid">
            <div class="profile-side">
              <el-carousel v-if="detail.person.photo_urls?.length" class="avatar-carousel" indicator-position="outside" arrow="hover" trigger="click">
                <el-carousel-item v-for="url in detail.person.photo_urls" :key="url">
                  <el-image class="avatar-photo" :src="ossImage(url, { w: 360, h: 480 })" fit="cover" :preview-src-list="ossImageList(detail.person.photo_urls, { w: 1600 })" preview-teleported />
                </el-carousel-item>
              </el-carousel>
              <div v-else class="avatar-empty">暂无照片</div>
            </div>
            <el-descriptions :column="3" border class="overview-desc">
              <el-descriptions-item label="客户编号">{{ detail.person.display_no || "-" }}</el-descriptions-item>
              <el-descriptions-item label="姓名">{{ detail.person.name || "-" }}</el-descriptions-item>
              <el-descriptions-item label="手机号">{{ detail.mobile_masked || "-" }}</el-descriptions-item>
              <el-descriptions-item label="当前阶段">{{ stageLabel(detail.current_stage) }}</el-descriptions-item>
              <el-descriptions-item label="最高进展">{{ stageLabel(detail.max_stage) }}</el-descriptions-item>
              <el-descriptions-item label="归属人">{{ detail.owner_user?.name || "-" }}</el-descriptions-item>
              <el-descriptions-item label="最近跟进">{{ detail.latest_follow_at || "-" }}</el-descriptions-item>
              <el-descriptions-item label="下次跟进">{{ detail.next_follow_at || "-" }}</el-descriptions-item>
              <el-descriptions-item label="建档时间">{{ detail.created_time || "-" }}</el-descriptions-item>
              <el-descriptions-item label="个人介绍" :span="3">{{ detail.person.profile_intro || "-" }}</el-descriptions-item>
              <el-descriptions-item label="觅AI印象" :span="3">{{ detail.ai_profile?.profile?.content || "暂无觅AI印象" }}</el-descriptions-item>
            </el-descriptions>
          </div>
        </el-tab-pane>

        <el-tab-pane label="基本资料" name="profile">
          <template v-if="detail && readOnly">
            <el-descriptions :column="3" border>
              <el-descriptions-item label="姓名">{{ detail.person.name || "-" }}</el-descriptions-item>
              <el-descriptions-item label="性别">{{ genderLabel(detail.person.gender) }}</el-descriptions-item>
              <el-descriptions-item label="手机号">{{ detail.person.primary_mobile || "-" }}</el-descriptions-item>
              <el-descriptions-item label="微信号">{{ detail.person.wechat || "-" }}</el-descriptions-item>
              <el-descriptions-item label="年龄">{{ detail.age ? `${detail.age}岁` : "-" }}</el-descriptions-item>
              <el-descriptions-item label="星座">{{ detail.constellation || "-" }}</el-descriptions-item>
              <el-descriptions-item label="生肖">{{ detail.zodiac || "-" }}</el-descriptions-item>
              <el-descriptions-item label="出生日期">{{ detail.person.birth_date || "-" }}</el-descriptions-item>
              <el-descriptions-item label="身高">{{ detail.person.height_cm ? `${detail.person.height_cm} cm` : "-" }}</el-descriptions-item>
              <el-descriptions-item label="体重">{{ detail.person.weight_kg ? `${detail.person.weight_kg} kg` : "-" }}</el-descriptions-item>
              <el-descriptions-item label="民族">{{ optionLabel(dictOptions.ethnicity, detail.person.ethnicity) }}</el-descriptions-item>
              <el-descriptions-item label="职业">{{ optionLabel(dictOptions.occupation, detail.person.occupation_code) || detail.person.occupation || "-" }}</el-descriptions-item>
              <el-descriptions-item label="年收入">{{ optionLabel(dictOptions.annualIncome, detail.person.annual_income) }}</el-descriptions-item>
              <el-descriptions-item label="婚况">{{ optionLabel(dictOptions.maritalStatus, detail.person.marital_status) }}</el-descriptions-item>
              <el-descriptions-item label="学历">{{ optionLabel(dictOptions.education, detail.person.education) }}</el-descriptions-item>
              <el-descriptions-item label="毕业院校">{{ detail.person.graduated_school || "-" }}</el-descriptions-item>
              <el-descriptions-item label="专业">{{ detail.person.major || "-" }}</el-descriptions-item>
              <el-descriptions-item label="单位类型">{{ optionLabel(dictOptions.unitType, detail.person.unit_type) }}</el-descriptions-item>
              <el-descriptions-item label="职务">{{ detail.person.job_title || "-" }}</el-descriptions-item>
              <el-descriptions-item label="工作单位">{{ detail.person.work_company || "-" }}</el-descriptions-item>
              <el-descriptions-item label="籍贯">{{ detail.person.hometown || "-" }}</el-descriptions-item>
              <el-descriptions-item label="常驻地">{{ detail.person.residence || "-" }}</el-descriptions-item>
              <el-descriptions-item label="房产信息">{{ optionLabel(dictOptions.houseStatus, detail.person.house_status) }}</el-descriptions-item>
              <el-descriptions-item label="购车信息">{{ optionLabel(dictOptions.carStatus, detail.person.car_status) }}</el-descriptions-item>
              <el-descriptions-item label="接受异地">{{ boolLabel(detail.person.accept_long_distance_self) }}</el-descriptions-item>
              <el-descriptions-item label="接受闪婚">{{ boolLabel(detail.person.accept_flash_marriage) }}</el-descriptions-item>
              <el-descriptions-item label="愿意搬家">{{ boolLabel(detail.person.willing_relocate) }}</el-descriptions-item>
              <el-descriptions-item label="结婚计划">{{ optionLabel(dictOptions.marriagePlan, detail.person.marriage_plan) }}</el-descriptions-item>
              <el-descriptions-item label="身份证号">{{ detail.id_card_no_masked || "-" }}</el-descriptions-item>
              <el-descriptions-item label="家庭情况" :span="3">{{ detail.person.family_background || "-" }}</el-descriptions-item>
              <el-descriptions-item label="备注" :span="3">{{ detail.person.profile_remark || "-" }}</el-descriptions-item>
              <el-descriptions-item label="个人介绍" :span="3">{{ detail.person.profile_intro || "-" }}</el-descriptions-item>
            </el-descriptions>
            <div class="photo-list">
              <el-image v-for="url in detail.person.photo_urls || []" :key="url" class="photo-item" :src="ossImage(url, { w: 120, h: 120 })" :preview-src-list="ossImageList(detail.person.photo_urls, { w: 1600 })" fit="cover" preview-teleported />
            </div>
          </template>

          <el-form v-else ref="formRef" :model="form" :rules="rules" label-width="92px" class="profile-form">
            <person-profile-fields :form="form" :dict-options="dictOptions" mobile-disabled>
              <template #photo>
                <el-form-item label="照片">
                  <el-upload v-model:file-list="photoFileList" list-type="picture-card" accept="image/*" multiple :http-request="uploadPhoto" :on-remove="removePhoto">
                    <el-icon><Plus /></el-icon>
                  </el-upload>
                </el-form-item>
              </template>
            </person-profile-fields>
            <div class="form-section">
              <div class="section-title">客户经营</div>
              <el-row :gutter="16">
                <el-col :xs="24" :md="8">
                  <el-form-item label="当前阶段">
                    <el-select v-model="form.current_stage" style="width: 100%">
                      <el-option v-for="item in stageOptions" :key="item.value" :label="item.label" :value="item.value" />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>
            </div>
            <div class="save-bar">
              <el-button type="primary" icon="Check" @click="submitProfile">保存客户资料</el-button>
            </div>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="认证资料" name="certification">
          <el-alert title="认证结果为认证事实，只读展示；红娘可在此收集和存档认证资料图片，不影响认证结果。" type="info" show-icon :closable="false" />
          <el-descriptions v-if="detail" :column="2" border class="mt12">
            <el-descriptions-item label="认证等级">{{ detail.person.certification_level || "none" }}</el-descriptions-item>
            <el-descriptions-item label="身份证号">{{ detail.id_card_no_masked || "-" }}</el-descriptions-item>
            <el-descriptions-item label="认证摘要" :span="2">{{ jsonText(detail.person.certification_summary) }}</el-descriptions-item>
          </el-descriptions>
          <div v-if="detail" class="cert-material-grid">
            <div v-for="item in certificationArchiveItems" :key="item.item_code" class="cert-material-card">
              <div class="cert-material-head">
                <div>
                  <div class="cert-material-title">{{ item.item_name }}</div>
                  <div class="cert-material-desc">{{ item.material_desc || "资料图片存档" }}</div>
                </div>
                <el-upload
                  v-hasPerm="['crm:customer:update']"
                  accept="image/*"
                  :show-file-list="false"
                  :http-request="(options) => uploadCertificationMaterial(options, item)"
                >
                  <el-button link type="primary" icon="Upload">上传</el-button>
                </el-upload>
              </div>
              <div v-if="materialsByItem(item.item_code).length" class="cert-material-list">
                <div v-for="material in materialsByItem(item.item_code)" :key="material.id" class="cert-material-item">
                  <el-image class="cert-material-image" :src="ossImage(material.file_url, { w: 160, h: 160 })" :preview-src-list="ossImageList([material.file_url], { w: 1600 })" fit="cover" preview-teleported />
                  <div class="cert-material-meta">
                    <span>{{ material.created_time || material.file_name || "已上传" }}</span>
                    <el-button v-hasPerm="['crm:customer:update']" link type="danger" @click="deleteCertificationMaterial(material.id)">删除</el-button>
                  </div>
                </div>
              </div>
              <el-empty v-else description="暂无资料" :image-size="48" />
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="择偶要求" name="preference">
          <PartnerPreferenceForm ref="preferenceFormRef" :model-value="form.partner_preference || detail?.partner_preference" :dict-options="dictOptions" :region-options="[]" :read-only="readOnly" :show-actions="false" />
          <div v-if="!readOnly" class="save-bar">
            <el-button type="primary" icon="Check" @click="submitProfile">保存择偶要求</el-button>
          </div>
        </el-tab-pane>

        <el-tab-pane label="过程记录" name="process">
          <div class="process-toolbar">
            <el-button v-hasPerm="['crm:customer:follow']" type="primary" @click="detail?.id && openProcess(detail.id, 'follow')">写跟进</el-button>
          </div>
          <el-timeline>
            <el-timeline-item v-for="item in mergedProcess" :key="`${item.source}-${item.id}`" :timestamp="String(item.occurred_at || item.created_time || '')">
              <div class="timeline-title">{{ sourceLabel(item.source) }} · {{ operatorName(item) }} · {{ processTypeLabel(String(item.record_type || '')) }} · {{ processResultLabel(item) }}</div>
              <div class="timeline-content">{{ item.content }}</div>
              <div v-for="line in processExtraLines(item)" :key="line" class="timeline-extra">{{ line }}</div>
              <div v-if="item.next_follow_at" class="timeline-extra">下次跟进：{{ item.next_follow_at }}</div>
            </el-timeline-item>
          </el-timeline>
        </el-tab-pane>

        <el-tab-pane label="生命周期" name="lifecycle">
          <el-timeline>
            <el-timeline-item v-for="item in mergedLifecycle" :key="`${item.source}-${item.id}`" :timestamp="String(item.created_time || '')">
              <div class="timeline-title">{{ sourceLabel(item.source) }} · {{ operatorName(item) }} · {{ lifecycleLabel(String(item.operation_type || '')) }}</div>
              <div class="timeline-content">{{ item.remark || formatChange(item.change_detail as Record<string, unknown>, String(item.operation_type || '')) }}</div>
            </el-timeline-item>
          </el-timeline>
        </el-tab-pane>

        <el-tab-pane label="合同收款" name="contract">
          <div class="contract-tab-toolbar">
            <el-button v-hasPerm="['crm:contract:create']" type="primary" icon="Plus" @click="goContractCreate">去合同管理创建合同</el-button>
          </div>
          <el-table :data="customerContracts" border size="small">
            <el-table-column prop="contract_no" label="合同编号" min-width="170" show-overflow-tooltip />
            <el-table-column prop="contract_name" label="合同名称" min-width="150" show-overflow-tooltip />
            <el-table-column label="合同金额" width="110">
              <template #default="{ row }">¥{{ Number(row.contract_amount || 0).toFixed(2) }}</template>
            </el-table-column>
            <el-table-column label="已收金额" min-width="170">
              <template #default="{ row }">
                <div class="payment-progress">
                  <div class="payment-progress__text">¥{{ Number(row.received_amount || 0).toFixed(2) }} / ¥{{ Number(row.contract_amount || 0).toFixed(2) }} · {{ progressPercent(row.payment_progress) }}%</div>
                  <el-progress :percentage="progressPercent(row.payment_progress)" :stroke-width="6" :show-text="false" />
                </div>
              </template>
            </el-table-column>
            <el-table-column label="支付状态" width="100">
              <template #default="{ row }">{{ paymentStatusLabel(row.payment_status) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">{{ contractStatusLabel(row.contract_status) }}</template>
            </el-table-column>
            <el-table-column label="有效期限" min-width="180">
              <template #default="{ row }">{{ row.validity_period || `${row.start_date} 至 ${row.end_date}` }}</template>
            </el-table-column>
            <el-table-column label="收款" min-width="180">
              <template #default="{ row }">
                <span v-if="!row.receipts?.length">暂无</span>
                <span v-else>{{ formatContractReceipts(row.receipts) }}</span>
              </template>
            </el-table-column>
            <el-table-column fixed="right" label="操作" width="110">
              <template #default="{ row }">
                <el-button link type="primary" @click="goContractDetail(row.id)">查看合同</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-drawer>

    <el-dialog v-model="processVisible" title="写跟进" width="620px">
      <el-form :model="processForm" label-width="96px">
        <el-form-item label="跟进方式" required>
          <el-select v-model="processForm.method" style="width: 100%">
            <el-option v-for="item in dictOptions.followMethod" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="常用语">
          <el-select placeholder="选择后填入内容" clearable style="width: 100%" @change="applyPhrase">
            <el-option v-for="item in dictOptions.followPhrase" :key="item.value" :label="item.label" :value="item.label" />
          </el-select>
        </el-form-item>
        <el-form-item label="内容" required><el-input v-model="processForm.content" type="textarea" :rows="4" /></el-form-item>
        <template v-if="processForm.method === 'appointment'">
          <el-form-item label="预约日期" required><el-date-picker v-model="processForm.scheduled_at" type="date" value-format="YYYY-MM-DD" style="width: 100%" /></el-form-item>
          <el-form-item label="预约时段"><el-select v-model="processForm.appointment_slot" clearable style="width: 100%"><el-option v-for="item in dictOptions.appointmentSlot" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
          <el-form-item label="到访目的"><el-select v-model="processForm.visit_purpose" clearable style="width: 100%"><el-option v-for="item in dictOptions.visitPurpose" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
          <el-form-item label="承诺礼品"><el-input v-model="processForm.promised_gift" clearable /></el-form-item>
        </template>
        <template v-if="processForm.method === 'consultation'">
          <el-form-item label="需求摘要"><el-input v-model="processForm.need_summary" type="textarea" :rows="2" /></el-form-item>
          <el-form-item label="预算区间"><el-input v-model="processForm.budget_range" /></el-form-item>
          <el-form-item label="主要异议"><el-input v-model="processForm.main_objection" type="textarea" :rows="2" /></el-form-item>
          <el-form-item label="意向等级"><el-select v-model="processForm.intention_level" clearable style="width: 100%"><el-option v-for="item in dictOptions.intentionLevel" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
          <el-form-item label="进入签约推进"><el-switch v-model="processForm.enter_signing" /></el-form-item>
        </template>
        <el-form-item label="下次跟进"><el-date-picker v-model="processForm.next_follow_at" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width: 100%" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="processVisible = false">取消</el-button>
        <el-button type="primary" @click="submitProcess">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="transferVisible" title="客户转派/转交" width="520px">
      <el-form :model="transferForm" label-width="90px">
        <el-form-item label="目标门店"><el-select v-model="transferForm.store_id" filterable clearable style="width: 100%"><el-option v-for="item in deptOptions" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
        <el-form-item label="目标归属人"><el-select v-model="transferForm.owner_user_id" filterable style="width: 100%"><el-option v-for="item in userOptions" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
        <el-form-item label="备注"><el-input v-model="transferForm.remark" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="transferVisible = false">取消</el-button>
        <el-button type="primary" @click="submitTransfer">确认</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="returnVisible" title="退回线索" width="520px">
      <el-form :model="returnForm" label-width="90px">
        <el-form-item label="原因分类" required><el-select v-model="returnForm.reason_type" style="width: 100%"><el-option v-for="item in returnReasonOptions" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
        <el-form-item label="说明" required><el-input v-model="returnForm.reason" type="textarea" :rows="4" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="returnVisible = false">取消</el-button>
        <el-button type="danger" @click="submitReturnLead">确认退回</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="printVisible" title="A4对外资料卡" width="860px" class="print-dialog">
      <div v-if="printCard" id="customer-print-card" class="print-card">
        <div class="watermark">{{ printCard.brand_name }}</div>
        <header class="print-header">
          <div>
            <div class="print-title">相亲资料卡</div>
            <div class="print-subtitle">{{ printCard.brand_name }}</div>
          </div>
          <div class="print-meta">打印时间：{{ printCard.printed_at }}</div>
        </header>
        <main class="print-body">
          <div class="print-photo-wrap">
            <img v-if="printCard.first_photo_url" class="print-photo" :src="ossImage(printCard.first_photo_url, { w: 420, h: 560 })" />
            <div v-else class="print-photo print-photo-empty">暂无照片</div>
          </div>
          <div class="print-info">
            <table>
              <tbody>
                <tr><th>姓名</th><td>{{ printCard.display_name }}</td><th>客户编号</th><td>{{ printCard.customer_no || "-" }}</td></tr>
                <tr><th>性别</th><td>{{ genderLabel(printCard.gender) }}</td><th>年龄</th><td>{{ printCard.age || "-" }}</td></tr>
                <tr><th>星座</th><td>{{ printCard.constellation || "-" }}</td><th>生肖</th><td>{{ printCard.zodiac || "-" }}</td></tr>
                <tr><th>身高</th><td>{{ printCard.height_cm ? `${printCard.height_cm} cm` : "-" }}</td><th>体重</th><td>{{ printCard.weight_kg ? `${printCard.weight_kg} kg` : "-" }}</td></tr>
                <tr><th>学历</th><td>{{ optionLabel(dictOptions.education, printCard.education) }}</td><th>毕业院校</th><td>{{ printCard.graduated_school || "-" }}</td></tr>
                <tr><th>专业</th><td>{{ printCard.major || "-" }}</td><th>职业</th><td>{{ optionLabel(dictOptions.occupation, printCard.occupation_code) || printCard.occupation || "-" }}</td></tr>
                <tr><th>单位类型</th><td>{{ optionLabel(dictOptions.unitType, printCard.unit_type) }}</td><th>职务</th><td>{{ printCard.job_title || "-" }}</td></tr>
                <tr><th>工作单位</th><td>{{ printCard.work_company || "-" }}</td><th>年收入</th><td>{{ optionLabel(dictOptions.annualIncome, printCard.annual_income) }}</td></tr>
                <tr><th>婚况</th><td>{{ optionLabel(dictOptions.maritalStatus, printCard.marital_status) }}</td><th>房产</th><td>{{ optionLabel(dictOptions.houseStatus, printCard.house_status) }}</td></tr>
                <tr><th>车辆</th><td>{{ optionLabel(dictOptions.carStatus, printCard.car_status) }}</td><th>常驻地</th><td>{{ printCard.residence || "-" }}</td></tr>
              </tbody>
            </table>
            <section><h4>个人介绍</h4><p>{{ printCard.profile_intro || "暂无" }}</p></section>
            <section><h4>家庭情况</h4><p>{{ printCard.family_background || "暂无" }}</p></section>
            <section><h4>择偶要求</h4><p>{{ printCard.partner_preference?.profile_summary || printCard.partner_preference?.preference_text || "暂无" }}</p></section>
            <section><h4>觅AI印象</h4><p>{{ printCard.miai_impression || "暂无" }}</p></section>
          </div>
        </main>
        <footer class="print-footer">本资料卡仅用于候选人沟通与外部宣传展示，已隐藏联系方式与实名敏感信息。</footer>
      </div>
      <template #footer>
        <el-button @click="printVisible = false">关闭</el-button>
        <el-button type="primary" icon="Printer" @click="printA4">打印</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from "element-plus";
import type { UploadFile, UploadRequestOptions } from "element-plus";
import { Plus } from "@element-plus/icons-vue";

import CustomerAPI, {
  type CustomerDetail,
  type CustomerCertificationArchiveItem,
  type CustomerCertificationMaterial,
  type CustomerForm,
  type CustomerPageQuery,
  type CustomerPrintCard,
  type CustomerProcessForm,
  type CustomerProcessType,
  type CustomerTable,
} from "@/api/module_crm/customer";
import ContractAPI, { type ContractTable } from "@/api/module_crm/contract";
import LeadAPI, { type PartnerPreference } from "@/api/module_crm/lead";
import DictAPI, { type DictDataTable } from "@/api/module_system/dict";
import PartnerPreferenceForm from "@/views/module_miailove/components/PartnerPreferenceForm.vue";
import PersonProfileFields from "@/views/module_miailove/components/PersonProfileFields.vue";
import { ossImage, ossImageList } from "@/utils/ossImage";
import { uploadImageDirect } from "@/utils/upload";

const loading = ref(false);
const rows = ref<CustomerTable[]>([]);
const total = ref(0);
const query = reactive<CustomerPageQuery>({ page_no: 1, page_size: 10 });
const route = useRoute();
const router = useRouter();
const isDealPage = computed(() => route.path.includes("/customer/deal"));
const detailVisible = ref(false);
const detail = ref<CustomerDetail>();
const activeTab = ref("overview");
const readOnly = ref(true);
const formRef = ref<FormInstance>();
const preferenceFormRef = ref<InstanceType<typeof PartnerPreferenceForm>>();
const photoFileList = ref<UploadFile[]>([]);
const processVisible = ref(false);
const processCustomerId = ref<number>();
const processType = ref<CustomerProcessType>("follow");
const transferVisible = ref(false);
const returnVisible = ref(false);
const printVisible = ref(false);
const printCard = ref<CustomerPrintCard>();
const customerContracts = ref<ContractTable[]>([]);

type TimelineItem = Record<string, unknown> & {
  id?: number | string;
  source: string;
  created_time?: string;
  operation_type?: string;
  remark?: string;
  change_detail?: Record<string, unknown>;
  operator_user_id?: number;
  operator_user_name?: string;
  created_by?: { name?: string };
};

type ProcessItem = Record<string, unknown> & {
  id?: number | string;
  source: string;
  created_time?: string;
  occurred_at?: string;
  record_type?: string;
  result?: string;
  content?: string;
  next_follow_at?: string;
  scheduled_at?: string;
  appointment_slot?: string;
  visit_purpose?: string;
  promised_gift?: string;
  appointment_status?: string;
  checked_in_at?: string;
  checked_in_user_name?: string;
  need_summary?: string;
  budget_range?: string;
  main_objection?: string;
  intention_level?: string;
  operator_user_id?: number;
  operator_user_name?: string;
  created_by?: { name?: string };
};

const deptOptions = ref<Array<{ label: string; value: number }>>([]);
const userOptions = ref<Array<{ label: string; value: number }>>([]);
const dictOptions = reactive({
  ethnicity: [] as Array<{ label: string; value: string }>,
  annualIncome: [] as Array<{ label: string; value: string }>,
  maritalStatus: [] as Array<{ label: string; value: string }>,
  education: [] as Array<{ label: string; value: string }>,
  houseStatus: [] as Array<{ label: string; value: string }>,
  carStatus: [] as Array<{ label: string; value: string }>,
  occupation: [] as Array<{ label: string; value: string }>,
  unitType: [] as Array<{ label: string; value: string }>,
  marriagePlan: [] as Array<{ label: string; value: string }>,
  followMethod: [] as Array<{ label: string; value: string }>,
  followPhrase: [] as Array<{ label: string; value: string }>,
  intentionLevel: [] as Array<{ label: string; value: string }>,
  visitPurpose: [] as Array<{ label: string; value: string }>,
  appointmentSlot: [] as Array<{ label: string; value: string }>,
  appointmentStatus: [] as Array<{ label: string; value: string }>,
  contractStatus: [] as Array<{ label: string; value: string }>,
  receiptStatus: [] as Array<{ label: string; value: string }>,
});

const stageOptions = [
  { label: "建档完善", value: "profiling" },
  { label: "跟进经营", value: "following" },
  { label: "已邀约", value: "appointed" },
  { label: "已到店", value: "visited" },
  { label: "已面谈", value: "consulted" },
  { label: "签约推进", value: "signing" },
  { label: "已签约待付款", value: "contracted" },
  { label: "已转VIP", value: "converted_vip" },
];

const returnReasonOptions = [
  { label: "无效客户", value: "invalid" },
  { label: "长期未响应", value: "no_response" },
  { label: "暂缓考虑", value: "not_ready" },
  { label: "预算不符", value: "budget_mismatch" },
  { label: "需求不匹配", value: "requirement_mismatch" },
  { label: "重复建档", value: "duplicate" },
  { label: "客户明确拒绝", value: "rejected" },
  { label: "其他", value: "other" },
];

const form = reactive<CustomerForm>({
  mobile: "",
  name: "",
  gender: "2",
  photo_urls: [],
});

const processForm = reactive<CustomerProcessForm>({
  content: "",
  enter_signing: false,
});

const transferForm = reactive({
  customer_id: 0,
  store_id: undefined as number | undefined,
  owner_user_id: undefined as number | undefined,
  remark: "",
});

const returnForm = reactive({
  customer_id: 0,
  reason_type: "not_ready",
  reason: "",
});

const rules: FormRules = {
  mobile: [{ required: true, message: "请输入手机号", trigger: "blur" }],
  name: [{ required: true, message: "请输入姓名", trigger: "blur" }],
  gender: [{ required: true, message: "请选择性别", trigger: "change" }],
};

const mergedLifecycle = computed(() => {
  const customerItems: TimelineItem[] = (detail.value?.lifecycle_records || []).map((item) => ({ ...item, source: "customer" }));
  const leadItems: TimelineItem[] = (detail.value?.lead_lifecycle_records || []).map((item) => ({ ...item, source: "lead" }));
  return [...customerItems, ...leadItems].sort((a, b) => String(b.created_time || "").localeCompare(String(a.created_time || "")));
});

const mergedProcess = computed(() => {
  const customerItems: ProcessItem[] = (detail.value?.process_records || []).map((item) => ({ ...item, source: "customer" }));
  const leadItems: ProcessItem[] = (detail.value?.lead_process_records || []).map((item) => ({ ...item, source: "lead" }));
  return [...customerItems, ...leadItems].sort((a, b) => String(b.occurred_at || b.created_time || "").localeCompare(String(a.occurred_at || a.created_time || "")));
});

const certificationArchiveItems = computed(() => detail.value?.certification?.archive_items || []);

function materialsByItem(itemCode: string) {
  return (detail.value?.certification?.archive_materials || []).filter((item) => item.item_code === itemCode);
}

async function fetchList() {
  loading.value = true;
  try {
    const res = isDealPage.value ? await CustomerAPI.listDealCustomer(query) : await CustomerAPI.listCustomer(query);
    rows.value = res.data.data.items || [];
    total.value = res.data.data.total || 0;
  } finally {
    loading.value = false;
  }
}

function createContract(customerId?: number) {
  if (!customerId) return;
  router.push({ path: "/miailove/crm/contract", query: { customer_id: customerId } });
}

function resetQuery() {
  Object.assign(query, { page_no: 1, page_size: query.page_size, keyword: undefined, current_stage: undefined, max_stage: undefined, store_id: undefined, owner_user_id: undefined });
  fetchList();
}

async function openDetail(id?: number) {
  if (!id) return;
  await ensureOptionsLoaded();
  const res = await CustomerAPI.detailCustomer(id);
  detail.value = res.data.data;
  await fetchCustomerContracts(id);
  fillForm(detail.value);
  readOnly.value = true;
  activeTab.value = "overview";
  detailVisible.value = true;
}

function fillForm(row: CustomerDetail) {
  Object.assign(form, {
    mobile: row.person.primary_mobile,
    name: row.person.name,
    gender: row.person.gender,
    wechat: row.person.wechat,
    birth_date: row.person.birth_date,
    height_cm: row.person.height_cm,
    weight_kg: row.person.weight_kg,
    ethnicity: row.person.ethnicity,
    occupation: row.person.occupation,
    occupation_code: row.person.occupation_code,
    annual_income: row.person.annual_income,
    marital_status: row.person.marital_status,
    education: row.person.education,
    graduated_school: row.person.graduated_school,
    major: row.person.major,
    unit_type: row.person.unit_type,
    job_title: row.person.job_title,
    work_company: row.person.work_company,
    hometown: row.person.hometown,
    residence: row.person.residence,
    house_status: row.person.house_status,
    car_status: row.person.car_status,
    accept_long_distance_self: row.person.accept_long_distance_self,
    accept_flash_marriage: row.person.accept_flash_marriage,
    willing_relocate: row.person.willing_relocate,
    marriage_plan: row.person.marriage_plan,
    family_background: row.person.family_background,
    profile_remark: row.person.profile_remark,
    photo_urls: row.person.photo_urls || [],
    profile_intro: row.person.profile_intro,
    id_card_no: row.person.id_card_no,
    current_stage: row.current_stage,
    next_follow_at: row.next_follow_at,
    partner_preference: row.partner_preference || undefined,
    description: row.description,
  });
  photoFileList.value = (row.person.photo_urls || []).map((url, index) => ({ name: `照片${index + 1}`, url, uid: index } as UploadFile));
}

function enableEdit() {
  if (!detail.value) return;
  fillForm(detail.value);
  readOnly.value = false;
  activeTab.value = "profile";
}

function cancelEdit() {
  if (detail.value) fillForm(detail.value);
  readOnly.value = true;
}

async function submitProfile() {
  if (!detail.value?.id) return;
  await formRef.value?.validate();
  form.partner_preference = preferenceFormRef.value?.getValue() as PartnerPreference | undefined;
  form.photo_urls = photoFileList.value.map((item) => item.url).filter((url): url is string => Boolean(url));
  await ElMessageBox.confirm("确认保存客户主档案？保存后将刷新觅AI印象。", "二次确认", { type: "warning" });
  await CustomerAPI.updateCustomer(detail.value.id, form);
  ElMessage.success("客户资料已保存");
  await openDetail(detail.value.id);
  readOnly.value = true;
  fetchList();
}

function openProcess(id: number | undefined, type: CustomerProcessType) {
  if (!id) return;
  processCustomerId.value = id;
  processType.value = type;
  Object.assign(processForm, {
    method: "phone",
    result: "",
    content: "",
    next_follow_at: "",
    scheduled_at: "",
    appointment_slot: "",
    visit_purpose: "",
    promised_gift: "",
    need_summary: "",
    budget_range: "",
    main_objection: "",
    intention_level: "",
    next_action: "",
    enter_signing: false,
  });
  processVisible.value = true;
}

async function submitProcess() {
  if (!processCustomerId.value || !processForm.content) return;
  const payload = { ...processForm };
  if (payload.method === "appointment" && payload.scheduled_at && payload.scheduled_at.length === 10) {
    payload.scheduled_at = `${payload.scheduled_at} 00:00:00`;
  }
  if (!payload.next_follow_at) delete payload.next_follow_at;
  if (!payload.scheduled_at) delete payload.scheduled_at;
  if (!payload.appointment_slot) delete payload.appointment_slot;
  if (!payload.visit_purpose) delete payload.visit_purpose;
  if (!payload.promised_gift) delete payload.promised_gift;
  if (!payload.need_summary) delete payload.need_summary;
  if (!payload.budget_range) delete payload.budget_range;
  if (!payload.main_objection) delete payload.main_objection;
  if (!payload.intention_level) delete payload.intention_level;
  if (!payload.next_action) delete payload.next_action;
  await CustomerAPI.createUnifiedProcess(processCustomerId.value, payload);
  ElMessage.success("过程记录已保存");
  processVisible.value = false;
  if (detailVisible.value && detail.value?.id === processCustomerId.value) await openDetail(processCustomerId.value);
  fetchList();
}

function applyPhrase(value: string) {
  if (value) processForm.content = value;
}

function openTransfer(row: CustomerTable) {
  Object.assign(transferForm, {
    customer_id: row.id,
    store_id: row.store_id,
    owner_user_id: row.owner_user_id,
    remark: "",
  });
  transferVisible.value = true;
}

async function submitTransfer() {
  if (!transferForm.customer_id || !transferForm.owner_user_id) return;
  const original = rows.value.find((item) => item.id === transferForm.customer_id);
  if (transferForm.store_id && original && transferForm.store_id !== original.store_id) {
    await CustomerAPI.transferStore({
      customer_id: transferForm.customer_id,
      store_id: transferForm.store_id,
      owner_user_id: transferForm.owner_user_id,
      remark: transferForm.remark,
    });
  } else {
    await CustomerAPI.transferOwner({
      customer_id: transferForm.customer_id,
      owner_user_id: transferForm.owner_user_id,
      remark: transferForm.remark,
    });
  }
  ElMessage.success("客户流转已完成");
  transferVisible.value = false;
  fetchList();
}

function openReturnLead(row: CustomerTable) {
  Object.assign(returnForm, { customer_id: row.id, reason_type: "not_ready", reason: "" });
  returnVisible.value = true;
}

async function submitReturnLead() {
  if (!returnForm.customer_id || !returnForm.reason) return;
  await ElMessageBox.confirm("确认将该客户退回线索？退回后客户列表将不再显示。", "退回线索", { type: "warning" });
  await CustomerAPI.returnLead(returnForm.customer_id, { reason_type: returnForm.reason_type, reason: returnForm.reason });
  ElMessage.success("已退回线索");
  returnVisible.value = false;
  detailVisible.value = false;
  fetchList();
}

async function openPrint(id?: number) {
  if (!id) return;
  await ensureOptionsLoaded();
  const res = await CustomerAPI.printCard(id);
  printCard.value = res.data.data;
  printVisible.value = true;
}

function printA4() {
  window.print();
}

async function uploadPhoto(options: UploadRequestOptions) {
  const fileInfo = await uploadImageDirect(options.file, "crm_lead_photo");
  const current = photoFileList.value.find((item) => item.uid === options.file.uid);
  if (current) {
    current.name = fileInfo.file_name || fileInfo.origin_name || options.file.name;
    current.url = fileInfo.file_url;
  }
  options.onSuccess?.(fileInfo);
}

async function uploadCertificationMaterial(options: UploadRequestOptions, item: CustomerCertificationArchiveItem) {
  if (!detail.value?.id) return;
  const fileInfo = await uploadImageDirect(options.file, "certification_material");
  const material = await CustomerAPI.saveCertificationMaterial(detail.value.id, {
    item_code: item.item_code,
    item_name: item.item_name,
    material_type: "image",
    file_name: fileInfo.file_name || fileInfo.origin_name || options.file.name,
    file_path: fileInfo.object_key || fileInfo.file_path,
    file_url: fileInfo.file_url,
    payload: { origin_name: fileInfo.origin_name, scene: fileInfo.scene },
  });
  const archive = detail.value.certification;
  if (archive) {
    archive.archive_materials = [material.data.data, ...(archive.archive_materials || [])];
  }
  options.onSuccess?.(fileInfo);
  ElMessage.success("认证资料已存档");
}

async function deleteCertificationMaterial(materialId?: number) {
  if (!materialId || !detail.value?.certification) return;
  await ElMessageBox.confirm("确认删除这张认证资料图片？该操作只删除客户资料存档，不影响认证结果。", "删除认证资料", { type: "warning" });
  await CustomerAPI.deleteCertificationMaterial(materialId);
  detail.value.certification.archive_materials = (detail.value.certification.archive_materials || []).filter((item: CustomerCertificationMaterial) => item.id !== materialId);
  ElMessage.success("认证资料已删除");
}

function removePhoto(file: UploadFile) {
  photoFileList.value = photoFileList.value.filter((item) => item.uid !== file.uid && item.url !== file.url);
}

let optionsLoaded = false;
let optionsPromise: Promise<void> | null = null;

async function ensureOptionsLoaded() {
  if (optionsLoaded) return;
  if (!optionsPromise) optionsPromise = loadOptions();
  await optionsPromise;
}

async function loadOptions() {
  const [deptRes, userRes] = await Promise.all([LeadAPI.storeOptions(), LeadAPI.salesOptions()]);
  deptOptions.value = (deptRes.data.data || []).map((item) => ({ label: item.name || String(item.id), value: item.id! }));
  userOptions.value = (userRes.data.data || []).map((item) => ({ label: item.name || String(item.id), value: item.id! }));
  await loadDictOptions();
  optionsLoaded = true;
}

async function loadDictOptions() {
  const dictMap = {
    ethnicity: "crm_ethnicity",
    annualIncome: "crm_annual_income",
    maritalStatus: "crm_marital_status",
    education: "crm_education",
    houseStatus: "crm_house_status",
    carStatus: "crm_car_status",
    occupation: "crm_occupation",
    unitType: "crm_unit_type",
    marriagePlan: "crm_marriage_plan",
    followMethod: "crm_customer_follow_method",
    followPhrase: "crm_customer_follow_phrase",
    intentionLevel: "crm_customer_intention_level",
    visitPurpose: "crm_customer_visit_purpose",
    appointmentSlot: "crm_customer_appointment_slot",
    appointmentStatus: "crm_customer_appointment_status",
    contractStatus: "crm_contract_status",
    receiptStatus: "crm_contract_receipt_status",
  } as const;
  await Promise.all(
    Object.entries(dictMap).map(async ([key, type]) => {
      const res = await DictAPI.getInitDict(type);
      dictOptions[key as keyof typeof dictOptions] = ((res.data.data as DictDataTable[]) || []).map((item) => ({ label: item.dict_label || item.dict_value || "", value: item.dict_value || "" }));
    })
  );
}

function stageLabel(value?: string) {
  return stageOptions.find((item) => item.value === value)?.label || value || "-";
}

function processTypeLabel(value?: string) {
  return (
    {
      follow: "跟进",
      appointment: "邀约",
      visit: "到店",
      visit_checkin: "登记到店",
      consultation: "面谈",
      no_show: "爽约",
      appointment_cancel: "取消预约",
      invalid: "标记无效",
      release: "释放线索",
      convert_customer: "转建档客户",
    } as Record<string, string>
  )[value || ""] || value || "";
}

function processResultLabel(item: ProcessItem) {
  const result = String(item.result || "");
  if (!result) return "无结果";
  if (item.record_type === "visit_checkin" || item.record_type === "consultation") {
    return stageLabel(result);
  }
  if (["pending", "checked_in", "consulted", "no_show", "cancelled"].includes(result)) {
    return optionLabel(dictOptions.appointmentStatus, result);
  }
  return result;
}

function genderLabel(value?: string) {
  return ({ "0": "男", "1": "女", "2": "未知" } as Record<string, string>)[value || ""] || "-";
}

function optionLabel(options: Array<{ label: string; value: string }>, value?: string) {
  if (!value) return "-";
  return options.find((item) => item.value === value)?.label || value;
}

function contractStatusLabel(value?: string) {
  return optionLabel(dictOptions.contractStatus, value);
}

function receiptStatusLabel(value?: string) {
  return optionLabel(dictOptions.receiptStatus, value);
}

function progressPercent(value?: string | number) {
  const percent = Number(value ?? 0);
  if (!Number.isFinite(percent)) return 0;
  return Math.max(0, Math.min(100, Math.round(percent)));
}

function paymentStatusLabel(value?: string) {
  return ({ unpaid: "未支付", partial: "部分支付", settled: "已结清" } as Record<string, string>)[value || ""] || value || "-";
}

function formatContractReceipts(receipts: ContractTable["receipts"] = []) {
  return receipts.map((item) => `${receiptStatusLabel(item.receipt_status)} ¥${Number(item.amount || 0).toFixed(2)}`).join("；");
}

async function fetchCustomerContracts(customerId: number) {
  const res = await ContractAPI.listContract({ page_no: 1, page_size: 20, customer_id: customerId });
  customerContracts.value = res.data.data.items || [];
}

function goContractCreate() {
  window.location.hash = `/miailove/crm/contract?customer_id=${detail.value?.id || ""}`;
}

function goContractDetail(id?: number) {
  window.location.hash = `/miailove/crm/contract?contract_id=${id || ""}`;
}

function processExtraLines(item: ProcessItem) {
  const lines: string[] = [];
  if (item.scheduled_at) lines.push(`预约日期：${formatDate(item.scheduled_at)}`);
  if (item.appointment_slot) lines.push(`预约时段：${optionLabel(dictOptions.appointmentSlot, item.appointment_slot)}`);
  if (item.visit_purpose) lines.push(`到访目的：${optionLabel(dictOptions.visitPurpose, item.visit_purpose)}`);
  if (item.promised_gift) lines.push(`到店礼：${item.promised_gift}`);
  if (item.appointment_status) lines.push(`预约状态：${optionLabel(dictOptions.appointmentStatus, item.appointment_status)}`);
  if (item.checked_in_at) lines.push(`核销时间：${item.checked_in_at}`);
  if (item.checked_in_user_name) lines.push(`核销人：${item.checked_in_user_name}`);
  if (item.need_summary) lines.push(`需求摘要：${item.need_summary}`);
  if (item.budget_range) lines.push(`预算区间：${item.budget_range}`);
  if (item.main_objection) lines.push(`主要异议：${item.main_objection}`);
  if (item.intention_level) lines.push(`意向等级：${optionLabel(dictOptions.intentionLevel, item.intention_level)}`);
  return lines;
}

function formatDate(value?: string) {
  return value ? String(value).slice(0, 10) : "-";
}

function boolLabel(value?: boolean | null) {
  if (value === true) return "是";
  if (value === false) return "否";
  return "-";
}

function lifecycleLabel(value: string) {
  return (
    {
      create_from_lead: "线索转客户",
      edit: "编辑资料",
      transfer_owner: "同店转派",
      transfer_store: "跨店转交",
      return_lead: "退回线索",
      convert_customer: "线索转建档客户",
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
    } as Record<string, string>
  )[value] || value;
}

function sourceLabel(value?: string) {
  return value === "lead" ? "线索阶段" : "客户阶段";
}

function operatorName(item: { operator_user_name?: string; operator_user_id?: number; created_by?: { name?: string } }) {
  return item.operator_user_name || item.created_by?.name || (item.operator_user_id ? `用户ID ${item.operator_user_id}` : "系统");
}

function formatChange(value?: Record<string, unknown>, operationType?: string) {
  if (!value) return "-";
  if (operationType === "edit") {
    return (
      Object.keys(value)
        .map((key) => fieldChangeText(key, value[key]))
        .filter(Boolean)
        .join("；") || "资料已更新"
    );
  }
  return Object.entries(value)
    .map(([key, val]) => `${fieldLabel(key)}：${displayChangeValue(val, key)}`)
    .join("；");
}

function fieldChangeText(key: string, value: unknown) {
  if (key === "partner_preference") {
    return `${fieldLabel(key)}：已更新`;
  }
  if (value && typeof value === "object" && ("from" in value || "to" in value)) {
    const change = value as { from?: unknown; to?: unknown };
    return `${fieldLabel(key)}：${displayChangeValue(change.from, key)} → ${displayChangeValue(change.to, key)}`;
  }
  return `${fieldLabel(key)}：${displayChangeValue(value, key)}`;
}

function fieldLabel(key: string) {
  return (
    {
      pool_type: "归属池",
      from_pool: "原归属池",
      to_pool: "新归属池",
      store_id: "归属门店",
      owner_sales_id: "归属人",
      owner_user_id: "归属人",
      from_owner_sales_id: "原归属人",
      to_owner_sales_id: "新归属人",
      from_owner_user_id: "原归属人",
      to_owner_user_id: "新归属人",
      lead_type: "线索类型",
      source_channel_code: "来源渠道",
      mobile: "手机号",
      name: "姓名",
      gender: "性别",
      wechat: "微信号",
      birth_date: "出生日期",
      height_cm: "身高",
      weight_kg: "体重",
      ethnicity: "民族",
      occupation: "职业",
      occupation_code: "标准职业",
      annual_income: "年收入",
      marital_status: "婚况",
      education: "学历",
      graduated_school: "毕业院校",
      major: "专业",
      unit_type: "单位类型",
      job_title: "职务",
      work_company: "工作单位",
      hometown: "籍贯",
      residence: "常驻地",
      house_status: "房产信息",
      car_status: "购车信息",
      accept_long_distance_self: "接受异地",
      accept_flash_marriage: "接受闪婚",
      willing_relocate: "愿意搬家",
      marriage_plan: "结婚计划",
      family_background: "家庭情况",
      profile_remark: "备注",
      photo_urls: "照片",
      description: "备注",
      partner_preference: "择偶要求",
      reason: "原因",
      reason_type: "原因分类",
      source_event_id: "来源事件",
      current_stage: "当前阶段",
      max_stage: "最高进展",
    } as Record<string, string>
  )[key] || key;
}

function displayChangeValue(value: unknown, field?: string): string {
  if (value === null || value === undefined || value === "") return "未设置";
  if (Array.isArray(value)) return value.length ? value.join("、") : "未设置";
  if (typeof value === "boolean") return boolLabel(value);
  if (typeof value === "number") {
    const name = idFieldName(field, value);
    if (name) return name;
  }
  if (typeof value === "string") {
    const name = idFieldName(field, value);
    if (name) return name;
    const dictLabel = dictValueLabel(field, value);
    if (dictLabel) return dictLabel;
    if (["hq_pool", "store_pool", "sales_private"].includes(value)) {
      return ({ hq_pool: "总部池", store_pool: "门店公海", sales_private: "销售私海" } as Record<string, string>)[value] || value;
    }
    if (["pending", "new", "second_hand", "invalid", "converted_customer"].includes(value)) {
      return ({ pending: "待分配", new: "新线索", second_hand: "二手线索", invalid: "无效线索", converted_customer: "已转建档客户" } as Record<string, string>)[value] || value;
    }
    if (field === "current_stage" || field === "max_stage") return stageLabel(value);
    return normalizeDisplayText(value, field);
  }
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function idFieldName(field: string | undefined, value: string | number) {
  const id = Number(value);
  if (!Number.isFinite(id)) return "";
  if (field?.includes("store_id")) {
    return deptOptions.value.find((item) => item.value === id)?.label || "";
  }
  if (field?.includes("owner_sales_id") || field?.includes("owner_user_id")) {
    return userOptions.value.find((item) => item.value === id)?.label || "";
  }
  return "";
}

function dictValueLabel(field: string | undefined, value: string) {
  if (field === "gender") return genderLabel(value);
  const map = {
    ethnicity: dictOptions.ethnicity,
    annual_income: dictOptions.annualIncome,
    marital_status: dictOptions.maritalStatus,
    education: dictOptions.education,
    house_status: dictOptions.houseStatus,
    car_status: dictOptions.carStatus,
    occupation_code: dictOptions.occupation,
    unit_type: dictOptions.unitType,
    marriage_plan: dictOptions.marriagePlan,
  } as Record<string, Array<{ label: string; value: string }>>;
  return field && map[field] ? map[field].find((item) => item.value === value)?.label || "" : "";
}

function normalizeDisplayText(value: string, field?: string) {
  if (!value.includes("/")) return value;
  const parts = value
    .split("/")
    .map((item) => item.trim())
    .filter(Boolean);
  const normalized = field === "hometown" || field === "residence" ? parts.slice(0, 2) : parts;
  return normalized.join(" / ");
}

function jsonText(value?: Record<string, unknown>) {
  return value ? JSON.stringify(value) : "-";
}

onMounted(() => {
  ensureOptionsLoaded();
  fetchList();
});
</script>

<style scoped>
.customer-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.filter-card,
.table-card {
  border-radius: 8px;
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

.toolbar-note,
.drawer-subtitle,
.timeline-extra {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  padding-top: 16px;
}

.table-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.table-actions :deep(.el-button) {
  margin-left: 0;
}

.table-actions :deep(.el-dropdown) {
  display: inline-flex;
  align-items: center;
}

.payment-progress {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.payment-progress__text {
  font-size: 12px;
  line-height: 16px;
  color: var(--el-text-color-primary);
  white-space: nowrap;
}

.drawer-head,
.drawer-actions,
.process-toolbar,
.save-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.drawer-title {
  font-size: 18px;
  font-weight: 700;
}

.overview-grid {
  display: grid;
  grid-template-columns: 220px 1fr;
  align-items: start;
  gap: 16px;
}

.overview-desc :deep(.el-descriptions__cell) {
  padding: 10px 12px;
  line-height: 1.6;
}

.overview-desc :deep(.el-descriptions__label) {
  width: 92px;
  min-width: 92px;
  white-space: nowrap;
}

.profile-side {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.cert-material-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 12px;
  margin-top: 14px;
}

.cert-material-card {
  padding: 12px;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
}

.cert-material-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.cert-material-title {
  font-weight: 600;
}

.cert-material-desc {
  margin-top: 4px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.cert-material-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(92px, 1fr));
  gap: 10px;
}

.cert-material-image {
  width: 100%;
  aspect-ratio: 1;
  border-radius: 6px;
}

.cert-material-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  margin-top: 4px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.avatar-carousel,
.avatar-empty {
  width: 100%;
  height: 300px;
}

.avatar-photo {
  width: 100%;
  height: 100%;
  border-radius: 8px;
  border: 1px solid var(--el-border-color-lighter);
  background: var(--el-fill-color-light);
}

.avatar-carousel :deep(.el-carousel__container) {
  height: 270px;
}

.avatar-carousel :deep(.el-carousel__indicator--horizontal) {
  padding: 8px 4px 0;
}

.avatar-empty {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: var(--el-fill-color-light);
}

.avatar-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--el-text-color-secondary);
}

.profile-form {
  padding: 14px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
}

.section-title {
  margin-bottom: 10px;
  font-weight: 600;
}

.timeline-content {
  line-height: 1.8;
  white-space: pre-wrap;
}

.photo-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
}

.photo-item {
  width: 96px;
  height: 96px;
  border-radius: 8px;
}

.mt12 {
  margin-top: 12px;
}

.process-toolbar {
  justify-content: flex-start;
  margin-bottom: 16px;
}

.timeline-title {
  font-weight: 600;
}

.print-card {
  position: relative;
  width: 794px;
  min-height: 1123px;
  padding: 34px;
  overflow: hidden;
  background: #fff;
  color: #1f2933;
}

.watermark {
  position: absolute;
  top: 44%;
  left: 50%;
  z-index: 0;
  color: rgba(0, 0, 0, 0.06);
  font-size: 92px;
  font-weight: 700;
  transform: translate(-50%, -50%) rotate(-28deg);
  white-space: nowrap;
}

.print-header,
.print-footer,
.print-body {
  position: relative;
  z-index: 1;
}

.print-header {
  display: flex;
  justify-content: space-between;
  padding-bottom: 14px;
  border-bottom: 2px solid #1f2933;
}

.print-title {
  font-size: 26px;
  font-weight: 700;
}

.print-subtitle,
.print-meta,
.print-footer {
  color: #667085;
  font-size: 12px;
}

.print-body {
  display: grid;
  grid-template-columns: 250px 1fr;
  gap: 22px;
  padding-top: 22px;
}

.print-photo {
  width: 250px;
  height: 330px;
  object-fit: cover;
  border: 1px solid #d0d5dd;
}

.print-photo-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f2f4f7;
}

.print-info table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.print-info th,
.print-info td {
  padding: 8px;
  border: 1px solid #d0d5dd;
  text-align: left;
}

.print-info th {
  width: 76px;
  background: #f8fafc;
}

.print-info section {
  margin-top: 14px;
}

.print-info h4 {
  margin: 0 0 6px;
  font-size: 14px;
}

.print-info p {
  max-height: 108px;
  margin: 0;
  overflow: hidden;
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-wrap;
}

.print-footer {
  position: absolute;
  right: 34px;
  bottom: 24px;
  left: 34px;
  padding-top: 10px;
  border-top: 1px solid #d0d5dd;
}

@media print {
  body * {
    visibility: hidden;
  }
  #customer-print-card,
  #customer-print-card * {
    visibility: visible;
  }
  #customer-print-card {
    position: fixed;
    top: 0;
    left: 0;
    width: 210mm;
    min-height: 297mm;
    box-shadow: none;
  }
}
</style>
