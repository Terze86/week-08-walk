export type Role =
  | "case_scientist"
  | "screening_lab_officer"
  | "dna_lab_officer"
  | "reviewer"
  | "codis_scientist"
  | "lims_admin";

export const ROLE_LABELS: Record<Role, string> = {
  case_scientist: "Case Scientist",
  screening_lab_officer: "Screening Lab Officer",
  dna_lab_officer: "DNA Lab Officer",
  reviewer: "Reviewer",
  codis_scientist: "CODIS Scientist",
  lims_admin: "LIMS Admin",
};

export interface User {
  id: string;
  username: string;
  display_name: string;
  email: string | null;
  status: "active" | "disabled";
  roles: Role[];
  laboratory_ids: string[];
}

export interface Me extends User {
  workspaces: { key: string; title: string }[];
}

export interface AuditEvent {
  id: number;
  occurred_at: string;
  actor_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string;
  reason: string | null;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
}
