import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { AnalysisResult } from '@/types/analysis'
import { ForecastTable } from './ForecastTable'
import { ProductionPlanTable } from './ProductionPlanTable'
import { RawOrdersTable } from './RawOrdersTable'
import { RiskAlerts } from './RiskAlerts'

export function ResultTabs({ data }: { data: AnalysisResult }) {
  return (
    <Tabs defaultValue="forecast" className="w-full">
      <TabsList className="mb-3">
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
              <span className="text-xl">📋</span>
              Executive Summary
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="prose dark:prose-invert max-w-none">
              <div className="text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-wrap bg-slate-50 dark:bg-slate-800/50 p-6 rounded-lg border">
                {data.summary_text}
              </div>
            </div>
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>
  )
}


