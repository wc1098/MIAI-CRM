import request from "@/utils/request";
import type { PartnerPreference } from "@/api/module_crm/lead";
import type { PersonDetail, PersonTimelineItem } from "@/api/module_crm/person";

const API_PATH = "/service/vip";

const VipServiceAPI = {
  listPendingAssign(query?: VipPageQuery) {
    return request<ApiResponse<PageResult<ServiceCaseTable[]>>>({
      url: `${API_PATH}/pending-assign`,
      method: "get",
      params: query,
    });
  },
  listVip(query?: VipPageQuery) {
    return request<ApiResponse<PageResult<ServiceCaseTable[]>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },
  detailVip(id: number) {
    return request<ApiResponse<ServiceCaseDetail>>({
      url: `${API_PATH}/detail/${id}`,
      method: "get",
    });
  },
  getCustomerProfile(id: number) {
    return request<ApiResponse<ServiceCustomerProfile>>({
      url: `${API_PATH}/${id}/customer-profile`,
      method: "get",
    });
  },
  updateCustomerProfile(id: number, body: ServiceCustomerProfileForm) {
    return request<ApiResponse<ServiceCustomerProfile>>({
      url: `${API_PATH}/${id}/customer-profile`,
      method: "put",
      data: body,
    });
  },
  getCertification(id: number) {
    return request<ApiResponse<ServiceCertification[]>>({
      url: `${API_PATH}/${id}/certification`,
      method: "get",
    });
  },
  getCertificationArchiveItems(id: number) {
    return request<ApiResponse<ServiceCertificationArchiveItem[]>>({
      url: `${API_PATH}/${id}/certification-archive-items`,
      method: "get",
    });
  },
  saveCertificationMaterial(id: number, body: ServiceCertificationMaterialForm) {
    return request<ApiResponse<ServiceCertification>>({
      url: `${API_PATH}/${id}/certification-material`,
      method: "post",
      data: body,
    });
  },
  deleteCertificationMaterial(id: number, materialId: number) {
    return request<ApiResponse>({
      url: `${API_PATH}/${id}/certification-material/${materialId}`,
      method: "delete",
    });
  },
  getTimeline(id: number) {
    return request<ApiResponse<ServiceTimelineItem[]>>({
      url: `${API_PATH}/${id}/timeline`,
      method: "get",
    });
  },
  createCustomerProcessRecord(id: number, body: ServiceCustomerProcessForm) {
    return request<ApiResponse<ServiceTimelineItem>>({
      url: `${API_PATH}/${id}/customer-process-record`,
      method: "post",
      data: body,
    });
  },
  createAppointment(id: number, body: ServiceCustomerProcessForm) {
    return request<ApiResponse<ServiceTimelineItem>>({
      url: `${API_PATH}/${id}/appointment`,
      method: "post",
      data: body,
    });
  },
  getLifecycle(id: number) {
    return request<ApiResponse<ServiceLifecycleItem[]>>({
      url: `${API_PATH}/${id}/lifecycle`,
      method: "get",
    });
  },
  getContracts(id: number) {
    return request<ApiResponse<ServiceContractRecord[]>>({
      url: `${API_PATH}/${id}/contracts`,
      method: "get",
    });
  },
  getWorkSummary(id: number) {
    return request<ApiResponse<ServiceWorkSummary>>({
      url: `${API_PATH}/${id}/work-summary`,
      method: "get",
    });
  },
  getPlan(id: number) {
    return request<ApiResponse<ServicePlan>>({
      url: `${API_PATH}/${id}/plan`,
      method: "get",
    });
  },
  updatePlan(id: number, body: ServicePlanForm) {
    return request<ApiResponse<ServicePlan>>({
      url: `${API_PATH}/${id}/plan`,
      method: "put",
      data: body,
    });
  },
  publishPlan(id: number) {
    return request<ApiResponse<ServicePlan>>({
      url: `${API_PATH}/${id}/plan/publish`,
      method: "post",
    });
  },
  rebuildPlan(id: number) {
    return request<ApiResponse<ServicePlan>>({
      url: `${API_PATH}/${id}/plan/rebuild-from-entitlements`,
      method: "post",
    });
  },
  autoSchedulePlan(id: number) {
    return request<ApiResponse<ServicePlan>>({
      url: `${API_PATH}/${id}/plan/auto-schedule`,
      method: "post",
    });
  },
  updatePlanItem(id: number, itemId: number, body: ServicePlanItemForm) {
    return request<ApiResponse<ServicePlanItem>>({
      url: `${API_PATH}/${id}/plan/items/${itemId}`,
      method: "put",
      data: body,
    });
  },
  cancelPlanItem(id: number, itemId: number, body: { reason?: string }) {
    return request<ApiResponse<ServicePlanItem>>({
      url: `${API_PATH}/${id}/plan/items/${itemId}/cancel`,
      method: "post",
      data: body,
    });
  },
  skipPlanItem(id: number, itemId: number, body: { reason?: string }) {
    return request<ApiResponse<ServicePlanItem>>({
      url: `${API_PATH}/${id}/plan/items/${itemId}/skip`,
      method: "post",
      data: body,
    });
  },
  restorePlanItem(id: number, itemId: number, body: { reason?: string }) {
    return request<ApiResponse<ServicePlanItem>>({
      url: `${API_PATH}/${id}/plan/items/${itemId}/restore`,
      method: "post",
      data: body,
    });
  },
  matchCandidates(id: number, itemId: number, body: MatchCandidateQuery) {
    return request<ApiResponse<PageResult<MatchCandidate[]>>>({
      url: `${API_PATH}/${id}/plan/items/${itemId}/match-candidates`,
      method: "post",
      data: body,
    });
  },
  getServiceCandidateDetail(id: number, personId: number) {
    return request<ApiResponse<ServiceCandidateDetail>>({
      url: `${API_PATH}/${id}/candidates/${personId}`,
      method: "get",
    });
  },
  createRecommendation(id: number, body: RecommendationForm) {
    return request<ApiResponse<ServiceRecommendation>>({
      url: `${API_PATH}/${id}/recommendations`,
      method: "post",
      data: body,
    });
  },
  listRecommendations(id: number) {
    return request<ApiResponse<ServiceRecommendation[]>>({
      url: `${API_PATH}/${id}/recommendations`,
      method: "get",
    });
  },
  updateRecommendation(id: number, recommendationId: number, body: RecommendationUpdateForm) {
    return request<ApiResponse<ServiceRecommendation>>({
      url: `${API_PATH}/${id}/recommendations/${recommendationId}`,
      method: "put",
      data: body,
    });
  },
  revokeRecommendation(id: number, recommendationId: number, body: { reason?: string }) {
    return request<ApiResponse<ServiceRecommendation>>({
      url: `${API_PATH}/${id}/recommendations/${recommendationId}/revoke`,
      method: "post",
      data: body,
    });
  },
  consumeRecommendation(id: number, recommendationId: number, body: { reason?: string }) {
    return request<ApiResponse<ServiceRecommendation>>({
      url: `${API_PATH}/${id}/recommendations/${recommendationId}/consume`,
      method: "post",
      data: body,
    });
  },
  createMeeting(id: number, body: MeetingForm) {
    return request<ApiResponse<ServiceMeeting>>({
      url: `${API_PATH}/${id}/meetings`,
      method: "post",
      data: body,
    });
  },
  listMeetings(id: number) {
    return request<ApiResponse<ServiceMeeting[]>>({
      url: `${API_PATH}/${id}/meetings`,
      method: "get",
    });
  },
  confirmMeeting(id: number, meetingId: number) {
    return request<ApiResponse<ServiceMeeting>>({
      url: `${API_PATH}/${id}/meetings/${meetingId}/confirm`,
      method: "post",
    });
  },
  completeMeeting(id: number, meetingId: number, body: MeetingActionForm) {
    return request<ApiResponse<ServiceMeeting>>({
      url: `${API_PATH}/${id}/meetings/${meetingId}/complete`,
      method: "post",
      data: body,
    });
  },
  cancelMeeting(id: number, meetingId: number, body: MeetingActionForm) {
    return request<ApiResponse<ServiceMeeting>>({
      url: `${API_PATH}/${id}/meetings/${meetingId}/cancel`,
      method: "post",
      data: body,
    });
  },
  noShowMeeting(id: number, meetingId: number, body: MeetingActionForm) {
    return request<ApiResponse<ServiceMeeting>>({
      url: `${API_PATH}/${id}/meetings/${meetingId}/no-show`,
      method: "post",
      data: body,
    });
  },
  listMeetingFeedback(id: number, meetingId: number) {
    return request<ApiResponse<ServiceMeetingFeedback[]>>({
      url: `${API_PATH}/${id}/meetings/${meetingId}/feedback`,
      method: "get",
    });
  },
  createMeetingFeedback(id: number, meetingId: number, body: MeetingFeedbackForm) {
    return request<ApiResponse<ServiceMeetingFeedback>>({
      url: `${API_PATH}/${id}/meetings/${meetingId}/feedback`,
      method: "post",
      data: body,
    });
  },
  updateMeetingFeedback(id: number, meetingId: number, feedbackId: number, body: MeetingFeedbackForm) {
    return request<ApiResponse<ServiceMeetingFeedback>>({
      url: `${API_PATH}/${id}/meetings/${meetingId}/feedback/${feedbackId}`,
      method: "put",
      data: body,
    });
  },
  createCourseRecord(id: number, itemId: number, body: CourseRecordForm) {
    return request<ApiResponse<ServiceCourseRecord>>({
      url: `${API_PATH}/${id}/plan/items/${itemId}/course-record`,
      method: "post",
      data: body,
    });
  },
  listCourseRecords(id: number) {
    return request<ApiResponse<ServiceCourseRecord[]>>({
      url: `${API_PATH}/${id}/course-records`,
      method: "get",
    });
  },
  revokeCourseRecord(id: number, recordId: number, body: { reason: string }) {
    return request<ApiResponse<ServiceCourseRecord>>({
      url: `${API_PATH}/${id}/course-records/${recordId}/revoke`,
      method: "post",
      data: body,
    });
  },
  listMatchmakers(storeId?: number) {
    return request<ApiResponse<MatchmakerOption[]>>({
      url: `${API_PATH}/matchmakers`,
      method: "get",
      params: storeId ? { store_id: storeId } : undefined,
    });
  },
  assignVip(id: number, body: VipAssignForm) {
    return request<ApiResponse<ServiceCaseTable>>({
      url: `${API_PATH}/assign/${id}`,
      method: "post",
      data: body,
    });
  },
  transferVip(id: number, body: VipAssignForm) {
    return request<ApiResponse<ServiceCaseTable>>({
      url: `${API_PATH}/transfer/${id}`,
      method: "post",
      data: body,
    });
  },
  createUsage(id: number, body: UsageForm) {
    return request<ApiResponse<UsageRecord>>({
      url: `${API_PATH}/usage/${id}`,
      method: "post",
      data: body,
    });
  },
  voidUsage(id: number, usageId: number, body: { reason: string }) {
    return request<ApiResponse<UsageRecord>>({
      url: `${API_PATH}/usage/${id}/${usageId}`,
      method: "delete",
      data: body,
    });
  },
  createInterview(id: number, body: InterviewForm) {
    return request<ApiResponse<DeepInterview>>({
      url: `${API_PATH}/interview/${id}`,
      method: "post",
      data: body,
    });
  },
  applyClose(id: number, body: { reason: string }) {
    return request<ApiResponse<ServiceCaseTable>>({
      url: `${API_PATH}/close/apply/${id}`,
      method: "post",
      data: body,
    });
  },
  reviewClose(id: number, body: { approved: boolean; review_remark?: string }) {
    return request<ApiResponse<ServiceCaseTable>>({
      url: `${API_PATH}/close/review/${id}`,
      method: "post",
      data: body,
    });
  },
  reopen(id: number, body: { reason: string }) {
    return request<ApiResponse<ServiceCaseTable>>({
      url: `${API_PATH}/reopen/${id}`,
      method: "post",
      data: body,
    });
  },
};

