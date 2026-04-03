import PanelCard from '../components/PanelCard.jsx'
import TopBar from '../components/TopBar.jsx'
import MetricLineChart from '../components/MetricLineChart.jsx'
import PredictionDecisionPanel from '../components/PredictionDecisionPanel.jsx'
import InstanceInfoPanel from '../components/InstanceInfoPanel.jsx'
import ScalingHistoryLog from '../components/ScalingHistoryLog.jsx'
import useAutoscalerDashboard from '../hooks/useAutoscalerDashboard.js'

const METRIC_COLORS = {
  cpu: { border: 'rgba(59,130,246,1)', fill: 'rgba(59,130,246,0.18)' }, // blue
  ram: { border: 'rgba(34,197,94,1)', fill: 'rgba(34,197,94,0.18)' }, // green
  disk: { border: 'rgba(168,85,247,1)', fill: 'rgba(168,85,247,0.18)' }, // purple
}

export default function Dashboard() {
  const {
    live,
    setLive,
    isLoading,
    backendError,
    online,
    timeseries,
    predictedCpu,
    confidence,
    decision,
    reason,
    actionTaken,
    currentInstance,
    history,
  } = useAutoscalerDashboard()

  return (
    <div className="min-h-screen p-4 bg-slate-950">
      <div className="max-w-[1400px] mx-auto">
        <TopBar
          online={online}
          live={live}
          onToggleLive={() => setLive((v) => !v)}
        />

        <div className="mt-3 grid grid-cols-2 gap-3">
          <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-md p-3 text-xs text-slate-300">
            <div className="text-slate-400">Latest Metrics</div>
            <div className="mt-1 text-slate-100">
              CPU:{' '}
              {Number.isFinite(timeseries.cpu?.[timeseries.cpu.length - 1])
                ? timeseries.cpu[timeseries.cpu.length - 1].toFixed(1)
                : '--'}
              % · RAM:{' '}
              {Number.isFinite(timeseries.ram?.[timeseries.ram.length - 1])
                ? timeseries.ram[timeseries.ram.length - 1].toFixed(1)
                : '--'}
              % · Disk I/O:{' '}
              {Number.isFinite(timeseries.disk?.[timeseries.disk.length - 1])
                ? timeseries.disk[timeseries.disk.length - 1].toFixed(1)
                : '--'}{' '}
              MB/s
            </div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-md p-3 text-xs text-slate-300">
            <div className="text-slate-400">Latest Prediction</div>
            <div className="mt-1 text-slate-100">
              {predictedCpu == null ? '--' : `${Number(predictedCpu).toFixed(1)}%`} ·{' '}
              Confidence:{' '}
              {confidence == null
                ? '--'
                : `${(Number(confidence) * 100).toFixed(1)}%`} ·{' '}
              Decision: <span className="text-slate-200">{decision?.toUpperCase()}</span>
            </div>
          </div>
        </div>

        {isLoading ? (
          <div className="mt-3 text-xs text-slate-300 animate-pulse">
            Initializing dashboard...
          </div>
        ) : null}

        {backendError ? (
          <div className="mt-3 text-xs text-red-200 bg-red-500/10 border border-red-500/30 px-3 py-2 rounded-2xl">
            {backendError}
          </div>
        ) : null}

        <div className="mt-4 grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-4 items-start">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <PanelCard>
              <MetricLineChart
                title="CPU %"
                labels={timeseries.labels}
                series={timeseries.cpu}
                color={METRIC_COLORS.cpu}
                suffix="%"
                yMax={100}
              />
            </PanelCard>

            <PanelCard>
              <MetricLineChart
                title="RAM %"
                labels={timeseries.labels}
                series={timeseries.ram}
                color={METRIC_COLORS.ram}
                suffix="%"
                yMax={100}
              />
            </PanelCard>

            <PanelCard>
              <MetricLineChart
                title="Disk I/O (MB/s)"
                labels={timeseries.labels}
                series={timeseries.disk}
                color={METRIC_COLORS.disk}
                suffix=" MB/s"
                autoScaleY
              />
            </PanelCard>

            <PanelCard>
              <PredictionDecisionPanel
                predictedCpu={predictedCpu}
                confidence={confidence}
                decision={decision}
                reason={reason}
                actionTaken={actionTaken}
              />
            </PanelCard>
          </div>

          <div className="flex flex-col gap-4">
            <PanelCard>
              <ScalingHistoryLog items={history} />
            </PanelCard>

            <PanelCard>
              <InstanceInfoPanel instanceType={currentInstance} />
            </PanelCard>
          </div>
        </div>
      </div>
    </div>
  )
}

