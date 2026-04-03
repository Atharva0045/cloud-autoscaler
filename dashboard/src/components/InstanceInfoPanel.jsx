const INSTANCE_MAP = {
  't2.small': { vcpus: 1, ram: '2GB', disk: '8GB (assumed)' },
  't2.medium': { vcpus: 2, ram: '4GB', disk: '16GB (assumed)' },
  't2.large': { vcpus: 2, ram: '8GB', disk: '32GB (assumed)' },
}

function InfoRow({ label, value }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-white/5 last:border-b-0">
      <div className="text-xs text-slate-400">{label}</div>
      <div className="text-sm font-medium text-slate-100 text-right">
        {value}
      </div>
    </div>
  )
}

export default function InstanceInfoPanel({ instanceType }) {
  const type = String(instanceType || 'unknown')
  const mapped = INSTANCE_MAP[type]

  return (
    <div className="p-4">
      <div className="text-sm text-slate-300 mb-2">EC2 Instance Info</div>

      <div className="rounded-xl border border-white/10 bg-white/5 p-3">
        <div className="text-xs text-slate-400">Instance Type</div>
        <div className="text-xl font-semibold text-slate-100 mt-1">
          {type}
        </div>
      </div>

      <div className="mt-3 rounded-xl border border-white/10 bg-white/5 overflow-hidden">
        <InfoRow label="vCPUs" value={mapped ? mapped.vcpus : 'Unknown'} />
        <InfoRow label="RAM" value={mapped ? mapped.ram : 'Unknown'} />
        <InfoRow label="Disk" value={mapped ? mapped.disk : 'Unknown'} />
      </div>
    </div>
  )
}

