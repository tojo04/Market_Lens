const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly requestId: string | null = null,
    public readonly fallbackAvailable = false,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    let code = "request_failed";
    let message = `Request failed with status ${response.status}`;
    let requestId: string | null = null;
    let fallbackAvailable = false;
    try {
      const payload = (await response.json()) as {
        error?: {
          code?: string;
          message?: string;
          request_id?: string | null;
          fallback_available?: boolean;
        };
      };
      code = payload.error?.code ?? code;
      message = payload.error?.message ?? message;
      requestId = payload.error?.request_id ?? null;
      fallbackAvailable = payload.error?.fallback_available ?? false;
    } catch {
      // A typed fallback is retained when the server does not return valid JSON.
    }
    throw new ApiError(response.status, code, message, requestId, fallbackAvailable);
  }
  return (await response.json()) as T;
}
