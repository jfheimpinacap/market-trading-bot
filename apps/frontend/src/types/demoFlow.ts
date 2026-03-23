export type WorkflowStatusTone = 'ready' | 'warning' | 'neutral' | 'muted';

export type WorkflowStatusItem = {
  label: string;
  value: string;
  helperText: string;
  tone?: WorkflowStatusTone;
  href?: string;
  linkLabel?: string;
};

export type ContextLinkTone = 'primary' | 'secondary' | 'neutral';

export type ContextLinkItem = {
  title: string;
  description: string;
  href: string;
  actionLabel: string;
  tone?: ContextLinkTone;
};
