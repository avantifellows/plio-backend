def get_plio_details_query(plio_uuid: str, schema: str):
    """Returns the details for the given plio"""
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


def get_sessions_dump_query(plio_uuid: str, schema: str):
    """Returns the dump of all the sessions for the given plio"""
    return f"""
        SELECT
            session.id as session_id,
            session.retention,
            session.watch_time,
            MD5(session.user_id::varchar(255)) as user_id
        FROM {schema}.session AS session
        INNER JOIN {schema}.plio AS plio ON plio.id = session.plio_id
        WHERE plio.uuid  = '{plio_uuid}'"""


def get_responses_dump_query(plio_uuid: str, schema: str):
    """Returns the dump of all the session responses for the given plio"""
    return f"""
        SELECT
            session.id as session_id,
            MD5(session.user_id::varchar(255)) as user_id,
            sessionAnswer.id AS session_answer_id,
            sessionAnswer.answer,
            sessionAnswer.item_id
        FROM {schema}.session AS session
        INNER JOIN {schema}.session_answer sessionAnswer ON session.id = sessionAnswer.session_id
        INNER JOIN {schema}.plio AS plio ON plio.id = session.plio_id
        WHERE plio.uuid  = '{plio_uuid}'"""


def get_events_query(plio_uuid: str, schema: str):
    """Returns the dump of all events across all sessions for the given plio"""
    return f"""
        SELECT
            session.id as session_id,
            MD5(session.user_id::varchar(255)) as user_id,
            event.type AS event_type,
            event.player_time AS event_player_time,
            event.details AS event_details,
            event.created_at AS event_global_time
        FROM {schema}.session AS session
        INNER JOIN {schema}.event AS event ON session.id = event.session_id
        INNER JOIN {schema}.plio AS plio ON plio.id = session.plio_id
        WHERE plio.uuid  = '{plio_uuid}'"""
