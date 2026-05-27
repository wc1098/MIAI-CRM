<template>
  <div class="app-container candidate-page">
    <el-card shadow="never">
      <template #header>
        <div class="toolbar">
          <div>
            <div class="toolbar-title">备选库</div>
            <div class="toolbar-note">服务红娘私有资源池；候选发现全程脱敏，审核通过后进入本人备选库</div>
          </div>
          <div class="toolbar-actions">
            <el-button v-if="canQueryRule" icon="Setting" @click="openRuleDialog">备选规则</el-button>
            <el-button v-hasPerm="['service:candidate:create']" type="success" icon="EditPen" @click="openManualCreate">手动新增</el-button>
          </div>
        </div>
      </template>

      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="我的备选" name="mine">
          <el-form :model="query" inline>
            <el-form-item label="关键词"><el-input v-model="query.keyword" clearable placeholder="姓名/手机号/编号" style="width: 220px" @keyup.enter="loadMine" /></el-form-item>
            <el-form-item label="来源">
              <el-select v-model="query.source_type" clearable placeholder="全部" style="width: 170px">
                <el-option v-for="item in sourceOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value || ''" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" icon="Search" @click="loadMine">查询</el-button>
              <el-button icon="Refresh" @click="resetMine">重置</el-button>
            </el-form-item>
          </el-form>

          <el-table v-loading="mineLoading" :data="rows" border stripe row-key="id">
            <el-table-column prop="name" label="姓名" width="110" show-overflow-tooltip />
            <el-table-column label="性别/年龄" width="110"><template #default="{ row }">{{ genderText(row.gender) }} / {{ row.age ?? "-" }}</template></el-table-column>
            <el-table-column prop="mobile" label="手机号" width="130" show-overflow-tooltip />
            <el-table-column prop="wechat" label="微信" width="130" show-overflow-tooltip />
            <el-table-column prop="height_cm" label="身高" width="80" />
            <el-table-column label="学历" width="120"><template #default="{ row }">{{ dictText(educationOptions, row.education) }}</template></el-table-column>
            <el-table-column label="年收入" width="120"><template #default="{ row }">{{ dictText(incomeOptions, row.annual_income) }}</template></el-table-column>
            <el-table-column label="婚况" width="100"><template #default="{ row }">{{ dictText(maritalOptions, row.marital_status) }}</template></el-table-column>
            <el-table-column prop="residence" label="常驻地" width="130" show-overflow-tooltip />
            <el-table-column label="来源" width="150"><template #default="{ row }">{{ dictText(sourceOptions, row.source_type) }}</template></el-table-column>
            <el-table-column prop="matchmaker_name" label="服务红娘" width="110" show-overflow-tooltip />
            <el-table-column label="私有标签" min-width="160">
              <template #default="{ row }"><el-tag v-for="tag in row.private_tags || []" :key="tag" size="small" class="tag">{{ dictText(tagOptions, tag) }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="private_remark" label="私有备注" min-width="180" show-overflow-tooltip />
            <el-table-column label="操作" fixed="right" width="90">
              <template #default="{ row }">
                <el-button v-hasPerm="['service:candidate:detail']" link type="primary" @click="openCandidateDetail(row)">详情</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pager"><el-pagination v-model:current-page="query.page_no" v-model:page-size="query.page_size" :total="total" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next, jumper" @size-change="loadMine" @current-change="loadMine" /></div>
        </el-tab-pane>

        <el-tab-pane v-if="canDiscover" label="候选发现" name="discover">
          <el-form :model="discoverQuery" label-width="86px">
            <el-row :gutter="12">
              <el-col :span="6"><el-form-item label="范围"><el-select v-model="discoverQuery.scope" style="width: 100%"><el-option v-for="item in scopeOptions" :key="item.dict_value" :label="item.dict_label" :value="item.dict_value || ''" /></el-select></el-form-item></el-col>
              <el-col v-if="canAssignService" :span="6"><el-form-item label="归属红娘"><el-select v-model="discoverQuery.matchmaker_id" clearable filterable placeholder="申请时选择" style="width: 100%"><el-option v-for="item in matchmakerOptions" :key="item.id" :label="`${item.name}${item.mobile ? `（${item.mobile}）` : ''}`" :value="item.id" /></el-select></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="关键词"><el-input v-model="discoverQuery.keyword" clearable placeholder="姓名/手机号/编号/ID" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="姓名"><el-input v-model="discoverQuery.name" clearable /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="展示编号"><el-input v-model="discoverQuery.display_no" clearable /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="手机号"><el-input v-model="discoverQuery.mobile" clearable /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="性别"><el-select v-model="discoverQuery.gender" clearable style="width: 100%"><el-option label="男" value="0" /><el-option label="女" value="1" /><el-option label="未知" value="2" /></el-select></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="年龄"><div class="range"><el-input-number v-model="discoverQuery.age_min" :min="18" :max="120" controls-position="right" /><span>-</span><el-input-number v-model="discoverQuery.age_max" :min="18" :max="120" controls-position="right" /></div></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="身高"><div class="range"><el-input-number v-model="discoverQuery.height_min" :min="80" :max="260" controls-position="right" /><span>-</span><el-input-number v-model="discoverQuery.height_max" :min="80" :max="260" controls-position="right" /></div></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="体重"><div class="range"><el-input-number v-model="discoverQuery.weight_min" :min="20" :max="300" controls-position="right" /><span>-</span><el-input-number v-model="discoverQuery.weight_max" :min="20" :max="300" controls-position="right" /></div></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="学历"><dict-select v-model="discoverQuery.education" :options="educationOptions" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="年收入"><dict-select v-model="discoverQuery.annual_income" :options="incomeOptions" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="婚况"><dict-select v-model="discoverQuery.marital_status" :options="maritalOptions" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="民族"><el-input v-model="discoverQuery.ethnicity" clearable /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="职业"><dict-select v-model="discoverQuery.occupation_code" :options="occupationOptions" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="单位类型"><dict-select v-model="discoverQuery.unit_type" :options="unitTypeOptions" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="常驻地"><el-input v-model="discoverQuery.residence" clearable /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="籍贯"><el-input v-model="discoverQuery.hometown" clearable /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="房产"><dict-select v-model="discoverQuery.house_status" :options="houseOptions" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="车辆"><dict-select v-model="discoverQuery.car_status" :options="carOptions" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="接受异地"><bool-select v-model="discoverQuery.accept_long_distance_self" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="接受闪婚"><bool-select v-model="discoverQuery.accept_flash_marriage" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="愿意搬家"><bool-select v-model="discoverQuery.willing_relocate" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="结婚计划"><dict-select v-model="discoverQuery.marriage_plan" :options="marriagePlanOptions" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="有照片"><bool-select v-model="discoverQuery.has_photo" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="认证等级"><el-select v-model="discoverQuery.certification_level" clearable style="width: 100%"><el-option label="未认证" value="none" /><el-option label="基础认证" value="basic" /><el-option label="增强认证" value="enhanced" /></el-select></el-form-item></el-col>
            </el-row>
            <el-collapse class="filter-collapse">
              <el-collapse-item title="择偶条件筛选" name="preference">
                <el-row :gutter="12">
                  <el-col :span="6"><el-form-item label="期望年龄"><div class="range"><el-input-number v-model="discoverQuery.pref_age_min" :min="18" :max="120" controls-position="right" /><span>-</span><el-input-number v-model="discoverQuery.pref_age_max" :min="18" :max="120" controls-position="right" /></div></el-form-item></el-col>
                  <el-col :span="6"><el-form-item label="期望身高"><div class="range"><el-input-number v-model="discoverQuery.pref_height_min" :min="80" :max="260" controls-position="right" /><span>-</span><el-input-number v-model="discoverQuery.pref_height_max" :min="80" :max="260" controls-position="right" /></div></el-form-item></el-col>
                  <el-col :span="6"><el-form-item label="期望体重"><div class="range"><el-input-number v-model="discoverQuery.pref_weight_min" :min="20" :max="300" controls-position="right" /><span>-</span><el-input-number v-model="discoverQuery.pref_weight_max" :min="20" :max="300" controls-position="right" /></div></el-form-item></el-col>
                  <el-col :span="6"><el-form-item label="接受异地"><bool-select v-model="discoverQuery.pref_accept_long_distance" /></el-form-item></el-col>
                  <el-col :span="6"><el-form-item label="接受离异"><bool-select v-model="discoverQuery.pref_accept_divorced" /></el-form-item></el-col>
                  <el-col :span="6"><el-form-item label="接受带孩"><bool-select v-model="discoverQuery.pref_accept_children" /></el-form-item></el-col>
                  <el-col :span="6"><el-form-item label="期望学历"><multi-dict-select v-model="discoverQuery.preferred_education_codes" :options="educationOptions" /></el-form-item></el-col>
                  <el-col :span="6"><el-form-item label="期望婚况"><multi-dict-select v-model="discoverQuery.preferred_marital_status_codes" :options="maritalOptions" /></el-form-item></el-col>
                  <el-col :span="6"><el-form-item label="期望收入"><multi-dict-select v-model="discoverQuery.preferred_annual_income_codes" :options="incomeOptions" /></el-form-item></el-col>
                  <el-col :span="6"><el-form-item label="期望房产"><multi-dict-select v-model="discoverQuery.preferred_house_status_codes" :options="houseOptions" /></el-form-item></el-col>
                  <el-col :span="6"><el-form-item label="期望车辆"><multi-dict-select v-model="discoverQuery.preferred_car_status_codes" :options="carOptions" /></el-form-item></el-col>
                  <el-col :span="6"><el-form-item label="严格程度"><el-select v-model="discoverQuery.strictness_level" clearable style="width: 100%"><el-option label="宽松" value="loose" /><el-option label="普通" value="normal" /><el-option label="严格" value="strict" /></el-select></el-form-item></el-col>
                  <el-col :span="12"><el-form-item label="职业偏好"><el-input v-model="discoverQuery.preferred_occupation_text" clearable /></el-form-item></el-col>
                  <el-col :span="12"><el-form-item label="自由说明"><el-input v-model="discoverQuery.preference_text" clearable /></el-form-item></el-col>
                </el-row>
              </el-collapse-item>
            </el-collapse>
            <div class="form-actions">
              <el-button type="primary" icon="Search" @click="loadDiscover">搜索</el-button>
              <el-button icon="Refresh" @click="resetDiscover">重置</el-button>
            </div>
          </el-form>

          <el-table v-loading="discoverLoading" :data="discoverRows" border stripe row-key="id">
            <el-table-column prop="display_no" label="编号" width="100" />
            <el-table-column prop="name" label="姓名" width="110" />
            <el-table-column label="性别/年龄" width="110"><template #default="{ row }">{{ genderText(row.gender) }} / {{ row.age ?? "-" }}</template></el-table-column>
            <el-table-column prop="mobile" label="手机号" width="130" />
            <el-table-column prop="wechat" label="微信" width="120" />
            <el-table-column prop="store_name" label="归属门店" width="140" show-overflow-tooltip />
            <el-table-column prop="height_cm" label="身高" width="80" />
            <el-table-column prop="weight_kg" label="体重" width="80" />
            <el-table-column prop="residence" label="常驻地" width="130" show-overflow-tooltip />
            <el-table-column label="学历" width="120"><template #default="{ row }">{{ dictText(educationOptions, row.education) }}</template></el-table-column>
            <el-table-column label="状态" width="110"><template #default="{ row }"><el-tag v-if="row.already_in_backup" type="success">已加入</el-tag><el-tag v-else-if="row.pending_request" type="warning">待审核</el-tag><span v-else>-</span></template></el-table-column>
            <el-table-column label="操作" fixed="right" width="120">
              <template #default="{ row }">
                <el-button v-if="!row.already_in_backup && !row.pending_request" v-hasPerm="['service:candidate:join_request']" link type="primary" @click="openJoinRequest(row)">申请加入</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pager"><el-pagination v-model:current-page="discoverQuery.page_no" v-model:page-size="discoverQuery.page_size" :total="discoverTotal" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next, jumper" @size-change="loadDiscover" @current-change="loadDiscover" /></div>
        </el-tab-pane>

        <el-tab-pane v-if="canQueryRequest" label="我的申请" name="requests">
          <request-table :rows="requestRows" :loading="requestLoading" :status-options="requestStatusOptions" :scope-options="scopeOptions" :tag-options="tagOptions" @reload="loadRequests" />
          <div class="pager"><el-pagination v-model:current-page="requestQuery.page_no" v-model:page-size="requestQuery.page_size" :total="requestTotal" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next, jumper" @size-change="loadRequests" @current-change="loadRequests" /></div>
        </el-tab-pane>

        <el-tab-pane v-if="canReviewRequest" label="加入审核" name="review">
          <request-table :rows="reviewRows" :loading="reviewLoading" :status-options="requestStatusOptions" :scope-options="scopeOptions" :tag-options="tagOptions" review @approve="reviewJoin($event, 'approved')" @reject="reviewJoin($event, 'rejected')" />
          <div class="pager"><el-pagination v-model:current-page="reviewQuery.page_no" v-model:page-size="reviewQuery.page_size" :total="reviewTotal" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next, jumper" @size-change="loadReview" @current-change="loadReview" /></div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-dialog v-model="joinVisible" title="申请加入备选库" width="620px" destroy-on-close>
      <el-form ref="joinFormRef" :model="joinForm" :rules="joinRules" label-width="90px">
        <el-form-item label="候选人">{{ joinTarget?.name }} {{ joinTarget?.mobile || "" }}</el-form-item>
        <el-form-item v-if="matchmakerOptions.length" label="归属红娘" prop="matchmaker_id">
          <el-select v-model="joinForm.matchmaker_id" filterable placeholder="选择归属服务红娘" style="width: 100%"><el-option v-for="item in matchmakerOptions" :key="item.id" :label="`${item.name}${item.mobile ? `（${item.mobile}）` : ''}`" :value="item.id" /></el-select>
        </el-form-item>
        <el-form-item label="私有标签"><tag-select v-model="joinForm.private_tags" :options="tagOptions" /></el-form-item>
        <el-form-item label="私有备注"><el-input v-model="joinForm.private_remark" type="textarea" :rows="3" maxlength="2000" show-word-limit /></el-form-item>
        <el-form-item label="申请理由" prop="request_reason"><el-input v-model="joinForm.request_reason" type="textarea" :rows="3" maxlength="2000" show-word-limit /></el-form-item>
      </el-form>
      <template #footer><el-button @click="joinVisible = false">取消</el-button><el-button type="primary" :loading="submitLoading" @click="submitJoinRequest">提交</el-button></template>
    </el-dialog>

    <el-dialog v-model="ruleVisible" title="备选规则" width="520px" destroy-on-close>
      <el-form :model="ruleForm" label-width="190px">
        <el-form-item label="本门店加入需要审核">
          <el-switch v-model="ruleForm.store_join_requires_review" active-text="需要" inactive-text="免审自动入库" :disabled="!canUpdateRule" />
        </el-form-item>
        <el-form-item label="跨门店/品牌范围">
          <el-tag type="warning">始终需要管理员审核</el-tag>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ruleVisible = false">取消</el-button>
        <el-button v-if="canUpdateRule" type="primary" :loading="submitLoading" @click="submitRule">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="manualVisible" title="手动新增备选资源" width="980px" destroy-on-close>
      <el-form ref="manualFormRef" :model="manualForm" :rules="manualRules" label-width="110px">
        <el-tabs v-model="manualActiveTab">
          <el-tab-pane label="基础资料" name="profile">
            <el-form-item label="本人照片">
              <el-upload v-model:file-list="manualPhotoFileList" list-type="picture-card" accept="image/*" multiple :http-request="uploadManualPhoto" :on-remove="removeManualPhoto" :on-preview="previewManualPhoto">
                <el-icon><Plus /></el-icon>
              </el-upload>
            </el-form-item>
            <person-profile-fields :form="manualForm" :dict-options="manualPersonDictOptions" mobile-field="primary_mobile" />
            <el-row :gutter="16">
              <el-col v-if="matchmakerOptions.length" :span="12"><el-form-item label="归属红娘" prop="matchmaker_id"><el-select v-model="manualForm.matchmaker_id" filterable placeholder="选择归属服务红娘" style="width: 100%"><el-option v-for="item in matchmakerOptions" :key="item.id" :label="`${item.name}${item.mobile ? `（${item.mobile}）` : ''}`" :value="item.id" /></el-select></el-form-item></el-col>
              <el-col :span="24"><el-form-item label="私有标签"><tag-select v-model="manualForm.private_tags" :options="tagOptions" /></el-form-item></el-col>
              <el-col :span="24"><el-form-item label="私有备注"><el-input v-model="manualForm.private_remark" type="textarea" :rows="3" maxlength="2000" show-word-limit /></el-form-item></el-col>
            </el-row>
          </el-tab-pane>
          <el-tab-pane label="择偶要求" name="preference">
            <partner-preference-form ref="manualPreferenceFormRef" :model-value="manualForm.partner_preference" :dict-options="manualPreferenceDictOptions" :region-options="[]" :show-actions="false" />
          </el-tab-pane>
          <el-tab-pane label="资料上传" name="materials">
            <el-alert title="资料仅作为认证材料存档，后续转客户或发起认证时可复用，不会改变当前认证结果。" type="info" show-icon :closable="false" />
            <div v-if="manualCertificationItems.length" class="cert-material-grid">
              <div v-for="item in manualCertificationItems" :key="item.item_code" class="cert-material-card">
                <div class="cert-material-head">
                  <div>
                    <div class="cert-material-title">{{ item.item_name }}</div>
                    <div class="cert-material-desc">{{ item.material_desc || "资料图片存档" }}</div>
                  </div>
                  <el-upload accept="image/*" :show-file-list="false" :http-request="(options) => uploadManualCertificationMaterial(options, item)">
                    <el-button link type="primary" icon="Upload">上传</el-button>
                  </el-upload>
                </div>
                <div v-if="materialsByItem(item.item_code).length" class="cert-material-list">
                  <div v-for="material in materialsByItem(item.item_code)" :key="material.file_url" class="cert-material-item">
                    <el-image class="cert-material-image" :src="ossImage(material.file_url, { w: 160, h: 160 })" :preview-src-list="ossImageList([material.file_url], { w: 1600 })" fit="cover" preview-teleported />
                    <div class="cert-material-meta">
                      <span>{{ material.file_name || "已上传" }}</span>
                      <el-button link type="danger" @click="deleteManualCertificationMaterial(material)">删除</el-button>
                    </div>
                  </div>
                </div>
                <el-empty v-else description="暂无资料" :image-size="48" />
              </div>
            </div>
            <el-empty v-else description="暂无可上传资料项" :image-size="72" />
          </el-tab-pane>
        </el-tabs>
      </el-form>
      <template #footer><el-button @click="manualVisible = false">取消</el-button><el-button type="primary" :loading="submitLoading" @click="submitManualCreate">保存</el-button></template>
    </el-dialog>
    <el-drawer v-model="detailVisible" size="82%" destroy-on-close>
      <template #header>
        <div class="drawer-head">
          <div class="toolbar-title">{{ candidateDetail?.person.name || "备选人详情" }}</div>
          <div class="toolbar-note">
            编号：{{ candidateDetail?.person.display_no || "-" }} ·
            {{ genderText(candidateDetail?.person.gender) }} ·
            {{ candidateDetail?.person.age ?? "-" }}岁 ·
            {{ candidateDetail?.person.store_name || "未归属门店" }}
          </div>
        </div>
      </template>
      <el-skeleton v-if="detailLoading" :rows="8" animated />
      <el-tabs v-else-if="candidateDetail" v-model="detailActiveTab">
        <el-tab-pane label="基础资料" name="profile">
          <div class="photo-list">
            <el-image v-for="url in candidateDetail.person.photo_urls || []" :key="url" class="photo-item" :src="ossImage(url, { w: 160, h: 160 })" :preview-src-list="ossImageList(candidateDetail.person.photo_urls || [], { w: 1600 })" fit="cover" preview-teleported />
            <el-empty v-if="!candidateDetail.person.photo_urls?.length" description="暂无照片" :image-size="64" />
          </div>
          <el-descriptions :column="3" border>
            <el-descriptions-item label="编号">{{ candidateDetail.person.display_no || "-" }}</el-descriptions-item>
            <el-descriptions-item label="姓名">{{ candidateDetail.person.name || "-" }}</el-descriptions-item>
            <el-descriptions-item label="性别">{{ genderText(candidateDetail.person.gender) }}</el-descriptions-item>
            <el-descriptions-item label="手机号">{{ candidateDetail.person.mobile || "-" }}</el-descriptions-item>
            <el-descriptions-item label="微信">{{ candidateDetail.person.wechat || "-" }}</el-descriptions-item>
            <el-descriptions-item label="门店">{{ candidateDetail.person.store_name || "-" }}</el-descriptions-item>
            <el-descriptions-item label="年龄">{{ candidateDetail.person.age ?? "-" }}</el-descriptions-item>
            <el-descriptions-item label="出生日期">{{ candidateDetail.person.birth_date || "-" }}</el-descriptions-item>
            <el-descriptions-item label="身高">{{ candidateDetail.person.height_cm ? `${candidateDetail.person.height_cm}cm` : "-" }}</el-descriptions-item>
            <el-descriptions-item label="体重">{{ candidateDetail.person.weight_kg ? `${candidateDetail.person.weight_kg}kg` : "-" }}</el-descriptions-item>
            <el-descriptions-item label="民族">{{ dictText(ethnicityOptions, candidateDetail.person.ethnicity) }}</el-descriptions-item>
            <el-descriptions-item label="学历">{{ dictText(educationOptions, candidateDetail.person.education) }}</el-descriptions-item>
            <el-descriptions-item label="年收入">{{ dictText(incomeOptions, candidateDetail.person.annual_income) }}</el-descriptions-item>
            <el-descriptions-item label="婚况">{{ dictText(maritalOptions, candidateDetail.person.marital_status) }}</el-descriptions-item>
            <el-descriptions-item label="职业">{{ dictText(occupationOptions, candidateDetail.person.occupation_code) || candidateDetail.person.occupation || "-" }}</el-descriptions-item>
            <el-descriptions-item label="单位类型">{{ dictText(unitTypeOptions, candidateDetail.person.unit_type) }}</el-descriptions-item>
            <el-descriptions-item label="工作单位">{{ candidateDetail.person.work_company || "-" }}</el-descriptions-item>
            <el-descriptions-item label="常驻地">{{ candidateDetail.person.residence || "-" }}</el-descriptions-item>
            <el-descriptions-item label="籍贯">{{ candidateDetail.person.hometown || "-" }}</el-descriptions-item>
            <el-descriptions-item label="房产">{{ dictText(houseOptions, candidateDetail.person.house_status) }}</el-descriptions-item>
            <el-descriptions-item label="车辆">{{ dictText(carOptions, candidateDetail.person.car_status) }}</el-descriptions-item>
            <el-descriptions-item label="接受异地">{{ boolText(candidateDetail.person.accept_long_distance_self) }}</el-descriptions-item>
            <el-descriptions-item label="接受闪婚">{{ boolText(candidateDetail.person.accept_flash_marriage) }}</el-descriptions-item>
            <el-descriptions-item label="愿意搬家">{{ boolText(candidateDetail.person.willing_relocate) }}</el-descriptions-item>
            <el-descriptions-item label="结婚计划">{{ dictText(marriagePlanOptions, candidateDetail.person.marriage_plan) }}</el-descriptions-item>
            <el-descriptions-item label="个人介绍" :span="3">{{ candidateDetail.person.profile_intro || "-" }}</el-descriptions-item>
            <el-descriptions-item label="备注" :span="3">{{ candidateDetail.person.profile_remark || "-" }}</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>
        <el-tab-pane label="择偶要求" name="preference">
          <partner-preference-form :model-value="candidateDetail.partner_preference || undefined" :dict-options="manualPreferenceDictOptions" :region-options="[]" read-only :show-actions="false" />
        </el-tab-pane>
        <el-tab-pane label="认证资料" name="certification">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="认证等级">{{ candidateDetail.person.certification_level || "none" }}</el-descriptions-item>
            <el-descriptions-item label="资料质量">{{ candidateDetail.person_center?.quality?.quality_level || "-" }}</el-descriptions-item>
            <el-descriptions-item label="缺失项" :span="2">{{ missingQualityText }}</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>
        <el-tab-pane label="过程记录" name="timeline">
          <el-timeline>
            <el-timeline-item v-for="item in candidateDetail.timeline || []" :key="item.id" :timestamp="item.occurred_at">
              <div class="timeline-title">{{ timelineSourceText(item.source_type) }} · {{ item.title || "-" }}</div>
              <div class="timeline-content">{{ item.content || "-" }}</div>
              <div class="toolbar-note">操作人：{{ item.operator_user_name || item.operator_user_id || "-" }}</div>
            </el-timeline-item>
          </el-timeline>
          <el-empty v-if="!candidateDetail.timeline?.length" description="暂无过程记录" :image-size="64" />
        </el-tab-pane>
        <el-tab-pane label="备选信息" name="backup">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="服务红娘">{{ candidateDetail.candidate?.matchmaker_name || "-" }}</el-descriptions-item>
            <el-descriptions-item label="来源">{{ dictText(sourceOptions, candidateDetail.candidate?.source_type) }}</el-descriptions-item>
            <el-descriptions-item label="私有标签" :span="2">
              <el-tag v-for="tag in candidateDetail.candidate?.private_tags || []" :key="tag" size="small" class="tag">{{ dictText(tagOptions, tag) }}</el-tag>
              <span v-if="!candidateDetail.candidate?.private_tags?.length">-</span>
            </el-descriptions-item>
            <el-descriptions-item label="私有备注" :span="2">{{ candidateDetail.candidate?.private_remark || "-" }}</el-descriptions-item>
            <el-descriptions-item label="审批时间">{{ candidateDetail.candidate?.approved_at || "-" }}</el-descriptions-item>
            <el-descriptions-item label="联系方式状态">{{ candidateDetail.backup.contact_unmasked ? "已授权" : "未授权" }}</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>
      </el-tabs>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-drawer>
    <el-image-viewer v-if="manualPhotoPreviewVisible" :url-list="manualPhotoPreviewUrls" :initial-index="manualPhotoPreviewIndex" :z-index="4000" @close="manualPhotoPreviewVisible = false" />
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, onMounted, reactive, ref } from "vue";
import { Plus } from "@element-plus/icons-vue";
import { ElButton, ElImageViewer, ElMessage, ElMessageBox, ElOption, ElSelect, ElTable, ElTableColumn, ElTag, type FormInstance, type FormRules, type UploadFile, type UploadRequestOptions, type UploadUserFile } from "element-plus";
import DictAPI, { type DictDataTable } from "@/api/module_system/dict";
import CandidateAPI, { type CandidateCreateForm, type CandidateDetail, type CandidateDiscoverQuery, type CandidateDiscoverRecord, type CandidateJoinRequestForm, type CandidateJoinRequestRecord, type CandidateRecord } from "@/api/module_service/candidate";
import type { CustomerCertificationArchiveItem, CustomerCertificationMaterialForm } from "@/api/module_crm/customer";
import VipServiceAPI, { type MatchmakerOption } from "@/api/module_service/vip";
import { ROLE_ROOT } from "@/constants";
import { useUserStore } from "@/store";
import PersonProfileFields from "@/views/module_miailove/components/PersonProfileFields.vue";
import PartnerPreferenceForm from "@/views/module_miailove/components/PartnerPreferenceForm.vue";
import { ossImage, ossImageList } from "@/utils/ossImage";
import { uploadImageDirect } from "@/utils/upload";

