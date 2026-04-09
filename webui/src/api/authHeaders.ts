import { getApiToken } from "./config";

function getSelectedAgentForHeader(): string | null {
  try {
    const agentStorage = sessionStorage.getItem("copaw-agent-storage");
    if (agentStorage) {
      const parsed = JSON.parse(agentStorage);
      const selectedAgent = parsed?.state?.selectedAgent;
      if (selectedAgent) {
        return selectedAgent;
      }
    }
  } catch (error) {
    console.warn("Failed to get selected agent from sessionStorage:", error);
  }
  
  try {
    const defaultAgent = localStorage.getItem("copaw_default_agent");
    if (defaultAgent) {
      return defaultAgent;
    }
  } catch (error) {
    console.warn("Failed to get default agent from localStorage:", error);
  }
  
  return "default";
}

/** Authorization + X-Agent-Id for API requests. Caller sets Content-Type when needed. */
export function buildAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  const token = getApiToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  
  const selectedAgent = getSelectedAgentForHeader();
  if (selectedAgent) {
    headers["X-Agent-Id"] = selectedAgent;
  }
  
  return headers;
}
