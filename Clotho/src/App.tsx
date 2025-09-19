import Dashboard from '@/pages/Dashboard'
import { ThemeProvider } from '@/components/common/ThemeProvider'

export default function App() {
  return (
    <ThemeProvider defaultTheme="system" storageKey="clotho-ui-theme">
      <Dashboard />
    </ThemeProvider>
  )
}