defineOptions({ name: "MiailoveCandidate", inheritAttrs: false });

const DictSelect = defineComponent({
  props: { modelValue: [String, Number], options: { type: Array as () => DictDataTable[], default: () => [] } },
  emits: ["update:modelValue"],
  setup(props, { emit }) {
    return () => h(ElSelect, { modelValue: props.modelValue, clearable: true, style: "width: 100%", "onUpdate:modelValue": (v: unknown) => emit("update:modelValue", v) }, () => props.options.map((item) => h(ElOption, { key: item.dict_value, label: item.dict_label, value: item.dict_value || "" })));
  },
});

const MultiDictSelect = defineComponent({
  props: { modelValue: { type: Array as () => string[], default: () => [] }, options: { type: Array as () => DictDataTable[], default: () => [] } },
  emits: ["update:modelValue"],
  setup(props, { emit }) {
    return () => h(ElSelect, { modelValue: props.modelValue, multiple: true, clearable: true, filterable: true, style: "width: 100%", "onUpdate:modelValue": (v: unknown) => emit("update:modelValue", v) }, () => props.options.map((item) => h(ElOption, { key: item.dict_value, label: item.dict_label, value: item.dict_value || "" })));
  },
});

const TagSelect = defineComponent({
  props: { modelValue: { type: Array as () => string[], default: () => [] }, options: { type: Array as () => DictDataTable[], default: () => [] } },
  emits: ["update:modelValue"],
  setup(props, { emit }) {
    return () => h(ElSelect, { modelValue: props.modelValue, multiple: true, filterable: true, allowCreate: true, defaultFirstOption: true, style: "width: 100%", "onUpdate:modelValue": (v: unknown) => emit("update:modelValue", v) }, () => props.options.map((item) => h(ElOption, { key: item.dict_value, label: item.dict_label, value: item.dict_value || "" })));
  },
});

