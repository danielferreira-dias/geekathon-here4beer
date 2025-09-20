import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Clock, TrendingDown, BarChart3, TrendingUp, HelpCircle, CheckCircle, AlertTriangle, AlertCircle } from 'lucide-react'
import type { RiskAlertItem } from '@/types/analysis'

export function RiskAlerts({ items }: { items: RiskAlertItem[] }) {
  const typeConfig: Record<RiskAlertItem['alert_type'], {
    color: string
    bgColor: string
    icon: React.ReactNode
    textColor: string
    severity: 'high' | 'medium' | 'low'
  }> = {
    expiry: { 
      color: 'bg-red-500', 
      bgColor: 'bg-red-50 dark:bg-red-950/20', 
      icon: <Clock className="w-5 h-5 text-red-600" />,
      textColor: 'text-red-800 dark:text-red-200',
      severity: 'high'
    },
    stockout: { 
      color: 'bg-red-500', 
      bgColor: 'bg-red-50 dark:bg-red-950/20', 
      icon: <TrendingDown className="w-5 h-5 text-red-600" />,
      textColor: 'text-red-800 dark:text-red-200',
      severity: 'high'
    },
    shortage: { 
      color: 'bg-orange-500', 
      bgColor: 'bg-orange-50 dark:bg-orange-950/20', 
      icon: <BarChart3 className="w-5 h-5 text-orange-600" />,
      textColor: 'text-orange-800 dark:text-orange-200',
      severity: 'medium'
    },
    overstock: { 
      color: 'bg-green-500', 
      bgColor: 'bg-green-50 dark:bg-green-950/20', 
      icon: <TrendingUp className="w-5 h-5 text-green-600" />,
      textColor: 'text-green-800 dark:text-green-200',
      severity: 'low'
    },
    other: { 
      color: 'bg-slate-500', 
      bgColor: 'bg-slate-50 dark:bg-slate-950/20', 
      icon: <HelpCircle className="w-5 h-5 text-slate-600" />,
      textColor: 'text-slate-800 dark:text-slate-200',
      severity: 'medium'
    }
  }

  const groupedRisks = items.reduce((acc, risk) => {
    const config = typeConfig[risk.alert_type];
    const severity = config ? config.severity : 'medium';
    if (!acc[severity]) acc[severity] = []
    acc[severity].push(risk)
    return acc
  }, {} as Record<'high' | 'medium' | 'low', RiskAlertItem[]>)

  const riskStats = {
    total: items.length,
    high: items.filter(r => {
      const config = typeConfig[r.alert_type];
      return config ? config.severity === 'high' : false;
    }).length,
    medium: items.filter(r => {
      const config = typeConfig[r.alert_type];
      return config ? config.severity === 'medium' : true;
    }).length,
    low: items.filter(r => {
      const config = typeConfig[r.alert_type];
      return config ? config.severity === 'low' : false;
    }).length,
  }

  if (items.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12">
          <CheckCircle className="w-16 h-16 text-green-600 mb-4" />
          <h3 className="text-xl font-semibold text-green-700 dark:text-green-300 mb-2">
            All Clear!
          </h3>
          <p className="text-slate-600 dark:text-slate-400 text-center">
            No risks detected in your current analysis. Everything looks good to proceed.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-slate-600 dark:text-slate-400">Total Risks</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-bold">
            {riskStats.total}
          </CardContent>
        </Card>
        <Card className="border-red-200 dark:border-red-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-red-600 dark:text-red-400">High Priority</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-bold text-red-600 dark:text-red-400">
            {riskStats.high}
          </CardContent>
        </Card>
        <Card className="border-orange-200 dark:border-orange-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-orange-600 dark:text-orange-400">Medium</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-bold text-orange-600 dark:text-orange-400">
            {riskStats.medium}
          </CardContent>
        </Card>
        <Card className="border-green-200 dark:border-green-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-green-600 dark:text-green-400">Low Priority</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-bold text-green-600 dark:text-green-400">
            {riskStats.low}
          </CardContent>
        </Card>
      </div>

      {(['high', 'medium', 'low'] as const).map(severity => {
        const risks = groupedRisks[severity]
        if (!risks || risks.length === 0) return null

        const severityIcon = severity === 'high' ? <AlertCircle className="w-6 h-6 text-red-600" /> : severity === 'medium' ? <AlertTriangle className="w-6 h-6 text-orange-600" /> : <CheckCircle className="w-6 h-6 text-green-600" />
        
        return (
          <Card key={severity} className={`border-l-4 border-l-${severity === 'high' ? 'red' : severity === 'medium' ? 'orange' : 'green'}-500`}>
            <CardHeader>
              <CardTitle className="flex items-center gap-3">
                {severityIcon}
                <span className="capitalize">{severity} Priority Risks</span>
                <Badge variant="secondary">{risks.length}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {risks.map((risk, i) => {
                  const config = typeConfig[risk.alert_type] || {
                    color: 'bg-slate-500',
                    bgColor: 'bg-slate-50 dark:bg-slate-950/20',
                    icon: <HelpCircle className="w-5 h-5 text-slate-600" />,
                    textColor: 'text-slate-800 dark:text-slate-200',
                    severity: 'medium'
                  };
                  
                  return (
                    <div 
                      key={i}
                      className={`p-4 rounded-lg border ${config.bgColor} border-${severity === 'high' ? 'red' : severity === 'medium' ? 'orange' : 'green'}-200 dark:border-${severity === 'high' ? 'red' : severity === 'medium' ? 'orange' : 'green'}-800`}
                    >
                      <div className="flex items-start gap-3">
                        <div className="flex-shrink-0 mt-0.5">
                          {config.icon}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <h4 className={`font-semibold ${config.textColor}`}>
                              {risk.alert_type.charAt(0).toUpperCase() + risk.alert_type.slice(1)} Alert
                            </h4>
                            <Badge variant="outline" className="text-xs">
                              {risk.sku_or_material?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) || 'Unknown'}
                            </Badge>
                          </div>
                          <p className={`text-sm ${config.textColor} opacity-90`}>
                            {risk.description}
                          </p>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}


