import { useState } from 'react'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { Table2, TrendingUp, Package, BarChart3, Target, ChevronDown, ChevronRight } from 'lucide-react'
import type { ForecastItem } from '@/types/analysis'

export function ForecastTable({ rows }: { rows: ForecastItem[] }) {
  const [viewMode, setViewMode] = useState<'table' | 'chart'>('table')
  const [expandedSku, setExpandedSku] = useState<string | null>(null)

  // Prepare chart data - since we don't have dates, we'll show demand by SKU
  const chartData = rows.map(item => ({
    sku: item.sku.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
    demand: item.forecasted_demand,
    fullSku: item.sku
  })).sort((a, b) => b.demand - a.demand)

  const totalForecast = rows.reduce((sum, item) => sum + item.forecasted_demand, 0)
  const uniqueSkus = rows.length
  const avgPerSku = Math.round(totalForecast / uniqueSkus)
  const highestDemand = Math.max(...rows.map(r => r.forecasted_demand))
  const topSku = rows.find(r => r.forecasted_demand === highestDemand)?.sku || 'N/A'

  return (
    <div className="space-y-4">
      {/* Summary Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs sm:text-sm text-slate-600 dark:text-slate-400">Total Demand</CardTitle>
          </CardHeader>
          <CardContent className="text-lg sm:text-2xl font-bold text-blue-600 dark:text-blue-400">
            {totalForecast.toLocaleString()}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs sm:text-sm text-slate-600 dark:text-slate-400">Products</CardTitle>
          </CardHeader>
          <CardContent className="text-lg sm:text-2xl font-bold text-teal-600 dark:text-teal-400">
            {uniqueSkus}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs sm:text-sm text-slate-600 dark:text-slate-400">Average Demand</CardTitle>
          </CardHeader>
          <CardContent className="text-lg sm:text-2xl font-bold text-cyan-600 dark:text-cyan-400">
            {avgPerSku.toLocaleString()}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs sm:text-sm text-slate-600 dark:text-slate-400">Top Product</CardTitle>
          </CardHeader>
          <CardContent className="text-xs sm:text-sm font-bold text-green-600 dark:text-green-400 break-words">
            {topSku.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
          </CardContent>
        </Card>
      </div>

      {/* View Toggle */}
      <div className="flex gap-1 sm:gap-2 w-full sm:w-auto">
        <Button 
          variant={viewMode === 'table' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setViewMode('table')}
          className={`flex-1 sm:flex-initial text-xs sm:text-sm px-2 sm:px-3 py-2 ${viewMode === 'table' ? 
            '!bg-teal-600 hover:!bg-teal-700 !text-white dark:!bg-teal-500 dark:hover:!bg-teal-600 dark:!text-white !border-teal-600 dark:!border-teal-500' : 
            '!border-slate-300 dark:!border-slate-600 !text-slate-700 dark:!text-slate-300 hover:!bg-slate-100 dark:hover:!bg-slate-800 !bg-transparent'
          }`}
        >
          <Table2 className="w-3 h-3 sm:w-4 sm:h-4 mr-1" />
          <span className="hidden sm:inline">Table View</span>
          <span className="sm:hidden">Table</span>
        </Button>
        <Button 
          variant={viewMode === 'chart' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setViewMode('chart')}
          className={`flex-1 sm:flex-initial text-xs sm:text-sm px-2 sm:px-3 py-2 ${viewMode === 'chart' ? 
            '!bg-teal-600 hover:!bg-teal-700 !text-white dark:!bg-teal-500 dark:hover:!bg-teal-600 dark:!text-white !border-teal-600 dark:!border-teal-500' : 
            '!border-slate-300 dark:!border-slate-600 !text-slate-700 dark:!text-slate-300 hover:!bg-slate-100 dark:hover:!bg-slate-800 !bg-transparent'
          }`}
        >
          <BarChart3 className="w-3 h-3 sm:w-4 sm:h-4 mr-1" />
          <span className="hidden sm:inline">Chart View</span>
          <span className="sm:hidden">Chart</span>
        </Button>
      </div>

      {viewMode === 'chart' ? (
        <Card>
          <CardHeader>
            <CardTitle>Demand by Product</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64 sm:h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-700" />
                  <XAxis
                    dataKey="sku"
                    className="text-slate-600 dark:text-slate-400"
                    angle={-45}
                    textAnchor="end"
                    height={60}
                    fontSize={12}
                    interval={0}
                  />
                  <YAxis className="text-slate-600 dark:text-slate-400" fontSize={12} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgb(248 250 252)',
                      border: '1px solid rgb(226 232 240)',
                      borderRadius: '0.5rem',
                      fontSize: '12px'
                    }}
                    labelFormatter={(value) => `Product: ${value}`}
                    formatter={(value) => [value, 'Forecasted Demand']}
                  />
                  <Bar dataKey="demand" fill="rgb(59 130 246)" radius={[4,4,0,0]} barSize={20} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Forecast Details</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="rounded-md border overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="min-w-[200px] sm:min-w-[250px]">Product (SKU)</TableHead>
                    <TableHead className="min-w-[120px] text-right">Forecasted Demand</TableHead>
                    <TableHead className="min-w-[200px] hidden lg:table-cell">Confidence & Reasoning</TableHead>
                    <TableHead className="min-w-[80px] text-center">Details</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((item, i) => (
                    <>
                      <TableRow 
                        key={`${item.sku}-${i}`} 
                        className="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/50"
                        onClick={() => setExpandedSku(expandedSku === item.sku ? null : item.sku)}
                      >
                        <TableCell className="font-medium">
                          <div className="flex items-center gap-2">
                            <Package className="w-5 h-5 text-slate-500" />
                            <div>
                              <div className="font-semibold">
                                {item.sku.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                              </div>
                              <div className="text-xs text-slate-500 dark:text-slate-400 font-mono">
                                {item.sku}
                              </div>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell className="text-right font-semibold text-base sm:text-lg">
                          {item.forecasted_demand.toLocaleString()}
                        </TableCell>
                        <TableCell className="text-slate-600 dark:text-slate-400 max-w-xs hidden lg:table-cell">
                          <div className="truncate">
                            {item.confidence_or_reason.length > 60 
                              ? `${item.confidence_or_reason.substring(0, 60)}...`
                              : item.confidence_or_reason
                            }
                          </div>
                        </TableCell>
                        <TableCell className="text-center">
                          <Button 
                            variant="ghost" 
                            size="sm"
                            className="!text-slate-600 dark:!text-slate-400 !bg-transparent hover:!bg-slate-100 dark:hover:!bg-slate-800 hover:!text-slate-900 dark:hover:!text-slate-100"
                          >
                            {expandedSku === item.sku ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                          </Button>
                        </TableCell>
                      </TableRow>
                      {expandedSku === item.sku && (
                        <TableRow className="bg-slate-50/50 dark:bg-slate-800/20">
                          <TableCell colSpan={4} className="pl-4 sm:pl-12">
                            <div className="py-4">
                              <h4 className="font-semibold text-slate-700 dark:text-slate-300 mb-2 text-sm sm:text-base">
                                <BarChart3 className="w-4 h-4 inline mr-1" />
                                Detailed Analysis
                              </h4>
                              <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                                {item.confidence_or_reason}
                              </p>
                              <div className="mt-3 flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 text-xs text-slate-500 dark:text-slate-400">
                                <div className="flex items-center gap-1">
                                  <TrendingUp className="w-3 h-3" />
                                  <span>Demand: {item.forecasted_demand.toLocaleString()} units</span>
                                </div>
                                <div className="flex items-center gap-1"> 
                                  <Target className="w-3 h-3" />
                                  <span>AI-Generated Forecast</span>
                                </div>
                              </div>
                            </div>
                          </TableCell>
                        </TableRow>
                      )}
                    </>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}


