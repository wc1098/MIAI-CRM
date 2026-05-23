import request from "@/utils/request";

const API_PATH = "/common/upload";

export type UploadScene = "mp_register_photo" | "certification_material" | "crm_lead_photo" | "crm_contract_attachment" | "event_cover" | "common_image";

export interface OssPolicyRequest {
  scene: UploadScene;
  filename: string;
  content_type: string;
  size: number;
}

export interface OssPolicyResponse {
  host: string;
  object_key: string;
  file_url: string;
  policy: string;
  signature: string;
  access_key_id: string;
  expire_at: string;
  max_size: number;
}

export interface UploadConfirmRequest {
  scene: UploadScene;
  object_key: string;
  file_url: string;
}

export interface UploadConfirmResponse {
  file_name: string;
  origin_name?: string;
  file_path: string;
  file_url: string;
  object_key: string;
  content_type?: string;
  scene: UploadScene;
}

const CommonUploadAPI = {
  ossPolicy(data: OssPolicyRequest) {
    return request<ApiResponse<OssPolicyResponse>>({
      url: `${API_PATH}/oss-policy`,
      method: "post",
      data,
    });
  },

  confirm(data: UploadConfirmRequest) {
    return request<ApiResponse<UploadConfirmResponse>>({
      url: `${API_PATH}/confirm`,
      method: "post",
      data,
    });
  },
};

export default CommonUploadAPI;
