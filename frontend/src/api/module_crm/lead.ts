import request from "@/utils/request";

const API_PATH = "/crm/lead";

const LeadAPI = {
  listLead(view: LeadView, query?: LeadPageQuery) {
    const pathMap: Record<LeadView, string> = {
      all: "all",
      storePool: "store-pool",
      salesPrivate: "sales-private",
    };
    return request<ApiResponse<PageResult<LeadTable[]>>>({
      url: `${API_PATH}/${pathMap[view]}/list`,
      method: "get",
      params: query,
    });
  },

  detailLead(id: number) {
    return request<ApiResponse<LeadDetail>>({
      url: `${API_PATH}/detail/${id}`,
      method: "get",
    });
  },

  checkMobile(mobile: string) {
    return request<ApiResponse<LeadMobileCheckResult>>({
      url: `${API_PATH}/mobile/check/${mobile}`,
      method: "get",
    });
  },

  createLead(body: LeadForm) {
    return request<ApiResponse<LeadTable>>({
      url: `${API_PATH}/create`,
      method: "post",
      data: body,
    });
  },

  updateLead(id: number, body: LeadForm) {
    return request<ApiResponse<LeadTable>>({
      url: `${API_PATH}/update/${id}`,
      method: "put",
      data: body,
    });
  },

  assignLead(body: LeadAssignForm) {
    return request<ApiResponse>({
      url: `${API_PATH}/assign`,
      method: "post",
      data: body,
    });
  },

  claimLead(body: LeadClaimForm) {
    return request<ApiResponse>({
      url: `${API_PATH}/claim`,
      method: "post",
      data: body,
    });
  },

  processLead(id: number, body: LeadProcessForm) {
    return request<ApiResponse<LeadProcessRecord>>({
      url: `${API_PATH}/process/${id}`,
      method: "post",
      data: body,
    });
  },

  getStoreRule(storeId: number) {
    return request<ApiResponse<LeadStoreRule>>({
      url: `${API_PATH}/store-rule/${storeId}`,
      method: "get",
    });
  },

  salesOptions(storeId?: number) {
    return request<ApiResponse<CommonType[]>>({
      url: `${API_PATH}/sales-options`,
      method: "get",
      params: { store_id: storeId },
    });
  },

  storeOptions() {
    return request<ApiResponse<CommonType[]>>({
      url: `${API_PATH}/store-options`,
      method: "get",
    });
  },

  sourceOptions() {
    return request<ApiResponse<Array<CommonType & { code?: string }>>>({
      url: `${API_PATH}/source-options`,
      method: "get",
    });
  },

  setStoreRule(storeId: number, body: LeadStoreRule) {
    return request<ApiResponse>({
      url: `${API_PATH}/store-rule/${storeId}`,
      method: "put",
      data: body,
    });
  },

  downloadTemplate() {
    return request<Blob>({
      url: `${API_PATH}/import/template`,
      method: "post",
      responseType: "blob",
    });
  },

  importLead(body: FormData) {
    return request<ApiResponse<LeadImportResult>>({
      url: `${API_PATH}/import/data`,
      method: "post",
      data: body,
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
};

export default LeadAPI;

export type LeadView = "all" | "storePool" | "salesPrivate";

export interface LeadPageQuery extends PageQuery {
  keyword?: string;
  lead_type?: string;
  source_channel_code?: string;
  store_id?: number;
  owner_sales_id?: number;
  latest_follow_time?: string[];
}

export interface LeadPerson extends BaseType {
  brand_id?: number;
  name: string;
  gender: string;
  primary_mobile: string;
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
}

export interface PartnerPreference {
  id?: number;
  person_id?: number;
  age_min?: number;
  age_max?: number;
  height_min_cm?: number;
  height_max_cm?: number;
  weight_min_kg?: number;
  weight_max_kg?: number;
  preferred_residence_region_codes: string[];
  preferred_hometown_region_codes: string[];
  preferred_education_codes: string[];
  preferred_marital_status_codes: string[];
  preferred_annual_income_codes: string[];
  preferred_house_status_codes: string[];
  preferred_car_status_codes: string[];
  accept_long_distance?: boolean | null;
  accept_divorced?: boolean | null;
  accept_children?: boolean | null;
  children_requirement?: string;
  preferred_personality_tags: string[];
  preferred_lifestyle_tags: string[];
  preferred_relationship_tags: string[];
  hard_reject_items: string[];
  soft_preference_items: string[];
  preferred_occupation_text?: string;
  preference_text?: string;
  strictness_level: "loose" | "normal" | "strict";
  must_match_fields: string[];
  preferred_match_fields: string[];
  profile_summary?: string;
  source_type?: string;
  source_id?: string;
  priority?: number;
  is_effective?: boolean;
  is_final?: boolean;
  vector_dirty?: boolean;
  last_vectorized_at?: string;
  version_no?: number;
}

export interface PartnerPreferenceVersion {
  id?: number;
  person_id?: number;
  version_no: number;
  source_type: string;
  source_id?: string;
  priority?: number;
  is_effective?: boolean;
  is_final?: boolean;
  snapshot: Record<string, unknown>;
  created_time?: string;
}

export interface AiProfileBrief {
  id?: number;
  profile_type?: string;
  source_type?: string;
  source_id?: number;
  priority?: number;
  content?: string;
  model_name?: string;
  generation_status?: string;
  is_effective?: boolean;
  generated_at?: string;
  last_error?: string;
  updated_time?: string;
}

export interface AiProfileTaskBrief {
  id?: number;
  profile_type?: string;
  source_type?: string;
  source_id?: number;
  priority?: number;
  status?: string;
  retry_count?: number;
  next_retry_at?: string;
  last_error?: string;
  updated_time?: string;
}

export interface AiProfileInfo {
  profile?: AiProfileBrief | null;
  latest_task?: AiProfileTaskBrief | null;
}

export interface LeadTable extends BaseType {
  brand_id?: number;
  person_id?: number;
  store_id?: number;
  owner_sales_id?: number;
  pool_type: string;
  lead_type: string;
  source_channel_code?: string;
  source_channel_name?: string;
  latest_follow_at?: string;
  next_follow_at?: string;
  store_entered_at?: string;
  assigned_at?: string;
  last_recycled_at?: string;
  protect_due_at?: string;
  protect_remaining_days?: number;
  protect_warning_level?: string;
  converted_customer_at?: string;
  description?: string;
  person: LeadPerson;
  store?: CommonType;
  owner_sales?: CommonType;
  mobile_masked?: string;
  wechat_masked?: string;
  can_view_contact?: boolean;
  age?: number;
  constellation?: string;
  zodiac?: string;
  ai_profile?: AiProfileInfo;
  partner_preference?: PartnerPreference | null;
}

export interface LeadDetail extends LeadTable {
  process_records: LeadProcessRecord[];
  lifecycle_records: LeadLifecycleRecord[];
  partner_preference_versions?: PartnerPreferenceVersion[];
}

export interface LeadForm {
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
  photo_urls: string[];
  source_channel_code?: string;
  store_id?: number;
  owner_sales_id?: number;
  partner_preference?: PartnerPreference;
  sync_to_miniprogram?: boolean;
  description?: string;
}

export interface LeadAssignForm {
  lead_ids: number[];
  store_id?: number;
  owner_sales_id?: number;
  remark?: string;
}

export interface LeadClaimForm {
  lead_ids: number[];
}

export interface LeadProcessForm {
  action_type: string;
  follow_method?: string;
  content: string;
  next_follow_at?: string;
}

export interface LeadProcessRecord extends BaseType {
  action_type: string;
  follow_method?: string;
  content: string;
  next_follow_at?: string;
  operator_user_id?: number;
}

export interface LeadLifecycleRecord extends BaseType {
  operation_type: string;
  operator_user_id?: number;
  change_detail?: Record<string, unknown>;
  remark?: string;
}

export interface LeadStoreRule {
  allow_sales_claim: boolean;
  no_follow_reclaim_days: number;
}

export interface LeadImportResult {
  success_count: number;
  failed_count: number;
  failed_rows: Array<{ row: number; reason: string }>;
}

export interface LeadMobileCheckResult {
  exists: boolean;
  person_id?: number;
  lead_id?: number;
  name?: string;
  mobile?: string;
}
