import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { AgentSummary } from "../api/types/agents";

function getDefaultAgent(): string {
  const stored = localStorage.getItem("copaw_default_agent");
  return stored || "default";
}

interface AgentStore {
  selectedAgent: string;
  agents: AgentSummary[];
  setSelectedAgent: (agentId: string) => void;
  setAgents: (agents: AgentSummary[]) => void;
  addAgent: (agent: AgentSummary) => void;
  removeAgent: (agentId: string) => void;
  updateAgent: (agentId: string, updates: Partial<AgentSummary>) => void;
}

export const useAgentStore = create<AgentStore>()(
  persist(
    (set) => ({
      selectedAgent: getDefaultAgent(),
      agents: [],

      setSelectedAgent: (agentId) => set({ selectedAgent: agentId }),

      setAgents: (agents) => set({ agents }),

      addAgent: (agent) =>
        set((state) => ({
          agents: [...state.agents, agent],
        })),

      removeAgent: (agentId) =>
        set((state) => {
          const newAgents = state.agents.filter((a) => a.id !== agentId);
          const fallback = getDefaultAgent();
          const newSelected = state.selectedAgent === agentId
            ? (newAgents.length > 0 ? newAgents[0].id : fallback)
            : state.selectedAgent;
          return { agents: newAgents, selectedAgent: newSelected };
        }),

      updateAgent: (agentId, updates) =>
        set((state) => ({
          agents: state.agents.map((a) =>
            a.id === agentId ? { ...a, ...updates } : a,
          ),
        })),
    }),
    {
      name: "copaw-agent-storage",
      storage: {
        getItem: (name) => {
          try {
            const value = sessionStorage.getItem(name);
            return value ? JSON.parse(value) : null;
          } catch (error) {
            console.error(`Failed to parse agent storage "${name}":`, error);
            // Remove corrupted data to prevent repeated errors
            sessionStorage.removeItem(name);
            return null;
          }
        },
        setItem: (name, value) => {
          try {
            sessionStorage.setItem(name, JSON.stringify(value));
          } catch (error) {
            console.error(`Failed to save agent storage "${name}":`, error);
          }
        },
        removeItem: (name) => {
          sessionStorage.removeItem(name);
        },
      },
    },
  ),
);
