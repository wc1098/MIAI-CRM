import request from "@/utils/request";

const API_PATH = "/crm/product";

const ProductAPI = {
  listProduct(query?: ProductPageQuery) {
    return request<ApiResponse<PageResult<ProductPackageTable[]>>>({
      url: `${API_PATH}/list`,
      method: "get",
      params: query,
    });
  },

  detailProduct(id: number) {
    return request<ApiResponse<ProductPackageTable>>({
      url: `${API_PATH}/detail/${id}`,
      method: "get",
    });
  },

  createProduct(body: ProductPackageForm) {
    return request<ApiResponse>({
      url: `${API_PATH}/create`,
      method: "post",
      data: body,
    });
  },

  updateProduct(id: number, body: ProductPackageForm) {
    return request<ApiResponse>({
      url: `${API_PATH}/update/${id}`,
      method: "put",
      data: body,
    });
  },

  changeProductStatus(id: number, status: string) {
    return request<ApiResponse>({
      url: `${API_PATH}/change-status/${id}`,
      method: "put",
      data: { status },
    });
  },

  deleteProduct(id: number) {
    return request<ApiResponse>({
      url: `${API_PATH}/delete/${id}`,
      method: "delete",
    });
  },
};

export default ProductAPI;

export interface ProductPageQuery extends PageQuery {
  keyword?: string;
  status?: string;
}

export interface ProductPackageTable extends BaseType {
  brand_id?: number;
  package_name?: string;
  standard_price?: string | number;
  service_days?: number;
  recommendation_quota?: number;
  meeting_quota?: number;
  course_quota?: number;
  supports_online_meeting?: boolean;
  description?: string;
  internal_remark?: string;
  sort?: number;
  created_by?: CommonType;
  updated_by?: CommonType;
}

export interface ProductPackageForm extends BaseFormType {
  package_name?: string;
  standard_price?: number;
  service_days?: number;
  recommendation_quota?: number;
  meeting_quota?: number;
  course_quota?: number;
  supports_online_meeting?: boolean;
  description?: string;
  internal_remark?: string;
  sort?: number;
}
