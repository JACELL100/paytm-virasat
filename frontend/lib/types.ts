/** Shared domain types, mirroring the Supabase schema in Implementation Plan §9. */

export type AssetType =
  | "term_life"
  | "life_endowment"
  | "ulip"
  | "health"
  | "motor"
  | "fd"
  | "savings"
  | "mutual_fund"
  | "stocks"
  | "ppf"
  | "epf"
  | "nps"
  | "gold"
  | "loan"
  | "credit_card"
  | "other";

export type NomineeStatus = "ok" | "missing" | "outdated" | "unknown";
export type VaultState = "draft" | "active" | "challenge" | "released" | "revoked";
export type ClaimStatus =
  | "not_started"
  | "docs_pending"
  | "ready_to_file"
  | "filed"
  | "under_review"
  | "query_raised"
  | "settled"
  | "rejected"
  | "escalated";
export type TxStatus = "queued" | "sent" | "mined" | "failed";

export interface Profile {
  id: string;
  full_name: string | null;
  email: string;
  phone: string | null;
  language: "en" | "hi" | "mr";
  annual_income: number | null;
  wallet_address: string | null;
  roles: Array<"owner" | "nominee" | "guardian">;
}

export interface Asset {
  id: string;
  owner_id: string;
  type: AssetType;
  institution_id: string | null;
  institution_name?: string;
  label: string;
  account_ref_masked: string | null;
  value_estimate: number | null;
  premium_amount: number | null;
  frequency: "monthly" | "quarterly" | "yearly" | "one_time" | null;
  nominee_status: NomineeStatus;
  nominee_names: string[];
  source: "statement" | "sms" | "paytm_feed" | "manual" | "document";
  confidence: number | null;
  created_at: string;
}

export interface DiscoverySuggestion {
  id: string;
  source: "statement" | "sms" | "paytm_feed";
  status: "pending" | "accepted" | "rejected";
  payload: {
    label: string;
    type: AssetType;
    institution_name?: string;
    amount?: number;
    frequency?: string;
    confidence: number;
    rationale?: string;
  };
}

export interface DocumentRecord {
  id: string;
  asset_id: string | null;
  kind: "policy" | "statement" | "death_certificate" | "id_proof" | "other";
  status: "processing" | "extracted" | "needs_review" | "failed";
  extracted: Record<string, unknown> | null;
  created_at: string;
}

export interface Nominee {
  id: string;
  name: string;
  relation: string;
  email: string;
  phone?: string | null;
  share_bps: number;
  invite_status: "invited" | "accepted" | "declined";
  legacy_key_issued_at: string | null;
}

export interface Guardian {
  id: string;
  name: string;
  relation: string;
  email: string;
  status: "invited" | "accepted" | "declined";
  onchain_added: boolean;
}

export interface VaultTimelineEvent {
  id: string;
  event: string;
  tx_hash: string | null;
  block_number: number | null;
  occurred_at: string;
}

export interface Vault {
  id: string;
  chain_vault_id: number | null;
  state: VaultState;
  inactivity_secs: number;
  challenge_secs: number;
  threshold: number;
  epoch: number;
  challenge_ends_at: string | null;
  last_activity_at: string | null;
  last_heartbeat_onchain_at: string | null;
  nominees: Nominee[];
  guardians: Guardian[];
  timeline: VaultTimelineEvent[];
}

export interface Insights {
  legacy_score: number;
  score_breakdown: {
    nominee_coverage: number;
    guardians: number;
    documents: number;
    protection_adequacy: number;
    contact_freshness: number;
  };
  gaps: Array<{
    id: string;
    kind: "nominee_missing" | "coverage_gap" | "outdated_nominee" | "share_mismatch";
    title: string;
    detail: string;
    asset_id?: string;
    severity: "high" | "medium" | "low";
  }>;
  asset_totals_by_type: Partial<Record<AssetType, number>>;
  total_value: number;
}

export interface ActivityEvent {
  id: string;
  kind: "login" | "upi_payment" | "app_open";
  occurred_at: string;
  source: string;
}

export interface Claim {
  id: string;
  vault_id: string;
  asset_id: string;
  asset_label?: string;
  institution_name?: string;
  status: ClaimStatus;
  priority_score: number;
  checklist: Array<{ label: string; done: boolean }>;
  pack_path: string | null;
  filed_at: string | null;
  sla_due_at: string | null;
  claim_ref: string | null;
}

export interface ClaimEvent {
  id: string;
  status: ClaimStatus;
  note: string | null;
  tx_hash: string | null;
  occurred_at: string;
}

export interface VerifyResponse {
  token_id: string;
  valid: boolean;
  vault_id: number;
  released_at_block: number;
  released_at: string;
  share_bps: number;
  claim_events: Array<{ status: string; at: string; tx_hash: string }>;
}

export interface CopilotMessage {
  id: string;
  role: "user" | "assistant" | "tool";
  content: string;
  tool_cards?: Array<{ type: string; data: unknown }>;
  created_at: string;
}
