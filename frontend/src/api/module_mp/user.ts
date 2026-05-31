import request from "@/utils/request";
import type { AiProfileInfo, PartnerPreference } from "@/api/module_crm/lead";

const API_PATH = "/mp/admin/user";

const MpUserAPI = {
  listUser(query?: MpUserPageQuery) {
    return request<ApiResponse<PageResult<MpUserTable[]>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },

  detailUser(id: number) {
    return request<ApiResponse<MpUserTable>>({
      url: `${API_PATH}/detail/${id}`,
      method: "get",
    });
  },

  updateProfile(id: number, body: MpUserProfileForm) {
    return request<ApiResponse<MpUserTable>>({
      url: `${API_PATH}/${id}/profile`,
      method: "put",
      data: body,
    });
  },

  updateUserWall(id: number, allow_user_wall: boolean) {
    return request<ApiResponse<MpUserTable>>({
      url: `${API_PATH}/${id}/user-wall`,
      method: "put",
      data: { allow_user_wall },
    });
  },

  getSettings() {
    return request<ApiResponse<MpOperationSettings>>({
      url: `${API_PATH}/settings`,
      method: "get",
    });
  },

  updateSettings(body: MpOperationSettings) {
    return request<ApiResponse<MpOperationSettings>>({
      url: `${API_PATH}/settings`,
      method: "put",
      data: body,
    });
  },

  listActions(query?: MpActionPageQuery) {
    return request<ApiResponse<PageResult<MpActionRecord[]>>>({
      url: `${API_PATH}/actions/list`,
      method: "get",
      params: query,
    });
  },

  listCoupons(query?: MpCouponPageQuery) {
    return request<ApiResponse<PageResult<MpCouponRecord[]>>>({
      url: `${API_PATH}/coupons/list`,
      method: "get",
      params: query,
    });
  },

  grantCoupon(body: MpCouponGrantForm) {
    return request<ApiResponse<{ granted: number }>>({
      url: `${API_PATH}/coupons/grant`,
      method: "post",
      data: body,
    });
  },

  listTasks() {
    return request<ApiResponse<MpUnlockTask[]>>({
      url: `${API_PATH}/tasks/list`,
      method: "get",
    });
  },

  saveTask(body: MpUnlockTask, id?: number) {
    return request<ApiResponse<MpUnlockTask>>({
      url: id ? `${API_PATH}/tasks/${id}` : `${API_PATH}/tasks`,
      method: id ? "put" : "post",
      data: body,
    });
  },

  listQuestions() {
    return request<ApiResponse<MpUnlockQuestion[]>>({
      url: `${API_PATH}/questions/list`,
      method: "get",
    });
  },

  saveQuestion(body: MpUnlockQuestion, id?: number) {
    return request<ApiResponse<MpUnlockQuestion>>({
      url: id ? `${API_PATH}/questions/${id}` : `${API_PATH}/questions`,
      method: id ? "put" : "post",
      data: body,
    });
  },

  listUnlockRecords(query?: MpUnlockRecordQuery) {
    return request<ApiResponse<PageResult<MpUnlockRecord[]>>>({
      url: `${API_PATH}/unlock-records/list`,
      method: "get",
      params: query,
    });
  },

  revokeUnlockRecord(id: number, body: { status: "revoked" | "blocked"; reason?: string }) {
    return request<ApiResponse<{ id: number; unlock_status: string }>>({
      url: `${API_PATH}/unlock-records/${id}/status`,
      method: "put",
      data: body,
    });
  },

  listContactViews(query?: MpUnlockRecordQuery) {
    return request<ApiResponse<PageResult<MpContactViewRecord[]>>>({
      url: `${API_PATH}/contact-views/list`,
      method: "get",
      params: query,
    });
  },

  matchDebug(query: MatchDebugQuery) {
    return request<ApiResponse<MatchDebugResult>>({
      url: "/match/admin/debug/candidates",
      method: "get",
      params: query,
    });
  },

  rebuildMatchVector(personId: number) {
    return request<ApiResponse<{ person_id: number }>>({
      url: `/match/admin/debug/person/${personId}/dirty`,
      method: "post",
    });
  },
};

export default MpUserAPI;

export interface MpUserPageQuery extends PageQuery {
  keyword?: string;
  is_registered?: boolean;
}

export interface MpUserPerson {
  id?: number;
  description?: string;
  name?: string;
  gender?: string;
  primary_mobile?: string;
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
  id_card_no_masked?: string;
  certification_level?: string;
  certification_summary?: Record<string, unknown>;
}

export interface MpUserProfileForm {
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
  description?: string;
}