export default VipServiceAPI;

export interface VipPageQuery extends PageQuery {
  keyword?: string;
  vip_status?: string;
  vip_level?: string;
  store_id?: number;
  service_owner_user_id?: number;
  owner_user_id?: number;
  effective_start?: string;
  effective_end?: string;
  ended_start?: string;
  ended_end?: string;
  close_review_status?: string;
  mine?: boolean;
  pending_interview?: boolean;
}

export interface ServiceCaseTable extends BaseType {
  case_id?: number;
  brand_id: number;
  vip_id?: number;
  person_id: number;
  customer_id: number;
  contract_id: number;
  store_id: number;
  service_owner_user_id?: number;
  owner_matchmaker_id?: number;
  vip_level: string;
  vip_status: string;
  case_status?: string;
  pool_type?: string;
  close_review_status?: string;
  close_requested_at?: string;
  close_requested_by_name?: string;
  close_reason?: string;
  close_reviewed_at?: string;
  close_reviewed_by_name?: string;
  close_review_remark?: string;
  started_at: string;
  ended_at?: string;
  assigned_at?: string;
  assigned_by?: number;
  source_receipt_id?: number;
  person_display_no?: string;
  person_name?: string;
  person_gender?: string;
  person_age?: number;
  person_mobile?: string;
  contract_no?: string;
  contract_name?: string;
  contract_status?: string;
  original_amount?: string | number;
  contract_amount?: string | number;
  discount_amount?: string | number;
  discount_rate?: string | number;
  discount_reason?: string;
  signer_name?: string;
  signed_at?: string;
  effective_at?: string;
  start_date?: string;
  end_date?: string;
  received_amount?: string | number;
  pending_amount?: string | number;
  payment_status?: string;
  contract_effective_at?: string;
  owner_user_id?: number;
  owner_user_name?: string;
  service_owner_user_name?: string;
  assigned_by_name?: string;
  store_name?: string;
  waiting_hours?: number;
  remaining_days?: number;
  entitlement_summary?: Record<string, { total: number; used: number; remaining: number }>;
  deep_interview_count?: number;
  usage_count?: number;
}

