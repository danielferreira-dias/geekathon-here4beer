import { useCallback, useState } from "react";
import { analyzeCsvs, type ApiError } from "@/lib/api";
import { showToast, handleApiError, handleApiSuccess } from "@/lib/toast";
import { toast } from "sonner";
import { useAnalysisContext } from "@/contexts/AnalysisContext";

export type AnalysisFiles = {
  sales: File | null;
  inventory: File | null;
  materials: File | null;
  bom: File | null;
};

export function useAnalysis() {
  const {
    analysisData,
    isAnalyzing,
    setAnalysisData,
    setIsAnalyzing,
    resetConversationId,
  } = useAnalysisContext();
  const [error, setError] = useState<string | null>(null);

  const analyze = useCallback(
    async (files: AnalysisFiles) => {
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

      setIsAnalyzing(true);
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

        setAnalysisData(data);
        resetConversationId(); // Reset conversation ID for new analysis context

        // Dismiss loading toast and show success
        toast.dismiss(loadingToast);
        handleApiSuccess(
          "Analysis completed successfully!",
          "analyze your data"
        );

        // Show warnings if any exist in the result
        if (data.risk_alerts && data.risk_alerts.length > 0) {
          const highRisks = data.risk_alerts.filter(
            (risk) =>
              risk.alert_type === "expiry" || risk.alert_type === "stockout"
          );
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
        setIsAnalyzing(false);
      }
    },
    [setIsAnalyzing, setAnalysisData, resetConversationId]
  );

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    result: analysisData,
    loading: isAnalyzing,
    error,
    analyze,
    setResult: setAnalysisData,
    clearError,
  };
}
