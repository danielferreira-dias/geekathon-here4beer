import { createContext, useContext } from 'react'
import type { AnalysisResult } from '@/types/analysis'

interface AnalysisContextType {
  analysisData: AnalysisResult | null
  isAnalyzing: boolean
  conversationId: string
  setAnalysisData: (data: AnalysisResult | null) => void
  setIsAnalyzing: (loading: boolean) => void
  resetConversationId: () => void
}

export const AnalysisContext = createContext<AnalysisContextType | undefined>(undefined)

export function useAnalysisContext() {
  const context = useContext(AnalysisContext)
  if (context === undefined) {
    throw new Error('useAnalysisContext must be used within an AnalysisProvider')
  }
  return context
}
