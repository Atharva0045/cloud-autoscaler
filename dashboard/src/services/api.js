import axios from 'axios'

// Use relative URLs by default so Vite dev-server proxy can avoid CORS.
// For production, set VITE_API_BASE_URL (e.g. "http://your-backend:8000").
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 8000,
})

// Metrics-only API used by the dashboard UI.
export async function getMetrics() {
  const res = await api.get('/metrics')
  return res.data
}

// Read-only view of the last autoscale decision.
export async function getAutoscaleStatus() {
  const res = await api.get('/autoscale_status')
  return res.data
}

