import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import type { RiskItem } from '@/types/analysis'

export function RiskAlerts({ items }: { items: RiskItem[] }) {
  const severityColor: Record<RiskItem['severity'], string> = {
    low: 'bg-emerald-500',
    medium: 'bg-amber-500',
    high: 'bg-red-600',
  }
  return (
    <div className="space-y-2">
      {items.map((r, i) => (
        <Alert key={i}>
          <AlertTitle className="flex items-center gap-2">
            <span className={`inline-block h-2.5 w-2.5 rounded-full ${severityColor[r.severity]}`} />
            {r.type} – <Badge variant="secondary">{r.severity}</Badge>
          </AlertTitle>
          <AlertDescription>
            {r.skuOrMaterial}: {r.message}
          </AlertDescription>
        </Alert>
      ))}
    </div>
  )
}


