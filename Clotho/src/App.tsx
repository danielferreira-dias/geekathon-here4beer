import Dashboard from '@/pages/Dashboard'
import { ThemeProvider } from '@/components/common/ThemeProvider'
import { Toaster } from 'sonner'

export default function App() {
  return (
    <ThemeProvider defaultTheme="system" storageKey="clotho-ui-theme">
      <Dashboard />
      <Toaster 
        position="top-right"
        expand={true}
        richColors={false}
        closeButton={true}
        theme="system"
      />
    </ThemeProvider>
  )
}
