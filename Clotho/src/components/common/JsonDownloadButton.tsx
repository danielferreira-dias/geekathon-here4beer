import { Button } from '@/components/ui/button'
import { generatePdfFromAnalysis } from '@/lib/pdf'
import type { AnalysisResult } from '@/types/analysis'

export function JsonDownloadButton({ data }: { data: unknown }) {
  const handleDownloadPdf = async () => {
    if (!data) return
    await generatePdfFromAnalysis(data as AnalysisResult)
  }
  return (
    <div className="flex items-center gap-2">
      <Button 
        size="sm"
        onClick={handleDownloadPdf}
        disabled={!data}
        className="!bg-teal-600 hover:!bg-teal-700 dark:!bg-teal-500 dark:hover:!bg-teal-600 !text-white"
      >
        Download PDF
      </Button>
    </div>
  )
}