const BoolSelect = defineComponent({
  props: { modelValue: { type: Boolean, default: undefined } },
  emits: ["update:modelValue"],
  setup(props, { emit }) {
    return () => h(ElSelect, { modelValue: props.modelValue, clearable: true, style: "width: 100%", "onUpdate:modelValue": (v: unknown) => emit("update:modelValue", v) }, () => [h(ElOption, { label: "是", value: true }), h(ElOption, { label: "否", value: false })]);
  },
});

const RequestTable = defineComponent({
  props: { rows: { type: Array as () => CandidateJoinRequestRecord[], default: () => [] }, loading: Boolean, review: Boolean, statusOptions: { type: Array as () => DictDataTable[], default: () => [] }, scopeOptions: { type: Array as () => DictDataTable[], default: () => [] }, tagOptions: { type: Array as () => DictDataTable[], default: () => [] } },
  emits: ["approve", "reject", "reload"],
  setup(props, { emit }) {
    const text = (options: DictDataTable[], value?: string) => options.find((item) => item.dict_value === value)?.dict_label || value || "-";
    return () => h(ElTable, { data: props.rows, loading: props.loading, border: true, stripe: true, rowKey: "id" }, () => [
      h(ElTableColumn, { prop: "person_name", label: "候选", width: 120 }),
      h(ElTableColumn, { prop: "person_mobile", label: "手机号", width: 130 }),
      h(ElTableColumn, { prop: "person_store_name", label: "候选门店", width: 140, showOverflowTooltip: true }),
      h(ElTableColumn, { prop: "request_matchmaker_name", label: "申请红娘", width: 120 }),
      h(ElTableColumn, { label: "范围", width: 100 }, { default: ({ row }: { row: CandidateJoinRequestRecord }) => text(props.scopeOptions, row.request_scope) }),
      h(ElTableColumn, { label: "状态", width: 100 }, { default: ({ row }: { row: CandidateJoinRequestRecord }) => text(props.statusOptions, row.review_status) }),
      h(ElTableColumn, { label: "私有标签", minWidth: 150 }, { default: ({ row }: { row: CandidateJoinRequestRecord }) => (row.private_tags_snapshot || []).map((tag) => h(ElTag, { key: tag, size: "small", class: "tag" }, () => text(props.tagOptions, tag))) }),
      h(ElTableColumn, { prop: "private_remark_snapshot", label: "私有备注", minWidth: 160, showOverflowTooltip: true }),
      h(ElTableColumn, { prop: "request_reason", label: "申请理由", minWidth: 160, showOverflowTooltip: true }),
      h(ElTableColumn, { prop: "review_remark", label: "审核备注", minWidth: 140, showOverflowTooltip: true }),
      props.review ? h(ElTableColumn, { label: "操作", width: 130, fixed: "right" }, { default: ({ row }: { row: CandidateJoinRequestRecord }) => row.review_status === "pending" ? [h(ElButton, { link: true, type: "primary", onClick: () => emit("approve", row) }, () => "通过"), h(ElButton, { link: true, type: "danger", onClick: () => emit("reject", row) }, () => "驳回")] : "-" }) : null,
    ]);
  },
});

