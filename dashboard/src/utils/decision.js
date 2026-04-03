export function normalizeDecision(decision) {
  const v = String(decision ?? '').toLowerCase()
  if (v === 'scale_up' || v === 'scale up') return 'scale_up'
  if (v === 'scale_down' || v === 'scale down') return 'scale_down'
  return 'noop'
}

export function decisionStyle(decision) {
  const d = normalizeDecision(decision)
  if (d === 'scale_up') {
    return {
      label: 'SCALE UP',
      colorClass: 'text-yellow-300',
      badgeClass: 'bg-yellow-500/15 border-yellow-500/30',
    }
  }
  if (d === 'scale_down') {
    return {
      label: 'SCALE DOWN',
      colorClass: 'text-red-400',
      badgeClass: 'bg-red-500/15 border-red-500/30',
    }
  }
  return {
    label: 'NOOP',
    colorClass: 'text-emerald-300',
    badgeClass: 'bg-emerald-500/15 border-emerald-500/30',
  }
}