export type VipTable = ServiceCaseTable;

export interface VipLog {
  id: number;
  operation_type: string;
  operator_user_id?: number;
  operator_user_name?: string;
  before_owner_user_id?: number;
  before_owner_user_name?: string;
  after_owner_user_id?: number;
  after_owner_user_name?: string;
  before_status?: string;
  after_status?: string;
  remark?: string;
  created_time: string;
}

export interface ServiceCaseDetail extends ServiceCaseTable {
  logs: VipLog[];
  contract_items: VipContractItem[];
  entitlements: ServiceEntitlement[];
  usages: UsageRecord[];
  deep_interviews: DeepInterview[];
  profile_insight?: Record<string, any>;
}

export type VipDetail = ServiceCaseDetail;

export interface ServiceCustomerProfile {
  person_id: number;
  person_brand_id?: number;
  customer_id?: number;
  customer_brand_id?: number;
  lead_id?: number;
  store_id?: number;
  store_name?: string;
  owner_user_id?: number;
  owner_user_name?: string;
  service_owner_user_id?: number;
  service_owner_user_name?: string;
  display_no?: string;
  name?: string;
  gender?: string;
  mobile?: string;
  wechat?: string;
  id_card_no?: string;
  birth_date?: string;
  age?: number;
  constellation?: string;
  zodiac?: string;
  height_cm?: number;
  weight_kg?: number;
  education?: string;
  annual_income?: string;
  marital_status?: string;
  ethnicity?: string;
  occupation?: string;
  occupation_code?: string;
  unit_type?: string;
  graduated_school?: string;
  major?: string;
  job_title?: string;
  work_company?: string;
  hometown?: string;
  residence?: string;
  house_status?: string;
  car_status?: string;
  accept_long_distance_self?: boolean;
  accept_flash_marriage?: boolean;
  willing_relocate?: boolean;
  marriage_plan?: string;
  family_background?: string;
  profile_remark?: string;
  photo_urls?: string[];
  profile_intro?: string;
  certification_level?: string;
  certification_summary?: Record<string, unknown>;
  partner_preference?: PartnerPreference | null;
  current_stage?: string;
  max_stage?: string;
  latest_follow_at?: string;
  next_follow_at?: string;
  ended_at?: string;
  end_reason?: string;
  returned_lead_id?: number;
  converted_vip_at?: string;
  created_time?: string;
  updated_time?: string;
}

