import "server-only";
import { api, type ApiResult } from "./api";

export type Faq = {
  id: number;
  category: string;
  question: string;
  answer: string;
  keywords: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type FaqPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Faq[];
};

export function listFaqs(token: string, page: number): Promise<ApiResult<FaqPage>> {
  return api<FaqPage>(`/api/faqs/?page=${page}`, { token });
}

export function getFaq(token: string, id: number): Promise<ApiResult<Faq>> {
  return api<Faq>(`/api/faqs/${id}/`, { token });
}
