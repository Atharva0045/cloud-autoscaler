import { Component } from 'react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error) {
    console.error(error)
  }

  render() {
    if (!this.state.error) return this.props.children

    const message = String(this.state.error?.message || this.state.error)

    return (
      <div className="min-h-screen p-6 bg-slate-950 text-slate-100">
        <div className="max-w-3xl mx-auto rounded-2xl border border-red-500/30 bg-red-500/10 p-4">
          <div className="font-semibold text-red-200">Dashboard error</div>
          <div className="text-sm text-red-100/90 mt-2 break-words">
            {message}
          </div>
        </div>
      </div>
    )
  }
}

