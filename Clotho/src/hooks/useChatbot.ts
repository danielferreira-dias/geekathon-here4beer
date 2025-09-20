import { useState, useCallback } from 'react'
import { BedrockService, type BedrockMessage } from '@/lib/bedrockService'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

export function useChatbot() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      role: 'assistant',
      content: 'Hello! I\'m your AI Forecasting and Planning Copilot for the meat factory. I can help you analyze sales data, create production plans, and provide supply chain insights. How can I assist you today?',
      timestamp: new Date()
    }
  ])
  const [isLoading, setIsLoading] = useState(false)

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading) return

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: content.trim(),
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setIsLoading(true)

    try {
      const bedrockService = BedrockService.getInstance()

      // Convert ChatMessage[] to BedrockMessage[] for the service
      const bedrockMessages: BedrockMessage[] = [...messages, userMessage].map(msg => ({
        role: msg.role,
        content: msg.content
      }))

      const response = await bedrockService.sendMessage(bedrockMessages)

      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response,
        timestamp: new Date()
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Error sending message:', error)
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'I apologize, but I encountered an error processing your request. Please try again or contact support if the issue persists.',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }, [messages, isLoading])

  const clearChat = useCallback(() => {
    setMessages([
      {
        id: '1',
        role: 'assistant',
        content: 'Hello! I\'m your AI Forecasting and Planning Copilot for the meat factory. I can help you analyze sales data, create production plans, and provide supply chain insights. How can I assist you today?',
        timestamp: new Date()
      }
    ])
  }, [])

  return {
    messages,
    isLoading,
    sendMessage,
    clearChat
  }
}