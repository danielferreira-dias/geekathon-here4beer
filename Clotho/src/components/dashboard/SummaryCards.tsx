import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { TrendingUp, Factory, Package, AlertTriangle, CheckCircle } from 'lucide-react'
import type { AnalysisResult } from '@/types/analysis'

export function SummaryCards({ data }: { data: AnalysisResult }) {
  const totalDemand = data.forecast_table.reduce((s, x) => s + x.forecasted_demand, 0)
  const totalProduce = data.production_plan.reduce((s, x) => s + x.suggested_production, 0)
  const totalOrders = data.raw_material_orders.reduce((s, x) => s + x.suggested_order_kg, 0)
  const riskCount = data.risk_alerts.length
  
  // Determine high risks based on alert type
  const highRisks = data.risk_alerts.filter(r => 
    r.alert_type === 'expiry' || r.alert_type === 'stockout'
  ).length

  const items = [
    { 
      title: 'Forecasted Demand', 
      value: totalDemand.toLocaleString(), 
      icon: <TrendingUp className="w-6 h-6 text-blue-600" />,
      description: 'Total units forecasted',
      color: 'from-blue-500 to-cyan-500'
    },
    { 
      title: 'Production Plan', 
      value: totalProduce.toLocaleString(), 
      icon: <Factory className="w-6 h-6 text-teal-600" />,
      description: 'Units to produce',
      color: 'from-teal-500 to-green-500'
    },
    { 
      title: 'Material Orders', 
      value: `${totalOrders.toLocaleString()} kg`, 
      icon: <Package className="w-6 h-6 text-orange-600" />,
      description: 'Raw materials to order',
      color: 'from-orange-500 to-yellow-500'
    },
    { 
      title: 'Risk Alerts', 
      value: riskCount.toString(), 
      icon: highRisks > 0 ? <AlertTriangle className="w-6 h-6 text-red-600" /> : <CheckCircle className="w-6 h-6 text-green-600" />,
      description: highRisks > 0 ? `${highRisks} high priority` : 'All systems normal',
      color: highRisks > 0 ? 'from-red-500 to-pink-500' : 'from-green-500 to-emerald-500'
    },
  ]

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
      {items.map((item) => (
        <Card key={item.title} className="relative overflow-hidden border-0 shadow-lg hover:shadow-xl transition-all duration-300 group">
          <div className={`absolute inset-0 bg-gradient-to-br ${item.color} opacity-5 group-hover:opacity-10 transition-opacity`}></div>
          <CardHeader className="pb-2 sm:pb-3 relative">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 sm:gap-3 min-w-0">
                <div className="flex-shrink-0">
                  <TrendingUp className={item.title === 'Forecasted Demand' ? "w-5 h-5 sm:w-6 sm:h-6 text-blue-600" : "hidden"} />
                  <Factory className={item.title === 'Production Plan' ? "w-5 h-5 sm:w-6 sm:h-6 text-teal-600" : "hidden"} />
                  <Package className={item.title === 'Material Orders' ? "w-5 h-5 sm:w-6 sm:h-6 text-orange-600" : "hidden"} />
                  {item.title === 'Risk Alerts' && (
                    highRisks > 0 ? <AlertTriangle className="w-5 h-5 sm:w-6 sm:h-6 text-red-600" /> : <CheckCircle className="w-5 h-5 sm:w-6 sm:h-6 text-green-600" />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <CardTitle className="text-xs sm:text-sm font-medium text-slate-600 dark:text-slate-400 truncate">
                    {item.title}
                  </CardTitle>
                  <p className="text-xs text-slate-500 dark:text-slate-500 mt-1 truncate">
                    {item.description}
                  </p>
                </div>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-0 relative">
            <div className="text-xl sm:text-2xl lg:text-3xl font-bold text-slate-900 dark:text-slate-100 break-words">
              {item.value}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}


