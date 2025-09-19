import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { AnalysisResult } from '@/types/analysis'

export function SummaryCards({ data }: { data: AnalysisResult }) {
  const totalDemand = data.forecast.reduce((s, x) => s + x.qty, 0)
  const totalProduce = data.productionPlan.reduce((s, x) => s + x.qtyToProduce, 0)
  const totalOrders = data.rawOrders.reduce((s, x) => s + x.qty, 0)
  const riskCount = data.risks.length

  const items = [
    { title: 'Forecasted demand', value: totalDemand.toLocaleString() },
    { title: 'To produce', value: totalProduce.toLocaleString() },
    { title: 'Materials to buy', value: totalOrders.toLocaleString() },
    { title: 'Risks', value: riskCount.toString() },
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
      {items.map((it) => (
        <Card key={it.title}>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">{it.title}</CardTitle></CardHeader>
          <CardContent className="text-2xl font-semibold">{it.value}</CardContent>
        </Card>
      ))}
    </div>
  )
}


