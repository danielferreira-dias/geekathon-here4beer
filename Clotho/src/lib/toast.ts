import { toast } from "sonner";

// HTTP status code to user-friendly message mapping
const HTTP_ERROR_MESSAGES: Record<number, string> = {
  400: "Bad Request - Please check your input data",
  401: "Unauthorized - Please check your credentials",
  403: "Forbidden - You don't have permission to perform this action",
  404: "Not Found - The requested resource was not found",
  408: "Request Timeout - The server took too long to respond",
  413: "File Too Large - One or more files exceed the size limit",
  415: "Unsupported File Type - Please upload CSV files only",
  422: "Invalid Data - Please check your CSV file format",
  429: "Too Many Requests - Please wait before trying again",
  500: "Internal Server Error - Something went wrong on our end",
  502: "Bad Gateway - Service temporarily unavailable",
  503: "Service Unavailable - Please try again later",
  504: "Gateway Timeout - The service is taking too long to respond",
};

export interface ToastOptions {
  duration?: number;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export const showToast = {
  success: (message: string, options?: ToastOptions) => {
    return toast.success(message, {
      duration: options?.duration || 4000,
      description: options?.description,
      action: options?.action,
      style: {
        background: "rgb(240 253 250)",
        border: "1px solid rgb(34 197 94)",
        color: "rgb(22 101 52)",
        borderRadius: "0.75rem",
        padding: "1rem",
        boxShadow:
          "0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)",
      },
      className:
        "dark:!bg-green-950 dark:!border-green-800 dark:!text-green-100 [&>[data-description]]:!text-black dark:[&>[data-description]]:!text-green-200",
    });
  },

  error: (message: string, options?: ToastOptions) => {
    return toast.error(message, {
      duration: options?.duration || 6000,
      description: options?.description,
      action: options?.action,
      style: {
        background: "rgb(254 242 242)",
        border: "1px solid rgb(239 68 68)",
        color: "rgb(127 29 29)",
        borderRadius: "0.75rem",
        padding: "1rem",
        boxShadow:
          "0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)",
      },
      className:
        "dark:!bg-red-950 dark:!border-red-800 dark:!text-red-100 [&>[data-description]]:!text-red-700 dark:[&>[data-description]]:!text-red-200",
    });
  },

  warning: (message: string, options?: ToastOptions) => {
    return toast.warning(message, {
      duration: options?.duration || 5000,
      description: options?.description,
      action: options?.action,
      style: {
        background: "rgb(255 247 237)",
        border: "1px solid rgb(245 158 11)",
        color: "rgb(120 53 15)",
        borderRadius: "0.75rem",
        padding: "1rem",
        boxShadow:
          "0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)",
      },
      className:
        "dark:!bg-amber-950 dark:!border-amber-800 dark:!text-amber-100 [&>[data-description]]:!text-amber-700 dark:[&>[data-description]]:!text-amber-200",
    });
  },

  info: (message: string, options?: ToastOptions) => {
    return toast.info(message, {
      duration: options?.duration || 4000,
      description: options?.description,
      action: options?.action,
      style: {
        background: "rgb(239 246 255)",
        border: "1px solid rgb(59 130 246)",
        color: "rgb(30 58 138)",
        borderRadius: "0.75rem",
        padding: "1rem",
        boxShadow:
          "0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)",
      },
      className:
        "dark:!bg-blue-950 dark:!border-blue-800 dark:!text-blue-100 [&>[data-description]]:!text-blue-800 dark:[&>[data-description]]:!text-blue-200",
    });
  },

  loading: (message: string) => {
    return toast.loading(message, {
      style: {
        background: "rgb(243 244 246)",
        border: "1px solid rgb(107 114 128)",
        color: "rgb(17 24 39)",
        borderRadius: "0.75rem",
        padding: "1rem",
        boxShadow:
          "0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)",
      },
      className:
        "dark:!bg-slate-950 dark:!border-slate-800 dark:!text-slate-100",
    });
  },
};

export const handleApiError = (error: unknown, context?: string) => {
  let title = "Something went wrong";
  let description = "";

  if (error instanceof Error) {
    // Try to parse the error message for HTTP status codes
    const statusMatch = error.message.match(/(\d{3})/);
    if (statusMatch) {
      const status = parseInt(statusMatch[1]);
      title = HTTP_ERROR_MESSAGES[status] || `HTTP ${status} Error`;
      description = context ? `Failed to ${context}` : "";
    } else {
      // Use the error message directly if it's not a status code
      title = error.message || title;
      description = context ? `Error during ${context}` : "";
    }
  } else if (typeof error === "string") {
    title = error;
    description = context ? `Failed to ${context}` : "";
  }

  showToast.error(title, {
    description,
  });
};

export const handleApiWarning = (message: string, context?: string) => {
  showToast.warning(message, {
    description: context ? `Warning during ${context}` : undefined,
  });
};

export const handleApiSuccess = (message: string, context?: string) => {
  showToast.success(message, {
    description: context ? `Successfully ${context}` : undefined,
  });
};
