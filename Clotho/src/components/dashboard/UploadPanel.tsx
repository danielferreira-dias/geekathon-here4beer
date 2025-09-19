import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { FileDrop } from '@/components/common/FileDrop'
import type { AnalysisFiles } from '@/hooks/useAnalysis'

export function UploadPanel({ onSubmit, loading }: { onSubmit: (files: AnalysisFiles) => void; loading: boolean }) {
  const [files, setFiles] = useState<AnalysisFiles>({ sales: null, inventory: null, materials: null, bom: null })

  const fileCount = Object.values(files).filter(Boolean).length

  return (
    <Card className="shadow-lg border-0 bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm">
      <CardHeader className="pb-4">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-10 h-10 bg-gradient-to-br from-cyan-500 to-teal-600 rounded-xl">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          <div>
            <CardTitle className="text-xl font-semibold">Upload Data Files</CardTitle>
            <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
              {fileCount > 0 ? `${fileCount} of 4 files selected` : 'Select your CSV files to begin analysis'}
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <FileDrop 
          label="Sales history (CSV)" 
          onFile={(f) => setFiles((s) => ({ ...s, sales: f }))} 
          icon="📈"
          description="Historical sales data for demand forecasting"
        />
        <FileDrop 
          label="Inventory (CSV)" 
          onFile={(f) => setFiles((s) => ({ ...s, inventory: f }))} 
          icon="📦"
          description="Current inventory levels and stock information"
        />
        <FileDrop 
          label="Raw materials (CSV)" 
          onFile={(f) => setFiles((s) => ({ ...s, materials: f }))} 
          icon="🏭"
          description="Raw material costs and availability"
        />
        <FileDrop 
          label="Bill of materials (CSV)" 
          onFile={(f) => setFiles((s) => ({ ...s, bom: f }))} 
          icon="📋"
          description="Product composition and material requirements"
        />
        
        <div className="pt-4 border-t border-slate-100 dark:border-slate-800">
          <Button 
            onClick={() => onSubmit(files)} 
            disabled={loading || fileCount === 0}
            className="w-full bg-gradient-to-r from-cyan-600 to-teal-600 hover:from-cyan-700 hover:to-teal-700 text-white font-medium py-3 rounded-xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                Analyzing Data...
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Run Analysis
              </div>
            )}
          </Button>
          {fileCount === 0 && (
            <p className="text-xs text-center text-slate-500 dark:text-slate-400 mt-2">
              Please upload at least one CSV file to continue
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  )
}


