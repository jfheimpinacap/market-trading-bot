import { formatDateTime, formatNumber, titleize } from '../markets/utils';

export function formatPaperCurrency(
  value: number | string | null | undefined,
  currency = 'USD',
  options?: Intl.NumberFormatOptions,
) {
  if (value === null || value === undefined || value === '') {
    return '—';
  }

  const numericValue = typeof value === 'number' ? value : Number(value);
  if (Number.isNaN(numericValue)) {
    return '—';
  }

  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    maximumFractionDigits: 2,
    ...options,
  }).format(numericValue);
}

export function getPnlTone(value: number | string | null | undefined) {
  if (value === null || value === undefined || value === '') {
    return 'neutral';
  }

  const numericValue = typeof value === 'number' ? value : Number(value);
  if (Number.isNaN(numericValue) || numericValue === 0) {
    return 'neutral';
  }

  return numericValue > 0 ? 'positive' : 'negative';
}

export function formatSideLabel(value: string) {
  return titleize(value);
}

export function formatTechnicalTimestamp(value: string | null | undefined) {
  return formatDateTime(value);
}

export function formatQuantity(value: number | string | null | undefined) {
  return formatNumber(value, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 4,
  });
}
