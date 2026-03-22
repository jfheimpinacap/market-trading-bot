export function formatNumber(value: number | string | null | undefined, options?: Intl.NumberFormatOptions) {
  if (value === null || value === undefined || value === '') {
    return '—';
  }

  const numericValue = typeof value === 'number' ? value : Number(value);
  if (Number.isNaN(numericValue)) {
    return '—';
  }

  return new Intl.NumberFormat('en-US', options).format(numericValue);
}

export function formatPercent(value: number | string | null | undefined) {
  if (value === null || value === undefined || value === '') {
    return '—';
  }

  const numericValue = typeof value === 'number' ? value : Number(value);
  if (Number.isNaN(numericValue)) {
    return '—';
  }

  return `${(numericValue * 100).toFixed(1)}%`;
}

export function formatDateTime(value: string | null | undefined) {
  if (!value) {
    return '—';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return '—';
  }

  return new Intl.DateTimeFormat('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

export function formatCompactCurrency(value: number | string | null | undefined) {
  if (value === null || value === undefined || value === '') {
    return '—';
  }

  const numericValue = typeof value === 'number' ? value : Number(value);
  if (Number.isNaN(numericValue)) {
    return '—';
  }

  return new Intl.NumberFormat('en-US', {
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(numericValue);
}

export function titleize(value: string) {
  return value
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((segment) => segment[0].toUpperCase() + segment.slice(1))
    .join(' ');
}
