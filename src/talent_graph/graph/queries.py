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
SET r.updated_at = timestamp()
"""

# ─── Batch upserts (UNWIND — reduces N+1 round trips) ─────────────────────────

MERGE_CONCEPTS_BATCH = """
UNWIND $concepts AS c
MERGE (concept:Concept {openalex_concept_id: c.openalex_concept_id})
SET concept.concept_id = c.openalex_concept_id,
    concept.name = c.name,
    concept.level = c.level,
    concept.updated_at = timestamp()
"""

MERGE_PAPER_ABOUT_CONCEPTS_BATCH = """
UNWIND $concepts AS c
MATCH (paper:Paper {openalex_work_id: $openalex_work_id})
MATCH (concept:Concept {openalex_concept_id: c.openalex_concept_id})
MERGE (paper)-[r:ABOUT]->(concept)
SET r.score = c.score
"""

MERGE_ORGS_BATCH = """
UNWIND $orgs AS o
MERGE (org:Org {openalex_institution_id: o.openalex_institution_id})
SET org.org_id = o.openalex_institution_id,
    org.name = o.name,
    org.updated_at = timestamp()
"""

MERGE_PERSONS_AND_AFFILIATED_BATCH = """
UNWIND $authors AS a
MERGE (person:Person {person_id: a.person_id})
SET person.name = a.name,
    person.openalex_author_id = a.openalex_author_id,
    person.github_login = a.github_login,
    person.orcid = a.orcid,
    person.updated_at = timestamp()
WITH person, a
WHERE a.openalex_institution_id IS NOT NULL
MATCH (org:Org {openalex_institution_id: a.openalex_institution_id})
MERGE (person)-[:AFFILIATED_WITH]->(org)
"""

MERGE_AUTHORED_BATCH = """
UNWIND $authors AS a
MATCH (person:Person {person_id: a.person_id})
MATCH (paper:Paper {openalex_work_id: $openalex_work_id})
MERGE (person)-[r:AUTHORED]->(paper)
SET r.author_position = a.author_position,
    r.is_corresponding = a.is_corresponding
"""

MERGE_COAUTHORED_BATCH = """
UNWIND $coauthors AS pair
MATCH (a:Person {person_id: pair.person_id_a})
MATCH (b:Person {person_id: pair.person_id_b})
MERGE (a)-[r:COAUTHORED_WITH]->(b)
SET r.updated_at = timestamp()
"""

MERGE_REPO = """
MERGE (r:Repo {full_name: $full_name})
SET r.github_repo_id = $github_repo_id,
    r.description = $description,
    r.language = $language,
    r.stars = $stars,
    r.topics = $topics,
    r.updated_at = timestamp()
RETURN r.full_name AS full_name
"""

MERGE_PERSONS_BASIC_BATCH = """
UNWIND $persons AS p
MERGE (person:Person {person_id: p.person_id})
SET person.name = p.name,
    person.github_login = p.github_login,
    person.updated_at = timestamp()
"""

MERGE_CONTRIBUTED_TO_BATCH = """
UNWIND $contributors AS c
MATCH (person:Person {person_id: c.person_id})
MATCH (repo:Repo {full_name: $full_name})
MERGE (person)-[r:CONTRIBUTED_TO]->(repo)
SET r.contributions = c.contributions,
    r.updated_at = timestamp()
"""

# ─── Inferred edge upserts ───────────────────────────────────────────────────

MERGE_SIMILAR_TO_BATCH = """
UNWIND $pairs AS p
MATCH (a:Person {person_id: p.person_id_a})
MATCH (b:Person {person_id: p.person_id_b})
MERGE (a)-[r:SIMILAR_TO]->(b)
SET r.similarity = p.similarity,
    r.source = 'inferred',
    r.updated_at = timestamp()
"""

MERGE_LIKELY_EXPERT_IN_BATCH = """
UNWIND $edges AS e
MATCH (person:Person {person_id: e.person_id})
MATCH (concept:Concept {openalex_concept_id: e.concept_id})
MERGE (person)-[r:LIKELY_EXPERT_IN]->(concept)
SET r.paper_count = e.paper_count,
    r.source = 'inferred',
    r.updated_at = timestamp()
"""
