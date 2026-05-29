import request from "@/utils/request";

const ADMIN_PATH = "/screen/admin";
const DEVICE_PATH = "/screen/device";
const PLAYER_PATH = "/screen/player";
const TOKEN_KEY = "screen_device_token";

function screenAuth() {
  const token = localStorage.getItem(TOKEN_KEY);
  return token ? { Authorization: `ScreenDevice ${token}` } : { Authorization: "no-auth" };
}

const ScreenAPI = {
  tokenKey: TOKEN_KEY,

  listDevices(query?: ScreenDeviceQuery) {
    return request<ApiResponse<PageResult<ScreenDevice[]>>>({
      url: `${ADMIN_PATH}/device/list`,
      method: "get",
      params: query,
    });
  },
  bindDevice(body: ScreenDeviceBindForm) {
    return request<ApiResponse<ScreenDevice>>({
      url: `${ADMIN_PATH}/device/bind`,
      method: "post",
      data: body,
    });
  },
  unbindDevice(id: number) {
    return request<ApiResponse<ScreenDevice>>({
      url: `${ADMIN_PATH}/device/${id}/unbind`,
      method: "post",
    });
  },
  deleteDevice(id: number) {
    return request<ApiResponse<ScreenDevice>>({
      url: `${ADMIN_PATH}/device/${id}`,
      method: "delete",
    });
  },
  resetDeviceToken(id: number) {
    return request<ApiResponse<ScreenDevice>>({
      url: `${ADMIN_PATH}/device/${id}/reset-token`,
      method: "post",
    });
  },
  getUserWallConfig() {
    return request<ApiResponse<ScreenUserWallConfig>>({
      url: `${ADMIN_PATH}/user-wall/config`,
      method: "get",
    });
  },
  saveUserWallConfig(body: ScreenUserWallConfig) {
    return request<ApiResponse<ScreenUserWallConfig>>({
      url: `${ADMIN_PATH}/user-wall/config`,
      method: "put",
      data: body,
    });
  },
  getPromoConfig() {
    return request<ApiResponse<ScreenPromoManagePayload>>({
      url: `${ADMIN_PATH}/promo/config`,
      method: "get",
    });
  },
  savePromoConfig(body: ScreenPromoConfig) {
    return request<ApiResponse<ScreenPromoConfig>>({
      url: `${ADMIN_PATH}/promo/config`,
      method: "put",
      data: body,
    });
  },
  createPromoStaff(body: ScreenPromoStaffForm) {
    return request<ApiResponse<ScreenPromoStaff>>({
      url: `${ADMIN_PATH}/promo/staff`,
      method: "post",
      data: body,
    });
  },
  updatePromoStaff(id: number, body: ScreenPromoStaffForm) {
    return request<ApiResponse<ScreenPromoStaff>>({
      url: `${ADMIN_PATH}/promo/staff/${id}`,
      method: "put",
      data: body,
    });
  },
  deletePromoStaff(id: number) {
    return request<ApiResponse<{ id: number }>>({
      url: `${ADMIN_PATH}/promo/staff/${id}`,
      method: "delete",
    });
  },
  createPromoItem(body: ScreenPromoItemForm) {
    return request<ApiResponse<ScreenPromoItem>>({
      url: `${ADMIN_PATH}/promo/item`,
      method: "post",
      data: body,
    });
  },
  updatePromoItem(id: number, body: ScreenPromoItemForm) {
    return request<ApiResponse<ScreenPromoItem>>({
      url: `${ADMIN_PATH}/promo/item/${id}`,
      method: "put",
      data: body,
    });
  },
  deletePromoItem(id: number) {
    return request<ApiResponse<{ id: number }>>({
      url: `${ADMIN_PATH}/promo/item/${id}`,
      method: "delete",
    });
  },
  sortPromoItems(ids: number[]) {
    return request<ApiResponse<{ ids: number[] }>>({
      url: `${ADMIN_PATH}/promo/item/sort`,
      method: "post",
      data: { ids },
    });
  },
  bootstrap(body: ScreenBootstrapForm) {
    return request<ApiResponse<ScreenBootstrapResult>>({
      url: `${DEVICE_PATH}/bootstrap`,
      method: "post",
      headers: { Authorization: "no-auth" },
      data: body,
    });
  },
  bindStatus(deviceCode: string) {
    return request<ApiResponse<ScreenBindStatus>>({
      url: `${DEVICE_PATH}/bind-status`,
      method: "get",
      headers: { Authorization: "no-auth" },
      params: { device_code: deviceCode },
    });
  },
  heartbeat(body: Record<string, unknown> = {}) {
    return request<ApiResponse<{ device_id: number; online_status: string; last_online_at?: string }>>({
      url: `${DEVICE_PATH}/heartbeat`,
      method: "post",
      headers: screenAuth(),
      silentSuccess: true,
      data: body,
    });
  },
  playerConfig() {
    return request<ApiResponse<ScreenPlayerConfig>>({
      url: `${PLAYER_PATH}/config`,
      method: "get",
      headers: screenAuth(),
    });
  },
  playerUserWall() {
    return request<ApiResponse<ScreenUserWallPayload>>({
      url: `${PLAYER_PATH}/user-wall`,
      method: "get",
      headers: screenAuth(),
    });
  },
  recordUserWall(body: ScreenUserWallRecordForm) {
    return request<ApiResponse<{ id: number }>>({
      url: `${PLAYER_PATH}/user-wall/record`,
      method: "post",
      headers: screenAuth(),
      silentSuccess: true,
      data: body,
    });
  },
  playerPromo() {
    return request<ApiResponse<ScreenPromoPlayerPayload>>({
      url: `${PLAYER_PATH}/promo`,
      method: "get",
      headers: screenAuth(),
    });
  },
};

