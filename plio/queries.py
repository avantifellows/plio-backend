from typing import Tuple


def get_plio_latest_sessions_query(plio_uuid: str, schema: str):
    """Returns the most recent sessions for each user for the given plio

    :param plio_uuid: The plio to fetch the details for
    :type plio_uuid: str
    :param schema: The schema from which the tables are to be accessed
    :type schema: str
    """
    return f"""
        WITH summary AS (
            SELECT
                session.id,
                plio.uuid as plio_uuid,
                session.watch_time,
                session.retention,
                ROW_NUMBER() OVER(PARTITION BY session.user_id, session.plio_id
                 ORDER BY session.id DESC) AS rank
            FROM {schema}.session
            INNER JOIN {schema}.plio AS plio ON plio.id = session.plio_id
        )
        SELECT id, watch_time, retention
        FROM summary
        WHERE rank = 1 AND plio_uuid = '{plio_uuid}'"""


def get_plio_latest_responses_query(schema: str, session_ids: Tuple[int]):
    """
    Returns the responses of each user to the given plio based on
    their most recent session.

    :param schema: The schema from which the tables are to be accessed
    :type schema: str
    :param session_ids: The database ids corresponding to the most recent session by each user
    :type session_ids: Tuple[int]
    """
    query = f"""
        SELECT
            sessionAnswer.id,
            session.user_id,
            sessionAnswer.answer,
            item.type AS item_type,
            question.type AS question_type,
            question.correct_answer AS question_correct_answer,
            question.survey AS survey
        FROM {schema}.session AS session
        INNER JOIN {schema}.session_answer AS sessionAnswer
        ON session.id = sessionAnswer.session_id
        INNER JOIN {schema}.item AS item
        ON item.id=sessionAnswer.item_id
        INNER JOIN {schema}.question AS question ON question.item_id = item.id """

    # for some reason, when there is only one id, we cannot use the
    # tuple form and have to resort to equality
    if len(session_ids) == 1:
        query += f"WHERE session.id = {session_ids[0]}"
    else:
        query += f"WHERE session.id IN {session_ids}"

    return query


def get_plio_details_query(plio_uuid: str, schema: str, **kwargs):
    """
    Returns the details for the given plio

    :param plio_uuid: The plio to fetch the details for
    :type plio_uuid: str
    :param schema: The schema from which the tables are to be accessed
    :type schema: str
    """
    return f"""
        SELECT
            item.id AS item_id,
            item.type AS item_type,
            item.time AS item_time,
            question.type AS question_type,
            question.text AS question_text,
            question.options AS question_options,
            question.correct_answer AS question_correct_answer
        FROM {schema}.plio AS plio
        INNER JOIN {schema}.item AS item ON item.plio_id = plio.id
        INNER JOIN {schema}.question AS question ON question.item_id = item.id
        WHERE plio.uuid  = '{plio_uuid}'"""


def get_sessions_dump_query(
    plio_uuid: str, schema: str, show_unmasked_user_id: bool = True
):
    """
    Returns the dump of all the sessions for the given plio

    :param plio_uuid: The plio to fetch the details for
    :type plio_uuid: str
    :param schema: The schema from which the tables are to be accessed
    :type schema: str
    :param show_unmasked_user_id: whether the user id should be masked, defaults to True
    :type show_unmasked_user_id: bool
    """
    return f"""
        SELECT
            session.id as session_id,
            session.watch_time,
            CASE
                WHEN {str(show_unmasked_user_id).lower()} THEN COALESCE(users.email, users.mobile, users.unique_id)
            ELSE
                {'MD5(session.user_id::varchar(255))'}
            END AS user_identifier,
            CASE
                WHEN users.unique_id IS NOT NULL AND users.auth_org_id IS NOT NULL THEN 'true'
                ELSE 'false'
            END AS has_user_logged_in_via_sso,
            session.created_at,
            session.updated_at as last_updated_at
        FROM {schema}.session AS session
        INNER JOIN {schema}.plio AS plio ON plio.id = session.plio_id
        INNER JOIN public.user AS users ON session.user_id = users.id
        WHERE plio.uuid  = '{plio_uuid}'"""


def get_responses_dump_query(
    plio_uuid: str, schema: str, show_unmasked_user_id: bool = True
):
    """
    Returns the dump of all the session responses for the given plio

    :param plio_uuid: The plio to fetch the details for
    :type plio_uuid: str
    :param schema: The schema from which the tables are to be accessed
    :type schema: str
    :param mask_useshow_unmasked_user_idr_id: whether the user id should be masked, defaults to True
    :type show_unmasked_user_id: bool
    """
    return f"""
        SELECT
            session.id as session_id,
            CASE
                WHEN {str(show_unmasked_user_id).lower()} THEN COALESCE(users.email, users.mobile, users.unique_id)
            ELSE
                {'MD5(session.user_id::varchar(255))'}
            END AS user_identifier,
            CASE
                WHEN users.unique_id IS NOT NULL AND users.auth_org_id IS NOT NULL THEN 'true'
                ELSE 'false'
            END AS has_user_logged_in_via_sso,
            sessionAnswer.answer,
            sessionAnswer.item_id,
            question.type as question_type,
            question.correct_answer as correct_answer,
            CASE
                WHEN sessionAnswer.answer IS NOT NULL AND sessionAnswer.answer = question.correct_answer THEN 'true'
                ELSE 'false'
            END AS is_answer_correct,
            sessionAnswer.created_at as answered_at
        FROM {schema}.session AS session
        INNER JOIN {schema}.session_answer sessionAnswer ON session.id = sessionAnswer.session_id
        INNER JOIN {schema}.plio AS plio ON plio.id = session.plio_id
        INNER JOIN public.user AS users ON session.user_id = users.id
        INNER JOIN {schema}.item item ON item.id = sessionAnswer.item_id
        INNER JOIN {schema}.question question ON question.item_id = item.id
        WHERE plio.uuid  = '{plio_uuid}'"""


