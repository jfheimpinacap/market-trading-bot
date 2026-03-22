export type DashboardStatCard = {
  label: string;
  value: string;
  helperText: string;
};

export type DashboardQuickLink = {
  title: string;
  description: string;
  path: string;
  availability: 'live' | 'placeholder';
};

export type DashboardModuleStatus = {
  name: string;
  summary: string;
  status: 'ready' | 'pending';
};

export type RecentMarketItem = {
  id: number;
  title: string;
  providerName: string;
  eventTitle: string | null;
  status: string;
  probability: string | null;
  updatedAt: string;
};