const userStore = useUserStore();
const activeTab = ref("mine");
const mineLoading = ref(false);
const discoverLoading = ref(false);
const requestLoading = ref(false);
const reviewLoading = ref(false);
const submitLoading = ref(false);
const detailLoading = ref(false);
const rows = ref<CandidateRecord[]>([]);
const discoverRows = ref<CandidateDiscoverRecord[]>([]);
const requestRows = ref<CandidateJoinRequestRecord[]>([]);
const reviewRows = ref<CandidateJoinRequestRecord[]>([]);
const candidateDetail = ref<CandidateDetail>();
const total = ref(0);
const discoverTotal = ref(0);
const requestTotal = ref(0);
const reviewTotal = ref(0);
const sourceOptions = ref<DictDataTable[]>([]);
const scopeOptions = ref<DictDataTable[]>([]);
const requestStatusOptions = ref<DictDataTable[]>([]);
const educationOptions = ref<DictDataTable[]>([]);
const incomeOptions = ref<DictDataTable[]>([]);
const maritalOptions = ref<DictDataTable[]>([]);
const ethnicityOptions = ref<DictDataTable[]>([]);
const occupationOptions = ref<DictDataTable[]>([]);
const unitTypeOptions = ref<DictDataTable[]>([]);
const houseOptions = ref<DictDataTable[]>([]);
const carOptions = ref<DictDataTable[]>([]);
const marriagePlanOptions = ref<DictDataTable[]>([]);
const tagOptions = ref<DictDataTable[]>([]);
const matchmakerOptions = ref<MatchmakerOption[]>([]);
const joinVisible = ref(false);
const manualVisible = ref(false);
const ruleVisible = ref(false);
const detailVisible = ref(false);
const detailActiveTab = ref("profile");
const joinTarget = ref<CandidateDiscoverRecord>();
const joinFormRef = ref<FormInstance>();
const manualFormRef = ref<FormInstance>();
const manualPreferenceFormRef = ref<InstanceType<typeof PartnerPreferenceForm>>();
const manualActiveTab = ref("profile");
const manualPhotoFileList = ref<UploadUserFile[]>([]);
const manualPhotoPreviewVisible = ref(false);
const manualPhotoPreviewUrls = ref<string[]>([]);
const manualPhotoPreviewIndex = ref(0);
const manualCertificationItems = ref<CustomerCertificationArchiveItem[]>([]);
const manualCertificationFileLists = reactive<Record<string, UploadUserFile[]>>({});
const manualCertificationMaterials = reactive<Record<string, CustomerCertificationMaterialForm[]>>({});

