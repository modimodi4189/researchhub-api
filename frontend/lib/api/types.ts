export type IsoDateString = string;

export type User = {
  id: number;
  email: string;
  created_at: IsoDateString;
};

export type Token = {
  access_token: string;
  refresh_token: string;
  token_type: "bearer" | string;
};

export type Paper = {
  id: number;
  title: string;
  abstract: string | null;
  content: string | null;
  summary: string | null;
  summary_status: "idle" | "queued" | "processing" | "complete" | "failed" | string;
  summary_error: string | null;
  is_public: boolean;
  created_at: IsoDateString;
  updated_at: IsoDateString | null;
  owner_id: number;
  category_id: number | null;
};

export type PaperListItem = Omit<Paper, "content">;

export type Collection = {
  id: number;
  name: string;
  created_at: IsoDateString;
  updated_at: IsoDateString | null;
  owner_id: number;
};

export type CollectionWithPapers = Collection & {
  papers: PaperListItem[];
};

export type PaginationResponse<T> = {
  items: T[];
  total: number;
  page: number;
  limit: number;
  pages: number;
};

export type HealthResponse = {
  status: string;
};
