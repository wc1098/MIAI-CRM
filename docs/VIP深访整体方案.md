# 人员深访画像公共基座方案

更新时间：2026-05-27

## 1. 目标口径

原“VIP 深访”调整为“人员深访画像公共基座”。深访能力不再只服务 VIP，而是上提到统一人员主体 `Person` 层，作为所有客户、候选资源、VIP 的高维画像入口。

核心目标：

- 所有 `Person` 都可以沉淀深访画像。
- VIP 首次深访仍是服务强流程。
- 候选资源、建档客户、普通资源可以按需深访，用于补足匹配画像。
- 匹配推荐读取 Person 当前画像，而不是只读取 VIP 画像。
- 服务人员只需要填写结构化深访表单并保存，系统自动更新当前画像和匹配画像。
- 首版不做录音、ASR、自动 AI 量表、画像多版本管理，先把低成本可用闭环跑通。

一句话：

```text
红娘填写结构化深访 -> 自动更新当前人员画像 -> 自动触发现有匹配向量重建 -> 后续推荐更精准
```

## 2. 当前系统基础

### 2.1 已有业务基础

- 系统已经以 `Person` 作为统一人员主体。
- 线索、建档客户、VIP、小程序用户、候选资源都围绕 `Person` 建模。
- VIP 服务模块已有 `deep_interview` 表和“新增服务深访”能力。
- VIP 服务详情页已有深访记录展示和新增深访弹窗。
- 候选备选库、推荐、约见、课程核销、关单等 VIP 服务主链路已经成型。

### 2.2 已有匹配技术基座

当前项目已经具备匹配画像与向量能力，不需要重新引入向量服务。

已有模块：

- `backend/app/plugin/module_match/`
- `person_match_profile`：人员匹配画像快照。
- `person_match_vector`：人员匹配向量。
- `person_match_vector_task`：人员匹配向量异步任务。
- `LocalText2VecProvider`：本地 `text2vec-base-chinese` embedding 提供者。
- `pgvector`：PostgreSQL 向量存储与相似度计算。
- `MatchProfileService.mark_dirty(...)`：标记画像待重建并投递向量任务。
- `MatchProfileService.score_people(...)`：结构化评分 + 向量评分的候选匹配。

当前推荐评分已经包含：

- 结构化硬筛与评分。
- 正向向量：本人择偶要求 vs 候选人画像。
- 反向向量：候选人择偶要求 vs 本人画像。
- 综合排序与匹配理由。

因此，深访画像公共基座的重点不是新增 AI/向量技术，而是：

```text
把红娘深访沉淀为 Person 当前画像，并接入现有 module_match。
```

## 3. 产品原则

### 3.1 以当前画像为准

用户数量和深访频次都不大，首版不需要复杂画像版本管理。

规则：

- 每个 Person 维护一份当前画像。
- 每次有效深访保存后，自动覆盖/更新当前画像。
- 当前画像以服务红娘最近一次有效深访为准。
- 匹配推荐永远读取当前画像。
- 深访历史只作为服务过程和审计记录，不作为多版本画像让红娘选择。

### 3.2 操作自动化

服务人员不需要理解“保存记录”和“同步画像”的区别。

规则：

- 页面只有“保存深访”主按钮。
- 保存后自动更新当前人员画像。
- 保存后自动触发匹配画像重建。
- 不提供“是否同步画像”的选择。
- 不要求红娘手动重建向量。

### 3.3 VIP强流程，普通资源弱流程

- VIP：分配给服务红娘后必须完成首次深访。
- 候选资源：加入备选库后可做深访，非强制。
- 建档客户：可做面谈画像，后续转 VIP 后继承。
- 普通 Person：可在人员中心补画像，用于匹配质量提升。

### 3.4 隐私分层

- 完整深访内容属于服务深度隐私。
- 销售默认不可见完整深访。
- 销售最多看到允许展示的脱敏摘要或红娘印象。
- 服务红娘、店长、管理员按归属和数据范围查看。
- 普通接口不得返回高敏感附件 URL。首版不做录音，因此录音审计后置。

## 4. 数据设计

### 4.1 改造 `deep_interview`

保留现有 `deep_interview` 表，不推倒重建。将它从 VIP 专属深访扩展为 Person 级深访记录。

当前已有关键字段：

