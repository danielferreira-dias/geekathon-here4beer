import { useCallback, useState } from "react";
import type { AnalysisResult } from "@/types/analysis";
import { analyzeCsvs } from "@/lib/api";

export type AnalysisFiles = {
  sales: File | null;
  inventory: File | null;
  materials: File | null;
  bom: File | null;
};

export function useAnalysis() {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyze = useCallback(async (files: AnalysisFiles) => {
    if (!files.sales || !files.inventory || !files.materials || !files.bom) {
      setError("Please select all four CSV files.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await analyzeCsvs({
        sales: files.sales,
        inventory: files.inventory,
        materials: files.materials,
        bom: files.bom,
      });
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to analyze files");
    } finally {
      setLoading(false);
    }
  }, []);

  return { result, loading, error, analyze, setResult };
}
