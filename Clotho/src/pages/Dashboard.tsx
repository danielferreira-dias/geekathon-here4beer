import { useState } from 'react'
import { useAnalysis, type AnalysisFiles } from '@/hooks/useAnalysis'
import { PageShell } from '@/components/common/PageShell'
import { TopNav } from '@/components/common/TopNav'
import { UploadPanel } from '@/components/dashboard/UploadPanel'
import { SummaryCards } from '@/components/dashboard/SummaryCards'
import { ResultTabs } from '@/components/dashboard/ResultTabs'
import { SkeletonSummaryCards, SkeletonResultTabs } from '@/components/dashboard/SkeletonLoaders'
import { JsonDownloadButton } from '@/components/common/JsonDownloadButton'
import { Button } from '@/components/ui/button'
import { UploadCloud } from 'lucide-react'

interface DashboardProps {
  onNavigate: (page: 'dashboard' | 'chatbot') => void
}

export default function Dashboard({ onNavigate }: DashboardProps) {
  const { result, loading, analyze } = useAnalysis()
  const [showUpload, setShowUpload] = useState(false)

  const handleAnalyze = async (files: AnalysisFiles) => {
    setShowUpload(false) // Close upload panel
    await analyze(files)
  }

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
            <div className="flex items-center gap-2 flex-shrink-0">
              {result && (
                <div className="flex-shrink-0">
                  <JsonDownloadButton data={result} />
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Results - full width */}
      {loading ? (
        <div id="results-panel" className="space-y-6">
          <SkeletonSummaryCards />
          <SkeletonResultTabs />
        </div>
      ) : result ? (
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

      {/* Floating Upload Button + Panel */}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3">
        {showUpload && (
          <UploadPanel onSubmit={handleAnalyze} loading={loading} compact />
        )}
        <Button
          onClick={() => setShowUpload((v) => !v)}
          className={showUpload 
            ? '!bg-teal-600 hover:!bg-teal-700 !text-white h-12 w-12 rounded-full'
            : '!bg-white dark:!bg-slate-100/10 !text-slate-700 dark:!text-slate-200 h-12 w-12 rounded-full !border !border-slate-300 dark:!border-slate-600 hover:!bg-slate-100 dark:hover:!bg-slate-800'}
          aria-label="Upload data"
        >
          <UploadCloud className="w-5 h-5" />
        </Button>
      </div>
    </PageShell>
  )
}


