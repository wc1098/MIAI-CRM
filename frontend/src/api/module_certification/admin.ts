import request from "@/utils/request";

const API_PATH = "/certification/admin";

const CertificationAdminAPI = {
  listItems() {
    return request<ApiResponse<CertificationItem[]>>({ url: `${API_PATH}/items/list`, method: "get" });
  },
  saveItem(itemCode: string, body: CertificationItem) {
    return request<ApiResponse<CertificationItem>>({ url: `${API_PATH}/items/${itemCode}`, method: "put", data: body });
  },
  listPackages() {
    return request<ApiResponse<CertificationPackage[]>>({ url: `${API_PATH}/packages/list`, method: "get" });
  },
  savePackage(levelCode: string, body: CertificationPackage) {
    return request<ApiResponse<CertificationPackage>>({ url: `${API_PATH}/packages/${levelCode}`, method: "put", data: body });
  },
  listApplications(query?: CertificationApplicationQuery) {
    return request<ApiResponse<PageResult<CertificationApplication[]>>>({ url: `${API_PATH}/applications/list`, method: "get", params: query });
  },
  getApplication(id: number) {
    return request<ApiResponse<CertificationApplication>>({ url: `${API_PATH}/applications/${id}`, method: "get" });
  },
  getPersonSummary(personId: number) {
    return request<ApiResponse<CertificationPersonSummary>>({ url: `${API_PATH}/person/${personId}/summary`, method: "get" });
  },
  listRecords(query?: CertificationRecordQuery) {
    return request<ApiResponse<PageResult<CertificationRecord[]>>>({ url: `${API_PATH}/records/list`, method: "get", params: query });
  },
  listVerificationLogs(query?: CertificationLogQuery) {
    return request<ApiResponse<PageResult<CertificationVerificationLog[]>>>({ url: `${API_PATH}/verification-logs/list`, method: "get", params: query });
  },
  listFaceLogs(query?: CertificationLogQuery) {
    return request<ApiResponse<PageResult<CertificationFaceLog[]>>>({ url: `${API_PATH}/face-logs/list`, method: "get", params: query });
  },
  reviewRecord(id: number, body: { action: "approve" | "reject"; reject_reason?: string }) {
    return request<ApiResponse<CertificationRecord>>({ url: `${API_PATH}/records/${id}/review`, method: "post", data: body });
  },
  viewIdCard(personId: number, reason?: string) {
    return request<ApiResponse<{ person_id: number; id_card_no?: string; id_card_no_masked?: string }>>({
      url: `${API_PATH}/person/${personId}/id-card/view`,
      method: "post",
      data: { reason },
    });
  },
};

export default CertificationAdminAPI;

export interface CertificationItem {
  id?: number;
  item_code: string;
  item_name: string;
  verify_mode: "auto_api" | "manual";
  verifier_code?: string;
  material_required: boolean;
  material_desc?: string;
  validity_days?: number;
  sort: number;
  status: string;
}

export interface CertificationPackage {
  id?: number;
  level_code: "basic" | "advanced" | "premium";
  level_name: string;
  price: string;
  item_codes: string[];
  reward_coupon_count: number;
  reward_coupon_valid_days: number;
  benefit_desc?: string;
  sort: number;
  status: string;
}

export interface CertificationApplicationQuery extends PageQuery {
  keyword?: string;
  status?: string;
  level_code?: string;
}

export interface CertificationRecordQuery extends PageQuery {
  keyword?: string;
  status?: string;
  item_code?: string;
}

export interface CertificationLogQuery extends PageQuery {
  keyword?: string;
  application_id?: number;
  record_id?: number;
  status?: string;
}

export interface CertificationMaterial {
  id: number;
  item_code: string;
  material_type: string;
  file_name?: string;
  file_url?: string;
  payload?: Record<string, unknown>;
  created_time?: string;
}

export interface CertificationRecord {
  id: number;
  application_id: number;
  user_id: number;
  person_id: number;
  item_code: string;
  item_name: string;
  verify_mode: string;
  record_status: string;
  submitted_at?: string;
  verified_at?: string;
  reviewed_at?: string;
  reject_reason?: string;
  payload?: Record<string, unknown>;
  materials?: CertificationMaterial[];
  nickname?: string;
  mobile?: string;
  display_no?: string;
  person_name?: string;
  id_card_no_masked?: string;
}

export interface CertificationProgress {
  total: number;
  approved: number;
  pending_review: number;
  rejected: number;
  percent: number;
}

export interface CertificationApplication {
  id: number;
  user_id: number;
  person_id: number;
  package_id: number;
  order_id?: number;
  level_code: string;
  level_name: string;
  item_codes: string[];
  application_status: string;
  paid_at?: string;
  approved_at?: string;
  reward_granted_at?: string;
  records?: CertificationRecord[];
  nickname?: string;
  mobile?: string;
  display_no?: string;
  person_name?: string;
  current_level?: string;
  current_level_name?: string;
  id_card_no_masked?: string;
  order?: {
    id: number;
    order_no: string;
    amount: string;
    payable_amount: string;
    order_status: string;
    pay_status: string;
    expire_at?: string;
    paid_at?: string;
  };
  reward_granted?: boolean;
  progress?: CertificationProgress;
}

export interface CertificationPersonSummary {
  person_id: number;
  display_no?: string;
  person_name?: string;
  mobile?: string;
  id_card_no_masked?: string;
  certification_level: string;
  certification_level_name: string;
  certification_summary?: Record<string, unknown>;
  latest_application?: CertificationApplication;
  applications: CertificationApplication[];
  verification_logs: CertificationVerificationLog[];
  face_logs: CertificationFaceLog[];
}

export interface CertificationVerificationLog {
  id: number;
  application_id?: number;
  record_id?: number;
  nickname?: string;
  mobile?: string;
  display_no?: string;
  person_name?: string;
  verifier_code: string;
  request_snapshot?: Record<string, unknown>;
  response_snapshot?: Record<string, unknown>;
  verify_status: string;
  provider_request_id?: string;
  error_message?: string;
  verified_at?: string;
}

export interface CertificationFaceLog {
  id: number;
  nickname?: string;
  mobile?: string;
  display_no?: string;
  person_name?: string;
  business_type: string;
  business_id?: number;
  file_url?: string;
  face_count: number;
  quality_score?: string;
  beauty_score?: string;
  age?: string;
  gender?: string;
  passed: boolean;
  response_snapshot?: Record<string, unknown>;
  error_message?: string;
  detected_at?: string;
}
