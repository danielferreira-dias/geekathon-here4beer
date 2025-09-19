import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
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
      <TabsContent value="forecast"><ForecastTable rows={data.forecast} /></TabsContent>
      <TabsContent value="plan"><ProductionPlanTable rows={data.productionPlan} /></TabsContent>
      <TabsContent value="orders"><RawOrdersTable rows={data.rawOrders} /></TabsContent>
      <TabsContent value="risks"><RiskAlerts items={data.risks} /></TabsContent>
      <TabsContent value="summary"><div className="text-sm text-muted-foreground whitespace-pre-wrap">{data.summary}</div></TabsContent>
    </Tabs>
  )
}


