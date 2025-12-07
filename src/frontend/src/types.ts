export interface Entry {
  id: string;
  theme: string;
  source_type: 'image' | 'link';
  source_url: string;
  entry_date: string;
  process_stage: 'Uploaded' | 'Preprocessing' | 'Summarizing' | 'Complete' | 'Error';
  summary_caption: string;
  updated_at: string;
}

export interface ApiResponse {
  data: Entry[];
  total: number;
}

export interface TablePagination {
  current: number;
  pageSize: number;
  total: number;
}