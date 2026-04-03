import { decisionStyle } from '../utils/decision.js'

function ConfidenceGauge({ value }) {
  const v = Math.max(0, Math.min(100, Number(value) || 0))
  return (
    <div className="mt-3">
      <div className="flex items-center justify-between text-xs text-slate-300">
        <span>Confidence</span>
        <span className="text-slate-200 font-medium">{v.toFixed(1)}%</span>
      </div>
      <div className="mt-2 h-2 rounded-full bg-white/10 overflow-hidden border border-white/10">
        <div
          className="h-full rounded-full bg-gradient-to-r from-cyan-400/80 via-emerald-400/80 to-emerald-300/80 transition-all duration-500"
          style={{ width: `${v}%` }}
        />
      </div>
    </div>
  )
}

export default function PredictionDecisionPanel({
  predictedCpu,
  confidence,
  decision,
  reason,
  actionTaken,
}) {
  const d = decisionStyle(decision)
  const predicted = Number(predictedCpu)
  const confPct = (Number(confidence) || 0) * 100

  return (
    <div className="p-4">
      <div className="text-sm text-slate-300 mb-1">
        Prediction + Decision
      </div>

      <div className="grid grid-cols-2 gap-3 mt-3">
        <div className="rounded-xl border border-white/10 bg-white/5 p-3">
          <div className="text-xs text-slate-400">Predicted CPU</div>
          <div className="text-3xl font-semibold text-slate-100">
            {Number.isFinite(predicted) ? predicted.toFixed(1) : '--'}%
          </div>
        </div>
        <div className="rounded-xl border border-white/10 bg-white/5 p-3">
          <div className="text-xs text-slate-400">Decision</div>
          <div className="mt-2">
            <div
              className={[
                'inline-flex items-center gap-2 px-3 py-2 rounded-xl border',
                d.badgeClass,
              ].join(' ')}
            >
              <span className={d.colorClass + ' font-semibold'}>{d.label}</span>
            </div>
          </div>
          {actionTaken ? (
            <div className="mt-2 text-xs text-slate-300">
              Action: <span className="text-slate-200">{actionTaken}</span>
            </div>
          ) : null}
        </div>
      </div>

      <ConfidenceGauge value={confPct} />

      <div className="mt-4">
        <div className="text-xs text-slate-400">Reason</div>
        <div className="text-sm text-slate-200 mt-1 leading-relaxed min-h-[3.25rem]">
          {reason || 'Waiting for backend...'}
        </div>
      </div>
    </div>
  )
}

