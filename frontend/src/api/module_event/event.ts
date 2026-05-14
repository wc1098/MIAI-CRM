import request from "@/utils/request";

const API_PATH = "/event/admin";

const EventAPI = {
  listEvent(params: EventPageQuery) {
    return request<ApiResponse<PageResult<EventTable[]>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params,
    });
  },
  detailEvent(id: number) {
    return request<ApiResponse<EventTable>>({
      url: `${API_PATH}/detail/${id}`,
      method: "get",
    });
  },
  createEvent(data: EventForm) {
    return request<ApiResponse<EventTable>>({
      url: `${API_PATH}/create`,
      method: "post",
      data,
    });
  },
  updateEvent(id: number, data: EventForm) {
    return request<ApiResponse<EventTable>>({
      url: `${API_PATH}/update/${id}`,
      method: "put",
      data,
    });
  },
  publishEvent(id: number) {
    return request<ApiResponse<EventTable>>({ url: `${API_PATH}/publish/${id}`, method: "patch" });
  },
  cancelEvent(id: number) {
    return request<ApiResponse<EventTable>>({ url: `${API_PATH}/cancel/${id}`, method: "patch" });
  },
  saveEffect(id: number, data: { effect_html?: string }) {
    return request<ApiResponse<EventTable>>({ url: `${API_PATH}/effect/${id}`, method: "patch", data });
  },
  listRegistrations(id: number) {
    return request<ApiResponse<EventRegistration[]>>({ url: `${API_PATH}/registrations/${id}`, method: "get" });
  },
  listParticipants(id: number) {
    return request<ApiResponse<EventParticipant[]>>({ url: `${API_PATH}/participants/${id}`, method: "get" });
  },
  adminCheckin(registrationId: number) {
    return request<ApiResponse>({ url: `${API_PATH}/checkin/${registrationId}`, method: "post" });
  },
  deleteEvent(ids: number[]) {
    return request<ApiResponse>({ url: `${API_PATH}/delete`, method: "delete", data: ids });
  },
};

export default EventAPI;

export interface EventPageQuery extends PageQuery {
  keyword?: string;
  event_status?: string;
  event_type?: string;
  store_id?: number;
  start_time?: string[];
}

export interface EventForm {
  store_id?: number;
  title: string;
  subtitle?: string;
  event_type: string;
  cover_url?: string;
  location: string;
  start_time: string;
  end_time: string;
  register_deadline: string;
  detail_html?: string;
  effect_html?: string;
  male_quota: number;
  female_quota: number;
  male_fee: number;
  female_fee: number;
  vip_free: boolean;
  require_realname: boolean;
  min_age?: number;
  max_age?: number;
  description?: string;
}

export interface EventTable extends EventForm, BaseType {
  id: number;
  store_name?: string;
  created_id?: number;
  created_name?: string;
  event_status: string;
  published_by?: number;
  published_at?: string;
  male_registered?: number;
  female_registered?: number;
  checked_in_count?: number;
  payment_summary?: Array<Record<string, unknown>>;
}

export interface EventRegistration {
  id: number;
  registration_no: string;
  name?: string;
  mobile_masked?: string;
  gender?: string;
  registration_status: string;
  payable_amount: number;
  paid_amount: number;
  registered_at: string;
  order_id?: number;
  order_no?: string;
  order_status?: string;
  pay_status?: string;
}

export interface EventParticipant {
  id: number;
  onsite_no: string;
  name?: string;
  nickname?: string;
  gender?: string;
  checkin_type: string;
  checked_in_at: string;
  participant_status: string;
}