export interface ServiceCustomerProfileForm {
  mobile: string;
  name: string;
  gender: string;
  wechat?: string;
  birth_date?: string;
  height_cm?: number;
  weight_kg?: number;
  ethnicity?: string;
  occupation?: string;
  occupation_code?: string;
  annual_income?: string;
  marital_status?: string;
  education?: string;
  graduated_school?: string;
  major?: string;
  unit_type?: string;
  job_title?: string;
  work_company?: string;
  hometown?: string;
  residence?: string;
  house_status?: string;
  car_status?: string;
  accept_long_distance_self?: boolean | null;
  accept_flash_marriage?: boolean | null;
  willing_relocate?: boolean | null;
  marriage_plan?: string;
  family_background?: string;
  profile_remark?: string;
  photo_urls?: string[];
  profile_intro?: string;
  id_card_no?: string;
  current_stage?: string;
  next_follow_at?: string;
  partner_preference?: PartnerPreference | null;
  description?: string;
}

export interface ServiceCertification {
  id: number;
  item_code: string;
  item_name: string;
  material_type: string;
  file_name?: string;
  file_path?: string;
  file_url: string;
  payload?: Record<string, unknown>;
  ocr_result?: IdCardOcrResult;
  collected_by?: number;
  collected_by_name?: string;
  created_time?: string;
  certification_record_id?: number;
  certification_record_status?: "not_submitted" | "pending_review" | "approved" | "rejected";
  certification_reject_reason?: string;
  certification_reviewed_at?: string;
}

