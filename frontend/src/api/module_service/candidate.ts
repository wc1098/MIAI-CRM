import request from "@/utils/request";
import type { PartnerPreference } from "@/api/module_crm/lead";
import type { PersonDetail, PersonTimelineItem } from "@/api/module_crm/person";
import type { CustomerCertificationArchiveItem, CustomerCertificationMaterialForm } from "@/api/module_crm/customer";

const API_PATH = "/service/candidate";

const CandidateAPI = {
  listCandidate(query?: CandidatePageQuery) {
    return request<ApiResponse<PageResult<CandidateRecord[]>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },
  detailCandidate(id: number) {
    return request<ApiResponse<CandidateDetail>>({
      url: `${API_PATH}/detail/${id}`,
      method: "get",
    });
  },
  searchPerson(query?: { keyword?: string; limit?: number }) {
    return request<ApiResponse<PersonOption[]>>({
      url: `${API_PATH}/person/search`,
      method: "get",
      params: query,
    });
  },
  addExisting(body: CandidateAddExistingForm) {
    return request<ApiResponse<CandidateRecord>>({
      url: `${API_PATH}/add-existing`,
      method: "post",
      data: body,
    });
  },
  manualCreate(body: CandidateCreateForm) {
    return request<ApiResponse<CandidateRecord>>({
      url: `${API_PATH}/manual-create`,
      method: "post",
      data: body,
    });
  },
  listCertificationArchiveItems() {
    return request<ApiResponse<CustomerCertificationArchiveItem[]>>({
      url: `${API_PATH}/certification-archive-items`,
      method: "get",
    });
  },
  discover(body: CandidateDiscoverQuery) {
    return request<ApiResponse<PageResult<CandidateDiscoverRecord[]>>>({
      url: `${API_PATH}/discover`,
      method: "post",
      data: body,
    });
  },
  createJoinRequest(body: CandidateJoinRequestForm) {
    return request<ApiResponse<CandidateJoinRequestRecord>>({
      url: `${API_PATH}/join-request`,
      method: "post",
      data: body,
    });
  },
  listJoinRequests(query?: CandidateJoinRequestQuery) {
    return request<ApiResponse<PageResult<CandidateJoinRequestRecord[]>>>({
      url: `${API_PATH}/join-request/list`,
      method: "get",
      params: query,
    });
  },
  reviewJoinRequest(id: number, body: CandidateJoinReviewForm) {
    return request<ApiResponse<CandidateJoinRequestRecord>>({
      url: `${API_PATH}/join-request/${id}/review`,
      method: "post",
      data: body,
    });
  },
  getRule() {
    return request<ApiResponse<CandidateRule>>({
      url: `${API_PATH}/rule`,
      method: "get",
    });
  },
  updateRule(body: CandidateRuleUpdateForm) {
    return request<ApiResponse<CandidateRule>>({
      url: `${API_PATH}/rule`,
      method: "put",
      data: body,
    });
  },
};

export default CandidateAPI;

export interface CandidatePageQuery extends PageQuery {
  keyword?: string;
  source_type?: string;
  mine?: boolean;
}

export interface CandidateRecord extends BaseType {
  candidate_id: number;
  person_id: number;
  matchmaker_id: number;
  matchmaker_name?: string;
  store_id?: number;
  store_name?: string;
  source_type: string;
  name: string;
  gender: string;
  mobile?: string;
  wechat?: string;
  birth_date?: string;
  age?: number;
  height_cm?: number;
  residence?: string;
  education?: string;
  annual_income?: string;
  marital_status?: string;
  private_tags?: string[];
  private_remark?: string;
  join_request_id?: number;
  approved_by?: number;
  approved_at?: string;
  contact_unmasked_after_approval?: boolean;
}

export interface CandidateDetail {
  person: {
    id: number;
    display_no?: string;
    name: string;
    gender: string;
    mobile?: string;
    wechat?: string;
    birth_date?: string;
    age?: number;
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
    accept_long_distance_self?: boolean;
    accept_flash_marriage?: boolean;
    willing_relocate?: boolean;
    marriage_plan?: string;
    profile_intro?: string;
    profile_remark?: string;
    photo_urls?: string[];
    certification_level?: string;
    store_id?: number;
    store_name?: string;
  };
  partner_preference?: PartnerPreference;
  person_center?: PersonDetail;
  timeline?: PersonTimelineItem[];
  candidate?: CandidateRecord;
  backup: {
    in_backup: boolean;
    backup_item_id?: number;
    contact_unmasked: boolean;
    pending_request: boolean;
    pending_request_id?: number;
    request_scope: "store" | "brand";
    unlock_method: "backup_approved" | "pending_review" | "join_request";
  };
}

