import request from "@/utils/request";
import type { AiProfileInfo, PartnerPreference, PartnerPreferenceVersion } from "./lead";

const API_PATH = "/crm/customer";

const CustomerAPI = {
  listCustomer(query?: CustomerPageQuery) {
    return request<ApiResponse<PageResult<CustomerTable[]>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },
  listDealCustomer(query?: CustomerPageQuery) {
    return request<ApiResponse<PageResult<CustomerTable[]>>>({
      url: `${API_PATH}/deal/list`,
      method: "get",
      params: query,
    });
  },
  detailCustomer(id: number) {
    return request<ApiResponse<CustomerDetail>>({
      url: `${API_PATH}/detail/${id}`,
      method: "get",
    });
  },
  updateCustomer(id: number, body: CustomerForm) {
    return request<ApiResponse<CustomerTable>>({
      url: `${API_PATH}/update/${id}`,
      method: "put",
      data: body,
    });
  },
  saveCertificationMaterial(id: number, body: CustomerCertificationMaterialForm) {
    return request<ApiResponse<CustomerCertificationMaterial>>({
      url: `${API_PATH}/certification-material/${id}`,
      method: "post",
      data: body,
    });
  },
  deleteCertificationMaterial(materialId: number) {
    return request<ApiResponse>({
      url: `${API_PATH}/certification-material/${materialId}`,
      method: "delete",
    });
  },
  createFromLead(leadId: number) {
    return request<ApiResponse<CustomerTable>>({
      url: `${API_PATH}/from-lead/${leadId}`,
      method: "post",
    });
  },
  createProcess(id: number, recordType: CustomerProcessType, body: CustomerProcessForm) {
    return request<ApiResponse<CustomerProcessRecord>>({
      url: `${API_PATH}/process/${recordType}/${id}`,
      method: "post",
      data: body,
    });
  },
  createUnifiedProcess(id: number, body: CustomerProcessForm) {
    return request<ApiResponse<CustomerProcessRecord>>({
      url: `${API_PATH}/process/${id}`,
      method: "post",
      data: body,
    });
  },
  listVisit(query?: CustomerVisitQuery) {
    return request<ApiResponse<PageResult<CustomerVisitRecord[]>>>({
      url: `${API_PATH}/visit/list`,
      method: "get",
      params: query,
    });
  },
  checkinVisit(processId: number) {
    return request<ApiResponse<CustomerProcessRecord>>({
      url: `${API_PATH}/visit/checkin/${processId}`,
      method: "post",
    });
  },
  noShowVisit(processId: number) {
    return request<ApiResponse<CustomerProcessRecord>>({
      url: `${API_PATH}/visit/no-show/${processId}`,
      method: "post",
    });
  },
  cancelVisit(processId: number) {
    return request<ApiResponse<CustomerProcessRecord>>({
      url: `${API_PATH}/visit/cancel/${processId}`,
      method: "post",
    });
  },
  consultationVisit(processId: number, body: CustomerVisitConsultationForm) {
    return request<ApiResponse<CustomerProcessRecord>>({
      url: `${API_PATH}/visit/consultation/${processId}`,
      method: "post",
      data: body,
    });
  },
  transferOwner(body: CustomerTransferOwnerForm) {
    return request<ApiResponse>({
      url: `${API_PATH}/transfer-owner`,
      method: "post",
      data: body,
    });
  },
  transferStore(body: CustomerTransferStoreForm) {
    return request<ApiResponse>({
      url: `${API_PATH}/transfer-store`,
      method: "post",
      data: body,
    });
  },
  returnLead(id: number, body: CustomerReturnLeadForm) {
    return request<ApiResponse>({
      url: `${API_PATH}/return-lead/${id}`,
      method: "post",
      data: body,
    });
  },
  printCard(id: number) {
    return request<ApiResponse<CustomerPrintCard>>({
      url: `${API_PATH}/print-card/${id}`,
      method: "get",
    });
  },
};

export default CustomerAPI;

export type CustomerProcessType = "follow" | "appointment" | "visit_checkin" | "consultation" | "no_show" | "appointment_cancel";

export interface CustomerPageQuery extends PageQuery {
  keyword?: string;
  current_stage?: string;
  max_stage?: string;
  gender?: string;
  age_min?: number;
  age_max?: number;
  education?: string;
  marital_status?: string;
  store_id?: number;
  owner_user_id?: number;
  latest_follow_time?: string[];
  next_follow_time?: string[];
  created_time?: string[];
}

export interface CustomerPerson extends BaseType {
  brand_id?: number;
  display_no?: string;
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
  profile_intro?: string;
  id_card_no?: string;
  certification_level?: string;
  certification_summary?: Record<string, unknown>;
}

export interface CustomerTable extends BaseType {
  brand_id?: number;
  person_id: number;
  lead_id?: number;
  store_id: number;
  owner_user_id: number;
  current_stage: string;
  max_stage: string;
  latest_follow_at?: string;
  next_follow_at?: string;
  ended_at?: string;
  end_reason?: string;
  returned_lead_id?: number;
  converted_vip_at?: string;
  person: CustomerPerson;
  store?: CommonType;
  owner_user?: CommonType;
  mobile_masked?: string;
  wechat_masked?: string;
  id_card_no_masked?: string;
  can_view_contact?: boolean;
  can_view_id_card?: boolean;
  age?: number;
  constellation?: string;
  zodiac?: string;
  ai_profile?: AiProfileInfo;
  partner_preference?: PartnerPreference | null;
}

