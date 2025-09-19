import { Button } from '@/components/ui/button'

export function JsonDownloadButton({ data }: { data: unknown }) {
  const handleDownload = () => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'clotho-analysis.json'
    a.click()
    URL.revokeObjectURL(url)
  }
  return (
    <Button size="sm" variant="outline" onClick={handleDownload} disabled={!data}>
      Download JSON
    </Button>
  )
}