export interface PersonOption {
  id: number;
  display_no?: string;
  name: string;
  gender: string;
  mobile?: string;
  store_id?: number;
  age?: number;
}

export interface CandidateAddExistingForm {
  person_id?: number;
  matchmaker_id?: number;
  private_tags?: string[];
  private_remark?: string;
}

export interface CandidateCreateForm {
  name?: string;
  gender?: string;
  primary_mobile?: string;
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
  accept_long_distance_self?: boolean;
  accept_flash_marriage?: boolean;
  willing_relocate?: boolean;
  marriage_plan?: string;
  family_background?: string;
  profile_remark?: string;
  photo_urls?: string[];
  profile_intro?: string;
  id_card_no?: string;
  partner_preference?: PartnerPreference;
  certification_materials?: CustomerCertificationMaterialForm[];
  matchmaker_id?: number;
  private_tags?: string[];
  private_remark?: string;
}

export interface CandidateDiscoverQuery extends PageQuery {
  scope: "store" | "brand";
  keyword?: string;
  person_id?: number;
  display_no?: string;
  mobile?: string;
  name?: string;
  matchmaker_id?: number;
  gender?: string;
  age_min?: number;
  age_max?: number;
  height_min?: number;
  height_max?: number;
  weight_min?: number;
  weight_max?: number;
  education?: string;
  annual_income?: string;
  marital_status?: string;
  ethnicity?: string;
  occupation_code?: string;
  unit_type?: string;
  residence?: string;
  hometown?: string;
  house_status?: string;
  car_status?: string;
  accept_long_distance_self?: boolean;
  accept_flash_marriage?: boolean;
  willing_relocate?: boolean;
  marriage_plan?: string;
  has_photo?: boolean;
  certification_level?: string;
  pref_age_min?: number;
  pref_age_max?: number;
  pref_height_min?: number;
  pref_height_max?: number;
  pref_weight_min?: number;
  pref_weight_max?: number;
  preferred_residence_region_codes?: string[];
  preferred_hometown_region_codes?: string[];
  preferred_education_codes?: string[];
  preferred_marital_status_codes?: string[];
  preferred_annual_income_codes?: string[];
  preferred_house_status_codes?: string[];
  preferred_car_status_codes?: string[];
  pref_accept_long_distance?: boolean;
  pref_accept_divorced?: boolean;
  pref_accept_children?: boolean;
  children_requirement?: string;
  preferred_occupation_text?: string;
  preference_text?: string;
  hard_reject_items?: string[];
  soft_preference_items?: string[];
  preferred_personality_tags?: string[];
  preferred_lifestyle_tags?: string[];
  preferred_relationship_tags?: string[];
  strictness_level?: string;
  must_match_fields?: string[];
  preferred_match_fields?: string[];
}

export interface CandidateDiscoverRecord {
  id: number;
  display_no?: string;
  name: string;
  gender: string;
  mobile?: string;
  wechat?: string;
  store_id?: number;
  store_name?: string;
  age?: number;
  height_cm?: number;
  weight_kg?: number;
  residence?: string;
  hometown?: string;
  education?: string;
  annual_income?: string;
  marital_status?: string;
  has_photo: boolean;
  certification_level?: string;
  already_in_backup: boolean;
  pending_request: boolean;
}

export interface CandidateJoinRequestForm {
  person_id?: number;
  scope?: "store" | "brand";
  matchmaker_id?: number;
  private_tags?: string[];
  private_remark?: string;
  request_reason?: string;
}

export interface CandidateJoinRequestQuery extends PageQuery {
  review_status?: string;
  scope?: string;
  mine?: boolean;
}

export interface CandidateJoinRequestRecord extends BaseType {
  person_id: number;
  person_name?: string;
  person_display_no?: string;
  person_gender?: string;
  person_mobile?: string;
  person_wechat?: string;
  person_store_id?: number;
  person_store_name?: string;
  request_scope: string;
  request_matchmaker_id: number;
  request_matchmaker_name?: string;
  request_store_id?: number;
  request_store_name?: string;
  private_tags_snapshot?: string[];
  private_remark_snapshot?: string;
  request_reason?: string;
  review_status: string;
  reviewer_id?: number;
  reviewer_name?: string;
  reviewed_at?: string;
  review_remark?: string;
  approved_backup_item_id?: number;
}

export interface CandidateJoinReviewForm {
  review_status: "approved" | "rejected";
  review_remark?: string;
}

export interface CandidateRule {
  store_join_requires_review: boolean;
  brand_join_requires_review: boolean;
}

export interface CandidateRuleUpdateForm {
  store_join_requires_review: boolean;
}
