import { useState } from 'react'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { Table2, BarChart3, Factory, ClipboardList } from 'lucide-react'
import type { ProductionPlanItem } from '@/types/analysis'

export function ProductionPlanTable({ rows }: { rows: ProductionPlanItem[] }) {
  const [viewMode, setViewMode] = useState<'table' | 'chart'>('table')

  // Calculate totals and metrics
  const totalDemand = rows.reduce((sum, item) => sum + item.forecasted_demand, 0)
  const totalInventory = rows.reduce((sum, item) => sum + item.current_inventory, 0)
  const totalProduction = rows.reduce((sum, item) => sum + item.suggested_production, 0)
  const productCount = rows.length

  // Prepare chart data
  const chartData = rows.map(item => ({
    product: item.sku.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
    demand: item.forecasted_demand,
    inventory: item.current_inventory,
    production: item.suggested_production,
    fullSku: item.sku
  })).sort((a, b) => b.demand - a.demand)

  // Calculate production efficiency (currently unused, but available for future features)
  // const efficiencyRate = totalInventory > 0 ? Math.round((totalProduction / (totalDemand - totalInventory)) * 100) : 100

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs sm:text-sm text-slate-600 dark:text-slate-400">Total Demand</CardTitle>
          </CardHeader>
          <CardContent className="text-lg sm:text-2xl font-bold text-blue-600 dark:text-blue-400">
            {totalDemand.toLocaleString()}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs sm:text-sm text-slate-600 dark:text-slate-400">Current Inventory</CardTitle>
          </CardHeader>
          <CardContent className="text-lg sm:text-2xl font-bold text-green-600 dark:text-green-400">
            {totalInventory.toLocaleString()}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs sm:text-sm text-slate-600 dark:text-slate-400">To Produce</CardTitle>
          </CardHeader>
          <CardContent className="text-lg sm:text-2xl font-bold text-orange-600 dark:text-orange-400">
            {totalProduction.toLocaleString()}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs sm:text-sm text-slate-600 dark:text-slate-400">Products</CardTitle>
          </CardHeader>
          <CardContent className="text-lg sm:text-2xl font-bold text-teal-600 dark:text-teal-400">
            {productCount}
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
            <CardTitle>Production Plan Overview</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64 sm:h-80 lg:h-96">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 80 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-slate-200 dark:stroke-slate-700" />
                  <XAxis 
                    dataKey="product" 
                    className="text-slate-600 dark:text-slate-400"
                    angle={-45}
                    textAnchor="end"
                    height={80}
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
                  />
                  <Bar dataKey="demand" fill="rgb(59 130 246)" name="Forecasted Demand" />
                  <Bar dataKey="inventory" fill="rgb(34 197 94)" name="Current Inventory" />
                  <Bar dataKey="production" fill="rgb(249 115 22)" name="Suggested Production" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Production Plan Details</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="rounded-md border overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="min-w-[200px] sm:min-w-[250px]">Product (SKU)</TableHead>
                    <TableHead className="min-w-[120px] text-right">Forecasted Demand</TableHead>
                    <TableHead className="min-w-[120px] text-right hidden sm:table-cell">Current Inventory</TableHead>
                    <TableHead className="min-w-[120px] text-right">Suggested Production</TableHead>
                    <TableHead className="min-w-[100px] text-center hidden lg:table-cell">Gap Analysis</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((item) => {
                    const gap = item.forecasted_demand - item.current_inventory
                    const inventoryRatio = item.current_inventory / item.forecasted_demand

                    return (
                      <TableRow key={item.sku} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                        <TableCell className="font-medium">
                          <div className="flex items-center gap-2 min-w-0">
                            <Factory className="w-4 h-4 sm:w-5 sm:h-5 text-slate-500 flex-shrink-0" />
                            <div className="min-w-0 flex-1">
                              <div className="font-semibold text-sm sm:text-base truncate">
                                {item.sku.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                              </div>
                              <div className="text-xs text-slate-500 dark:text-slate-400 font-mono truncate">
                                {item.sku}
                              </div>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell className="text-right font-semibold text-sm sm:text-base">
                          {item.forecasted_demand.toLocaleString()}
                        </TableCell>
                        <TableCell className="text-right hidden sm:table-cell">
                          <div className="flex flex-col items-end gap-1">
                            <span className={`font-medium text-sm ${inventoryRatio > 0.7 ? 'text-green-600 dark:text-green-400' : inventoryRatio > 0.3 ? 'text-orange-600 dark:text-orange-400' : 'text-red-600 dark:text-red-400'}`}>
                              {item.current_inventory.toLocaleString()}
                            </span>
                            <span className="text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">
                              ({Math.round(inventoryRatio * 100)}%)
                            </span>
                          </div>
                        </TableCell>
                        <TableCell className="text-right font-semibold text-orange-600 dark:text-orange-400 text-sm sm:text-base">
                          {item.suggested_production.toLocaleString()}
                        </TableCell>
                        <TableCell className="text-center hidden lg:table-cell">
                          <div className="flex justify-center">
                            {gap > 0 ? (
                              <Badge variant="destructive" className="text-xs whitespace-nowrap">
                                Insufficient
                              </Badge>
                            ) : (
                              <Badge variant="success" className="text-xs whitespace-nowrap">
                                Sufficient
                              </Badge>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </div>
            
            {/* Production Summary */}
            <div className="mt-6 p-4 bg-slate-50 dark:bg-slate-800/50 rounded-lg">
              <h4 className="font-semibold text-slate-700 dark:text-slate-300 mb-2 flex items-center gap-2">
                <ClipboardList className="w-4 h-4" />
                Production Summary
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4 text-xs sm:text-sm">
                <div>
                  <span className="text-slate-600 dark:text-slate-400">Total Production Needed:</span>
                  <div className="font-semibold text-orange-600 dark:text-orange-400">
                    {totalProduction.toLocaleString()} units
                  </div>
                </div>
                <div>
                  <span className="text-slate-600 dark:text-slate-400">Inventory Coverage:</span>
                  <div className="font-semibold text-green-600 dark:text-green-400">
                    {Math.round((totalInventory / totalDemand) * 100)}% of demand
                  </div>
                </div>
                <div>
                  <span className="text-slate-600 dark:text-slate-400">Production Gap:</span>
                  <div className="font-semibold text-blue-600 dark:text-blue-400">
                    {(totalDemand - totalInventory).toLocaleString()} units
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}