export interface IdCardOcrResult {
  status: "success" | "failed" | "skipped";
  card_side?: "front" | "back" | "unknown";
  id_card_no_masked?: string;
  name?: string;
  sex?: string;
  birth_date?: string;
  address?: string;
  issue_authority?: string;
  valid_period?: string;
  message?: string;
}

export interface ServiceCertificationArchiveItem {
  item_code: string;
  item_name: string;
  sort?: number;
  material_required?: boolean;
  material_desc?: string;
}

export interface ServiceCertificationMaterialForm {
  item_code: string;
  item_name?: string;
  material_type?: string;
  file_name?: string;
  file_path?: string;
  file_url: string;
  payload?: Record<string, unknown>;
}

export interface ServiceTimelineItem {
  id: string;
  source_type: string;
  record_type: string;
  occurred_at: string;
  title: string;
  content?: string;
  operator_user_id?: number;
  operator_user_name?: string;
  related_id?: number;
  payload?: Record<string, unknown>;
}

export interface ServiceLifecycleItem {
  id: string;
  stage_group: string;
  operation_type: string;
  occurred_at: string;
  title: string;
  remark?: string;
  operator_user_id?: number;
  operator_user_name?: string;
  related_id?: number;
  change_detail?: Record<string, unknown>;
}

export interface ServiceContractRecord {
  id: number;
  contract_no: string;
  contract_name: string;
  contract_status: string;
  vip_level: string;
  owner_user_name?: string;
  original_amount: string | number;
  contract_amount: string | number;
  discount_amount: string | number;
  discount_rate?: string | number;
  discount_reason?: string;
  signer_name?: string;
  signed_at?: string;
  review_submitted_at?: string;
  reviewed_at?: string;
  review_remark?: string;
  effective_at?: string;
  start_date?: string;
  end_date?: string;
  validity_period?: string;
  expire_remind_days?: number;
  remark?: string;
  received_amount: string | number;
  pending_amount: string | number;
  payment_status: string;
  items: Array<Record<string, unknown>>;
  attachments: Array<Record<string, unknown>>;
  receipts: Array<Record<string, unknown>>;
}

