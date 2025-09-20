import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ClipboardList } from 'lucide-react'
import type { AnalysisResult } from '@/types/analysis'
import { ForecastTable } from './ForecastTable'
import { ProductionPlanTable } from './ProductionPlanTable'
import { RawOrdersTable } from './RawOrdersTable'
import { RiskAlerts } from './RiskAlerts'
import { formatSummaryText } from '@/lib/format'

export function ResultTabs({ data }: { data: AnalysisResult }) {
  return (
    <Tabs defaultValue="forecast" className="w-full">
      <TabsList className="mb-3 w-full">
        <TabsTrigger value="forecast">Forecast</TabsTrigger>
        <TabsTrigger value="plan">Production Plan</TabsTrigger>
        <TabsTrigger value="orders">Raw Orders</TabsTrigger>
        <TabsTrigger value="risks">Risks</TabsTrigger>
        <TabsTrigger value="summary">Summary</TabsTrigger>
      </TabsList>
      <TabsContent value="forecast"><ForecastTable rows={data.forecast_table} /></TabsContent>
      <TabsContent value="plan"><ProductionPlanTable rows={data.production_plan} /></TabsContent>
      <TabsContent value="orders"><RawOrdersTable rows={data.raw_material_orders} /></TabsContent>
      <TabsContent value="risks"><RiskAlerts items={data.risk_alerts} /></TabsContent>
      <TabsContent value="summary">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ClipboardList className="w-5 h-5" />
              Executive Summary
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="prose dark:prose-invert max-w-none">
              <div 
                className="text-slate-700 dark:text-slate-300 leading-relaxed bg-slate-50 dark:bg-slate-800/50 p-6 rounded-lg border"
                dangerouslySetInnerHTML={{ 
                  __html: formatSummaryText(data.summary_text).replace(/\n/g, '<br>')
                }}
              />
            </div>
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>
  )
}


