export interface RecommendationItem {
  item_id: string;
  title: string;
  category: string;
  score: number;
  rank: number;
  explanation: string;
  model_version: string;
  attributes: {
    year?: number;
    rating?: number;
    description?: string;
    genres?: string[];
  };
}

export interface RecommendationResponse {
  user_id: string;
  recommendations: RecommendationItem[];
  model_used: string;
  is_cold_start: boolean;
  served_at: string;
}

export interface EventResponse {
  id: number;
  user_external_id: string;
  item_external_id: string;
  event_type: string;
  weight: number;
  timestamp: string;
}

export interface ModelMetrics {
  model_name: string;
  precision_at_5: number;
  precision_at_10: number;
  recall_at_5: number;
  recall_at_10: number;
  ndcg_at_5: number;
  ndcg_at_10: number;
  mrr: number;
  coverage: number;
  diversity: number;
  evaluated_users: number;
}

export interface EvaluationResponse {
  models: ModelMetrics[];
  train_size: number;
  test_size: number;
  total_items: number;
  evaluated_at: string;
}

export interface VariantResult {
  name: string;
  model: string;
  users_assigned: number;
  avg_precision_at_10: number;
  avg_ndcg_at_10: number;
  expected_lift_percent: number;
}

export interface ExperimentResult {
  experiment_id: number;
  name: string;
  status: string;
  allocation: number;
  variants: VariantResult[];
  winner: string | null;
  confidence: number;
  created_at: string;
}

export interface User {
  id: number;
  external_id: string;
  segment: string;
}

export interface ModelStatus {
  popularity: boolean;
  content_based: boolean;
  collaborative_filtering: boolean;
  ranker: boolean;
}

export interface HealthResponse {
  status: string;
  database: string;
  models: ModelStatus;
}

export interface ApiSuccessResponse<T> {
  success: true;
  data: T;
  request_id?: string;
}

export interface ApiErrorResponse {
  success: false;
  error: { code: string; message: string };
  request_id?: string;
}

export type ApiResponse<T> = ApiSuccessResponse<T> | ApiErrorResponse;

export interface PaginatedResponse<T> {
  success: true;
  data: T[];
  meta: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
  };
}
