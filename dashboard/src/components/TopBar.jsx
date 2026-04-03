export default function TopBar({ online, live, onToggleLive }) {
  return (
    <div className="flex items-center justify-between px-4 py-3 border border-white/10 rounded-2xl bg-white/5 backdrop-blur-md">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-white/5 border border-white/10 grid place-items-center">
          <div className="text-lg">⚡</div>
        </div>
        <div>
          <div className="text-lg font-semibold text-slate-100">
            AI Autoscaler Dashboard
          </div>
          <div className="text-xs text-slate-300">
            {online ? (
              <span className="text-emerald-300">🟢 System Online</span>
            ) : (
              <span className="text-red-400">🔴 System Offline</span>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onToggleLive}
          className={[
            'px-3 py-2 rounded-xl border transition',
            live
              ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-200 hover:bg-emerald-500/20'
              : 'bg-white/5 border-white/10 text-slate-200 hover:bg-white/10',
          ].join(' ')}
        >
          {live ? 'Live' : 'Paused'}
        </button>
      </div>
    </div>
  )
}