export interface ServiceWorkSummary {
  entitlement_summary: Record<string, { total: number; used: number; remaining: number }>;
  deep_interview_count: number;
  active_usage_count: number;
  process_record_count: number;
  contract_count: number;
  contract_amount: string | number;
  received_amount: string | number;
  pending_amount: string | number;
  remaining_days?: number;
}

export interface VipContractItem {
  id: number;
  product_id?: number;
  product_name_snapshot: string;
  price_snapshot: string | number;
  service_days_snapshot: number;
  recommendation_quota_snapshot: number;
  meeting_quota_snapshot: number;
  course_quota_snapshot: number;
  supports_online_meeting_snapshot: boolean;
}

export interface ServiceEntitlement {
  id: number;
  entitlement_type: string;
  total_quota: number;
  used_quota: number;
  remaining_quota: number;
  unit: string;
  allow_overuse: boolean;
  entitlement_status: string;
  source_contract_item_id?: number;
}

export interface UsageRecord {
  id: number;
  entitlement_id: number;
  usage_type: string;
  quantity: number;
  usage_status: string;
  occurred_at: string;
  title?: string;
  content?: string;
  candidate_person_id?: number;
  candidate_name?: string;
  is_overuse: boolean;
  overuse_reason?: string;
  void_reason?: string;
  customer_confirm_status?: string;
  customer_signature_url?: string;
  customer_signed_at?: string;
  created_by_name?: string;
  service_plan_item_id?: number;
  source_type?: string;
  source_id?: number;
  recommendation_id?: number;
  meeting_id?: number;
}

export interface ServicePlan {
  id: number;
  brand_id: number;
  service_case_id: number;
  vip_id: number;
  contract_id: number;
  person_id: number;
  matchmaker_id?: number;
  matchmaker_name?: string;
  plan_status: string;
  service_start_at?: string;
  service_end_at?: string;
  plan_summary?: string;
  remark?: string;
  items: ServicePlanItem[];
}

export interface ServicePlanItem {
  id: number;
  plan_id: number;
  service_case_id: number;
  entitlement_id?: number;
  entitlement_type?: string;
  item_type: string;
  item_status: string;
  sequence_no: number;
  title: string;
  planned_at?: string;
  due_at?: string;
  planned_start_at?: string;
  planned_end_at?: string;
  source_contract_id?: number;
  source_contract_no?: string;
  source_contract_item_id?: number;
  candidate_person_id?: number;
  candidate_name?: string;
  recommendation_count?: number;
  related_recommendation_id?: number;
  related_meeting_id?: number;
  related_usage_id?: number;
  remark?: string;
}

export interface ServicePlanForm {
  service_start_at?: string;
  service_end_at?: string;
  plan_summary?: string;
  remark?: string;
}

export interface ServicePlanItemForm {
  planned_at?: string;
  due_at?: string;
  planned_start_at?: string;
  planned_end_at?: string;
  title?: string;
  remark?: string;
  sequence_no?: number;
}

export interface MatchCandidateQuery extends PageQuery {
  search_mode: "score" | "filter";
  scope: "backup" | "store" | "brand";
  keyword?: string;
  person_id?: number;
  display_no?: string;
  mobile?: string;
  name?: string;
  gender?: string;
  age_min?: number;
  age_max?: number;
  height_min?: number;
  height_max?: number;
  weight_min?: number;
  weight_max?: number;
  education?: string;
  annual_income?: string;
  marital_status?: string;
  ethnicity?: string;
  occupation_code?: string;
  unit_type?: string;
  residence?: string;
  hometown?: string;
  house_status?: string;
  car_status?: string;
  accept_long_distance_self?: boolean;
  accept_flash_marriage?: boolean;
  willing_relocate?: boolean;
  marriage_plan?: string;
  has_photo?: boolean;
  certification_level?: string;
  pref_age_min?: number;
  pref_age_max?: number;
  pref_height_min?: number;
  pref_height_max?: number;
  pref_weight_min?: number;
  pref_weight_max?: number;
  preferred_education_codes?: string[];
  preferred_marital_status_codes?: string[];
  preferred_annual_income_codes?: string[];
  preferred_house_status_codes?: string[];
  preferred_car_status_codes?: string[];
  pref_accept_long_distance?: boolean;
  pref_accept_divorced?: boolean;
  pref_accept_children?: boolean;
  children_requirement?: string;
  preferred_occupation_text?: string;
  preference_text?: string;
  hard_reject_items?: string[];
  soft_preference_items?: string[];
  strictness_level?: string;
}

