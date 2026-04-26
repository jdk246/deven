const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim() || "";
const useDevProxy = import.meta.env.DEV && !configuredApiBaseUrl;

const defaultApiBaseUrl =
  typeof window !== "undefined" && window.location.hostname === "127.0.0.1"
    ? "http://127.0.0.1:8000"
    : "http://localhost:8000";

function normalizeLoopbackBaseUrl(rawValue: string) {
  const trimmed = rawValue.trim();

  if (!trimmed) {
    return defaultApiBaseUrl;
  }

  try {
    const parsed = new URL(trimmed);
    const frontendHostname =
      typeof window !== "undefined" ? window.location.hostname : "";

    if (frontendHostname === "127.0.0.1" && parsed.hostname === "localhost") {
      parsed.hostname = "127.0.0.1";
      return parsed.toString().replace(/\/$/, "");
    }

    if (frontendHostname === "localhost" && parsed.hostname === "127.0.0.1") {
      parsed.hostname = "localhost";
      return parsed.toString().replace(/\/$/, "");
    }

    return parsed.toString().replace(/\/$/, "");
  } catch {
    return trimmed;
  }
}

export const apiBaseUrl = normalizeLoopbackBaseUrl(
  configuredApiBaseUrl || defaultApiBaseUrl,
);

export const apiFetchBaseUrl = useDevProxy ? "" : apiBaseUrl;
