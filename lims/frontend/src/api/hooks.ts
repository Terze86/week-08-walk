import { useQuery } from "@tanstack/react-query";

import { api } from "./client";
import type { Client, Colleague, Laboratory, Location, Me } from "./types";

export const useMe = () => useQuery({ queryKey: ["me-cached"], queryFn: () => api<Me>("/me") });
export const useStaff = () =>
  useQuery({ queryKey: ["staff"], queryFn: () => api<Colleague[]>("/staff") });
export const useLocations = () =>
  useQuery({ queryKey: ["locations"], queryFn: () => api<Location[]>("/locations") });
export const useClients = () =>
  useQuery({ queryKey: ["clients"], queryFn: () => api<Client[]>("/clients") });
export const useLaboratories = () =>
  useQuery({ queryKey: ["laboratories"], queryFn: () => api<Laboratory[]>("/admin/laboratories") });

export function placeLabel(m: {
  to_person?: { display_name: string } | null;
  to_location?: { code: string } | null;
}): string {
  const parts = [m.to_person?.display_name, m.to_location?.code].filter(Boolean);
  return parts.join(" @ ") || "—";
}

export const fmt = (iso: string | null | undefined) => (iso ? new Date(iso).toLocaleString() : "");
