import request from "@/utils/request";

const API_PATH = "/crm/person";

const PersonAPI = {
  listPerson(query?: PersonPageQuery) {
    return request<ApiResponse<PageResult<PersonRecord[]>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },
  detailPerson(personId: number) {
    return request<ApiResponse<PersonDetail>>({
      url: `${API_PATH}/detail/${personId}`,
      method: "get",
    });
  },
  timelinePerson(personId: number) {
    return request<ApiResponse<PersonTimelineItem[]>>({
      url: `${API_PATH}/timeline/${personId}`,
      method: "get",
    });
  },
  qualityPerson(personId: number) {
    return request<ApiResponse<PersonQuality>>({
      url: `${API_PATH}/quality/${personId}`,
      method: "get",
    });
  },
  viewPhone(personId: number, reason: string) {
    return request<
      ApiResponse<{ person_id: number; primary_mobile?: string; mobile_masked?: string }>
    >({
      url: `${API_PATH}/phone/view/${personId}`,
      method: "post",
      data: { reason },
    });
  },
  viewIdCard(personId: number, reason: string) {
    return request<
      ApiResponse<{ person_id: number; id_card_no?: string; id_card_no_masked?: string }>
    >({
      url: `${API_PATH}/id-card/view/${personId}`,
      method: "post",
      data: { reason },
    });
  },
  sensitiveLog(personId: number) {
    return request<ApiResponse<SensitiveLogRecord[]>>({
      url: `${API_PATH}/sensitive-log/${personId}`,
      method: "get",
    });
  },
  userOptions() {
    return request<ApiResponse<PersonUserOption[]>>({
      url: `${API_PATH}/user-options`,
      method: "get",
    });
  },
};

export default PersonAPI;

export interface PersonPageQuery extends PageQuery {
  keyword?: string;
  store_id?: number;
  owner_sales_id?: number;
  service_owner_user_id?: number;
  identity_tag?: string;
  certification_level?: string;
  quality_level?: string;
  latest_activity_start?: string;
  latest_activity_end?: string;
}

export interface PersonUserOption {
  id: number;
  name?: string;
  username?: string;
  dept_id?: number;
}

export interface PersonBrief {
  id: number;
  display_no?: string;
  name: string;
  gender: string;
  primary_mobile?: string;
  mobile_masked?: string;
  wechat?: string;
  birth_date?: string;
  age?: number;
  height_cm?: number;
  education?: string;
  annual_income?: string;
  marital_status?: string;
  occupation?: string;
  occupation_code?: string;
  residence?: string;
  photo_urls?: string[];
  certification_level?: string;
  id_card_no_masked?: string;
}

export interface PersonQuality {
  score: number;
  quality_level: string;
  basic_score: number;
  display_score: number;
  service_score: number;
  missing_basic: string[];
  missing_display: string[];
  missing_service: string[];
  risk_flags: Array<{ type: string; level: string; title: string }>;
}

export interface PersonRecord {
  person: PersonBrief;
  store?: CommonType;
  owner_sales?: CommonType;
  service_owner?: CommonType;
  identity_tags: string[];
  identity_summary: Record<string, unknown>;
  quality: PersonQuality;
  latest_activity_at?: string;
  created_time?: string;
}

export interface PersonRelations {
  lead?: Record<string, any>;
  customer?: Record<string, any>;
  vip?: Record<string, any>;
  service_case?: Record<string, any>;
  candidate?: Record<string, any>;
  backup_items: Array<Record<string, any>>;
  join_requests: Array<Record<string, any>>;
  miniprogram_user?: Record<string, any>;
  subscription?: Record<string, any>;
  certification?: Record<string, any>;
  partner_preference?: Record<string, any>;
  ai_profile?: Record<string, any>;
}

export interface PersonDetail {
  person: PersonBrief;
  relations: PersonRelations;
  quality: PersonQuality;
  sensitive_log_count: number;
}

export interface PersonTimelineItem {
  id: string;
  source_type: string;
  title: string;
  occurred_at: string;
  content?: string;
  operator_user_id?: number;
  operator_user_name?: string;
  related_id?: number;
  payload?: Record<string, any>;
}

export interface SensitiveLogRecord {
  id: number;
  access_type: string;
  permission_result: string;
  reason?: string;
  operator_id?: number;
  operator_name?: string;
  accessed_at?: string;
}