const query = reactive({ page_no: 1, page_size: 10, keyword: "", source_type: undefined as string | undefined, mine: true });
const discoverQuery = reactive<CandidateDiscoverQuery>({ scope: "store", page_no: 1, page_size: 10, preferred_education_codes: [], preferred_marital_status_codes: [], preferred_annual_income_codes: [], preferred_house_status_codes: [], preferred_car_status_codes: [] });
const requestQuery = reactive({ page_no: 1, page_size: 10, mine: true });
const reviewQuery = reactive({ page_no: 1, page_size: 10, review_status: "pending" });
const joinForm = reactive<CandidateJoinRequestForm>({ private_tags: [] });
const manualForm = reactive<CandidateCreateForm>({ name: "", gender: "2", primary_mobile: "", private_tags: [] });
const ruleForm = reactive({ store_join_requires_review: true });

const hasRoot = computed(() => (userStore.basicInfo.roles || []).some((role) => role.code === ROLE_ROOT));
const hasPerm = (permission: string) => hasRoot.value || userStore.prems.includes(permission);
const canDiscover = computed(() => hasPerm("service:candidate:discover"));
const canQueryRequest = computed(() => hasPerm("service:candidate:join_request:query"));
const canReviewRequest = computed(() => hasPerm("service:candidate:join_request:review"));
const canQueryRule = computed(() => hasPerm("service:candidate:rule:query"));
const canUpdateRule = computed(() => hasPerm("service:candidate:rule:update"));
const canAssignService = computed(() => hasPerm("service:vip:assign"));
const manualPersonDictOptions = computed(() => ({
  ethnicity: ethnicityOptions.value,
  occupation: occupationOptions.value,
  annualIncome: incomeOptions.value,
  maritalStatus: maritalOptions.value,
  education: educationOptions.value,
  unitType: unitTypeOptions.value,
  houseStatus: houseOptions.value,
  carStatus: carOptions.value,
  marriagePlan: marriagePlanOptions.value,
}));
const toPreferenceOptions = (options: DictDataTable[]) => options.map((item) => ({ label: item.dict_label || "", value: item.dict_value || "" }));
const manualPreferenceDictOptions = computed(() => ({
  education: toPreferenceOptions(educationOptions.value),
  maritalStatus: toPreferenceOptions(maritalOptions.value),
  annualIncome: toPreferenceOptions(incomeOptions.value),
  houseStatus: toPreferenceOptions(houseOptions.value),
  carStatus: toPreferenceOptions(carOptions.value),
  occupation: toPreferenceOptions(occupationOptions.value),
}));
const missingQualityText = computed(() => {
  const quality = candidateDetail.value?.person_center?.quality;
  if (!quality) return "-";
  const missing = [...(quality.missing_basic || []), ...(quality.missing_display || []), ...(quality.missing_service || [])];
  return missing.length ? missing.join("、") : "-";
});

