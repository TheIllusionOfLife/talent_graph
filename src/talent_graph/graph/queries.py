"""Cypher query constants and builders."""

# ─── Constraints (run once at startup) ────────────────────────────────────────

CONSTRAINTS = [
    "CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.person_id IS UNIQUE",
    "CREATE CONSTRAINT paper_id IF NOT EXISTS FOR (p:Paper) REQUIRE p.openalex_work_id IS UNIQUE",
    "CREATE CONSTRAINT repo_id IF NOT EXISTS FOR (r:Repo) REQUIRE r.full_name IS UNIQUE",
    "CREATE CONSTRAINT concept_id IF NOT EXISTS FOR (c:Concept) REQUIRE c.openalex_concept_id IS UNIQUE",
    "CREATE CONSTRAINT org_id IF NOT EXISTS FOR (o:Org) REQUIRE o.openalex_institution_id IS UNIQUE",
]

# ─── Node upserts (MERGE — idempotent) ────────────────────────────────────────

MERGE_PERSON = """
MERGE (p:Person {person_id: $person_id})
SET p.name = $name,
    p.openalex_author_id = $openalex_author_id,
    p.github_login = $github_login,
    p.orcid = $orcid,
    p.updated_at = timestamp()
RETURN p.person_id AS person_id
"""

MERGE_PAPER = """
MERGE (p:Paper {openalex_work_id: $openalex_work_id})
SET p.paper_id = $paper_id,
    p.title = $title,
    p.publication_year = $publication_year,
    p.citation_count = $citation_count,
    p.updated_at = timestamp()
RETURN p.openalex_work_id AS openalex_work_id
"""

MERGE_CONCEPT = """
MERGE (c:Concept {openalex_concept_id: $openalex_concept_id})
SET c.concept_id = $concept_id,
    c.name = $name,
    c.level = $level,
    c.updated_at = timestamp()
RETURN c.openalex_concept_id AS openalex_concept_id
"""

MERGE_ORG = """
MERGE (o:Org {openalex_institution_id: $openalex_institution_id})
SET o.org_id = $org_id,
    o.name = $name,
    o.updated_at = timestamp()
RETURN o.openalex_institution_id AS openalex_institution_id
"""

MERGE_REPO = """
MERGE (r:Repo {full_name: $full_name})
SET r.repo_id = $repo_id,
    r.description = $description,
    r.language = $language,
    r.stars = $stars,
    r.updated_at = timestamp()
RETURN r.full_name AS full_name
"""

# ─── Relationship upserts ──────────────────────────────────────────────────────

MERGE_AUTHORED = """
MATCH (person:Person {person_id: $person_id})
MATCH (paper:Paper {openalex_work_id: $openalex_work_id})
MERGE (person)-[r:AUTHORED]->(paper)
SET r.author_position = $author_position,
    r.is_corresponding = $is_corresponding
"""

MERGE_PAPER_ABOUT_CONCEPT = """
MATCH (paper:Paper {openalex_work_id: $openalex_work_id})
MATCH (concept:Concept {openalex_concept_id: $openalex_concept_id})
MERGE (paper)-[r:ABOUT]->(concept)
SET r.score = $score
"""

MERGE_AFFILIATED = """
MATCH (person:Person {person_id: $person_id})
MATCH (org:Org {openalex_institution_id: $openalex_institution_id})
MERGE (person)-[:AFFILIATED_WITH]->(org)
"""

MERGE_COAUTHORED = """
MATCH (a:Person {person_id: $person_id_a})
MATCH (b:Person {person_id: $person_id_b})
MERGE (a)-[r:COAUTHORED_WITH]->(b)
SET r.paper_count = coalesce(r.paper_count, 0) + 1
"""
