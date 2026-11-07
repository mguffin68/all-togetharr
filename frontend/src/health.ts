import { useQuery } from "@tanstack/react-query";

export interface HealthData {
  status: string;
  version: string;
}

export function useHealth() {
  return useQuery<HealthData, Error>({
    queryKey: ["health"],
    queryFn: async ({ signal }) => {
      const res = await fetch("/api/health", { signal });
      if (!res.ok) {
        throw new Error("API error");
      }
      return res.json();
    },
  });
}