const joinRules = reactive<FormRules<CandidateJoinRequestForm>>({ request_reason: [{ required: true, message: "请填写申请理由", trigger: "blur" }] });
const manualRules = reactive<FormRules<CandidateCreateForm>>({ name: [{ required: true, message: "请填写姓名", trigger: "blur" }], primary_mobile: [{ required: true, message: "请填写手机号", trigger: "blur" }], gender: [{ required: true, message: "请选择性别", trigger: "change" }] });

async function loadDicts() {
  const [sourceRes, scopeRes, statusRes, educationRes, incomeRes, maritalRes, ethnicityRes, occupationRes, unitRes, houseRes, carRes, planRes, tagRes] = await Promise.all([
    DictAPI.getInitDict("candidate_source_type"),
    DictAPI.getInitDict("candidate_search_scope"),
    DictAPI.getInitDict("candidate_join_request_status"),
    DictAPI.getInitDict("crm_education"),
    DictAPI.getInitDict("crm_annual_income"),
    DictAPI.getInitDict("crm_marital_status"),
    DictAPI.getInitDict("crm_ethnicity"),
    DictAPI.getInitDict("crm_occupation"),
    DictAPI.getInitDict("crm_unit_type"),
    DictAPI.getInitDict("crm_house_status"),
    DictAPI.getInitDict("crm_car_status"),
    DictAPI.getInitDict("crm_marriage_plan"),
    DictAPI.getInitDict("candidate_private_tag"),
  ]);
  sourceOptions.value = sourceRes.data.data || [];
  scopeOptions.value = scopeRes.data.data || [];
  requestStatusOptions.value = statusRes.data.data || [];
  educationOptions.value = educationRes.data.data || [];
  incomeOptions.value = incomeRes.data.data || [];
  maritalOptions.value = maritalRes.data.data || [];
  ethnicityOptions.value = ethnicityRes.data.data || [];
  occupationOptions.value = occupationRes.data.data || [];
  unitTypeOptions.value = unitRes.data.data || [];
  houseOptions.value = houseRes.data.data || [];
  carOptions.value = carRes.data.data || [];
  marriagePlanOptions.value = planRes.data.data || [];
  tagOptions.value = tagRes.data.data || [];
}

