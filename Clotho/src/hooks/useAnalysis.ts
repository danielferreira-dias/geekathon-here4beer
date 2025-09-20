import { useCallback, useState } from "react";
import type { AnalysisResult } from "@/types/analysis";
import { analyzeCsvs, type ApiError } from "@/lib/api";
import { showToast, handleApiError, handleApiSuccess } from "@/lib/toast";
import { toast } from "sonner";

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
    // Validation
    const missingFiles = [];
    if (!files.sales) missingFiles.push("Sales history");
    if (!files.inventory) missingFiles.push("Inventory");
    if (!files.materials) missingFiles.push("Raw materials");
    if (!files.bom) missingFiles.push("Bill of materials");

    if (missingFiles.length > 0) {
      const errorMsg = `Please select all required files: ${missingFiles.join(
        ", "
      )}`;
      setError(errorMsg);
      showToast.warning("Missing Files", {
        description: errorMsg,
        duration: 5000,
      });
      return;
    }

    setLoading(true);
    setError(null);

    // Show loading toast
    const loadingToast = showToast.loading("Analyzing your data...");

    try {
      const data = await analyzeCsvs({
        sales: files.sales!,
        inventory: files.inventory!,
        materials: files.materials!,
        bom: files.bom!,
      });

      setResult(data);

      // Dismiss loading toast and show success
      toast.dismiss(loadingToast);
      handleApiSuccess("Analysis completed successfully!", "analyze your data");

      // Show warnings if any exist in the result
      if (data.risks && data.risks.length > 0) {
        const highRisks = data.risks.filter((risk) => risk.severity === "high");
        if (highRisks.length > 0) {
          showToast.warning("High Risk Alerts Detected", {
            description: `Found ${highRisks.length} high priority risk(s) in your analysis`,
            duration: 8000,
          });
        }
      }
    } catch (e) {
      toast.dismiss(loadingToast);

      const apiError = e as ApiError;
      let errorMessage = "Failed to analyze files";

      if (apiError.status === 0) {
        errorMessage = "Network connection failed";
      } else if (apiError.status && apiError.status >= 400) {
        // Use the enhanced error handling
        handleApiError(apiError, "analyze your data");
        setError(apiError.message);
        return;
      } else {
        errorMessage = apiError.message || errorMessage;
      }

      setError(errorMessage);
      handleApiError(apiError, "analyze your data");
    } finally {
      setLoading(false);
    }
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return { result, loading, error, analyze, setResult, clearError };
}
