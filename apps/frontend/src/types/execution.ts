export type PaperOrder = {
  id: number;
  market_title?: string;
  market: number;
  side: string;
  requested_quantity: string;
  remaining_quantity: string;
  status: string;
  requested_price: string | null;
  effective_price: string | null;
  created_from: string;
  created_at: string;
};

export type PaperFill = {
  id: number;
  paper_order: number;
  fill_quantity: string;
  fill_price: string;
  fill_type: string;
  created_at: string;
};

export type ExecutionSummary = {
  total_orders: number;
  total_fills: number;
  status_counts: Array<{ status: string; count: number }>;
  attempt_status_counts: Array<{ attempt_status: string; count: number }>;
};
