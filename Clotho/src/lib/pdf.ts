/* eslint-disable @typescript-eslint/no-explicit-any */
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import type {
  AnalysisResult,
  ProductionPlanItem,
  RawMaterialOrderItem,
} from "@/types/analysis";

function drawHeader(doc: jsPDF) {
  // Gradient-like header bar with title
  doc.setFillColor(5, 150, 105); // teal-600
  doc.rect(0, 0, doc.internal.pageSize.getWidth(), 24, "F");
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(18);
  doc.setFont("helvetica", "bold");
  doc.text("Clotho Analysis Report", 14, 16);
}

function drawFooter(doc: jsPDF) {
  const pageCount = doc.getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    doc.setFontSize(9);
    doc.setTextColor(100);
    doc.text(
      `Page ${i} / ${pageCount}`,
      doc.internal.pageSize.getWidth() - 28,
      doc.internal.pageSize.getHeight() - 10
    );
  }
}

function kpiCard(
  doc: jsPDF,
  x: number,
  y: number,
  w: number,
  h: number,
  title: string,
  value: string,
  accent: [number, number, number]
) {
  // background
  doc.setFillColor(248, 250, 252); // slate-50
  doc.roundedRect(x, y, w, h, 3, 3, "F");
  // left accent
  doc.setFillColor(...accent);
  doc.roundedRect(x, y, 4, h, 3, 3, "F");
  // text
  doc.setTextColor(100, 116, 139); // slate-500
  doc.setFontSize(10);
  doc.setFont("helvetica", "bold");
  doc.text(title, x + 8, y + 8);
  doc.setTextColor(15, 23, 42); // slate-900
  doc.setFontSize(16);
  doc.setFont("helvetica", "bold");
  doc.text(value, x + 8, y + 18);
}

function addSummary(doc: jsPDF, data: AnalysisResult, startY: number): number {
  // returns the Y position after rendering summary block
  doc.setTextColor(15, 23, 42); // slate-900
  doc.setFontSize(14);
  doc.setFont("helvetica", "bold");
  doc.text("Executive Summary", 14, startY);

  doc.setFontSize(11);
  doc.setFont("helvetica", "normal");
  const maxWidth = doc.internal.pageSize.getWidth() - 28;
  const textLines = doc.splitTextToSize(
    data.summary_text || "No summary provided.",
    maxWidth
  );
  const textStart = startY + 8;
  doc.text(textLines, 14, textStart);
  const lineHeight = 5; // approx line height in mm for fontSize 11
  const endY = textStart + textLines.length * lineHeight;
  return endY;
}

function addPlanTable(doc: jsPDF, rows: ProductionPlanItem[], startY: number) {
  autoTable(doc, {
    startY,
    headStyles: { fillColor: [2, 132, 199], textColor: 255 },
    styles: { fontSize: 10 },
    head: [["SKU", "Forecast", "Inventory", "Production", "Gap", "Status"]],
    body: rows
      .map((r) => {
        const gap = r.forecasted_demand - r.current_inventory;
        const status =
          gap <= 0
            ? "Sufficient"
            : gap <= r.suggested_production
            ? "Covered"
            : "Short";
        return [
          r.sku,
          r.forecasted_demand.toLocaleString(),
          r.current_inventory.toLocaleString(),
          r.suggested_production.toLocaleString(),
          gap.toLocaleString(),
          status,
        ];
      })
      .slice(0, 8),
  });
}