export default ScreenAPI;

export interface ScreenDeviceQuery extends PageQuery {
  keyword?: string;
  bind_status?: string;
  online_status?: string;
}

export interface ScreenDevice {
  id: number;
  brand_id: number;
  store_id?: number;
  device_code: string;
  device_name?: string;
  device_type: string;
  bind_status: string;
  online_status: string;
  bound_by?: number;
  bound_at?: string;
  last_online_at?: string;
  last_sync_at?: string;
  app_version?: string;
  system_info?: Record<string, unknown>;
  created_time?: string;
}

export interface ScreenDeviceBindForm {
  device_code: string;
  device_name?: string;
  store_id?: number;
}

export interface ScreenUserWallConfig {
  id?: number;
  title: string;
  user_switch_seconds: number;
  photo_switch_seconds: number;
  sort_strategy: string;
  filter_config: Record<string, unknown>;
  qr_action: string;
  status: string;
}

export interface ScreenBootstrapForm {
  device_type: "web" | "android_tv" | string;
  app_version?: string;
  system_info?: Record<string, unknown>;
}

export interface ScreenBootstrapResult {
  device_id?: number;
  device_code: string;
  bind_status: string;
  expires_at?: string;
}

export interface ScreenBindStatus {
  device_id?: number;
  device_code: string;
  bind_status: string;
  device_token?: string;
  device_name?: string;
}

export interface ScreenPlayerConfig {
  device: ScreenDevice;
  user_wall: ScreenUserWallConfig;
}

export interface ScreenUserWallItem {
  user_id?: number;
  person_id: number;
  display_no?: string;
  display_name?: string;
  avatar_url?: string;
  photos: string[];
  age?: number;
  gender?: string;
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
  miai_impression?: string;
  matchmaker_impression?: string;
  qrcode_url?: string;
  certification_level?: string;
  certification_level_name?: string;
}

export interface ScreenUserWallPayload {
  config: ScreenUserWallConfig;
  items: ScreenUserWallItem[];
}

export interface ScreenUserWallRecordForm {
  person_id: number;
  user_id?: number;
  display_no?: string;
  display_snapshot?: Record<string, unknown>;
  duration_seconds?: number;
  play_result?: string;
  error_message?: string;
}

export interface ScreenPromoConfig {
  id?: number;
  enabled: boolean;
  image_duration_seconds: number;
  staff_duration_seconds: number;
  sync_interval_seconds: number;
  cache_limit_gb: number;
  status: string;
}

export interface ScreenPromoStaff {
  id: number;
  avatar_url?: string;
  display_name: string;
  role_title?: string;
  years_experience?: number;
  specialties: string[];
  specialties_text?: string;
  service_slogan?: string;
  public_tags: string[];
  sort: number;
  status: string;
}

export type ScreenPromoStaffForm = Omit<ScreenPromoStaff, "id">;

export interface ScreenPromoItem {
  id: number;
  type: "image" | "video" | "staff";
  item_type: "image" | "video" | "staff";
  title: string;
  file_url?: string;
  cover_url?: string;
  file_hash?: string;
  file_size?: number;
  version: number;
  duration_seconds?: number;
  sort: number;
  staff_id?: number;
  staff?: ScreenPromoStaff;
  status: string;
}

export type ScreenPromoItemForm = Omit<ScreenPromoItem, "id" | "type" | "staff">;

export interface ScreenPromoManagePayload {
  config: ScreenPromoConfig;
  items: ScreenPromoItem[];
  staffs: ScreenPromoStaff[];
}

export interface ScreenPromoPlayerPayload {
  config: ScreenPromoConfig;
  items: ScreenPromoItem[];
}
