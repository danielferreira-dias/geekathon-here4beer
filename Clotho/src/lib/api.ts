import type { AnalysisResult } from "../types/analysis";

export async function analyzeCsvs(files: {
  sales: File;
  inventory: File;
  materials: File;
  bom: File;
}): Promise<AnalysisResult> {
  const form = new FormData();
  form.append("sales", files.sales);
  form.append("inventory", files.inventory);
  form.append("materials", files.materials);
  form.append("bom", files.bom);

  const res = await fetch("/api/analyze", { method: "POST", body: form });
  if (!res.ok) throw new Error(await res.text().catch(() => "Request failed"));
  return res.json();
}
