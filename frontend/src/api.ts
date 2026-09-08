const BASE =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export const token = (): string => {
  return localStorage.getItem("token") || "";
};

export async function api(
  path: string,
  options: RequestInit = {}
): Promise<any> {
  const headers = new Headers(options.headers);
  const currentToken = token();

  if (currentToken) {
    headers.set("Authorization", `Bearer ${currentToken}`);
  }

  if (!(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;

  try {
    response = await fetch(`${BASE}${path}`, {
      ...options,
      headers
    });
  } catch {
    throw new Error(
      `Cannot reach the backend at ${BASE}. Start FastAPI and check VITE_API_URL.`
    );
  }

  const data = await response
    .json()
    .catch(() => ({ detail: response.statusText }));

  if (!response.ok) {
    throw new Error(
      data.detail || `Request failed (${response.status})`
    );
  }

  return data;
}

export { BASE };