```text
brand_id
service_case_id
vip_id
person_id
contract_id
matchmaker_id
interview_type
interviewed_at
content
keywords
summary
ai_summary
ai_dimension_scores
audio_file_url
interview_status
void_reason
```

建议调整：

```text
service_case_id  改为可空
vip_id           改为可空
contract_id      改为可空
```

建议新增：

```text
interview_scope      深访场景：vip_service/candidate/customer/general
customer_id          可空，建档客户场景
backup_item_id       可空，备选库场景
interview_method     深访方式：offline/phone/wechat_voice/video/history
structured_payload   结构化深访表单 JSON
manual_notes         红娘备注
is_current_source    是否当前画像来源
voided_by            作废人
voided_at            作废时间
```

字段说明：

- `person_id` 是核心绑定字段，所有深访都必须绑定 Person。
- `interview_scope` 标识业务场景。
- VIP 场景继续绑定 `service_case_id/vip_id/contract_id`。
- 候选场景可绑定 `backup_item_id`。
- 建档客户场景可绑定 `customer_id`。
- `structured_payload` 保存完整结构化引导表单内容。
- `is_current_source` 仅用于快速识别当前画像来源记录。

### 4.2 新增 `person_profile_insight`

新增 Person 当前深访画像表。每个 Person 最多一条有效当前画像。

建议字段：

```text
id
brand_id
person_id
source_interview_id
source_scope
personality_tags
family_background
relationship_history
marriage_view
communication_style
emotional_needs
hard_reject_items
soft_preference_items
compromise_items
risk_level
risk_notes
communication_taboo
recommendation_strategy
matchmaker_comment
public_matchmaker_impression
keywords
profile_status
updated_by
updated_at
created_at
```

规则：

- `person_id` 唯一。
- `source_interview_id` 指向当前画像来源深访。
- `profile_status` 首版建议：`active/stale`。
- 深访保存后自动 upsert 当前画像。
- 不做画像版本表。

### 4.3 与现有匹配表关系

画像进入匹配的链路：

```text
deep_interview
  -> person_profile_insight
  -> person_match_profile.self_input_text / preference_input_text
  -> person_match_vector_task
  -> text2vec-base-chinese
  -> person_match_vector
  -> pgvector
  -> MatchProfileService.score_people()
```

需要扩展 `MatchProfileService._build_profile_payload(...)`：

- 读取 `person_profile_insight`。
- 将性格、家庭、情感经历、婚恋观、沟通方式、风险点、推荐策略、红娘印象等合并进 `self_input_text`。
- 将硬性拒绝项、软性偏好、可妥协项等合并进 `preference_input_text`。
- 保持现有 `self_profile/preference` 两类向量，不新增 vector_type。

## 5. 结构化引导表单

### 5.1 表单定位

结构化引导不是问卷系统，不做题库、题目版本、答案统计。

它是一张固定业务表单，用于引导服务人员把关键判断填完整。

保存后：

- 完整内容写入 `deep_interview.structured_payload`。
- 当前有用画像写入 `person_profile_insight`。
- 匹配画像自动重建。

### 5.2 表单分段

#### A. 基本信息

- 深访场景：VIP服务 / 候选资源 / 建档客户 / 普通画像。
- 深访类型：首次 / 阶段 / 结案 / 补充。
- 深访方式：线下面谈 / 电话 / 微信语音 / 视频 / 历史补录。
- 深访时间。
- 访谈人/红娘。
- 关联业务对象：服务工单、备选库、客户档案，按场景自动带出。

#### B. 个人与家庭背景

- 家庭结构。
- 父母关系与家庭氛围。
- 经济/居住情况补充。
- 家庭对婚姻的参与程度：低 / 中 / 高。
- 是否存在家人强干预。
- 家庭背景备注。

#### C. 性格与相处模式

- 性格标签：慢热、外向、内向、理性、感性、强势、温和、敏感、稳定、重视边界感等。
- 沟通风格：主动表达、被动表达、回避冲突、直接沟通、需要引导。
- 冲突处理方式。
- 情绪稳定性：低 / 中 / 高。
- 亲密关系节奏：慢热 / 正常 / 快速推进。
- 红娘观察。

#### D. 情感经历与婚恋观

