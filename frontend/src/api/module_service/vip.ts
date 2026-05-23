import request from "@/utils/request";
import type { PartnerPreference } from "@/api/module_crm/lead";

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
  collected_by?: number;
  collected_by_name?: string;
  created_time?: string;
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
}

export interface DeepInterview {
  id: number;
  interview_type: string;
  interviewed_at: string;
  content: string;
  keywords?: string[];
  summary?: string;
  interview_status: string;
  matchmaker_id?: number;
  matchmaker_name?: string;
  created_by_name?: string;
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
  interview_type?: string;
  interviewed_at?: string;
  content?: string;
  keywords?: string[];
  summary?: string;
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
