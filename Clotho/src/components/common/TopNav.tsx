import { Button } from '@/components/ui/button'
import { ThemeToggle } from './ThemeToggle'
import { MessageSquare, BarChart3 } from 'lucide-react'

interface TopNavProps {
  currentPage?: 'dashboard' | 'chatbot'
  onNavigate?: (page: 'dashboard' | 'chatbot') => void
}

export function TopNav({ currentPage = 'dashboard', onNavigate }: TopNavProps) {
  return (
    <nav className="flex items-center justify-between py-4 mb-6">
      <div className="flex items-center gap-3">
        <div className="flex items-center justify-center w-8 h-8 bg-gradient-to-br from-cyan-600 to-teal-600 rounded-lg">
          <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>
        <div className="font-bold text-xl bg-gradient-to-r from-slate-900 to-slate-600 dark:from-slate-100 dark:to-slate-300 bg-clip-text text-transparent">
          Clotho
        </div>
      </div>
      
      <div className="flex items-center gap-1">
        <Button
          onClick={() => onNavigate?.('dashboard')}
          variant="ghost"
          size="sm"
          className={`!text-slate-600 hover:!text-slate-900 dark:!text-slate-400 dark:hover:!text-slate-100 hover:!bg-slate-100 dark:hover:!bg-slate-800 rounded-lg ${
            currentPage === 'dashboard' ? '!bg-slate-100 dark:!bg-slate-800 !text-slate-900 dark:!text-slate-100' : ''
          }`}
        >
          <div className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4" />
            <span className="hidden sm:inline">Dashboard</span>
          </div>
        </Button>
        <Button
          onClick={() => onNavigate?.('chatbot')}
          variant="ghost"
          size="sm"
          className={`!text-slate-600 hover:!text-slate-900 dark:!text-slate-400 dark:hover:!text-slate-100 hover:!bg-slate-100 dark:hover:!bg-slate-800 rounded-lg ${
            currentPage === 'chatbot' ? '!bg-slate-100 dark:!bg-slate-800 !text-slate-900 dark:!text-slate-100' : ''
          }`}
        >
          <div className="flex items-center gap-2">
            <MessageSquare className="w-4 h-4" />
            <span className="hidden sm:inline">AI Chat</span>
          </div>
        </Button>
        
        {/* Theme Toggle */}
        <div className="ml-2 pl-2 border-l border-slate-200 dark:border-slate-700">
          <ThemeToggle />
        </div>
      </div>
    </nav>
  )
}


