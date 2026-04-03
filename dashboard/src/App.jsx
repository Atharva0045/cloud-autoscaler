import Dashboard from './pages/Dashboard.jsx'
import ErrorBoundary from './components/ErrorBoundary.jsx'

function App() {
  return (
    <ErrorBoundary>
      <Dashboard />
    </ErrorBoundary>
  )
}

export default App
