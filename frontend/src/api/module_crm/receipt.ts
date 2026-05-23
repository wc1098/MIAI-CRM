import request from "@/utils/request";

const API_PATH = "/crm/receipt";

const ReceiptAPI = {
  listReceipt(query?: ReceiptPageQuery) {
    return request<ApiResponse<PageResult<ReceiptTable[]>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },
  detailReceipt(id: number) {
    return request<ApiResponse<ReceiptTable>>({
      url: `${API_PATH}/detail/${id}`,
      method: "get",
    });
  },
  searchContract(query?: { keyword?: string; limit?: number }) {
    return request<ApiResponse<ReceiptContractOption[]>>({
      url: `${API_PATH}/contract/search`,
      method: "get",
      params: query,
    });
  },
  createOffline(contractId: number, body: ReceiptForm) {
    return request<ApiResponse<ReceiptTable>>({
      url: `${API_PATH}/offline/${contractId}`,
      method: "post",
      data: body,
    });
  },
  createPending(contractId: number, body: ReceiptPendingForm) {
    return request<ApiResponse<ReceiptTable>>({
      url: `${API_PATH}/pending/${contractId}`,
      method: "post",
      data: body,
    });
  },
  qrcodePay(receiptId: number, body: QrcodePayForm) {
    return request<ApiResponse<ReceiptPaymentResult>>({
      url: `${API_PATH}/qrcode/${receiptId}`,
      method: "post",
      data: body,
    });
  },
  offlineConfirm(receiptId: number, body: OfflineConfirmForm) {
    return request<ApiResponse<ReceiptTable>>({
      url: `${API_PATH}/offline-confirm/${receiptId}`,
      method: "post",
      data: body,
    });
  },
  createOnline(contractId: number, body: OnlineReceiptForm) {
    return request<ApiResponse<ReceiptPaymentResult>>({
      url: `${API_PATH}/online/${contractId}`,
      method: "post",
      data: body,
    });
  },
  barcodePay(receiptId: number, body: BarcodePayForm) {
    return request<ApiResponse<ReceiptPaymentResult>>({
      url: `${API_PATH}/barcode/${receiptId}`,
      method: "post",
      data: body,
    });
  },
  createBarcode(contractId: number, body: BarcodeReceiptForm) {
    return request<ApiResponse<ReceiptPaymentResult>>({
      url: `${API_PATH}/barcode-create/${contractId}`,
      method: "post",
      data: body,
    });
  },
  reviewReceipt(id: number, body: ReceiptReviewForm) {
    return request<ApiResponse<ReceiptTable>>({
      url: `${API_PATH}/review/${id}`,
      method: "post",
      data: body,
    });
  },
  voidReceipt(id: number, body: { reason: string }) {
    return request<ApiResponse<ReceiptTable>>({
      url: `${API_PATH}/void/${id}`,
      method: "post",
      data: body,
    });
  },
  reverseReceipt(id: number, body: { reason: string }) {
    return request<ApiResponse<ReceiptTable>>({
      url: `${API_PATH}/reverse/${id}`,
      method: "post",
      data: body,
    });
  },
  refundRegister(id: number, body: { amount: number; reason: string }) {
    return request<ApiResponse<ReceiptTable>>({
      url: `${API_PATH}/refund-register/${id}`,
      method: "post",
      data: body,
    });
  },
  summary(query?: { contract_id?: number }) {
    return request<ApiResponse<ReceiptSummary>>({
      url: `${API_PATH}/summary`,
      method: "get",
      params: query,
    });
  },
};

export default ReceiptAPI;

export interface ReceiptPageQuery extends PageQuery {
  keyword?: string;
  contract_id?: number;
  receipt_type?: string;
  payment_scene?: string;
  pay_method?: string;
  receipt_status?: string;
  store_id?: number;
  owner_user_id?: number;
  submitted_start?: string;
  submitted_end?: string;
  confirmed_start?: string;
  confirmed_end?: string;
}

export interface ReceiptTable extends BaseType {
  brand_id?: number;
  receipt_no: string;
  contract_id: number;
  contract_no?: string;
  contract_name?: string;
  customer_id: number;
  person_id: number;
  person_name?: string;
  person_display_no?: string;
  person_mobile?: string;
  store_id: number;
  store_name?: string;
  owner_user_id?: number;
  owner_user_name?: string;
  receipt_type: string;
  pay_method: string;
  amount: string | number;
  receipt_status: string;
  payment_scene: string;
  order_id?: number;
  order_no?: string;
  order_pay_status?: string;
  payment_id?: number;
  channel_trade_no?: string;
  submitted_at: string;
  reviewed_at?: string;
  reviewed_by?: number;
  reviewed_by_name?: string;
  review_remark?: string;
  paid_at?: string;
  confirmed_at?: string;
  confirmed_by?: number;
  confirmed_by_name?: string;
  voided_at?: string;
  voided_by?: number;
  voided_by_name?: string;
  void_reason?: string;
  reverse_receipt_id?: number;
  reverse_reason?: string;
  payment_payload?: Record<string, unknown>;
  remark?: string;
}

export interface ReceiptContractOption {
  id: number;
  contract_no: string;
  contract_name: string;
  contract_status: string;
  contract_amount: string | number;
  received_amount?: string | number;
  pending_amount?: string | number;
  payment_status?: string;
  customer_id: number;
  person_id: number;
  person_name?: string;
  person_display_no?: string;
  person_mobile?: string;
  store_id: number;
  store_name?: string;
  owner_user_id?: number;
  owner_user_name?: string;
}

export interface ReceiptForm {
  receipt_type: string;
  pay_method: string;
  amount: number;
  remark?: string;
}

export interface ReceiptPendingForm {
  receipt_type: string;
  amount: number;
  remark?: string;
}

export interface OfflineConfirmForm {
  pay_method: string;
  remark?: string;
}

export interface OnlineReceiptForm {
  receipt_type: string;
  pay_channel: string;
  amount: number;
  operator_id?: string;
  remark?: string;
}

export interface QrcodePayForm {
  pay_channel: string;
  operator_id?: string;
}

export interface BarcodePayForm {
  auth_code: string;
  pay_channel?: string;
  operator_id?: string;
}

export interface BarcodeReceiptForm extends BarcodePayForm {
  receipt_type: string;
  pay_channel: string;
  amount: number;
  remark?: string;
}

export interface ReceiptReviewForm {
  approved: boolean;
  review_remark?: string;
}

export interface ReceiptPaymentResult {
  receipt: ReceiptTable;
  payment: Record<string, unknown>;
}

export interface ReceiptSummary {
  contract_id?: number;
  contract_amount: string | number;
  received_amount: string | number;
  pending_amount: string | number;
  first_payment_received: boolean;
  balance_paid: boolean;
}
