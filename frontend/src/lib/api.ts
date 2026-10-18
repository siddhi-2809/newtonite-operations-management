const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(status: number, message: string, data?: any) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

export function generateIdempotencyKey(action: string): string {
  return `${action}-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

export async function fetchApi<T>(
  endpoint: string,
  options: RequestInit & { idempotencyKey?: string } = {}
): Promise<T> {
  const { idempotencyKey, headers = {}, ...customConfig } = options;

  const defaultHeaders: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (typeof window !== "undefined") {
    const token = localStorage.getItem("newtonite_token");
    if (token) {
      defaultHeaders["Authorization"] = `Bearer ${token}`;
    }
  }

  if (idempotencyKey) {
    defaultHeaders["Idempotency-Key"] = idempotencyKey;
  }

  const url = `${API_BASE_URL}${endpoint}`;

  const response = await fetch(url, {
    headers: {
      ...defaultHeaders,
      ...(headers as Record<string, string>),
    },
    ...customConfig,
  });

  if (response.status === 204) {
    return {} as T;
  }

  let data: any = null;
  const contentType = response.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) {
    data = await response.json();
  } else {
    data = await response.text();
  }

  if (!response.ok) {
    let errorMessage = "An error occurred during the request.";
    if (typeof data === "object" && data !== null) {
      if (typeof data.detail === "string") {
        errorMessage = data.detail;
      } else if (Array.isArray(data.detail)) {
        errorMessage = data.detail.map((err: any) => err.msg || JSON.stringify(err)).join("; ");
      } else if (data.message) {
        errorMessage = data.message;
      }
    }

    if (response.status === 401 && typeof window !== "undefined") {
      // Token invalid or expired
      localStorage.removeItem("newtonite_token");
      localStorage.removeItem("newtonite_user");
      if (!window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
    }

    throw new ApiError(response.status, errorMessage, data);
  }

  return data as T;
}
