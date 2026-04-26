import { apiFetchBaseUrl } from "../lib/env";

export type HealthResponse = {
  status: string;
};

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${apiFetchBaseUrl}/health`);

  if (!response.ok) {
    throw new Error(`Backend request failed with status ${response.status}`);
  }

  return response.json() as Promise<HealthResponse>;
}
