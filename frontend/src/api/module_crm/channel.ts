import request from "@/utils/request";

const API_PATH = "/crm/channel";

const ChannelAPI = {
  listChannel(query?: ChannelPageQuery) {
    return request<ApiResponse<PageResult<ChannelTable[]>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },

  detailChannel(id: number) {
    return request<ApiResponse<ChannelTable>>({
      url: `${API_PATH}/detail/${id}`,
      method: "get",
    });
  },

  createChannel(body: ChannelForm) {
    return request<ApiResponse>({
      url: `${API_PATH}/create`,
      method: "post",
      data: body,
    });
  },

  updateChannel(id: number, body: ChannelForm) {
    return request<ApiResponse>({
      url: `${API_PATH}/update/${id}`,
      method: "put",
      data: body,
    });
  },

  deleteChannel(body: number[]) {
    return request<ApiResponse>({
      url: `${API_PATH}/delete`,
      method: "delete",
      data: body,
    });
  },

  batchChannel(body: BatchType) {
    return request<ApiResponse>({
      url: `${API_PATH}/available/setting`,
      method: "patch",
      data: body,
    });
  },

  exportChannel(body: ChannelPageQuery) {
    return request<Blob>({
      url: `${API_PATH}/export`,
      method: "post",
      data: body,
      responseType: "blob",
    });
  },
};

export default ChannelAPI;

export interface ChannelPageQuery extends PageQuery {
  channel_code?: string;
  channel_name?: string;
  channel_type?: string;
  source_system?: string;
  status?: string;
  created_time?: string[];
  updated_time?: string[];
}

export interface ChannelTable extends BaseType {
  channel_code?: string;
  channel_name?: string;
  channel_type?: string;
  source_system?: string;
  external_code?: string;
  landing_url?: string;
  sort?: number;
  created_by?: CommonType;
  updated_by?: CommonType;
}

export interface ChannelForm extends BaseFormType {
  channel_code?: string;
  channel_name?: string;
  channel_type?: string;
  source_system?: string;
  external_code?: string;
  landing_url?: string;
  sort?: number;
}
