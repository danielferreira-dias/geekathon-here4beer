import type { ReactNode } from 'react'

export function PageShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-dvh min-w-screen bg-gradient-to-br from-slate-50 via-cyan-50/30 to-blue-50/50 dark:from-slate-950 dark:via-slate-900/20 dark:to-slate-800/30 text-foreground">
      {/* Background pattern */}
      <div className="absolute inset-0 bg-grid-pattern opacity-[0.02] pointer-events-none"></div>
      
      <div className="relative max-w-7xl mx-auto px-4 md:px-6 py-4 md:py-6">
        {children}
      </div>
    </div>
  )
}


