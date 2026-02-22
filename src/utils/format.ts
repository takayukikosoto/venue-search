export function formatNumber(n: number): string {
  return n.toLocaleString('ja-JP')
}

export function formatArea(sqm: number): string {
  return `${formatNumber(sqm)}㎡`
}

export function formatCeiling(m: number): string {
  return `${m}m`
}

export function formatCapacity(n: number): string {
  return `${formatNumber(n)}名`
}

export const capacityTypeLabel: Record<string, string> = {
  theater: 'シアター',
  school: 'スクール',
  banquet: '着席',
  standing: '立食',
  max: '最大',
}