def get_events_query(plio_uuid: str, schema: str, show_unmasked_user_id: bool = True):
    """
    Returns the dump of all events across all sessions for the given plio

    :param plio_uuid: The plio to fetch the details for
    :type plio_uuid: str
    :param schema: The schema from which the tables are to be accessed
    :type schema: str
    :param show_unmasked_user_id: whether the user id should be masked, defaults to True
    :type show_unmasked_user_id: bool
    """
    return f"""
        SELECT
            session.id as session_id,
            CASE
                WHEN {str(show_unmasked_user_id).lower()} THEN COALESCE(users.email, users.mobile, users.unique_id)
            ELSE
                {'MD5(session.user_id::varchar(255))'}
            END AS user_identifier,
            CASE
                WHEN users.unique_id IS NOT NULL AND users.auth_org_id IS NOT NULL THEN 'true'
                ELSE 'false'
            END AS has_user_logged_in_via_sso,
            event.type AS event_type,
            event.player_time AS event_player_time,
            event.details AS event_details,
            event.created_at AS event_global_time
        FROM {schema}.session AS session
        INNER JOIN {schema}.event AS event ON session.id = event.session_id
        INNER JOIN {schema}.plio AS plio ON plio.id = session.plio_id
        INNER JOIN public.user AS users ON session.user_id = users.id
        WHERE plio.uuid  = '{plio_uuid}'"""


def get_user_level_metrics_query(
    plio_uuid: str, schema: str, show_unmasked_user_id: bool = True
):
    """
    Returns data for each user for the given plio. These include
    - The user's identifier
    - Whether the user has logged in via SSO
    - Number of questions attempted by the user
    - Number of questions answered correctly by the user
    - Number of questions answered incorrectly by the user
    - Number of questions skipped by the user
    - Has the user attempted all the questions?
    - Has the user answered all the questions correctly?

    :param plio_uuid: The plio to fetch the details for
    :type plio_uuid: str
    :param schema: The schema from which the tables are to be accessed
    :type schema: str
    :param show_unmasked_user_id: whether the user id should be masked, defaults to True
    :type show_unmasked_user_id: bool
    """

    return f"""
        WITH summary AS (
            SELECT
                session.id as session_id,
                CASE
                    WHEN {str(show_unmasked_user_id).lower()} THEN COALESCE(users.email, users.mobile, users.unique_id)
                ELSE
                    {'MD5(session.user_id::varchar(255))'}
                END AS user_identifier,
                CASE
                    WHEN users.unique_id IS NOT NULL AND users.auth_org_id IS NOT NULL THEN 'true'
                    ELSE 'false'
                END AS has_user_logged_in_via_sso,
                sessionAnswer.answer,
                sessionAnswer.item_id,
                question.type as question_type,
                sessionAnswer.created_at as answered_at
            FROM {schema}.session AS session
            INNER JOIN {schema}.session_answer sessionAnswer ON session.id = sessionAnswer.session_id
            INNER JOIN {schema}.plio AS plio ON plio.id = session.plio_id
            INNER JOIN public.user AS users ON session.user_id = users.id
            INNER JOIN {schema}.item item ON item.id = sessionAnswer.item_id
            INNER JOIN {schema}.question question ON question.item_id = item.id
            WHERE plio.uuid  = '{plio_uuid}'
        ),
        latestSession AS (
            SELECT user_identifier, MAX (session_id) AS latest_session_id
            FROM summary
            GROUP BY user_identifier
        ),
        totalQuestions AS (
            SELECT COUNT(DISTINCT item_id) AS total_questions
            FROM summary
            WHERE session_id = (SELECT MAX(session_id) FROM summary) -- assuming latest session for any user has the highest session_id
        )

        SELECT
            latestSession.user_identifier,
            MAX(summary.has_user_logged_in_via_sso) as has_user_logged_in_via_sso,
            COUNT(DISTINCT CASE WHEN summary.answer IS NOT NULL THEN summary.item_id END) AS num_questions_attempted,
            COUNT(DISTINCT CASE WHEN summary.answer = question.correct_answer THEN summary.item_id END) AS num_questions_answered_correctly,
            CASE
                WHEN COUNT(DISTINCT CASE WHEN summary.answer IS NOT NULL THEN summary.item_id END) = (SELECT total_questions FROM totalQuestions)
                THEN 'true'
                ELSE 'false'
            END AS are_all_questions_attempted
        FROM latestSession
        INNER JOIN summary ON summary.session_id = latestSession.latest_session_id AND summary.user_identifier = latestSession.user_identifier
        INNER JOIN {schema}.question question ON question.item_id = summary.item_id
        GROUP BY latestSession.user_identifier
        ORDER BY latestSession.user_identifier
    """
