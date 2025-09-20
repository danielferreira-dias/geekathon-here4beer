import { type ReactNode } from 'react'
import { AnalysisContext } from './AnalysisContext'
import { useState, useCallback } from 'react'
import { v4 as uuidv4 } from 'uuid'
import type { AnalysisResult } from '@/types/analysis'

interface AnalysisProviderProps {
  children: ReactNode
}

export function AnalysisProvider({ children }: AnalysisProviderProps) {
  const [analysisData, setAnalysisData] = useState<AnalysisResult | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [conversationId, setConversationId] = useState(() => uuidv4())

  const resetConversationId = useCallback(() => {
    setConversationId(uuidv4())
  }, [])

  return (
    <AnalysisContext.Provider
      value={{
        analysisData,
        isAnalyzing,
        conversationId,
        setAnalysisData,
        setIsAnalyzing,
        resetConversationId,
      }}
    >
      {children}
    </AnalysisContext.Provider>
  )
}
