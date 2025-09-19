import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import type { OrderItem } from '@/types/analysis'

export function RawOrdersTable({ rows }: { rows: OrderItem[] }) {
  return (
    <div className="rounded-md border overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Material</TableHead>
            <TableHead className="text-right">Qty</TableHead>
            <TableHead>UoM</TableHead>
            <TableHead>Needed By</TableHead>
            <TableHead>Supplier</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((r, i) => (
            <TableRow key={i}>
              <TableCell>{r.material}</TableCell>
              <TableCell className="text-right">{r.qty.toLocaleString()}</TableCell>
              <TableCell>{r.uom}</TableCell>
              <TableCell>{new Date(r.neededBy).toLocaleDateString()}</TableCell>
              <TableCell>{r.supplier ?? '-'}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}


