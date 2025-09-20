import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import type { RawMaterialOrderItem } from '@/types/analysis'

export function RawOrdersTable({ rows }: { rows: RawMaterialOrderItem[] }) {
  // Group materials by type (beef, pork, chicken, etc.)
  const groupedByType = rows.reduce((acc, order) => {
    // Extract material type from material_id
    const type = order.material_id.split('_')[0] || 'Other'
    const capitalizedType = type.charAt(0).toUpperCase() + type.slice(1)
    
    if (!acc[capitalizedType]) {
      acc[capitalizedType] = []
    }
    acc[capitalizedType].push(order)
    return acc
  }, {} as Record<string, RawMaterialOrderItem[]>)

  const totalMaterials = rows.length
  const totalStock = rows.reduce((sum, order) => sum + order.current_stock_kg, 0)
  const totalToOrder = rows.reduce((sum, order) => sum + order.suggested_order_kg, 0)
  const criticalMaterials = rows.filter(order => order.suggested_order_kg > 0).length

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-slate-600 dark:text-slate-400">Materials Tracked</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-bold text-blue-600 dark:text-blue-400">
            {totalMaterials}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-slate-600 dark:text-slate-400">Current Stock</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-bold text-green-600 dark:text-green-400">
            {totalStock.toLocaleString()} kg
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-slate-600 dark:text-slate-400">Need to Order</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-bold text-orange-600 dark:text-orange-400">
            {totalToOrder.toLocaleString()} kg
          </CardContent>
        </Card>
        <Card className={criticalMaterials > 0 ? 'border-red-200 dark:border-red-800' : ''}>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-slate-600 dark:text-slate-400">Critical Orders</CardTitle>
          </CardHeader>
          <CardContent className={`text-2xl font-bold ${criticalMaterials > 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
            {criticalMaterials}
          </CardContent>
        </Card>
      </div>

      {/* Materials by Type */}
      <Card>
        <CardHeader>
          <CardTitle>Raw Materials by Category</CardTitle>
        </CardHeader>
        <CardContent>
          <Accordion type="multiple" className="w-full">
            {Object.entries(groupedByType).map(([materialType, materials]) => {
              const typeTotal = materials.reduce((sum, material) => sum + material.suggested_order_kg, 0)
              const criticalCount = materials.filter(material => material.suggested_order_kg > 0).length

              const typeIcon = {
                'Beef': '🥩',
                'Pork': '🐷',
                'Chicken': '🐔',
                'Bbq': '🔥',
                'Other': '📦'
              }[materialType] || '📦'

              return (
                <AccordionItem key={materialType} value={materialType}>
                  <AccordionTrigger className="hover:no-underline !bg-white dark:!bg-slate-900 !text-slate-900 dark:!text-slate-100 border border-slate-200 dark:border-slate-800 rounded-md">
                    <div className="flex items-center justify-between w-full pr-4">
                      <div className="flex items-center gap-3">
                        <span className="text-lg">{typeIcon}</span>
                        <div className="text-left">
                          <div className="font-semibold">{materialType} Materials</div>
                          <div className="text-sm text-slate-500 dark:text-slate-400">
                            {materials.length} material{materials.length !== 1 ? 's' : ''}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {criticalCount > 0 && (
                          <Badge variant="destructive" className="text-xs">
                            {criticalCount} need ordering
                          </Badge>
                        )}
                        <div className="text-right">
                          <div className="font-semibold text-orange-600 dark:text-orange-400">
                            {typeTotal.toLocaleString()} kg
                          </div>
                          <div className="text-xs text-slate-500 dark:text-slate-400">
                            to order
                          </div>
                        </div>
                      </div>
                    </div>
                  </AccordionTrigger>
                  <AccordionContent>
                    <div className="pt-2">
                      <div className="rounded-md border overflow-x-auto">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Material</TableHead>
                              <TableHead className="text-right">Current Stock</TableHead>
                              <TableHead className="text-right">Needed (kg)</TableHead>
                              <TableHead className="text-right">Order (kg)</TableHead>
                              <TableHead className="text-center">Status</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {materials.map((material, i) => {
                              const needsOrdering = material.suggested_order_kg > 0
                              const hasEnoughStock = material.current_stock_kg >= material.needed_qty_kg

                              return (
                                <TableRow 
                                  key={i} 
                                  className={needsOrdering ? 'bg-orange-50 dark:bg-orange-950/20' : hasEnoughStock ? 'bg-green-50 dark:bg-green-950/20' : ''}
                                >
                                  <TableCell className="font-medium">
                                    <div className="flex items-center gap-2">
                                      <span className="text-sm">📦</span>
                                      <div>
                                        <div className="font-semibold">
                                          {material.material_id.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                        </div>
                                        <div className="text-xs text-slate-500 dark:text-slate-400 font-mono">
                                          {material.material_id}
                                        </div>
                                      </div>
                                    </div>
                                  </TableCell>
                                  <TableCell className="text-right">
                                    <div className="flex items-center justify-end gap-2">
                                      <span className={hasEnoughStock ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}>
                                        {material.current_stock_kg.toLocaleString()} kg
                                      </span>
                                    </div>
                                  </TableCell>
                                  <TableCell className="text-right font-semibold">
                                    {material.needed_qty_kg.toLocaleString()} kg
                                  </TableCell>
                                  <TableCell className="text-right font-semibold">
                                    {material.suggested_order_kg > 0 ? (
                                      <span className="text-orange-600 dark:text-orange-400">
                                        {material.suggested_order_kg.toLocaleString()} kg
                                      </span>
                                    ) : (
                                      <span className="text-slate-400">-</span>
                                    )}
                                  </TableCell>
                                  <TableCell className="text-center">
                                    {needsOrdering ? (
                                      <Badge variant="destructive" className="text-xs">
                                        Order Now
                                      </Badge>
                                    ) : hasEnoughStock ? (
                                      <Badge variant="success" className="text-xs">
                                        Sufficient
                                      </Badge>
                                    ) : (
                                      <Badge variant="outline" className="text-xs">
                                        Adequate
                                      </Badge>
                                    )}
                                  </TableCell>
                                </TableRow>
                              )
                            })}
                          </TableBody>
                        </Table>
                      </div>
                    </div>
                  </AccordionContent>
                </AccordionItem>
              )
            })}
          </Accordion>
        </CardContent>
      </Card>
    </div>
  )
}


