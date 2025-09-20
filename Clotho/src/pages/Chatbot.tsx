import { useState, useRef, useEffect } from 'react'
import { marked } from 'marked'
import { PageShell } from '@/components/common/PageShell'
import { TopNav } from '@/components/common/TopNav'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Send, Bot, User, Loader2, RotateCcw } from 'lucide-react'
import { useChatbot } from '@/hooks/useChatbot'

interface ChatbotProps {
  onNavigate: (page: 'dashboard' | 'chatbot') => void
}

export default function Chatbot({ onNavigate }: ChatbotProps) {
  const { messages, isLoading, sendMessage, clearChat } = useChatbot()
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSendMessage = async () => {
    if (!input.trim() || isLoading) return

    const messageContent = input.trim()
    setInput('')

    await sendMessage(messageContent)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  const parseMarkdown = (content: string) => {
    // Configure marked for safe HTML output
    marked.setOptions({
      breaks: true, // Convert line breaks to <br>
      gfm: true, // GitHub flavored markdown
    })
    
    return marked(content)
  }

  return (
    <PageShell>
      <TopNav currentPage="chatbot" onNavigate={onNavigate} />

      {/* Chat Interface */}
      <div className="w-full bg-transparent h-full">
        <Card className="h-[calc(100vh-200px)] max-h-[800px] min-h-[500px] flex flex-col">
          <CardHeader className="flex-shrink-0 pb-4">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Bot className="h-5 w-5 text-emerald-600" />
                AI Forecasting & Planning Assistant
              </CardTitle>
              <Button
                onClick={clearChat}
                variant="ghost"
                size="sm"
                className="flex items-center gap-2 !bg-white !text-slate-700 !border !border-slate-300 hover:!bg-slate-100 dark:!bg-transparent dark:!text-slate-400 dark:hover:!bg-slate-800 dark:!border-slate-700"
              >
                <RotateCcw className="h-4 w-4" />
                Clear Chat
              </Button>
            </div>
            <Separator />
          </CardHeader>

          <CardContent className="flex-1 flex flex-col p-0 min-h-0">
            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4 min-h-0">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {message.role === 'assistant' && (
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-emerald-100 dark:bg-emerald-800 flex items-center justify-center">
                      <Bot className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                    </div>
                  )}

                  <div className={`${message.role === 'user' ? 'max-w-[70%] order-1' : 'max-w-[85%]'}`}>
                    <div
                      className={`rounded-2xl px-4 py-3 ${
                        message.role === 'user'
                          ? 'bg-blue-600 text-white'
                          : 'bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100'
                      }`}
                    >
                      {message.role === 'assistant' ? (
                        <div 
                          className="prose prose-sm max-w-none dark:prose-invert prose-headings:mt-3 prose-headings:mb-2 prose-p:my-1 prose-ul:my-2 prose-ol:my-2 prose-li:my-0"
                          dangerouslySetInnerHTML={{ __html: parseMarkdown(message.content) }}
                        />
                      ) : (
                        <p className="whitespace-pre-wrap">{message.content}</p>
                      )}
                    </div>
                    <p className={`text-xs text-slate-500 dark:text-slate-400 mt-1 ${
                      message.role === 'user' ? 'text-right' : 'text-left'
                    }`}>
                      {formatTime(message.timestamp)}
                    </p>
                  </div>

                  {message.role === 'user' && (
                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-800 flex items-center justify-center order-2">
                      <User className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                    </div>
                  )}
                </div>
              ))}

              {isLoading && (
                <div className="flex gap-3 justify-start">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-emerald-100 dark:bg-emerald-800 flex items-center justify-center">
                    <Bot className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                  </div>
                  <div className="bg-slate-100 dark:bg-slate-800 rounded-2xl px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin text-slate-500" />
                      <span className="text-slate-500 dark:text-slate-400">AI is thinking...</span>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="flex-shrink-0 border-t border-slate-200 dark:border-slate-700 p-4">
              <div className="flex gap-3">
                <div className="flex-1 relative">
                  <textarea
                    ref={textareaRef}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Start chatting..."
                    className="w-full resize-none rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-4 py-3 pr-12 text-slate-900 dark:text-slate-100 placeholder-slate-500 dark:placeholder-slate-400 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 min-h-[44px] max-h-32 placeholder:text-sm"
                    rows={1}
                    style={{
                      height: '44px',
                      lineHeight: '1.5'
                    }}
                    onInput={(e) => {
                      const target = e.target as HTMLTextAreaElement
                      target.style.height = '44px'
                      target.style.height = Math.min(target.scrollHeight, 128) + 'px'
                    }}
                  />
                </div>
                <Button
                  onClick={handleSendMessage}
                  disabled={!input.trim() || isLoading}
                  className="flex-shrink-0 h-11 w-11 rounded-xl bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 dark:disabled:bg-slate-600"
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>

              <div className="mt-2">
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Press Enter to send, Shift+Enter for new line
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </PageShell>
  )
}