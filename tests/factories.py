"""Factory-boy factories for test data.

Uses factory.Factory (not SQLAlchemyModelFactory) to remain sync-safe with
async SQLAlchemy sessions.
"""

import factory
from factory import LazyFunction, Sequence

from talent_graph.storage.id_gen import new_id
from talent_graph.storage.models import (
    Concept,
    EntityLink,
    Org,
    Paper,
    Person,
    Shortlist,
    ShortlistItem,
)


class OrgFactory(factory.Factory):
    class Meta:
        model = Org

    id = LazyFunction(lambda: f"org_{new_id()}")
    name = Sequence(lambda n: f"Test Org {n}")
    country_code = "US"
    type = "education"
    openalex_institution_id = None
    github_org_login = None
    raw_metadata = None


class PersonFactory(factory.Factory):
    class Meta:
        model = Person

    id = LazyFunction(lambda: f"p_{new_id()}")
    name = Sequence(lambda n: f"Test Person {n}")
    openalex_author_id = None
    github_login = None
    orcid = None
    email = None
    homepage = None
    org_id = None
    raw_metadata = None
    hidden_expert_score = None
    embedding = None


class ConceptFactory(factory.Factory):
    class Meta:
        model = Concept

    id = LazyFunction(lambda: f"concept_{new_id()}")
    name = Sequence(lambda n: f"Test Concept {n}")
    openalex_concept_id = None
    wikidata_id = None
    level = None


class PaperFactory(factory.Factory):
    class Meta:
        model = Paper

    id = LazyFunction(lambda: f"paper_{new_id()}")
    title = Sequence(lambda n: f"Test Paper {n}")
    openalex_work_id = None
    doi = None
    publication_year = 2023
    citation_count = 10
    abstract = None
    concepts: list[str] = []
    raw_metadata = None


class EntityLinkFactory(factory.Factory):
    class Meta:
        model = EntityLink

    id = LazyFunction(lambda: f"el_{new_id()}")
    # person_id_a and person_id_b must be set by caller; constraint requires a < b
    person_id_a = None
    person_id_b = None
    confidence = 0.75
    method = "heuristic"
    status = "pending"


class ShortlistFactory(factory.Factory):
    class Meta:
        model = Shortlist

    id = LazyFunction(lambda: f"sl_{new_id()}")
    name = Sequence(lambda n: f"Test Shortlist {n}")
    description = None
    owner_key = "default_owner_hash"


class ShortlistItemFactory(factory.Factory):
    class Meta:
        model = ShortlistItem

    # shortlist_id and person_id must be set by caller
    shortlist_id = None
    person_id = None
    note = None
    position = 0
