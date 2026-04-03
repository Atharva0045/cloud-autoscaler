export default function PanelCard({ children, className = '' }) {
  return (
    <div
      className={[
        'rounded-2xl border border-white/10 bg-white/5 backdrop-blur-md',
        'shadow-[0_10px_30px_rgba(0,0,0,0.25)]',
        className,
      ].join(' ')}
    >
      {children}
    </div>
  )
}

