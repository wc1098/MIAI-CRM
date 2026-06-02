import request from "@/utils/request";

const ADMIN_PATH = "/screen/admin";
const DEVICE_PATH = "/screen/device";
const PLAYER_PATH = "/screen/player";
const CONTROL_PATH = "/screen/control";
const TOKEN_KEY = "screen_device_token";

function screenAuth() {
  const token = localStorage.getItem(TOKEN_KEY);
  return token ? { Authorization: `ScreenDevice ${token}` } : { Authorization: "no-auth" };
}

function controlAuth(token: string) {
  return token ? { Authorization: `ScreenControl ${token}` } : { Authorization: "no-auth" };
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
  listActivities(query?: ScreenActivityQuery) {
    return request<ApiResponse<PageResult<ScreenActivityConfig[]>>>({
      url: `${ADMIN_PATH}/activity/list`,
      method: "get",
      params: query,
    });
  },
  createActivity(body: ScreenActivityForm) {
    return request<ApiResponse<ScreenActivityConfig>>({
      url: `${ADMIN_PATH}/activity/create`,
      method: "post",
      data: body,
    });
  },
  updateActivity(id: number, body: ScreenActivityForm) {
    return request<ApiResponse<ScreenActivityConfig>>({
      url: `${ADMIN_PATH}/activity/update/${id}`,
      method: "put",
      data: body,
    });
  },
  deleteActivity(id: number) {
    return request<ApiResponse<{ id: number }>>({
      url: `${ADMIN_PATH}/activity/delete/${id}`,
      method: "delete",
    });
  },
  regenerateActivityQrcode(id: number) {
    return request<ApiResponse<ScreenActivityConfig>>({
      url: `${ADMIN_PATH}/activity/${id}/qrcode/regenerate`,
      method: "post",
    });
  },
  createActivityControlToken(id: number) {
    return request<ApiResponse<ScreenActivityControlToken>>({
      url: `${ADMIN_PATH}/activity/${id}/control-token`,
      method: "post",
      silentSuccess: true,
    });
  },
  getActivityBarrageSettings() {
    return request<ApiResponse<ScreenActivityBarrageSettings>>({
      url: `${ADMIN_PATH}/activity/barrage/settings`,
      method: "get",
    });
  },
  updateActivityBarrageSettings(body: ScreenActivityBarrageSettings) {
    return request<ApiResponse<ScreenActivityBarrageSettings>>({
      url: `${ADMIN_PATH}/activity/barrage/settings`,
      method: "put",
      data: body,
    });
  },
  getActivityDominateSettings() {
    return request<ApiResponse<ScreenActivityDominateSettings>>({
      url: `${ADMIN_PATH}/activity/dominate/settings`,
      method: "get",
    });
  },
  updateActivityDominateSettings(body: ScreenActivityDominateSettings) {
    return request<ApiResponse<ScreenActivityDominateSettings>>({
      url: `${ADMIN_PATH}/activity/dominate/settings`,
      method: "put",
      data: body,
    });
  },
  getActivityQrcodeSettings() {
    return request<ApiResponse<ScreenActivityQrcodeSettings>>({
      url: `${ADMIN_PATH}/activity/qrcode/settings`,
      method: "get",
    });
  },
  updateActivityQrcodeSettings(body: ScreenActivityQrcodeSettings) {
    return request<ApiResponse<ScreenActivityQrcodeSettings>>({
      url: `${ADMIN_PATH}/activity/qrcode/settings`,
      method: "put",
      data: body,
    });
  },
  getActivityCheckinWallSettings() {
    return request<ApiResponse<ScreenActivityCheckinWallSettings>>({
      url: `${ADMIN_PATH}/activity/checkin-wall/settings`,
      method: "get",
    });
  },
  updateActivityCheckinWallSettings(body: ScreenActivityCheckinWallSettings) {
    return request<ApiResponse<ScreenActivityCheckinWallSettings>>({
      url: `${ADMIN_PATH}/activity/checkin-wall/settings`,
      method: "put",
      data: body,
    });
  },
  getActivityMusicSettings() {
    return request<ApiResponse<ScreenActivityMusicSettings>>({
      url: `${ADMIN_PATH}/activity/music/settings`,
      method: "get",
    });
  },
  updateActivityMusicSettings(body: ScreenActivityMusicSettings) {
    return request<ApiResponse<ScreenActivityMusicSettings>>({
      url: `${ADMIN_PATH}/activity/music/settings`,
      method: "put",
      data: body,
    });
  },
  sendActivityCommand(id: number, body: ScreenActivityCommand) {
    return request<ApiResponse<ScreenActivityConfig>>({
      url: `${ADMIN_PATH}/activity/${id}/command`,
      method: "post",
      data: body,
      silentSuccess: true,
    });
  },
  adminActivityParticipants(id: number) {
    return request<ApiResponse<ScreenActivityParticipantsPayload>>({
      url: `${ADMIN_PATH}/activity/${id}/participants`,
      method: "get",
      silentSuccess: true,
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
  playerActivityList() {
    return request<ApiResponse<{ items: ScreenActivityConfig[] }>>({
      url: `${PLAYER_PATH}/activity/list`,
      method: "get",
      headers: screenAuth(),
    });
  },
  playerActivityDetail(id: number) {
    return request<ApiResponse<ScreenActivityPlayerPayload>>({
      url: `${PLAYER_PATH}/activity/detail/${id}`,
      method: "get",
      headers: screenAuth(),
    });
  },
  playerActivityParticipants(id: number) {
    return request<ApiResponse<ScreenActivityParticipantsPayload>>({
      url: `${PLAYER_PATH}/activity/${id}/participants`,
      method: "get",
      headers: screenAuth(),
      silentSuccess: true,
    });
  },
  controlActivity(token: string) {
    return request<ApiResponse<ScreenActivityControlPayload>>({
      url: `${CONTROL_PATH}/activity`,
      method: "get",
      headers: controlAuth(token),
      silentSuccess: true,
    });
  },
  sendControlCommand(token: string, body: ScreenActivityCommand) {
    return request<ApiResponse<ScreenActivityConfig>>({
      url: `${CONTROL_PATH}/activity/command`,
      method: "post",
      headers: controlAuth(token),
      data: body,
      silentSuccess: true,
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

export interface ScreenActivityQuery extends PageQuery {
  keyword?: string;
  enabled?: boolean;
}

export interface ScreenActivityEvent {
  id: number;
  title: string;
  subtitle?: string;
  event_type?: string;
  cover_url?: string;
  location?: string;
  store_id?: number;
  store_name?: string;
  start_time?: string;
  end_time?: string;
  register_deadline?: string;
  event_status?: string;
}

export interface ScreenActivityConfig {
  id: number;
  brand_id: number;
  store_id?: number;
  event_id: number;
  event?: ScreenActivityEvent;
  screen_name?: string;
  title?: string;
  subtitle?: string;
  background_url?: string;
  active_background?: ScreenActivityBackground;
  theme_config?: ScreenActivityThemeConfig;
  module_config?: ScreenActivityModuleConfig;
  enabled: boolean;
  current_scene: "blank" | "checkin";
  show_qrcode: boolean;
  qrcode_url?: string;
  qrcode_page?: string;
  checkin_scene?: string;
  qrcode_generated_at?: string;
  last_command?: ScreenActivityCommand;
  last_command_at?: string;
  status: string;
  registered_count?: number;
  checkin_count?: number;
  online?: boolean;
}

export interface ScreenActivityModuleItem {
  enabled: boolean;
  placeholder?: boolean;
  settings?: Record<string, unknown>;
}

export interface ScreenActivityModuleConfig {
  activity_qrcode?: ScreenActivityModuleItem;
  checkin_wall?: ScreenActivityModuleItem;
  barrage?: ScreenActivityModuleItem;
  dominate?: ScreenActivityModuleItem;
  gift?: ScreenActivityModuleItem;
  welfare?: ScreenActivityModuleItem;
  music?: ScreenActivityModuleItem;
  lottery?: ScreenActivityModuleItem;
  game?: ScreenActivityModuleItem;
  message_wall?: ScreenActivityModuleItem;
  [key: string]: ScreenActivityModuleItem | undefined;
}

export interface ScreenActivityBackground {
  id: string;
  name: string;
  type: "image" | "color";
  url?: string;
  color?: string;
}

export interface ScreenActivityThemeConfig {
  backgrounds: ScreenActivityBackground[];
  active_background_id?: string;
  mobile_background_url?: string;
  welcome_message?: string;
  show_people_count?: boolean;
  [key: string]: unknown;
}

export type ScreenActivityForm = Omit<ScreenActivityConfig, "id" | "brand_id" | "event" | "event_id" | "qrcode_url" | "qrcode_page" | "checkin_scene" | "qrcode_generated_at" | "registered_count" | "checkin_count" | "online"> & {
  event_id?: number;
};

export interface ScreenActivityCommand {
  command: "set_scene" | "set_background" | "toggle_module" | "toggle_people_count" | "toggle_qrcode" | "refresh" | "clear_screen" | "music_play" | "music_pause" | "music_next" | "music_prev" | "music_set_volume" | "music_set_track" | "dominate_play";
  value?: string | number | boolean | Record<string, unknown>;
}

export interface ScreenActivityParticipant {
  id: number;
  onsite_no: string;
  display_nickname?: string;
  gender?: string;
  avatar_url?: string;
  checkin_type: "registered" | "walk_in" | string;
  checked_in_at?: string;
}

export interface ScreenActivityParticipantsPayload {
  items: ScreenActivityParticipant[];
  counts: {
    registered_count: number;
    checkin_count: number;
  };
}

export interface ScreenActivityPlayerPayload {
  config: ScreenActivityConfig;
  participants: ScreenActivityParticipant[];
  barrages?: ScreenActivityBarrage[];
}

export interface ScreenActivityBarrage {
  id: number;
  activity_id: number;
  event_id: number;
  mp_user_id?: number;
  nickname?: string;
  avatar_url?: string;
  content: string;
  display_status?: string;
  displayed_at?: string;
  created_time?: string;
  duration_seconds?: number;
  size?: "large" | "medium" | "small";
}

export interface ScreenActivityBarrageSettings {
  max_length: number;
  duration_seconds: number;
  size: "large" | "medium" | "small";
  need_review: boolean;
}

export interface ScreenActivityDominateSettings {
  max_length: number;
  duration_seconds: number;
  need_review: boolean;
}

export interface ScreenActivityQrcodeSettings {
  position: "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9";
  size: "large" | "medium" | "small";
}

export interface ScreenActivityCheckinWallSettings {
  title: string;
  show_count: boolean;
  show_avatar: boolean;
  show_nickname: boolean;
  list_size: "large" | "medium" | "small";
}

export interface ScreenActivityMusicCategory {
  id: string;
  name: string;
}

export interface ScreenActivityMusicTrack {
  id: string;
  name: string;
  url: string;
  file_name?: string;
  category_id?: string;
  enabled: boolean;
  sort: number;
}

export interface ScreenActivityMusicSettings {
  volume: number;
  play_mode: "list_loop" | "single_loop" | "random";
  categories: ScreenActivityMusicCategory[];
  tracks: ScreenActivityMusicTrack[];
}

export interface ScreenActivityControlToken {
  token: string;
  expires_in: number;
  control_url: string;
}

export interface ScreenActivityControlPayload {
  config: ScreenActivityConfig;
  participants: ScreenActivityParticipantsPayload;
}