function addOrdersTable(
  doc: jsPDF,
  rows: RawMaterialOrderItem[],
  startY: number
) {
  autoTable(doc, {
    startY,
    headStyles: { fillColor: [234, 88, 12], textColor: 255 },
    styles: { fontSize: 10 },
    head: [
      [
        "Material",
        "Needed (kg)",
        "Stock (kg)",
        "Order (kg)",
        "Shortfall",
        "Priority",
      ],
    ],
    body: rows
      .map((r) => {
        const shortfall = Math.max(0, r.needed_qty_kg - r.current_stock_kg);
        const priority =
          r.suggested_order_kg > 0
            ? shortfall > 0
              ? "High"
              : "Medium"
            : "Low";
        return [
          r.material_id,
          r.needed_qty_kg.toLocaleString(),
          r.current_stock_kg.toLocaleString(),
          r.suggested_order_kg.toLocaleString(),
          shortfall.toLocaleString(),
          priority,
        ];
      })
      .sort(
        (a: any, b: any) =>
          Number(b[4].replace(/\D/g, "")) - Number(a[4].replace(/\D/g, ""))
      )
      .slice(0, 8),
  });
}

function miniBarChart(
  doc: jsPDF,
  x: number,
  y: number,
  w: number,
  h: number,
  title: string,
  items: { label: string; value: number; color: [number, number, number] }[]
) {
  doc.setFontSize(11);
  doc.setFont("helvetica", "bold");
  doc.setTextColor(15, 23, 42);
  doc.text(title, x, y - 3);

  const max = Math.max(...items.map((i) => i.value), 1);
  const barHeight = Math.floor((h - 8) / items.length);
  items.slice(0, Math.min(items.length, 6)).forEach((it, idx) => {
    const by = y + idx * barHeight + 2;
    const bw = Math.max(2, Math.round((it.value / max) * (w - 60)));
    // label
    doc.setFontSize(9);
    doc.setTextColor(100, 116, 139);
    doc.text(it.label, x, by + 4);
    // bar
    doc.setFillColor(...it.color);
    doc.rect(x + 42, by - 3, bw, 6, "F");
    // value
    doc.setTextColor(15, 23, 42);
    doc.text(String(it.value), x + 42 + bw + 3, by + 4);
  });
}

