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

export interface Person {
  id: string;
  display_name: string;
}

export interface Colleague extends Person {
  roles: Role[];
}

export interface Client {
  id: string;
  code: string;
  name: string;
  active: boolean;
}

export type LocationKind = "storage" | "bench" | "instrument" | "transit" | "disposal";

export interface Location {
  id: string;
  code: string;
  name: string;
  kind: LocationKind;
  laboratory_id: string;
  active: boolean;
}

export interface Laboratory {
  id: string;
  code: string;
  name: string;
}

export interface CaseSummary {
  id: string;
  case_number: string;
  client_reference: string;
  state: "open" | "closed";
  created_at: string;
}

export interface Case extends CaseSummary {
  laboratory_id: string;
  client_id: string;
  source: "paper" | "electronic";
  submission_reference: string | null;
  submitter_name: string;
  submitter_contact: string | null;
  investigating_officer_name: string;
  investigating_officer_contact: string | null;
  case_information: string | null;
}

export interface Subcase {
  id: string;
  subcase_number: string;
  case_id: string;
  state: "open" | "closed";
  created_at: string;
  case_scientist: Person | null;
}

export interface CaseDetail {
  case: Case;
  subcases: Subcase[];
}

export type ExhibitState = "submitted" | "accepted" | "rejected" | "received";

export interface Exhibit {
  id: string;
  barcode: string;
  subcase_id: string;
  submitter_item_ref: string | null;
  description: string;
  marking: string | null;
  seal: string | null;
  state: ExhibitState;
  description_matches: boolean | null;
  marking_matches: boolean | null;
  seal_intact: boolean | null;
  check_notes: string | null;
  rejection_reason: string | null;
  receipt_id: string | null;
  examiner: Person | null;
}

export type ReceiptState = "draft" | "completed" | "exception" | "cancelled";
export type ExceptionKind = "submitter_refused" | "signature_failed" | "handover_other";

export interface ReceiptSummary {
  id: string;
  receipt_number: string;
  subcase_id: string;
  state: ReceiptState;
  created_at: string;
  completed_at: string | null;
  exception_kind: ExceptionKind | null;
  exception_note: string | null;
}

export interface Receipt extends ReceiptSummary {
  actual_submitter_name: string | null;
  prepared_by: Person | null;
  receiving_staff: Person | null;
  has_signature: boolean;
  accepted_exhibits: Exhibit[];
  rejected_exhibits: Exhibit[];
}

export interface Place {
  id: string;
  code: string;
  name: string;
}

export interface Movement {
  id: string;
  kind: "receipt" | "move" | "handover" | "correction";
  from_person: Person | null;
  from_location: Place | null;
  to_person: Person | null;
  to_location: Place | null;
  moved_at: string;
  recorded_at: string;
  recorded_by: Person | null;
  note: string | null;
}

export interface CustodyEntry {
  movement: Movement;
  original: Movement | null;
  corrections: Movement[];
}

export interface Item {
  id: string;
  barcode: string;
  kind: "exhibit" | "sample" | "material";
  label: string;
  subcase_id: string;
  current: Movement | null;
  history: CustodyEntry[];
}

export interface Handover {
  id: string;
  from_person: Person | null;
  note: string | null;
  created_at: string;
  items: { id: string; barcode: string; label: string }[];
}

export interface Correction {
  id: string;
  state: "requested" | "authorized" | "declined";
  barcode: string;
  reason: string;
  requested_by: Person | null;
  original: Movement;
  to_person: Person | null;
  to_location: Place | null;
  moved_at: string;
}

export interface MyWork {
  subcases: Subcase[];
  examinations: Exhibit[];
  incoming_handovers: Handover[];
  receipt_exceptions: ReceiptSummary[];
  corrections_to_decide: Correction[];
}
