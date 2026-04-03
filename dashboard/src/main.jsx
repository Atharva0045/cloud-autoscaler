import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

// Tailwind `dark:` variants (if used) rely on a `.dark` class on the root element.
document.documentElement.classList.add('dark')

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
