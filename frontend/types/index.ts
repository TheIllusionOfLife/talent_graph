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