- 感情经历摘要。
- 上段关系结束原因。
- 当前结婚意愿：低 / 中 / 高。
- 期望结婚时间。
- 对婚姻中角色分工的看法。
- 对父母同住、异地、婚史、子女的接受度。
- 婚恋观备注。

#### E. 择偶偏好补充

这部分不替代现有择偶要求，而是补充“真实偏好”和“红娘判断”。

- 硬性拒绝项。
- 软性偏好。
- 可妥协项。
- 加分项。
- 雷区。
- 对方性格偏好。
- 对方家庭偏好。
- 对方职业/生活方式偏好。

#### F. 服务与推荐策略

- 推荐节奏：保守 / 正常 / 积极。
- 推荐前是否需要充分铺垫。
- 适合的候选类型。
- 不适合的候选类型。
- 首次沟通建议。
- 约见安排注意事项。
- 红娘推荐策略。

#### G. 风险与沟通禁忌

- 风险等级：低 / 中 / 高。
- 风险标签：情绪、家庭、经济、婚史、隐私、期望过高、沟通配合度低等。
- 沟通禁忌。
- 内部提醒。
- 是否影响推荐。

#### H. 摘要与红娘印象

- 内部摘要：给红娘/店长看的完整服务摘要。
- 对外红娘印象：脱敏、温和、可用于小程序或候选资料。
- 关键词。

### 5.3 `structured_payload` 示例

```json
{
  "family": {
    "family_structure": "独生女，父母同住本市",
    "family_involvement_level": "medium",
    "family_strong_interference": false,
    "family_notes": "父母会参与择偶意见，但最终尊重本人"
  },
  "personality": {
    "tags": ["慢热", "稳定", "重视边界感"],
    "communication_style": "需要对方主动打开话题",
    "conflict_style": "倾向冷静后再沟通",
    "emotional_stability": "high",
    "relationship_pace": "slow"
  },
  "relationship": {
    "history_summary": "有一段三年恋爱经历",
    "last_relationship_end_reason": "长期规划不一致",
    "marriage_intention": "high",
    "marriage_timeline": "一年内明确关系方向",
    "marriage_view": "重视稳定沟通和家庭责任"
  },
  "preference_insight": {
    "hard_reject_items": ["异地长期分居", "情绪不稳定"],
    "soft_preference_items": ["生活规律", "家庭观念稳定"],
    "compromise_items": ["收入可适当放宽"],
    "bonus_items": ["表达主动", "工作稳定"],
    "taboo_items": ["催婚压迫感强"]
  },
  "service_strategy": {
    "recommendation_pace": "normal",
    "need_preheat": true,
    "candidate_strategy": "适合成熟稳定、表达主动型候选",
    "first_contact_advice": "建议从生活节奏和家庭观念切入",
    "meeting_notes": "初次约见避免直接讨论年龄压力"
  },
  "risk": {
    "risk_level": "medium",
    "risk_tags": ["家庭参与", "慢热"],
    "communication_taboo": "避免一开始强调年龄压力",
    "internal_notes": "需要红娘前期做关系铺垫"
  },
  "summary": {
    "internal_summary": "客户慢热但目标清晰，需要红娘做前期铺垫。",
    "public_matchmaker_impression": "性格稳定，重视真诚沟通与长期规划。",
    "keywords": ["慢热", "稳定", "家庭观念", "长期规划"]
  }
}
```

## 6. 自动同步规则

### 6.1 保存即同步

服务人员只有一个主操作：

```text
保存深访
```

保存后系统自动执行：

1. 写入 `deep_interview`。
2. 将旧的当前来源深访 `is_current_source` 置为 false。
3. 将本次深访 `is_current_source` 置为 true。
4. upsert `person_profile_insight`。
5. 设置 `person_profile_insight.source_interview_id = 当前深访 ID`。
6. 调用 `MatchProfileService.mark_dirty(...)`。
7. 前端提示“已保存，人员画像和匹配画像已更新”。

### 6.2 匹配重建

保存深访后统一调用：

```python
await MatchProfileService.mark_dirty(
    db=db,
    person_id=person_id,
    dirty_parts=["self_profile", "preference"],
    source_type="deep_interview",
    source_id=interview.id,
)
```

如果后续要更精细，可以按字段变化判断是否只重建 `self_profile`。首版为了简单，统一重建 `self_profile` 和 `preference`。

### 6.3 作废规则