export interface CustomerDetail extends CustomerTable {
  process_records: CustomerProcessRecord[];
  lead_process_records: Array<Record<string, unknown>>;
  lifecycle_records: CustomerLifecycleRecord[];
  lead_lifecycle_records: Array<Record<string, unknown>>;
  partner_preference_versions?: PartnerPreferenceVersion[];
  certification?: CustomerCertificationArchive;
}

export interface CustomerCertificationArchiveItem {
  item_code: string;
  item_name: string;
  sort?: number;
  material_required?: boolean;
  material_desc?: string;
}

export interface CustomerCertificationMaterial extends BaseType {
  customer_id: number;
  person_id: number;
  item_code: string;
  item_name: string;
  material_type: string;
  file_name?: string;
  file_path?: string;
  file_url: string;
  payload?: Record<string, unknown>;
  collected_by?: number;
}

export interface CustomerCertificationArchive {
  certification_level?: string;
  certification_summary?: Record<string, unknown>;
  id_card_no_masked?: string;
  archive_items?: CustomerCertificationArchiveItem[];
  archive_materials?: CustomerCertificationMaterial[];
}

export interface CustomerCertificationMaterialForm {
  item_code: string;
  item_name?: string;
  material_type?: string;
  file_name?: string;
  file_path?: string;
  file_url: string;
  payload?: Record<string, unknown>;
}

export interface CustomerForm {
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
  profile_intro?: string;
  id_card_no?: string;
  current_stage?: string;
  next_follow_at?: string;
  partner_preference?: PartnerPreference;
  description?: string;
}

export interface CustomerProcessForm {
  method?: string;
  result?: string;
  content: string;
  next_follow_at?: string;
  scheduled_at?: string;
  appointment_slot?: string;
  visit_purpose?: string;
  promised_gift?: string;
  need_summary?: string;
  budget_range?: string;
  main_objection?: string;
  intention_level?: string;
  next_action?: string;
  enter_signing?: boolean;
}

export interface CustomerProcessRecord extends BaseType {
  record_type: string;
  occurred_at: string;
  method?: string;
  result?: string;
  content: string;
  next_follow_at?: string;
  scheduled_at?: string;
  appointment_slot?: string;
  visit_purpose?: string;
  promised_gift?: string;
  appointment_status?: string;
  checked_in_at?: string;
  checked_in_user_id?: number;
  checked_in_user_name?: string;
  need_summary?: string;
  budget_range?: string;
  main_objection?: string;
  intention_level?: string;
  next_action?: string;
  enter_signing?: boolean;
  operator_user_id?: number;
  operator_user_name?: string;
  source?: string;
}

export interface CustomerVisitQuery extends PageQuery {
  keyword?: string;
  scheduled_time?: string[];
  appointment_slot?: string;
  visit_purpose?: string;
  appointment_status?: string;
  operator_user_id?: number;
  store_id?: number;
}

export interface CustomerVisitRecord extends CustomerProcessRecord {
  appointment_source?: "sales" | "service";
  customer?: {
    id: number;
    current_stage?: string;
    store_id?: number;
    owner_user_id?: number;
    owner_user_name?: string;
  };
  person?: {
    id: number;
    display_no?: string;
    name: string;
    gender?: string;
    primary_mobile?: string;
  };
}

export interface CustomerVisitConsultationForm {
  content: string;
  need_summary?: string;
  budget_range?: string;
  main_objection?: string;
  intention_level?: string;
  next_follow_at?: string;
  enter_signing?: boolean;
}

export interface CustomerLifecycleRecord extends BaseType {
  operation_type: string;
  operator_user_id?: number;
  operator_user_name?: string;
  change_detail?: Record<string, unknown>;
  remark?: string;
  source?: string;
}

export interface CustomerTransferOwnerForm {
  customer_id: number;
  owner_user_id: number;
  remark?: string;
}

export interface CustomerTransferStoreForm extends CustomerTransferOwnerForm {
  store_id: number;
}

export interface CustomerReturnLeadForm {
  reason_type: string;
  reason: string;
}

export interface CustomerPrintCard {
  brand_name: string;
  printed_at: string;
  customer_no?: string;
  display_name: string;
  gender: string;
  age?: number;
  constellation?: string;
  zodiac?: string;
  height_cm?: number;
  weight_kg?: number;
  education?: string;
  occupation?: string;
  occupation_code?: string;
  graduated_school?: string;
  major?: string;
  unit_type?: string;
  job_title?: string;
  work_company?: string;
  annual_income?: string;
  marital_status?: string;
  hometown?: string;
  residence?: string;
  house_status?: string;
  car_status?: string;
  profile_intro?: string;
  family_background?: string;
  first_photo_url?: string;
  partner_preference?: PartnerPreference;
  miai_impression?: string;
}