export interface MpUserTable extends BaseType {
  brand_id: number;
  person_id?: number;
  openid?: string;
  unionid?: string;
  mobile?: string;
  nickname?: string;
  avatar_url?: string;
  is_invisible: boolean;
  allow_user_wall: boolean;
  registered_at?: string;
  last_login_at?: string;
  is_registered: boolean;
  lead_id?: number;
  source_event_count: number;
  person?: MpUserPerson;
  ai_profile?: AiProfileInfo;
  partner_preference?: PartnerPreference | null;
  interaction_stats?: {
    liked_count?: number;
    favorited_count?: number;
    unlocked_count?: number;
  };
  recent_actions?: MpActionRecord[];
  coupon_summary?: {
    unused_count?: number;
  };
}

export interface MpOperationSettings {
  plaza_show_pending_users: boolean;
  contact_price: string;
  allow_coupon: boolean;
  allow_paid_boost: boolean;
  allow_task_free: boolean;
  daily_unlock_limit: number;
  default_store_id?: number;
  heartbeat_initial_min: number;
  heartbeat_initial_max: number;
  heartbeat_view_score: number;
  heartbeat_like_score: number;
  heartbeat_favorite_score: number;
  heartbeat_profile_score: number;
  heartbeat_unlock_score: number;
  coupon_enabled: boolean;
  coupon_name: string;
  coupon_valid_days: number;
  coupon_cycle_days: number;
  coupon_hold_limit: number;
  coupon_description: string;
  copy_progress: string;
  copy_final: string;
  copy_pay: string;
  copy_contact: string;
  copy_risk: string;
}

export interface MpActionPageQuery extends PageQuery {
  keyword?: string;
  action_type?: string;
}

export interface MpActionRecord {
  id: number;
  action_type: string;
  viewer_user_id?: number;
  viewer_display_no?: string;
  viewer_name?: string;
  viewer_nickname?: string;
  viewer_mobile?: string;
  target_user_id?: number;
  target_display_no?: string;
  target_name?: string;
  target_nickname?: string;
  target_mobile?: string;
  occurred_at?: string;
  payload?: Record<string, unknown>;
}

export interface MpCouponPageQuery extends PageQuery {
  keyword?: string;
  coupon_status?: string;
}

export interface MpCouponRecord {
  id: number;
  user_id: number;
  display_no?: string;
  nickname?: string;
  mobile?: string;
  coupon_name: string;
  coupon_status: string;
  valid_from?: string;
  valid_to?: string;
  used_at?: string;
  grant_reason?: string;
}

export interface MpCouponGrantForm {
  user_id: number;
  quantity: number;
  coupon_name?: string;
  valid_days?: number;
  grant_reason?: string;
}

export interface MatchDebugQuery extends PageQuery {
  person_id?: number;
  display_no?: string;
  scene?: "subscription" | "debug" | "matchmaker_service";
}

export interface MatchCandidate {
  person_id: number;
  display_no?: string;
  nickname?: string;
  gender?: string;
  age?: number;
  height_cm?: number;
  residence?: string;
  education?: string;
  annual_income?: string;
  marital_status?: string;
  match_score: number;
  rank_score: number;
  confidence_score: number;
  structured_score: number;
  vector_score?: number;
  vector_status: string;
  matched_points: string[];
  risk_points: string[];
  blocked_reasons: string[];
  user_reason: string;
  admin_reason: string;
}

export interface MatchDebugResult extends PageResult<MatchCandidate[]> {
  query_person_id: number;
  query_display_no?: string;
  scene: string;
  model_info: Record<string, unknown>;
  vector_status: Record<string, unknown>;
}

export interface MpUnlockTask {
  id?: number;
  task_code: string;
  task_name: string;
  task_type: string;
  task_group: string;
  score: number;
  is_global: boolean;
  is_target: boolean;
  daily_limit: number;
  sort: number;
  status: string;
}

export interface MpUnlockQuestion {
  id?: number;
  question: string;
  options: Array<{ label: string; value: string }>;
  recommended_answer?: string;
  match_tags?: string[];
  correct_score: number;
  wrong_score: number;
  category: string;
  sort: number;
  status: string;
}

export interface MpUnlockRecordQuery extends PageQuery {
  keyword?: string;
  unlock_status?: string;
}

export interface MpUnlockRecord {
  id: number;
  viewer_user_id: number;
  target_user_id: number;
  viewer_display_no?: string;
  viewer_name?: string;
  viewer_nickname?: string;
  viewer_mobile?: string;
  target_display_no?: string;
  target_name?: string;
  target_nickname?: string;
  unlock_source: string;
  unlock_method: string;
  unlock_status: string;
  amount: string;
  order_id?: number;
  coupon_id?: number;
  unlocked_at?: string;
  revoked_at?: string;
  revoke_reason?: string;
  view_count: number;
  last_viewed_at?: string;
}

export interface MpContactViewRecord {
  id: number;
  unlock_id: number;
  viewer_user_id: number;
  target_user_id: number;
  target_display_no?: string;
  target_name?: string;
  target_nickname?: string;
  viewed_at?: string;
  payload?: Record<string, unknown>;
}