async function loadMine() {
  mineLoading.value = true;
  try {
    const res = await CandidateAPI.listCandidate(query);
    rows.value = res.data.data.items || [];
    total.value = res.data.data.total || 0;
  } finally {
    mineLoading.value = false;
  }
}

async function loadDiscover() {
  if (canAssignService.value && discoverQuery.scope === "store" && !discoverQuery.matchmaker_id) {
    discoverRows.value = [];
    discoverTotal.value = 0;
    return;
  }
  discoverLoading.value = true;
  try {
    const res = await CandidateAPI.discover(discoverQuery);
    discoverRows.value = res.data.data.items || [];
    discoverTotal.value = res.data.data.total || 0;
  } finally {
    discoverLoading.value = false;
  }
}

async function loadRequests() {
  requestLoading.value = true;
  try {
    const res = await CandidateAPI.listJoinRequests(requestQuery);
    requestRows.value = res.data.data.items || [];
    requestTotal.value = res.data.data.total || 0;
  } finally {
    requestLoading.value = false;
  }
}

async function loadReview() {
  reviewLoading.value = true;
  try {
    const res = await CandidateAPI.listJoinRequests(reviewQuery);
    reviewRows.value = res.data.data.items || [];
    reviewTotal.value = res.data.data.total || 0;
  } finally {
    reviewLoading.value = false;
  }
}

function handleTabChange() {
  if (activeTab.value === "mine") loadMine();
  if (activeTab.value === "discover" && canDiscover.value) {
    if (canAssignService.value) loadMatchmakers();
  }
  if (activeTab.value === "requests" && canQueryRequest.value) loadRequests();
  if (activeTab.value === "review" && canReviewRequest.value) loadReview();
}

function resetMine() {
  Object.assign(query, { page_no: 1, keyword: "", source_type: undefined, mine: true });
  loadMine();
}

function resetDiscover() {
  Object.assign(discoverQuery, { scope: "store", page_no: 1, page_size: 10, keyword: undefined, person_id: undefined, display_no: undefined, mobile: undefined, name: undefined, gender: undefined, age_min: undefined, age_max: undefined, height_min: undefined, height_max: undefined, weight_min: undefined, weight_max: undefined, education: undefined, annual_income: undefined, marital_status: undefined, ethnicity: undefined, occupation_code: undefined, unit_type: undefined, residence: undefined, hometown: undefined, house_status: undefined, car_status: undefined, accept_long_distance_self: undefined, accept_flash_marriage: undefined, willing_relocate: undefined, marriage_plan: undefined, has_photo: undefined, certification_level: undefined, pref_age_min: undefined, pref_age_max: undefined, pref_height_min: undefined, pref_height_max: undefined, pref_weight_min: undefined, pref_weight_max: undefined, pref_accept_long_distance: undefined, pref_accept_divorced: undefined, pref_accept_children: undefined, preferred_education_codes: [], preferred_marital_status_codes: [], preferred_annual_income_codes: [], preferred_house_status_codes: [], preferred_car_status_codes: [], strictness_level: undefined, preferred_occupation_text: undefined, preference_text: undefined });
  discoverRows.value = [];
  discoverTotal.value = 0;
}

function dictText(options: DictDataTable[], value?: string) {
  return options.find((item) => item.dict_value === value)?.dict_label || value || "-";
}

function genderText(value?: string) {
  const map: Record<string, string> = { "0": "男", "1": "女", "2": "未知", male: "男", female: "女", unknown: "未知" };
  return value ? map[value] || value : "-";
}

function boolText(value?: boolean) {
  if (value === true) return "是";
  if (value === false) return "否";
  return "-";
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
  return value ? map[value] || value : "-";
}

async function loadMatchmakers() {
  if (!canAssignService.value) {
    matchmakerOptions.value = [];
    return;
  }
  try {
    const response = await VipServiceAPI.listMatchmakers();
    matchmakerOptions.value = response.data.data || [];
  } catch {
    matchmakerOptions.value = [];
  }
}

async function openJoinRequest(row: CandidateDiscoverRecord) {
  if (canAssignService.value && !discoverQuery.matchmaker_id) {
    ElMessage.warning("请先选择归属红娘");
    return;
  }
  joinTarget.value = row;
  Object.assign(joinForm, { person_id: row.id, scope: discoverQuery.scope, matchmaker_id: discoverQuery.matchmaker_id, private_tags: [], private_remark: undefined, request_reason: undefined });
  await loadMatchmakers();
  joinVisible.value = true;
}

async function openCandidateDetail(row: CandidateRecord) {
  if (!row.id) return;
  detailVisible.value = true;
  detailActiveTab.value = "profile";
  detailLoading.value = true;
  candidateDetail.value = undefined;
  try {
    const res = await CandidateAPI.detailCandidate(row.id);
    candidateDetail.value = res.data.data;
  } finally {
    detailLoading.value = false;
  }
}

async function openRuleDialog() {
  const res = await CandidateAPI.getRule();
  ruleForm.store_join_requires_review = res.data.data.store_join_requires_review;
  ruleVisible.value = true;
}

async function submitRule() {
  submitLoading.value = true;
  try {
    await CandidateAPI.updateRule({ store_join_requires_review: ruleForm.store_join_requires_review });
    ElMessage.success("备选规则已保存");
    ruleVisible.value = false;
  } finally {
    submitLoading.value = false;
  }
}

async function submitJoinRequest() {
  const valid = await joinFormRef.value?.validate();
  if (!valid) return;
  submitLoading.value = true;
  try {
    await CandidateAPI.createJoinRequest(joinForm);
    ElMessage.success("加入申请已提交");
    joinVisible.value = false;
    await loadDiscover();
    if (canQueryRequest.value) await loadRequests();
  } finally {
    submitLoading.value = false;
  }
}