export interface MatchCandidate {
  id: number;
  display_no?: string;
  name: string;
  gender: string;
  mobile?: string;
  wechat?: string;
  age?: number;
  height_cm?: number;
  weight_kg?: number;
  residence?: string;
  hometown?: string;
  education?: string;
  annual_income?: string;
  marital_status?: string;
  store_id?: number;
  store_name?: string;
  in_backup: boolean;
  contact_unmasked: boolean;
  is_vip: boolean;
  match_score?: number;
  matched_points?: string[];
  unmatched_points?: string[];
}

export interface ServiceCandidateDetail {
  person: {
    id: number;
    display_no?: string;
    name: string;
    gender: string;
    mobile?: string;
    wechat?: string;
    birth_date?: string;
    age?: number;
    height_cm?: number;
    weight_kg?: number;
    ethnicity?: string;
    occupation?: string;
    occupation_code?: string;
    annual_income?: string;
    marital_status?: string;
    education?: string;
    graduated_school?: string;
    major?: string;
    unit_type?: string;
    job_title?: string;
    work_company?: string;
    hometown?: string;
    residence?: string;
    house_status?: string;
    car_status?: string;
    accept_long_distance_self?: boolean;
    accept_flash_marriage?: boolean;
    willing_relocate?: boolean;
    marriage_plan?: string;
    profile_intro?: string;
    profile_remark?: string;
    photo_urls?: string[];
    certification_level?: string;
    store_id?: number;
    store_name?: string;
  };
  partner_preference?: PartnerPreference;
  person_center?: PersonDetail;
  timeline?: PersonTimelineItem[];
  backup: {
    in_backup: boolean;
    backup_item_id?: number;
    contact_unmasked: boolean;
    pending_request: boolean;
    pending_request_id?: number;
    request_scope: "store" | "brand";
    unlock_method: "backup_approved" | "pending_review" | "join_request";
  };
}

export interface RecommendationForm {
  plan_item_id: number;
  candidate_person_id: number;
  recommend_reason?: string;
  match_score?: number;
  matched_points?: string[];
  unmatched_points?: string[];
  risk_notes?: string;
  matchmaker_remark?: string;
}

export interface RecommendationUpdateForm {
  recommendation_status?: string;
  recommend_reason?: string;
  match_score?: number;
  matched_points?: string[];
  unmatched_points?: string[];
  risk_notes?: string;
  matchmaker_remark?: string;
}

export interface ServiceRecommendation {
  id: number;
  service_case_id: number;
  plan_item_id: number;
  vip_person_id: number;
  vip_name?: string;
  candidate_person_id: number;
  candidate_name?: string;
  candidate_mobile?: string;
  recommendation_status: string;
  recommend_reason?: string;
  match_score?: number;
  matched_points?: string[];
  unmatched_points?: string[];
  risk_notes?: string;
  matchmaker_remark?: string;
  related_usage_id?: number;
  created_time?: string;
}

export interface MeetingForm {
  recommendation_id?: number;
  plan_item_id?: number;
  meeting_type: string;
  scheduled_at?: string;
  appointment_slot?: string;
  location?: string;
}

export interface MeetingActionForm {
  reason?: string;
  meeting_result?: string;
  next_action?: string;
}