export async function generatePdfFromAnalysis(data: AnalysisResult) {
  const doc = new jsPDF("p", "mm", "a4");
  drawHeader(doc);

  // KPIs row
  const totalDemand = data.forecast_table.reduce(
    (s, x) => s + x.forecasted_demand,
    0
  );
  const totalProduce = data.production_plan.reduce(
    (s, x) => s + x.suggested_production,
    0
  );
  const totalOrders = data.raw_material_orders.reduce(
    (s, x) => s + x.suggested_order_kg,
    0
  );
  const highRisks = data.risk_alerts.filter(
    (r) => r.alert_type === "expiry" || r.alert_type === "stockout"
  ).length;

  const kpiY = 28;
  kpiCard(
    doc,
    14,
    kpiY,
    45,
    22,
    "Forecast",
    totalDemand.toLocaleString(),
    [59, 130, 246]
  );
  kpiCard(
    doc,
    63,
    kpiY,
    45,
    22,
    "Production",
    totalProduce.toLocaleString(),
    [16, 185, 129]
  );
  kpiCard(
    doc,
    112,
    kpiY,
    45,
    22,
    "Order (kg)",
    totalOrders.toLocaleString(),
    [251, 146, 60]
  );
  kpiCard(
    doc,
    161,
    kpiY,
    35,
    22,
    "High Risks",
    String(highRisks),
    [239, 68, 68]
  );

  // Summary paragraph directly below KPI cards
  const summaryStartY = kpiY + 22 + 8; // card height + spacing
  const afterSummaryY = addSummary(doc, data, summaryStartY);

  // Mini charts row (ensure ample spacing after summary)
  const chartTop = Math.max(afterSummaryY + 12, 96);
  // subtle divider above charts
  doc.setDrawColor(226, 232, 240); // slate-200
  doc.line(
    14,
    chartTop - 6,
    doc.internal.pageSize.getWidth() - 14,
    chartTop - 6
  );
  miniBarChart(
    doc,
    14,
    chartTop,
    88,
    42,
    "Top Forecast (units)",
    data.forecast_table
      .slice()
      .sort((a, b) => b.forecasted_demand - a.forecasted_demand)
      .slice(0, 6)
      .map((r) => ({
        label: r.sku,
        value: r.forecasted_demand,
        color: [59, 130, 246],
      }))
  );
  miniBarChart(
    doc,
    112,
    chartTop,
    88,
    42,
    "Orders Needed (kg)",
    data.raw_material_orders
      .slice()
      .sort((a, b) => b.suggested_order_kg - a.suggested_order_kg)
      .slice(0, 6)
      .map((r) => ({
        label: r.material_id,
        value: r.suggested_order_kg,
        color: [251, 146, 60],
      }))
  );

  // Compact tables on the same page
  doc.setTextColor(15, 23, 42);
  doc.setFontSize(12);
  doc.setFont("helvetica", "bold");
  const firstTableY = chartTop + 46; // charts block height
  doc.text("Production Plan (top)", 14, firstTableY);
  addPlanTable(doc, data.production_plan, firstTableY + 4);

  doc.setFont("helvetica", "bold");
  const afterPlanY =
    ((doc as any).lastAutoTable?.finalY || firstTableY + 40) + 8;
  doc.text("Raw Orders (top)", 14, afterPlanY);
  addOrdersTable(doc, data.raw_material_orders, afterPlanY + 4);

  // Full tables stacked on a single page
  doc.addPage();
  drawHeader(doc);
  doc.setTextColor(15, 23, 42);
  doc.setFontSize(14);
  doc.setFont("helvetica", "bold");
  doc.text("Full Forecast Table", 14, 32);
  autoTable(doc, {
    startY: 38,
    headStyles: { fillColor: [5, 150, 105], textColor: 255 },
    styles: { fontSize: 10 },
    head: [["SKU", "Forecasted"]],
    body: data.forecast_table.map((r) => [
      r.sku,
      r.forecasted_demand.toLocaleString(),
    ]),
  });
  const afterForecastY = ((doc as any).lastAutoTable?.finalY || 40) + 10;
  if (afterForecastY > doc.internal.pageSize.getHeight() - 40) {
    doc.addPage();
    drawHeader(doc);
  }
  doc.setTextColor(15, 23, 42);
  doc.setFontSize(14);
  doc.setFont("helvetica", "bold");
  const planTitleY = ((doc as any).lastAutoTable?.finalY || 32) + 8;
  doc.text("Full Production Plan", 14, planTitleY);
  autoTable(doc, {
    startY: planTitleY + 6,
    headStyles: { fillColor: [2, 132, 199], textColor: 255 },
    styles: { fontSize: 10 },
    head: [["SKU", "Forecast", "Inventory", "Production", "Gap"]],
    body: data.production_plan.map((r) => [
      r.sku,
      r.forecasted_demand.toLocaleString(),
      r.current_inventory.toLocaleString(),
      r.suggested_production.toLocaleString(),
      (r.forecasted_demand - r.current_inventory).toLocaleString(),
    ]),
  });
  const afterPlanFullY = ((doc as any).lastAutoTable?.finalY || 40) + 10;
  if (afterPlanFullY > doc.internal.pageSize.getHeight() - 40) {
    doc.addPage();
    drawHeader(doc);
  }
  doc.setTextColor(15, 23, 42);
  doc.setFontSize(14);
  doc.setFont("helvetica", "bold");
  const ordersTitleY = ((doc as any).lastAutoTable?.finalY || 32) + 8;
  doc.text("Full Raw Orders", 14, ordersTitleY);
  autoTable(doc, {
    startY: ordersTitleY + 6,
    headStyles: { fillColor: [234, 88, 12], textColor: 255 },
    styles: { fontSize: 10 },
    head: [["Material", "Needed (kg)", "Stock (kg)", "Order (kg)"]],
    body: data.raw_material_orders.map((r) => [
      r.material_id,
      r.needed_qty_kg.toLocaleString(),
      r.current_stock_kg.toLocaleString(),
      r.suggested_order_kg.toLocaleString(),
    ]),
  });

  drawFooter(doc);
  doc.save("clotho-analysis.pdf");
}