async function reviewJoin(row: CandidateJoinRequestRecord, status: "approved" | "rejected") {
  if (!row.id) return;
  const title = status === "approved" ? "通过申请" : "驳回申请";
  const { value } = await ElMessageBox.prompt("审核备注", title, { inputType: "textarea", confirmButtonText: "确定", cancelButtonText: "取消" }).catch(() => ({ value: undefined }));
  if (value === undefined) return;
  await CandidateAPI.reviewJoinRequest(row.id, { review_status: status, review_remark: value });
  ElMessage.success("审核已处理");
  await loadReview();
}

async function openManualCreate() {
  Object.assign(manualForm, {
    name: "",
    gender: "2",
    primary_mobile: "",
    wechat: undefined,
    birth_date: undefined,
    height_cm: undefined,
    weight_kg: undefined,
    ethnicity: undefined,
    occupation: undefined,
    occupation_code: undefined,
    annual_income: undefined,
    marital_status: undefined,
    education: undefined,
    graduated_school: undefined,
    major: undefined,
    unit_type: undefined,
    job_title: undefined,
    work_company: undefined,
    hometown: undefined,
    residence: undefined,
    house_status: undefined,
    car_status: undefined,
    accept_long_distance_self: undefined,
    accept_flash_marriage: undefined,
    willing_relocate: undefined,
    marriage_plan: undefined,
    family_background: undefined,
    profile_remark: undefined,
    photo_urls: [],
    profile_intro: undefined,
    id_card_no: undefined,
    matchmaker_id: undefined,
    private_tags: [],
    private_remark: undefined,
    partner_preference: undefined,
    certification_materials: [],
  });
  manualActiveTab.value = "profile";
  manualPhotoFileList.value = [];
  manualPhotoPreviewVisible.value = false;
  resetManualCertificationMaterials();
  await loadMatchmakers();
  await loadManualCertificationItems();
  manualVisible.value = true;
}

async function submitManualCreate() {
  const valid = await manualFormRef.value?.validate();
  if (!valid) return;
  submitLoading.value = true;
  try {
    manualForm.photo_urls = manualPhotoFileList.value.map((item) => item.url).filter((url): url is string => Boolean(url));
    manualForm.partner_preference = manualPreferenceFormRef.value?.getValue();
    manualForm.certification_materials = Object.values(manualCertificationMaterials).flat();
    await CandidateAPI.manualCreate(manualForm);
    ElMessage.success("备选资源已保存");
    manualVisible.value = false;
    await loadMine();
  } finally {
    submitLoading.value = false;
  }
}

function resetManualCertificationMaterials() {
  for (const key of Object.keys(manualCertificationFileLists)) delete manualCertificationFileLists[key];
  for (const key of Object.keys(manualCertificationMaterials)) delete manualCertificationMaterials[key];
}

function materialsByItem(itemCode: string) {
  return manualCertificationMaterials[itemCode] || [];
}

async function loadManualCertificationItems() {
  const res = await CandidateAPI.listCertificationArchiveItems();
  manualCertificationItems.value = res.data.data || [];
  for (const item of manualCertificationItems.value) {
    manualCertificationFileLists[item.item_code] = [];
    manualCertificationMaterials[item.item_code] = [];
  }
}

async function uploadManualPhoto(options: UploadRequestOptions) {
  const fileInfo = await uploadImageDirect(options.file, "crm_lead_photo");
  const current = manualPhotoFileList.value.find((item) => item.uid === options.file.uid);
  if (current) {
    current.name = fileInfo.file_name || fileInfo.origin_name || options.file.name;
    current.url = fileInfo.file_url;
  }
  options.onSuccess?.(fileInfo);
}

function removeManualPhoto(file: UploadFile) {
  manualPhotoFileList.value = manualPhotoFileList.value.filter((item) => item.uid !== file.uid && item.url !== file.url);
}

function previewManualPhoto(file: UploadFile) {
  const urls = manualPhotoFileList.value.map((item) => item.url).filter((url): url is string => Boolean(url));
  if (!urls.length) return;
  manualPhotoPreviewUrls.value = ossImageList(urls, { w: 1600 });
  manualPhotoPreviewIndex.value = Math.max(urls.findIndex((url) => url === file.url), 0);
  manualPhotoPreviewVisible.value = true;
}

async function uploadManualCertificationMaterial(options: UploadRequestOptions, item: CustomerCertificationArchiveItem) {
  const fileInfo = await uploadImageDirect(options.file, "certification_material");
  const current = manualCertificationFileLists[item.item_code]?.find((row) => row.uid === options.file.uid);
  if (current) {
    current.name = fileInfo.file_name || fileInfo.origin_name || options.file.name;
    current.url = fileInfo.file_url;
  }
  const material: CustomerCertificationMaterialForm = {
    item_code: item.item_code,
    item_name: item.item_name,
    material_type: "image",
    file_name: fileInfo.file_name || fileInfo.origin_name || options.file.name,
    file_path: fileInfo.object_key || fileInfo.file_path,
    file_url: fileInfo.file_url,
    payload: { origin_name: fileInfo.origin_name, scene: fileInfo.scene },
  };
  const list = manualCertificationMaterials[item.item_code] || [];
  manualCertificationMaterials[item.item_code] = [material, ...list.filter((row) => row.file_url !== material.file_url)];
  options.onSuccess?.(fileInfo);
}

function removeManualCertificationMaterial(file: UploadFile, item: CustomerCertificationArchiveItem) {
  manualCertificationMaterials[item.item_code] = (manualCertificationMaterials[item.item_code] || []).filter((row) => row.file_url !== file.url);
}

function deleteManualCertificationMaterial(material: CustomerCertificationMaterialForm) {
  manualCertificationMaterials[material.item_code] = (manualCertificationMaterials[material.item_code] || []).filter((row) => row.file_url !== material.file_url);
}

onMounted(async () => {
  await loadDicts();
  if (canAssignService.value) await loadMatchmakers();
  await loadMine();
});
</script>

<style scoped>
.candidate-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
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

.toolbar-actions {
  display: inline-flex;
  gap: 8px;
}

.range {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 12px minmax(0, 1fr);
  align-items: center;
  gap: 6px;
  width: 100%;
}

.range :deep(.el-input-number) {
  width: 100%;
}

.filter-collapse {
  margin-bottom: 12px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-bottom: 12px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  padding-top: 16px;
}

.tag {
  margin-right: 4px;
}

.drawer-head {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.photo-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 12px;
}

.photo-item {
  width: 120px;
  height: 120px;
  border-radius: 6px;
}

.timeline-title {
  color: var(--el-text-color-primary);
  font-weight: 600;
}

.timeline-content {
  margin-top: 4px;
  color: var(--el-text-color-regular);
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
</style>