首版不做复杂版本回滚。

规则：

- 如果作废的不是当前画像来源深访，只更新深访状态，不影响当前画像。
- 如果作废的是当前画像来源深访：
  - 当前深访状态改为作废。
  - `person_profile_insight.profile_status = stale`。
  - `person_profile_insight.source_interview_id` 可保留，用于说明来源已作废。
  - 页面提示“当前画像来源已作废，请重新深访”。
  - 触发匹配画像重建。
- 不自动回滚到上一条深访。

## 7. API设计

### 7.1 公共人员深访接口

建议新增在 CRM Person 上下文：

```text
GET  /crm/person/{person_id}/interviews
POST /crm/person/{person_id}/interviews
GET  /crm/person/{person_id}/interviews/{interview_id}
PUT  /crm/person/{person_id}/interviews/{interview_id}
POST /crm/person/{person_id}/interviews/{interview_id}/void

GET  /crm/person/{person_id}/profile-insight
PUT  /crm/person/{person_id}/profile-insight
```

说明：

- `POST /interviews` 保存后自动同步画像。
- `PUT /interviews/{id}` 修改后自动同步画像。
- `PUT /profile-insight` 允许店长/红娘直接维护当前画像，保存后同样触发匹配重建。

### 7.2 保留VIP兼容接口

保留当前 VIP 服务上下文接口，避免大改已实现页面：

```text
POST /service/vip/interview/{case_id}
```

内部改为调用公共深访服务，并自动写入：

```text
interview_scope = vip_service
person_id = case.person_id
service_case_id = case.id
vip_id = case.vip_id
contract_id = case.contract_id
matchmaker_id = case.owner_matchmaker_id
```

后续可新增更统一的 VIP 上下文接口：

```text
GET  /service/vip/{case_id}/interviews
POST /service/vip/{case_id}/interviews
```

### 7.3 候选备选库入口

可在候选上下文提供便捷接口，内部仍走公共 Person 深访：

```text
GET  /candidate/{backup_item_id}/interviews
POST /candidate/{backup_item_id}/interviews
```

首版也可以不单独做候选接口，直接在前端拿到 `person_id` 后调用公共 Person 接口。

## 8. 权限设计

### 8.1 权限码建议

```text
crm:person:interview:query
crm:person:interview:create
crm:person:interview:update
crm:person:interview:void
crm:person:profile_insight:query
crm:person:profile_insight:update
```

VIP 兼容权限可继续保留：

```text
service:vip:deep_interview
```

后续可逐步拆细：

```text
service:vip:deep_interview:update
service:vip:deep_interview:void
```

### 8.2 角色口径

服务红娘：

- 可维护自己名下 VIP 的深访画像。
- 可维护自己备选库中候选人的深访画像。
- 可查看自己有服务关系或备选关系的 Person 画像。

店长：

- 可维护本门店 VIP、客户、候选资源的深访画像。
- 可作废本门店深访记录。

老板/管理员：

- 可全局查看和维护。

销售：

- 默认不可查看完整深访。
- 可按业务需要查看脱敏红娘印象或基础摘要。
- 不可编辑服务深访字段。

## 9. 前端设计

### 9.1 公共组件

新增公共组件：

```text
frontend/src/views/module_miailove/components/PersonInsightInterviewForm.vue
frontend/src/views/module_miailove/components/PersonProfileInsightPanel.vue
```

职责：

- `PersonInsightInterviewForm.vue`：结构化深访表单。
- `PersonProfileInsightPanel.vue`：当前人员画像展示与编辑。

### 9.2 页面入口

首版建议三个入口：

1. VIP 服务详情页
   - 保留“新增深访”按钮。
   - 表单替换为公共结构化深访组件。
   - 保存后自动更新当前人员画像。

2. 候选备选库详情
   - 增加“画像访谈”入口。
   - 红娘可对备选库候选人补充画像。

3. Person 中心详情
   - 增加“深访记录 / 当前画像”Tab。
   - 管理员、店长用于统一查看和维护。

### 9.3 交互原则

- 主按钮只有“保存深访”。
- 不出现“是否同步画像”。
- 保存成功提示：“已保存，人员画像和匹配画像已更新”。
- 当前画像区域显示：

```text
当前画像来源：2026-05-27 首次深访，红娘：张三
```

