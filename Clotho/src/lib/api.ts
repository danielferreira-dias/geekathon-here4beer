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
  form.append("sales", files.sales);
  form.append("inventory", files.inventory);
  form.append("materials", files.materials);
  form.append("bom", files.bom);

  try {
    // Use VITE_API_URL environment variable, fallback to localhost for development
    const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";

    const res = await fetch(`${apiUrl}/analyze`, {
      method: "POST",
      body: form,
      headers: {
        // Don't set Content-Type for FormData, let the browser set it with boundary
      },
    });

    if (!res.ok) {
      let errorMessage = `HTTP ${res.status}`;
      let details = "";

      try {
        // Try to get error details from response
        const errorText = await res.text();
        if (errorText) {
          try {
            const errorJson = JSON.parse(errorText);
            errorMessage = errorJson.message || errorJson.error || errorMessage;
            details = errorJson.details || errorJson.description || "";
          } catch {
            // If not JSON, use the text as is
            errorMessage = errorText || errorMessage;
          }
        }
      } catch {
        // Fallback to generic message
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
