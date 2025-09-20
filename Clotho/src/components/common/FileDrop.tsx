import { useCallback, useRef, useState, type ReactNode } from 'react'
import { Input } from '@/components/ui/input'

type Props = {
  label: string
  accept?: string
  onFile: (file: File | null) => void
  icon?: ReactNode
  description?: string
  compact?: boolean
}

export function FileDrop({ label, accept = '.csv', onFile, icon, description, compact = false }: Props) {
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

  const handleRemoveFile = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setSelectedFile(null)
    onFile(null)
    // Clear the input value to allow re-selecting the same file
    if (inputRef.current) {
      inputRef.current.value = ''
    }
  }, [onFile])

  return (
    <div
      className={`
        relative rounded-xl border-dashed transition-all duration-200 cursor-pointer group
        ${compact ? 'p-3 border' : 'p-4 border-2'}
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
      <div className={compact ? 'flex items-center gap-2' : 'flex items-center gap-3'}>
        {icon && (
          <div className={compact ? 'text-xl flex-shrink-0' : 'text-2xl flex-shrink-0'}>
            {icon}
          </div>
        )}
        <div className="flex-1 min-w-0">
          <div className={compact ? 'font-medium text-slate-900 dark:text-slate-100 mb-0.5 text-sm' : 'font-medium text-slate-900 dark:text-slate-100 mb-1'}>
            {label}
          </div>
          {description && (
            <div className={compact ? 'text-[11px] text-slate-500 dark:text-slate-400 mb-1' : 'text-xs text-slate-500 dark:text-slate-400 mb-2'}>
              {description}
            </div>
          )}
          {selectedFile ? (
            <div className={compact ? 'flex items-center gap-1.5 text-[12px]' : 'flex items-center gap-2 text-sm'}>
              <svg className={compact ? 'w-3.5 h-3.5 text-teal-600' : 'w-4 h-4 text-teal-600'} fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <span className="text-teal-700 dark:text-teal-300 font-medium truncate" title={selectedFile.name}>
                {selectedFile.name}
              </span>
              <span className="text-slate-500 text-xs">
                ({(selectedFile.size / 1024).toFixed(1)} KB)
              </span>
            </div>
          ) : (
            <div className={compact ? 'text-[12px] text-slate-500 dark:text-slate-400' : 'text-sm text-slate-500 dark:text-slate-400'}>
              Click to browse or drag & drop your CSV file
            </div>
          )}
        </div>
        <div className="flex-shrink-0 relative">
          {selectedFile ? (
            <div className="relative">
              {/* Success indicator - always visible */}
              <div className={compact ? 'w-7 h-7 bg-teal-100 dark:bg-teal-900/30 rounded-lg flex items-center justify-center group-hover:opacity-0 transition-opacity duration-200' : 'w-8 h-8 bg-teal-100 dark:bg-teal-900/30 rounded-lg flex items-center justify-center group-hover:opacity-0 transition-opacity duration-200'}>
                <svg className={compact ? 'w-3.5 h-3.5 text-teal-600 dark:text-teal-400' : 'w-4 h-4 text-teal-600 dark:text-teal-400'} fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              </div>
              
              {/* Remove button - appears on hover */}
              <button
                onClick={handleRemoveFile}
                className={compact ? 'absolute top-0 left-0 w-7 h-7 p-0 m-0 border-0 !bg-red-100 dark:!bg-red-900/30 rounded-lg flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all duration-200 hover:!bg-red-200 dark:hover:!bg-red-900/50 z-10' : 'absolute top-0 left-0 w-8 h-8 p-0 m-0 border-0 !bg-red-100 dark:!bg-red-900/30 rounded-lg flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all duration-200 hover:!bg-red-200 dark:hover:!bg-red-900/50 z-10'}
                title="Remove file"
                type="button"
                style={{ padding: 0, margin: 0, border: 'none', transition: 'all 0.2s ease-in-out' }}
              >
                <svg className={compact ? 'w-3.5 h-3.5 text-red-600 dark:text-red-400 z-10' : 'w-4 h-4 text-red-600 dark:text-red-400 z-10'} fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </button>
            </div>
          ) : (
            <div className={compact ? 'w-7 h-7 bg-slate-100 dark:bg-slate-800 rounded-lg flex items-center justify-center group-hover:bg-slate-200 dark:group-hover:bg-slate-700 transition-colors' : 'w-8 h-8 bg-slate-100 dark:bg-slate-800 rounded-lg flex items-center justify-center group-hover:bg-slate-200 dark:group-hover:bg-slate-700 transition-colors'}>
              <svg className={compact ? 'w-3.5 h-3.5 text-slate-500 dark:text-slate-400' : 'w-4 h-4 text-slate-500 dark:text-slate-400'} fill="none" viewBox="0 0 24 24" stroke="currentColor">
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


