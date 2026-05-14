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
  ethnicity?: string;
  occupation?: string;
  annual_income?: string;
  marital_status?: string;
  education?: string;
  hometown?: string;
  residence?: string;
  house_status?: string;
  car_status?: string;
  photo_urls?: string[];
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
  assigned_at?: string;
  last_recycled_at?: string;
  converted_customer_at?: string;
  description?: string;
  person: LeadPerson;
  store?: CommonType;
  owner_sales?: CommonType;
  mobile_masked?: string;
  wechat_masked?: string;
  can_view_contact?: boolean;
  ai_profile?: AiProfileInfo;
}

export interface LeadDetail extends LeadTable {
  process_records: LeadProcessRecord[];
  lifecycle_records: LeadLifecycleRecord[];
}

export interface LeadForm {
  mobile: string;
  name: string;
  gender: string;
  wechat?: string;
  birth_date?: string;
  height_cm?: number;
  ethnicity?: string;
  occupation?: string;
  annual_income?: string;
  marital_status?: string;
  education?: string;
  hometown?: string;
  residence?: string;
  house_status?: string;
  car_status?: string;
  photo_urls: string[];
  source_channel_code?: string;
  store_id?: number;
  owner_sales_id?: number;
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
