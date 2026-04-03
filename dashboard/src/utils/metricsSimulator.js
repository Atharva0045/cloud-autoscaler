export function clamp(n, min, max) {
  return Math.min(max, Math.max(min, n))
}

// Box–Muller transform for an approximately standard normal distribution.
function randn() {
  let u = 0
  let v = 0
  while (u === 0) u = Math.random()
  while (v === 0) v = Math.random()
  return Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v)
}

export function makeInitialLabels(pointCount, intervalMs) {
  const now = Date.now()
  const labels = []
  for (let i = pointCount - 1; i >= 0; i -= 1) {
    const t = now - i * intervalMs
    labels.push(
      new Date(t).toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      }),
    )
  }
  return labels
}

export function simulateNextMetrics({ predictedCpu, prevCpu, prevRam, prevDisk }) {
  const baseCpu = Number.isFinite(predictedCpu) ? predictedCpu : prevCpu ?? 50

  // Smooth-ish motion with bounded noise.
  const cpuNoise = randn() * 3.2
  const cpuTrend = prevCpu != null ? (baseCpu - prevCpu) * 0.18 : 0
  const cpu = clamp(baseCpu + cpuTrend + cpuNoise, 0, 100)

  const ramNoise = randn() * 2.5
  const ramFactor = 1.15 + Math.random() * 0.18
  const ram = clamp(cpu * ramFactor + ramNoise, 0, 100)

  const diskNoise = randn() * 1.8
  const disk = clamp(18 + cpu * 0.55 + diskNoise, 0, 100)

  // If your previous value is known, blend slightly to avoid jumps.
  const nextCpu = prevCpu == null ? cpu : clamp(prevCpu * 0.35 + cpu * 0.65, 0, 100)
  const nextRam = prevRam == null ? ram : clamp(prevRam * 0.35 + ram * 0.65, 0, 100)
  const nextDisk = prevDisk == null ? disk : clamp(prevDisk * 0.35 + disk * 0.65, 0, 100)

  return { cpu: nextCpu, ram: nextRam, disk: nextDisk }
}

