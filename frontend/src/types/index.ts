export interface ChatResponse {
  success: boolean;
  question: string;
  database: string;
  sql: string;
  columns: string[];
  rows: (string | number | null)[][];
  row_count: number;
  error: string;
  detection_info: {
    method?: string;
    candidates?: Array<{
      name: string;
      similarity: number;
    }>;
    timing?: {
      search?: number;
      llm?: number;
    };
  };
  timing?: {
    detection: number;
    generation: number;
    execution: number;
    total: number;
  };
}

export interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  response?: ChatResponse;
}

export interface Database {
  name: string;
  tables: string[];
  table_count: number;
}
