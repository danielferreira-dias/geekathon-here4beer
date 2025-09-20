import { useAnalysis } from '@/hooks/useAnalysis'
import { PageShell } from '@/components/common/PageShell'
import { TopNav } from '@/components/common/TopNav'
import { UploadPanel } from '@/components/dashboard/UploadPanel'
import { SummaryCards } from '@/components/dashboard/SummaryCards'
import { ResultTabs } from '@/components/dashboard/ResultTabs'
import { JsonDownloadButton } from '@/components/common/JsonDownloadButton'

interface DashboardProps {
  onNavigate: (page: 'dashboard' | 'chatbot') => void
}

export default function Dashboard({ onNavigate }: DashboardProps) {
  const { result, loading, analyze } = useAnalysis()

  return (
    <PageShell>
      <TopNav currentPage="dashboard" onNavigate={onNavigate} />
      
      {/* Hero Section */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-50 via-blue-50 to-cyan-50 dark:from-slate-800/20 dark:via-slate-700/20 dark:to-slate-600/20 px-8 py-12 mb-8">
        <div className="absolute inset-0 bg-grid-pattern opacity-5"></div>
        <div className="relative">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-cyan-600 via-blue-600 to-teal-600 bg-clip-text text-transparent mb-2">
                Clotho Dashboard
              </h1>
              <p className="text-lg text-slate-600 dark:text-slate-300 max-w-2xl">
                Upload your CSV files, run intelligent analysis, and get actionable insights for your supply chain planning.
              </p>
            </div>
            {result && (
              <div className="flex-shrink-0">
                <JsonDownloadButton data={result} />
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Upload Section */}
        <div className="lg:col-span-1">
          <UploadPanel onSubmit={analyze} loading={loading} />
        </div>

        {/* Results Section */}
        <div className="lg:col-span-2">
          {result ? (
            <div id="results-panel" className="space-y-6">
              <SummaryCards data={result} />
              <ResultTabs data={result} />
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-96 rounded-2xl border-2 border-dashed border-slate-200 dark:border-slate-600 bg-slate-50/50 dark:bg-slate-800/20">
              <div className="text-center">
                <svg className="mx-auto h-12 w-12 text-slate-400 dark:text-slate-500 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">No Analysis Yet</h3>
                <p className="text-slate-500 dark:text-slate-400 max-w-sm">
                  Upload your CSV files and click "Analyze" to see detailed insights and recommendations.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </PageShell>
  )
}


