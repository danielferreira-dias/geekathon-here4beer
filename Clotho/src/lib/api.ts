import type { AnalysisResult } from "../types/analysis";

export interface ApiError extends Error {
  status?: number;
  statusText?: string;
  details?: string;
}

export async function analyzeCsvs(files: {
  sales: File;
  inventory: File;
  materials: File;
  bom: File;
}): Promise<AnalysisResult> {
  const form = new FormData();
  form.append("sales_history", files.sales);
  form.append("inventory", files.inventory);
  form.append("raw_materials", files.materials);
  form.append("bill_of_materials", files.bom);

  try {
    const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";

    const res = await fetch(`${apiUrl}/analyze`, {
      method: "POST",
      body: form,
    });

    if (!res.ok) {
      let errorMessage = `HTTP ${res.status}`;
      let details = "";

      try {
        const errorText = await res.text();
        if (errorText) {
          try {
            const errorJson = JSON.parse(errorText);
            errorMessage = errorJson.message || errorJson.error || errorMessage;
            details = errorJson.details || errorJson.description || "";
          } catch {
            errorMessage = errorText || errorMessage;
          }
        }
      } catch {
        errorMessage = `HTTP ${res.status} ${res.statusText}`;
      }

      const error = new Error(errorMessage) as ApiError;
      error.status = res.status;
      error.statusText = res.statusText;
      error.details = details;
      throw error;
    }

    const result = await res.json();
    return result;
  } catch (error) {
    if (error instanceof TypeError && error.message.includes("fetch")) {
      // Network error
      const networkError = new Error(
        "Network error - please check your connection"
      ) as ApiError;
      networkError.status = 0;
      throw networkError;
    }
    throw error;
  }
}

export async function getExistingAnalysis(): Promise<AnalysisResult | null> {
  try {
    const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
    console.log("Fetching existing analysis from:", `${apiUrl}/analyze`);

    const res = await fetch(`${apiUrl}/analyze`, {
      method: "GET",
    });

    if (res.status === 404) {
      // No existing analysis found
      console.log("No existing analysis found (404)");
      return null;
    }

    if (!res.ok) {
      let errorMessage = `HTTP ${res.status}`;
      let details = "";

      try {
        const errorText = await res.text();
        if (errorText) {
          try {
            const errorJson = JSON.parse(errorText);
            errorMessage = errorJson.message || errorJson.error || errorMessage;
            details = errorJson.details || errorJson.description || "";
          } catch {
            errorMessage = errorText || errorMessage;
          }
        }
      } catch {
        errorMessage = `HTTP ${res.status} ${res.statusText}`;
      }

      const error = new Error(errorMessage) as ApiError;
      error.status = res.status;
      error.statusText = res.statusText;
      error.details = details;
      throw error;
    }

    const result = await res.json();
    console.log("Existing analysis loaded successfully");
    return result;
  } catch (error) {
    if (error instanceof TypeError && error.message.includes("fetch")) {
      // Network error - don't throw for GET requests, just return null
      console.warn("Network error fetching existing analysis:", error.message);
      return null;
    }

    // For other errors (like 500, etc.), log but don't throw
    console.warn("Failed to fetch existing analysis:", error);
    return null;
  }
}
