import "server-only";
import { api, type ApiResult } from "./api";

export type ChatbotConfig = {
  assistant_name: string;
  welcome_message: string;
  no_answer_message: string;
  handoff_message: string;
  handoff_keywords: string;
  schedule: string;
  contact_info: string;
  primary_color: string;
  is_active: boolean;
  catalog_api_url: string;
  catalog_page_url: string;
  updated_at?: string;
};

export type Business = {
  id: number;
  public_id: string;
  slug: string;
  name: string;
  description: string;
  logo_url: string;
  is_active: boolean;
  created_at: string;
  chatbot?: ChatbotConfig;
};

export type PlatformBusiness = Business & {
  admins: { id: number; name: string; email: string }[];
  counts: { faqs: number | null; conversations: number | null };
};

export type Domain = { id: number; origin: string; created_at: string };

export type Member = {
  id: number;
  user: number;
  name: string;
  email: string;
  role: "admin" | "asesor";
  created_at: string;
};

export type Metrics = {
  conversations_total: number;
  conversations_by_status: Record<string, number>;
  conversations_last_7_days: number;
  widget_conversations: number;
  messages_total: number;
  messages_last_7_days: number;
  faqs_active: number;
  faqs_total: number;
  team?: Record<string, number>;
  domains?: number;
  businesses_total?: number;
  businesses_active?: number;
  visitor_sessions_24h?: number;
};

type Page<T> = { count: number; next: string | null; previous: string | null; results: T[] };

export const getBusiness = (token: string): Promise<ApiResult<Business>> => api<Business>("/api/business/", { token });
export const listDomains = (token: string): Promise<ApiResult<Domain[]>> =>
  api<Domain[]>("/api/business/domains/", { token });
export const listMembers = (token: string): Promise<ApiResult<Member[]>> =>
  api<Member[]>("/api/business/members/", { token });
export const getMetrics = (token: string): Promise<ApiResult<Metrics>> =>
  api<Metrics>("/api/business/metrics/", { token });
export const listPlatformBusinesses = (token: string, page: number): Promise<ApiResult<Page<PlatformBusiness>>> =>
  api<Page<PlatformBusiness>>(`/api/platform/businesses/?page=${page}`, { token });
export const getPlatformMetrics = (token: string): Promise<ApiResult<Metrics>> =>
  api<Metrics>("/api/platform/metrics/", { token });
