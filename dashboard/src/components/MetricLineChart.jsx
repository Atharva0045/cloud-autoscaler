import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
} from 'chart.js'
import { Filler } from 'chart.js'
import { Line } from 'react-chartjs-2'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Filler,
)

export default function MetricLineChart({
  title,
  labels,
  series,
  color,
  suffix = '%',
  yMin = 0,
  yMax = 100,
  autoScaleY = false,
}) {
  const data = {
    labels,
    datasets: [
      {
        label: title,
        data: series,
        borderColor: color.border,
        backgroundColor: color.fill,
        fill: true,
        borderWidth: 2,
        tension: 0.4, // fallback for older Chart.js typings
        pointRadius: 0,
        pointHoverRadius: 3,
      },
    ],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (ctx) => `${ctx.parsed.y.toFixed(1)}${suffix}`,
        },
      },
    },
    interaction: { mode: 'index', intersect: false },
    elements: {
      line: {
        tension: 0.4,
      },
    },
    scales: {
      x: {
        display: false,
      },
      y: autoScaleY
        ? {
            ticks: {
              color: 'rgba(226,232,240,0.8)',
            },
            grid: {
              color: 'rgba(148,163,184,0.15)',
            },
          }
        : {
            suggestedMin: yMin,
            suggestedMax: Number.isFinite(yMax) ? yMax : undefined,
            ticks: {
              color: 'rgba(226,232,240,0.8)',
            },
            grid: {
              color: 'rgba(148,163,184,0.15)',
            },
          },
    },
  }

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="text-sm text-slate-300">{title}</div>
        <div className="text-xs text-slate-400">Last 5 minutes</div>
      </div>
      <div className="h-56">
        <Line data={data} options={options} />
      </div>
    </div>
  )
}

