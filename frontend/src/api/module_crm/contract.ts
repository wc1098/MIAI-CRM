import request from "@/utils/request";

const API_PATH = "/crm/contract";

const ContractAPI = {
  listContract(query?: ContractPageQuery) {
    return request<ApiResponse<PageResult<ContractTable[]>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },
  detailContract(id: number) {
    return request<ApiResponse<ContractTable>>({
      url: `${API_PATH}/detail/${id}`,
      method: "get",
    });
  },
  createContract(body: ContractForm) {
    return request<ApiResponse<ContractTable>>({
      url: `${API_PATH}/create`,
      method: "post",
      data: body,
    });
  },
  updateContract(id: number, body: ContractForm) {
    return request<ApiResponse<ContractTable>>({
      url: `${API_PATH}/update/${id}`,
      method: "put",
      data: body,
    });
  },
  signContract(id: number, body: { remark?: string }) {
    return request<ApiResponse<ContractTable>>({
      url: `${API_PATH}/sign/${id}`,
      method: "post",
      data: body,
    });
  },
  submitReview(id: number) {
    return request<ApiResponse<ContractTable>>({
      url: `${API_PATH}/submit-review/${id}`,
      method: "post",
    });
  },
  reviewContract(id: number, body: ContractReviewForm) {
    return request<ApiResponse<ContractTable>>({
      url: `${API_PATH}/review/${id}`,
      method: "post",
      data: body,
    });
  },
  getStoreRule(storeId: number) {
    return request<ApiResponse<ContractStoreRule>>({
      url: `${API_PATH}/store-rule/${storeId}`,
      method: "get",
    });
  },
  setStoreRule(storeId: number, body: ContractStoreRule) {
    return request<ApiResponse>({
      url: `${API_PATH}/store-rule/${storeId}`,
      method: "put",
      data: body,
    });
  },
  voidContract(id: number, body: { reason: string }) {
    return request<ApiResponse<ContractTable>>({
      url: `${API_PATH}/void/${id}`,
      method: "post",
      data: body,
    });
  },
  saveAttachment(id: number, body: ContractAttachmentForm) {
    return request<ApiResponse<ContractAttachment>>({
      url: `${API_PATH}/attachment/${id}`,
      method: "post",
      data: body,
    });
  },
  deleteAttachment(attachmentId: number) {
    return request<ApiResponse>({
      url: `${API_PATH}/attachment/${attachmentId}`,
      method: "delete",
    });
  },
  searchCustomer(query?: { keyword?: string; limit?: number }) {
    return request<ApiResponse<ContractCustomerOption[]>>({
      url: `${API_PATH}/customer/search`,
      method: "get",
      params: query,
    });
  },
};

export default ContractAPI;

export interface ContractPageQuery extends PageQuery {
  keyword?: string;
  contract_status?: string;
  payment_status?: string;
  vip_level?: string;
  store_id?: number;
  owner_user_id?: number;
  customer_id?: number;
}

export interface ContractForm {
  id?: number;
  customer_id?: number;
  product_ids: number[];
  contract_name: string;
  contract_amount: number;
  discount_reason?: string;
  start_date?: string;
  end_date?: string;
  expire_remind_days?: number;
  signer_name: string;
  vip_level?: string;
  remark?: string;
}

export interface ContractTable extends BaseType {
  brand_id: number;
  contract_no: string;
  contract_name: string;
  customer_id: number;
  person_id: number;
  store_id: number;
  owner_user_id: number;
  vip_level: string;
  contract_status: string;
  original_amount: string | number;
  contract_amount: string | number;
  received_amount?: string | number;
  pending_amount?: string | number;
  payment_progress?: string | number;
  payment_status?: string;
  validity_period?: string;
  discount_amount: string | number;
  discount_rate: string | number;
  discount_reason?: string;
  start_date: string;
  end_date: string;
  expire_remind_days: number;
  signer_name: string;
  signed_at?: string;
  review_submitted_at?: string;
  reviewed_at?: string;
  reviewed_by?: number;
  review_remark?: string;
  effective_at?: string;
  first_paid_at?: string;
  voided_at?: string;
  void_reason?: string;
  remark?: string;
  customer?: CommonType;
  person?: CommonType;
  person_display_no?: string;
  person_mobile?: string;
  owner_user_name?: string;
  store_name?: string;
  items: ContractItem[];
  attachments: ContractAttachment[];
  receipts: ContractReceipt[];
}

export interface ContractItem extends BaseType {
  contract_id: number;
  product_id?: number;
  product_name_snapshot: string;
  price_snapshot: string | number;
  service_days_snapshot: number;
  recommendation_quota_snapshot: number;
  meeting_quota_snapshot: number;
  course_quota_snapshot: number;
  supports_online_meeting_snapshot: boolean;
}

export interface ContractAttachment extends BaseType {
  contract_id: number;
  file_name?: string;
  file_path?: string;
  file_url: string;
  file_type: string;
  page_count?: number;
  attachment_status: string;
  payload?: Record<string, unknown>;
}

export interface ContractAttachmentForm {
  file_name?: string;
  file_path?: string;
  file_url: string;
  file_type?: string;
  page_count?: number;
  payload?: Record<string, unknown>;
}

export interface ContractReceipt extends BaseType {
  receipt_no: string;
  contract_id: number;
  customer_id: number;
  person_id: number;
  store_id: number;
  receipt_type: string;
  pay_method: string;
  amount: string | number;
  receipt_status: string;
  payment_scene: string;
  submitted_at: string;
  reviewed_at?: string;
  reviewed_by?: number;
  review_remark?: string;
  remark?: string;
}

export interface ContractReviewForm {
  approved: boolean;
  review_remark?: string;
}

export interface ContractStoreRule {
  require_contract_review: boolean;
}

export interface ContractCustomerOption {
  id: number;
  person_id: number;
  display_no?: string;
  name: string;
  mobile: string;
  gender: string;
  store_id: number;
  owner_user_id: number;
}
