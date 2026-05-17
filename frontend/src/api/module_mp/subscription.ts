import request from "@/utils/request";

const API_PATH = "/subscription/admin";

const MpSubscriptionAPI = {
  listPlans() {
    return request<ApiResponse<SubscriptionPlan[]>>({
      url: `${API_PATH}/plans/list`,
      method: "get",
    });
  },
  savePlan(body: SubscriptionPlan, id?: number) {
    return request<ApiResponse<SubscriptionPlan>>({
      url: id ? `${API_PATH}/plans/${id}` : `${API_PATH}/plans`,
      method: id ? "put" : "post",
      data: body,
    });
  },
  listSubscriptions(query?: SubscriptionQuery) {
    return request<ApiResponse<PageResult<UserSubscriptionRecord[]>>>({
      url: `${API_PATH}/subscriptions/list`,
      method: "get",
      params: query,
    });
  },
  listRecommendations(query?: SubscriptionQuery) {
    return request<ApiResponse<PageResult<SubscriptionRecommendationRecord[]>>>({
      url: `${API_PATH}/recommendations/list`,
      method: "get",
      params: query,
    });
  },
  rematchRecommendation(id: number) {
    return request<ApiResponse<{ status: string }>>({
      url: `${API_PATH}/recommendations/${id}/rematch`,
      method: "post",
    });
  },
};

export default MpSubscriptionAPI;

export interface SubscriptionPlan {
  id?: number;
  plan_code: string;
  plan_name: string;
  pay_period: "month" | "quarter" | "year";
  period_days: number;
  price: string;
  monthly_recommend_count: number;
  total_quota: number;
  benefit_desc?: string;
  sort: number;
  status: string;
}

export interface SubscriptionQuery extends PageQuery {
  keyword?: string;
  status?: string;
}

export interface UserSubscriptionRecord {
  id: number;
  user_id: number;
  display_no?: string;
  nickname?: string;
  mobile?: string;
  plan_name: string;
  started_at?: string;
  expired_at?: string;
  total_quota: number;
  used_quota: number;
  status: string;
  order_id?: number;
}

export interface SubscriptionRecommendationRecord {
  id: number;
  subscription_id: number;
  viewer_display_no?: string;
  viewer_nickname?: string;
  target_display_no?: string;
  target_nickname?: string;
  recommend_index: number;
  unlock_at?: string;
  status: string;
  viewed_at?: string;
  match_score?: number;
  match_reason?: string;
  match_reason_rule?: string;
  match_reason_ai?: string;
  reason_generation_status?: string;
  reason_model_name?: string;
  reason_generated_at?: string;
  reason_last_error?: string;
  last_error?: string;
}
