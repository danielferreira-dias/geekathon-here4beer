import { useState } from 'react'
import Dashboard from '@/pages/Dashboard'
import Chatbot from '@/pages/Chatbot'
import { ThemeProvider } from '@/components/common/ThemeProvider'
import { Toaster } from 'sonner'

type Page = 'dashboard' | 'chatbot'

export default function App() {
  const [currentPage, setCurrentPage] = useState<Page>('dashboard')

  const renderPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return <Dashboard onNavigate={setCurrentPage} />
      case 'chatbot':
        return <Chatbot onNavigate={setCurrentPage} />
      default:
        return <Dashboard onNavigate={setCurrentPage} />
    }
  }

  return (
    <ThemeProvider defaultTheme="system" storageKey="clotho-ui-theme">
      {renderPage()}
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
