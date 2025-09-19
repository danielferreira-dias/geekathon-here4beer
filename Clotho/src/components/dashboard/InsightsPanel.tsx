import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export function InsightsPanel({ text }: { text: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Insights</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground whitespace-pre-wrap">{text}</p>
      </CardContent>
    </Card>
  )
}


