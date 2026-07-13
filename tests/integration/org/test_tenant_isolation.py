"""Tenant isolation across every entity type.

Data created inside org-a's workspace must be invisible under org-b's
``Organization`` header and under the personal workspace (no header). Every
entity in the Plio graph and the learner-entries graph is covered. Invisibility
is observed only through the API -- a detail read returns 200 in org-a and 404
elsewhere -- never through ORM queries.
"""
import pytest

from tests.builders import in_workspace
from tests.factories import (
    EventFactory,
    ImageFactory,
    ItemFactory,
    PlioFactory,
    QuestionFactory,
    SessionAnswerFactory,
    SessionFactory,
)

# The eight entity types the isolation guarantee must hold for.
ENTITY_TYPES = [
    "plio",
    "video",
    "item",
    "question",
    "image",
    "session",
    "session-answer",
    "event",
]


@pytest.fixture
def org_a_entities(creator, org_a):
    """One instance of every entity type, all created inside org-a's schema.

    Returns a mapping of entity type to its API detail path. The plio is public
    and the session belongs to ``creator`` so that the org-a read is a genuine
    200 (the positive control) rather than an access denial.
    """
    with in_workspace(org_a):
        plio = PlioFactory(created_by=creator.user, is_public=True)
        video = plio.video
        item = ItemFactory(plio=plio)
        question = QuestionFactory(item=item)
        image = ImageFactory()
        session = SessionFactory(user=creator.user, plio=plio)
        answer = SessionAnswerFactory(session=session, item=item)
        event = EventFactory(session=session)

    return {
        "plio": "/api/v1/plios/{}/".format(plio.uuid),
        "video": "/api/v1/videos/{}/".format(video.id),
        "item": "/api/v1/items/{}/".format(item.id),
        "question": "/api/v1/questions/{}/".format(question.id),
        "image": "/api/v1/images/{}/".format(image.id),
        "session": "/api/v1/sessions/{}/".format(session.id),
        "session-answer": "/api/v1/session-answers/{}/".format(answer.id),
        "event": "/api/v1/events/{}/".format(event.id),
    }


@pytest.mark.parametrize("entity_type", ENTITY_TYPES, ids=ENTITY_TYPES)
def test_org_a_entity_is_isolated_from_org_b_and_personal_workspace(
    entity_type, org_a_entities, creator, org_a, org_b
):
    path = org_a_entities[entity_type]

    # positive control: visible in the workspace it was created in
    assert creator.get(path, organization=org_a).status_code == 200
    # invisible under another org's header
    assert creator.get(path, organization=org_b).status_code == 404
    # invisible in the personal workspace (no Organization header)
    assert creator.get(path).status_code == 404
