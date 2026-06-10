import type {
  ApiResponse,
  EvaluationResponse,
  EventResponse,
  ExperimentResult,
  HealthResponse,
  ModelStatus,
  PaginatedResponse,
  RecommendationResponse,
  User,
} from "./types";

const BASE_URL =
  typeof window !== "undefined"
    ? process.env.NEXT_PUBLIC_API_URL || "/api/backend"
    : process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
  const body = await res.json();
  if (!res.ok) {
    const msg = body?.error?.message || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return body as T;
}

// Health
export async function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

// Users
export async function fetchUsers(): Promise<
  ApiResponse<{ users: User[]; total: number }>
> {
  return request<ApiResponse<{ users: User[]; total: number }>>(
    "/recommendations"
  );
}

// Recommendations
export async function fetchRecommendations(
  userId: string,
  k = 10,
  model = "auto"
): Promise<ApiResponse<RecommendationResponse>> {
  return request<ApiResponse<RecommendationResponse>>(
    `/recommendations/${encodeURIComponent(userId)}?k=${k}&model=${model}`
  );
}

// Events
export async function fetchEvents(
  page = 1,
  pageSize = 20
): Promise<PaginatedResponse<EventResponse>> {
  return request<PaginatedResponse<EventResponse>>(
    `/events?page=${page}&page_size=${pageSize}`
  );
}

export async function recordEvent(payload: {
  user_external_id: string;
  item_external_id: string;
  event_type: string;
}): Promise<ApiResponse<EventResponse>> {
  return request<ApiResponse<EventResponse>>("/events", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// Models
export async function fetchModelStatus(): Promise<ApiResponse<ModelStatus>> {
  return request<ApiResponse<ModelStatus>>("/models/status");
}

export async function triggerTraining(): Promise<
  ApiResponse<{ status: string; models: Record<string, string> }>
> {
  return request<ApiResponse<{ status: string; models: Record<string, string> }>>(
    "/models/train",
    { method: "POST" }
  );
}

// Evaluations
export async function fetchEvaluations(): Promise<
  ApiResponse<EvaluationResponse>
> {
  return request<ApiResponse<EvaluationResponse>>("/evaluations/latest");
}

// Experiments
export async function fetchExperiments(): Promise<
  ApiResponse<{ experiments: ExperimentResult[]; total: number }>
> {
  return request<ApiResponse<{ experiments: ExperimentResult[]; total: number }>>(
    "/experiments"
  );
}

export async function createExperiment(payload: {
  name: string;
  description?: string;
  control_model: string;
  treatment_model: string;
  allocation: number;
}): Promise<ApiResponse<ExperimentResult>> {
  return request<ApiResponse<ExperimentResult>>("/experiments", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
