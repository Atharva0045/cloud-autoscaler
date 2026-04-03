export default function ScalingHistoryLog({ items }) {
  const safeItems = Array.isArray(items) ? items : []

  return (
    <div className="p-4">
      <div className="text-sm text-slate-300 mb-3">
        Scaling Decision Summary
      </div>

      <div className="rounded-xl border border-white/10 bg-white/5 p-3">
        {safeItems.length === 0 ? (
          <div className="text-xs text-slate-400">
            Waiting for backend calls...
          </div>
        ) : (
          <div className="text-xs text-slate-300 leading-relaxed">
            Latest: <span className="text-slate-100">{safeItems[0].decision}</span>
            <span className="text-slate-400"> · </span>
            CPU {safeItems[0].predictedCpu?.toFixed?.(1) ?? safeItems[0].predictedCpu}{' '}
            % · Confidence{' '}
            {safeItems[0].confidencePct?.toFixed?.(1) ?? safeItems[0].confidencePct}
            %
          </div>
        )}
      </div>

      <div className="mt-3 rounded-xl border border-white/10 bg-white/5 p-2 max-h-56 overflow-auto">
        {safeItems.length === 0 ? null : (
          <div className="space-y-2">
            {safeItems.map((it) => (
              <div
                key={it.id}
                className="px-2 py-2 rounded-lg border border-white/5 bg-white/5"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="text-[11px] text-slate-400">
                    {it.timestamp}
                  </div>
                  <div className="text-[11px] font-medium text-slate-200">
                    {it.decision}
                  </div>
                </div>
                <div className="text-[11px] text-slate-300 mt-1">
                  {it.reason || '—'}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

