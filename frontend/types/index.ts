// Shared TypeScript types mirroring backend Pydantic schemas

export interface SearchResult {
	id: string;
	name: string;
	score: number;
}

export interface SearchResponse {
	query: string;
	results: SearchResult[];
}

export interface ScoreBreakdown {
	semantic_similarity: number;
	graph_proximity: number;
	novelty: number;
	growth: number;
	evidence_quality: number;
	credibility: number;
}

export interface CandidateResult {
	id: string;
	name: string;
	score: number;
	breakdown: ScoreBreakdown;
	hop_distance: number;
	explanation: string | null;
}

export interface DiscoveryResponse {
	seed_entity_type: string;
	seed_entity_id: string;
	mode: string;
	candidates: CandidateResult[];
}

export interface OrgOut {
	id: string;
	name: string;
	country_code: string | null;
	type: string | null;
}

export interface PaperOut {
	id: string;
	title: string;
	publication_year: number | null;
	citation_count: number;
	concepts: string[];
}

export interface RepoOut {
	id: string;
	full_name: string;
	description: string | null;
	language: string | null;
	stars: number;
	topics: string[];
}

export interface PersonDetail {
	id: string;
	name: string;
	openalex_author_id: string | null;
	github_login: string | null;
	orcid: string | null;
	email: string | null;
	homepage: string | null;
	hidden_expert_score: number | null;
	org: OrgOut | null;
	papers: PaperOut[];
	repos: RepoOut[];
}

export type RankMode = "standard" | "hidden" | "emerging";

export interface EvidenceItem {
	type: "paper" | "repo" | "org";
	label: string;
	detail: string | null;
}

export interface PersonBrief {
	person_id: string;
	explanation: string;
	evidence: EvidenceItem[];
	fallback: boolean;
}

export interface ShortlistItemOut {
	person_id: string;
	note: string | null;
	position: number;
	added_at: string;
	person: {
		id: string;
		name: string;
		openalex_author_id: string | null;
		github_login: string | null;
	} | null;
}

export interface ShortlistOut {
	id: string;
	name: string;
	description: string | null;
	created_at: string;
	updated_at: string;
	items: ShortlistItemOut[];
}

export interface ShortlistItemUpdate {
	note?: string | null;
	position?: number | null;
}

export interface ShortlistSummary {
	id: string;
	name: string;
	description: string | null;
	created_at: string;
	item_count: number;
}

export interface AdminStats {
	person_count: number;
	paper_count: number;
	repo_count: number;
	pending_entity_links: number;
}

export type EntityLinkStatus = "pending" | "merged" | "rejected";

export interface EntityLinkOut {
	id: string;
	person_id_a: string;
	person_id_b: string;
	confidence: number;
	method: string;
	status: EntityLinkStatus;
	created_at: string;
}

export interface EntityLinkPage {
	items: EntityLinkOut[];
	total: number;
	page: number;
	page_size: number;
}

export interface SavedSearchOut {
	id: string;
	name: string;
	query: string;
	filters: Record<string, unknown> | null;
	created_at: string;
	last_run_at: string | null;
}

// ── Graph visualization ──────────────────────────────────────────────────

export interface GraphNode {
	id: string; // compound: "person__abc123"
	type: string; // "Person", "Paper", "Repo", "Concept", "Org"
	label: string;
	metadata: Record<string, unknown>;
}

export interface GraphLink {
	source: string; // GraphNode.id
	target: string;
	type: string; // "AUTHORED", "ABOUT", etc.
}

export interface EgoGraphResponse {
	center_id: string;
	nodes: GraphNode[];
	links: GraphLink[];
	truncated: boolean;
}

// ── Lookalike discovery ──────────────────────────────────────────────────

export interface LookalikeResult {
	id: string;
	name: string;
	similarity: number;
}

export interface LookalikeResponse {
	person_id: string;
	results: LookalikeResult[];
}
