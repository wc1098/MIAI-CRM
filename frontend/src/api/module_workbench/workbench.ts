import request from "@/utils/request";

const API_PATH = "/workbench";

const WorkbenchAPI = {
  summary(params: WorkbenchSummaryQuery) {
    return request<ApiResponse<WorkbenchSummary>>({
      url: `${API_PATH}/summary`,
      method: "get",
      params,
    });
  },

  tasks(params: WorkbenchTasksQuery) {
    return request<ApiResponse<WorkbenchTaskGroup>>({
      url: `${API_PATH}/tasks`,
      method: "get",
      params,
    });
  },

  nodes(params: WorkbenchNodesQuery) {
    return request<ApiResponse<WorkbenchNodes>>({
      url: `${API_PATH}/nodes`,
      method: "get",
      params,
    });
  },
};

export default WorkbenchAPI;

export type WorkbenchRange = "today" | "week" | "month";
export type WorkbenchBucket = "today" | "overdue" | "upcoming";
export type WorkbenchScope = "mine" | "store";

export interface WorkbenchSummaryQuery {
  range: WorkbenchRange;
  store_id?: number;
}

export interface WorkbenchTasksQuery {
  bucket: WorkbenchBucket;
  days?: number;
  limit?: number;
}

export interface WorkbenchNodesQuery {
  scope: WorkbenchScope;
  store_id?: number;
}

export interface WorkbenchMetric {
  key: string;
  title: string;
  value: number | string;
  unit?: string;
  hint?: string;
  priority: "primary" | "success" | "warning" | "danger" | "info";
  route_path?: string;
  query: Record<string, unknown>;
}

export interface WorkbenchSummary {
  role_type: string;
  role_name: string;
  range: WorkbenchRange;
  scope: string;
  metrics: WorkbenchMetric[];
}

export interface WorkbenchTask {
  id: string;
  task_type: string;
  title: string;
  object_type: string;
  object_id: number;
  object_name?: string;
  status: string;
  due_at?: string;
  owner_user_id?: number;
  owner_user_name?: string;
  priority: "primary" | "success" | "warning" | "danger" | "info";
  action_text: string;
  route_path: string;
  query: Record<string, unknown>;
}

export interface WorkbenchTaskGroup {
  role_type: string;
  bucket: WorkbenchBucket;
  total: number;
  items: WorkbenchTask[];
}

export interface WorkbenchNode {
  key: string;
  title: string;
  count: number;
  priority: "primary" | "success" | "warning" | "danger" | "info";
  route_path: string;
  query: Record<string, unknown>;
}

export interface WorkbenchNodeGroup {
  key: string;
  title: string;
  nodes: WorkbenchNode[];
}

export interface WorkbenchNodes {
  role_type: string;
  scope: WorkbenchScope;
  groups: WorkbenchNodeGroup[];
}