- 当前画像来源被作废时，显示：

```text
当前画像来源已作废，请重新深访。
```

## 10. 开发进度拆分

### 阶段一：公共基座与数据迁移

目标：把 VIP 深访上提为 Person 级公共能力，但先不改复杂页面。

任务：

- 修改 `DeepInterviewModel`，增加公共字段。
- 增加 Alembic 迁移。
- 新增 `PersonProfileInsightModel`。
- 新增公共 schema。
- 新增公共服务类，例如 `PersonInsightService`。
- 实现保存深访后自动 upsert 当前画像。
- 实现保存深访后自动调用 `MatchProfileService.mark_dirty(...)`。
- 扩展 `MatchProfileService._build_profile_payload(...)`，读取 `person_profile_insight`。

验收：

- 可以给任意 Person 保存深访。
- 保存后自动生成/更新当前画像。
- 保存后产生匹配向量任务。
- 现有 VIP 深访接口仍可用。

### 阶段二：公共接口与VIP页面接入

目标：先让 VIP 服务详情用上公共结构化深访。

任务：

- 新增 Person 深访接口。
- 新增 Person 当前画像接口。
- 当前 VIP `create_interview_service` 改为调用公共服务。
- 前端 VIP 深访弹窗替换为结构化表单。
- VIP 详情增加当前人员画像展示。
- VIP 列表支持待深访筛选。

验收：

- VIP 分配后可以看到待深访。
- 保存首次深访后自动退出待深访。
- VIP 详情可以看到当前画像。
- 匹配候选时使用更新后的画像。

### 阶段三：候选备选库与Person中心接入

目标：让非 VIP 资源也能沉淀高维画像。

任务：

- 候选备选库详情增加“画像访谈”入口。
- Person 中心增加“深访记录 / 当前画像”Tab。
- 实现按权限查看完整深访和脱敏摘要。
- 店长/管理员支持直接编辑当前画像。

验收：

- 红娘可以给备选库候选人做画像访谈。
- 候选人画像更新后参与后续匹配。
- Person 中心能查看该人的深访记录和当前画像。

### 阶段四：权限、审计与报表小计

目标：补齐管理和合规。

任务：

- 同步新增权限码到权限矩阵。
- 补充角色权限。
- 查看完整深访记录审计。
- 作废深访留痕。
- 红娘服务报表增加深访数、待深访数。
- 店长视角增加本门店待深访统计。

验收：

- 销售不能查看完整深访。
- 红娘只能维护自己名下或自己备选库的人员。
- 店长可维护本门店。
- 作废必须填写原因。
- 报表能统计待深访和已深访。

### 阶段五：后续增强

该阶段不进入首版范围。

可选能力：

- 录音上传。
- ASR 转写。
- 红娘校对转写文本。
- AI 摘要。
- AI 四维量表。
- 自动生成红娘印象。
- AI 推荐理由增强。
- 敏感附件访问审计。

## 11. 与原VIP深访方案的差异

| 项目 | 原方案 | 新方案 |
| --- | --- | --- |
| 能力归属 | VIP 服务模块 | Person 公共画像基座 |
| 深访对象 | 主要是 VIP | 所有 Person |
| VIP 深访 | 强流程 | 仍是强流程 |
| 候选资源深访 | 后续考虑 | 首版纳入公共能力 |
| 画像同步 | 可选择同步 | 保存后自动同步 |
| 画像版本 | 可能保留多版本 | 不做多版本，以当前画像为准 |
| 匹配接入 | 后续接入 | 首版必须接入现有 module_match |
| 录音/ASR | 曾考虑首版 | 后续增强 |
| AI 量表 | 曾考虑首版预留 | 后续增强 |

## 12. 待确认问题

1. `deep_interview` 是否接受将 `service_case_id/vip_id/contract_id` 改为可空。建议接受，这是最小改动实现公共化的关键。
2. `person_profile_insight` 字段是否按本方案先固定，后续再扩展。建议先固定，避免做重型问卷系统。
3. 销售是否能看 `public_matchmaker_impression`。建议可以看脱敏红娘印象，不可看完整深访。
4. 候选备选库首版是否必须接入。建议阶段三接入，不阻塞 VIP 首版。
5. 作废当前来源深访后，画像是否保留但标记 `stale`。建议保留并标记，避免误删有用信息。