export interface ServiceMeeting {
  id: number;
  recommendation_id: number;
  initiator_service_case_id: number;
  initiator_plan_item_id?: number;
  initiator_person_id: number;
  initiator_name?: string;
  initiator_gender?: string;
  initiator_matchmaker_id?: number;
  initiator_matchmaker_name?: string;
  target_service_case_id?: number;
  target_plan_item_id?: number;
  target_person_id: number;
  target_name?: string;
  target_gender?: string;
  target_matchmaker_id?: number;
  target_matchmaker_name?: string;
  target_is_vip: boolean;
  meeting_type: string;
  meeting_status: string;
  scheduled_at?: string;
  appointment_slot?: string;
  location?: string;
  meeting_result?: string;
  next_action?: string;
  completed_at?: string;
  cancelled_at?: string;
  cancel_reason?: string;
  matchmaker_opinion?: string;
}

export interface MeetingFeedbackForm {
  feedback_person_id: number;
  feedback_service_case_id?: number;
  feedback_content: string;
  interest_level?: string;
  meeting_result?: string;
  next_action?: string;
  matchmaker_opinion?: string;
}

export interface ServiceMeetingFeedback {
  id: number;
  meeting_id: number;
  feedback_person_id: number;
  feedback_person_name?: string;
  feedback_service_case_id?: number;
  feedback_matchmaker_id?: number;
  feedback_matchmaker_name?: string;
  feedback_content: string;
  interest_level?: string;
  meeting_result?: string;
  next_action?: string;
  created_time?: string;
}

export interface CourseRecordForm {
  course_at?: string;
  course_title: string;
  course_mode: string;
  content?: string;
  customer_feedback?: string;
  matchmaker_remark?: string;
  customer_confirm_status?: string;
  customer_signature_url?: string;
  customer_signed_at?: string;
}

export interface ServiceCourseRecord {
  id: number;
  service_case_id: number;
  service_plan_item_id: number;
  entitlement_id: number;
  usage_id?: number;
  course_at: string;
  course_title: string;
  course_mode: string;
  content?: string;
  customer_feedback?: string;
  matchmaker_remark?: string;
  quantity: number;
  customer_confirm_status: string;
  customer_signature_url?: string;
  customer_signed_at?: string;
  record_status: string;
  revoke_reason?: string;
  revoked_at?: string;
  matchmaker_id?: number;
  matchmaker_name?: string;
  created_time?: string;
}

export interface DeepInterview {
  id: number;
  person_id?: number;
  interview_scope?: string;
  interview_type: string;
  interview_method?: string;
  interviewed_at: string;
  content: string;
  structured_payload?: Record<string, any>;
  keywords?: string[];
  summary?: string;
  manual_notes?: string;
  interview_status: string;
  is_current_source?: boolean;
  matchmaker_id?: number;
  matchmaker_name?: string;
  created_by_name?: string;
  void_reason?: string;
  voided_at?: string;
}

export interface MatchmakerOption {
  id: number;
  name: string;
  mobile?: string;
  dept_id?: number;
}

export interface VipAssignForm {
  service_owner_user_id?: number;
  remark?: string;
}

export interface UsageForm {
  entitlement_id?: number;
  quantity: number;
  occurred_at?: string;
  title?: string;
  content?: string;
  candidate_person_id?: number;
  overuse_reason?: string;
  customer_confirm_status?: string;
  customer_signature_url?: string;
  customer_signed_at?: string;
}

export interface InterviewForm {
  interview_scope?: string;
  interview_type?: string;
  interview_method?: string;
  interviewed_at?: string;
  content?: string;
  structured_payload?: Record<string, any>;
  keywords?: string[];
  summary?: string;
  manual_notes?: string;
}

export interface ServiceCustomerProcessForm {
  record_type?: string;
  occurred_at?: string;
  method?: string;
  result?: string;
  content?: string;
  next_follow_at?: string;
  scheduled_at?: string;
  appointment_slot?: string;
  visit_purpose?: string;
  promised_gift?: string;
  need_summary?: string;
  intention_level?: string;
  next_action?: string;
  enter_signing?: boolean;
}
