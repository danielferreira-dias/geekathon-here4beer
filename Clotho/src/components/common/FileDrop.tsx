import { useCallback, useRef, useState } from 'react'
import { Input } from '@/components/ui/input'

type Props = {
  label: string
  accept?: string
  onFile: (file: File | null) => void
  icon?: string
  description?: string
}

export function FileDrop({ label, accept = '.csv', onFile, icon, description }: Props) {
  const inputRef = useRef<HTMLInputElement | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  const onChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null
    setSelectedFile(file)
    onFile(file)
  }, [onFile])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files?.[0] ?? null
    if (file && file.name.endsWith('.csv')) {
      setSelectedFile(file)
      onFile(file)
    }
  }, [onFile])

  return (
    <div
      className={`
        relative rounded-xl border-2 border-dashed p-4 transition-all duration-200 cursor-pointer group
        ${dragOver 
          ? 'border-cyan-400 bg-cyan-50/50 dark:bg-cyan-950/20' 
          : selectedFile
          ? 'border-teal-300 bg-teal-50/50 dark:bg-teal-950/20'
          : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600 bg-slate-50/30 dark:bg-slate-800/30'
        }
      `}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
    >
      <div className="flex items-center gap-3">
        {icon && (
          <div className="text-2xl flex-shrink-0">
            {icon}
          </div>
        )}
        <div className="flex-1 min-w-0">
          <div className="font-medium text-slate-900 dark:text-slate-100 mb-1">
            {label}
          </div>
          {description && (
            <div className="text-xs text-slate-500 dark:text-slate-400 mb-2">
              {description}
            </div>
          )}
          {selectedFile ? (
            <div className="flex items-center gap-2 text-sm">
              <svg className="w-4 h-4 text-teal-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <span className="text-teal-700 dark:text-teal-300 font-medium truncate">
                {selectedFile.name}
              </span>
              <span className="text-slate-500 text-xs">
                ({(selectedFile.size / 1024).toFixed(1)} KB)
              </span>
            </div>
          ) : (
            <div className="text-sm text-slate-500 dark:text-slate-400">
              Click to browse or drag & drop your CSV file
            </div>
          )}
        </div>
        <div className="flex-shrink-0">
          {selectedFile ? (
            <div className="w-8 h-8 bg-teal-100 dark:bg-teal-900/30 rounded-lg flex items-center justify-center">
              <svg className="w-4 h-4 text-teal-600 dark:text-teal-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            </div>
          ) : (
            <div className="w-8 h-8 bg-slate-100 dark:bg-slate-800 rounded-lg flex items-center justify-center group-hover:bg-slate-200 dark:group-hover:bg-slate-700 transition-colors">
              <svg className="w-4 h-4 text-slate-500 dark:text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
            </div>
          )}
        </div>
      </div>
      
      <Input 
        ref={inputRef} 
        type="file" 
        accept={accept} 
        onChange={onChange} 
        className="hidden" 
      />
    </div>
  )
}


