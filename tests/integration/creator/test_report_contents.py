"""Creator CSV report journeys.

``download_data`` returns a zip of CSVs for a published plio. These specs
construct one deliberately tiny scenario and assert the *actual cell values* of
the downloaded CSVs against expectations worked out by hand from that scenario —
watch-time preserved exactly, submitted/correct answers re-indexed to 1-based,
the graded outcome — not merely that a file came back. The report is downloaded
by an org admin (admins see unmasked identifiers) so tenancy rides on the
``Organization`` header only; no spec touches ``connection.set_schema()``.
"""

import csv
import io
import zipfile

from tests.builders import in_workspace
from tests.factories import (
    EventFactory,
    ItemFactory,
    PlioFactory,
    QuestionFactory,
    SessionAnswerFactory,
    SessionFactory,
    UserFactory,
)
from users.models import OrganizationUser, Role


def _read_csv(archive, name):
    with archive.open(name) as handle:
        return list(csv.DictReader(io.TextIOWrapper(handle, encoding="utf-8")))


def test_downloaded_report_cells_match_the_constructed_scenario(authed_client, org_a):
    admin = authed_client()
    OrganizationUser.objects.create(
        user=admin.user,
        organization=org_a,
        role=Role.objects.get(name="org-admin"),
    )
    learner = UserFactory(email="reporter-learner@example.com")

    with in_workspace(org_a):
        plio = PlioFactory(
            created_by=admin.user,
            name="CSV report plio",
            published=True,
            video__url="https://www.youtube.com/watch?v=csvreport1",
            video__duration=120,
        )
        item = ItemFactory(plio=plio, time=5)
        QuestionFactory(
            item=item,
            type="mcq",
            text="Capital of France?",
            options=["Paris", "Rome", "Berlin"],
            correct_answer=0,  # option index 0 (1-based: 1) is correct
        )
        session = SessionFactory(plio=plio, user=learner, watch_time=42.5)
        # learner chose option index 1 (1-based: 2) -> wrong
        SessionAnswerFactory(session=session, item=item, answer=1)
        EventFactory(session=session, type="played", player_time=7)

    response = admin.get(
        "/api/v1/plios/{}/download_data/".format(plio.uuid), organization=org_a
    )
    assert response.status_code == 200

    archive = zipfile.ZipFile(io.BytesIO(b"".join(response.streaming_content)))

    # plio-meta-details.csv: identity of the exported plio
    meta = _read_csv(archive, "plio-meta-details.csv")
    assert len(meta) == 1
    assert meta[0]["id"] == plio.uuid
    assert meta[0]["name"] == "CSV report plio"
    assert meta[0]["video"] == "https://www.youtube.com/watch?v=csvreport1"

    # sessions.csv: watch time is preserved verbatim as 42.5 (not rounded to
    # 42 or 43), the identifier is unmasked to the learner's email, no SSO login
    sessions = _read_csv(archive, "sessions.csv")
    assert len(sessions) == 1
    assert sessions[0]["watch_time"] == "42.5"
    assert sessions[0]["user_identifier"] == "reporter-learner@example.com"
    assert sessions[0]["has_user_logged_in_via_sso"] == "false"

    # responses.csv: submitted answer re-indexed 1-based (0-based 1 -> 2) and
    # graded incorrect (chose option 2, correct is option 1)
    responses = _read_csv(archive, "responses.csv")
    assert len(responses) == 1
    assert responses[0]["answer"] == "2"
    assert responses[0]["is_answer_correct"] == "false"

    # plio-interaction-details.csv: correct answer re-indexed 1-based (0 -> 1)
    interactions = _read_csv(archive, "plio-interaction-details.csv")
    assert len(interactions) == 1
    assert interactions[0]["question_text"] == "Capital of France?"
    assert interactions[0]["question_correct_answer"] == "1"

    # events.csv: the single played event at player time 7.0
    events = _read_csv(archive, "events.csv")
    assert len(events) == 1
    assert events[0]["event_type"] == "played"
    assert events[0]["event_player_time"] == "7.0"
