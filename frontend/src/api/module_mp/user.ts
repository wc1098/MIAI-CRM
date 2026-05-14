import request from "@/utils/request";
import type { AiProfileInfo } from "@/api/module_crm/lead";

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
};

export default MpUserAPI;

export interface MpUserPageQuery extends PageQuery {
  keyword?: string;
  is_registered?: boolean;
}

export interface MpUserPerson {
  id?: number;
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
}
