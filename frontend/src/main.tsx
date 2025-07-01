import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App'
import { ThemeProvider } from 'styled-components'
import { ThemeProvider as ThemeContainer, defaultTheme } from '@beamcloud/design-system'
import { BrowserRouter } from 'react-router-dom'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <ThemeProvider theme={defaultTheme}>
        <ThemeContainer>
          <App />
        </ThemeContainer>
      </ThemeProvider>
    </BrowserRouter>
  </StrictMode>,
)
