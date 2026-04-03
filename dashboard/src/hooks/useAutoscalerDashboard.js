import { useEffect, useState } from 'react'
import { getAutoscaleStatus, getMetrics } from '../services/api.js'
import { makeInitialLabels, clamp } from '../utils/metricsSimulator.js'

const POINTS = 60
const METRICS_POLL_MS = 5000
const AUTOSCALE_STATUS_POLL_MS = 30000

function fmtTime(ts) {
  return new Date(ts).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function initialSeries() {
  const labels = makeInitialLabels(POINTS, METRICS_POLL_MS)
  const cpu = Array.from({ length: POINTS }, (_, i) => {
    // Start with a plausible mid-range curve.
    const t = i / (POINTS - 1)
    return clamp(45 + 6 * Math.sin(t * Math.PI * 1.2) + (Math.random() - 0.5) * 4, 0, 100)
  })
  const ram = Array.from({ length: POINTS }, (_, i) => clamp(cpu[i] * 1.25 + (Math.random() - 0.5) * 6, 0, 100))
  const disk = Array.from({ length: POINTS }, (_, i) => clamp(18 + cpu[i] * 0.55 + (Math.random() - 0.5) * 5, 0, 100))

  return { labels, cpu, ram, disk }
}

export default function useAutoscalerDashboard() {
  const [live, setLive] = useState(true)
  const [isLoading, setIsLoading] = useState(true)
  const [metricsError, setMetricsError] = useState('')
  const [online, setOnline] = useState(false)

  const [timeseries, setTimeseries] = useState(() => initialSeries())

  const [predictedCpu, setPredictedCpu] = useState(null)
  const [confidence, setConfidence] = useState(null)
  const [decision, setDecision] = useState('noop')
  const [reason, setReason] = useState('')
  const [actionTaken, setActionTaken] = useState('')
  const [currentInstance, setCurrentInstance] = useState('unknown')
  const [history, setHistory] = useState([])

  // Metrics polling: drive charts from Prometheus via /metrics
  useEffect(() => {
    if (!live) return

    let cancelled = false

    async function pollMetrics() {
      try {
        const res = await getMetrics()
        if (cancelled || !res) return

        const cpu = Number(res.cpu)
        const ram = Number(res.ram)
        const diskBytesPerSec = Number(res.disk)

        if (
          !Number.isFinite(cpu) ||
          !Number.isFinite(ram) ||
          !Number.isFinite(diskBytesPerSec)
        ) {
          return
        }

        setMetricsError('')
        setOnline(true)
        setIsLoading(false)

        setTimeseries((prev) => ({
          labels: [...prev.labels.slice(1), fmtTime(Date.now())],
          cpu: [...prev.cpu.slice(1), clamp(cpu, 0, 100)],
          ram: [...prev.ram.slice(1), clamp(ram, 0, 100)],
          // disk from backend is bytes/sec; convert to MB/s for visualization
          disk: [
            ...prev.disk.slice(1),
            Math.max(0, diskBytesPerSec / (1024 * 1024)),
          ],
        }))
      } catch (e) {
        if (cancelled) return

        const msg = e?.response?.data?.detail
          ? String(e.response.data.detail)
          : 'Failed to fetch /metrics from Prometheus.'
        setMetricsError(msg)
        setOnline(false)
        setIsLoading(false)
      }
    }

    const timer = setInterval(pollMetrics, METRICS_POLL_MS)
    pollMetrics()

    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [live])

  // Read-only autoscale status: reflect daemon /autoscale decisions without triggering them.
  useEffect(() => {
    if (!live) return

    let cancelled = false
    let inFlight = false

    async function pollStatus() {
      if (inFlight) return
      inFlight = true
      try {
        const res = await getAutoscaleStatus()
        if (cancelled || !res) return

        const predicted = Number(res.predicted_cpu)
        const conf = Number(res.confidence)
        const decisionRaw = String(res.decision || 'noop')
        const nextReason = res.reason || ''
        const nextActionTaken = res.action_taken || ''
        const nextInstance = res.current_instance_type || 'unknown'
        const ts = res.timestamp || null

        setPredictedCpu(Number.isFinite(predicted) ? predicted : null)
        setConfidence(Number.isFinite(conf) ? conf : null)
        setDecision(decisionRaw)
        setReason(nextReason)
        setActionTaken(nextActionTaken)
        setCurrentInstance(nextInstance)

        // Update history log (display-only).
        const confPct = Number.isFinite(conf) ? conf * 100 : null
        setHistory((prev) => {
          const id = `${Date.now()}_${Math.random().toString(16).slice(2)}`
          const entry = {
            id,
            timestamp: ts || fmtTime(Date.now()),
            decision: decisionRaw.toUpperCase(),
            predictedCpu: Number.isFinite(predicted) ? predicted : null,
            confidencePct: confPct,
            reason: nextReason,
            actionTaken: nextActionTaken,
          }
          const next = [entry, ...prev]
          return next.slice(0, 10)
        })
      } catch {
        if (cancelled) return
        // If status cannot be fetched, keep existing display values.
      } finally {
        inFlight = false
      }
    }

    const timer = setInterval(pollStatus, AUTOSCALE_STATUS_POLL_MS)
    pollStatus()

    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [live])

  return {
    live,
    setLive,
    isLoading,
    backendError: metricsError,
    online,
    timeseries,
    predictedCpu,
    confidence,
    decision,
    reason,
    actionTaken,
    currentInstance,
    history,
  }
}

