# Plio Data

This folder contains the following files:

- `plio-meta-details.csv`: contains the meta information for the plio:

  - `id`: the unique identifier for the plio
  - `name`: the name of the plio as set by you
  - `video`: the URL of the video linked to the plio

- `plio-interaction-details.csv`: contains the details of each interaction (referred to as `item` in Plio) added to the plio. The columns represent the following:

  - `item_id`: the unique identifier for the interaction item
  - `item_type`: the type of the interaction (e.g. `question`)
  - `item_time`: the time in the video when the interaction would appear

  If the `item_type` is `question`, the following columns are also present:

  - `question_type`: the type of question (e.g. `mcq`)
  - `question_text`: the text of the question itself
  - `question_options`: the options for the question
  - `question_correct_answer`: the correct answer for the given question. For `question_type = mcq`, this represents the index of the correct answer among the `question_options`.

- `responses.csv`: contains the responses to each interaction by every user in every session. The columns represent the following:

  - `session_id`: the unique identifier for the session
  - `user_id`: the unique identifier for the user associated with this session
  - `session_answer_id`: the unique identifier for the user's answer in the current session
  - `answer`: the user's actual answer to the interaction
  - `item_id`: the unique identifier of the interaction that the user responded to

- `sessions.csv`: contains the details of each session of every user. The columns represent the following:

  - `session_id`: the unique identifier for the session
  - `user_id`: the unique identifier for the user associated with this session
  - `watch_time`: the amount of time the user has watched the video (in seconds) - the most recent session of any user includes the total time across all previous sessions by that user.
  - `retention`: the retention array over the video for the given session for the given user. The length of the array is the number of seconds of the video and each value represents how many times the user has visited that particular second of the video while watching the plio.

- `events.csv`: contains the details of each event in each session of every user. The columns represent the following:

  - `session_id`: the unique identifier for the session
  - `user_id`: the unique identifier for the user associated with this session
  - `event_type`: the type of the event (e.g. `played`, `paused`, etc.)
  - `event_player_time`: the current time in the video when the event was triggered (in seconds)
  - `event_details`: further details for the event based on the event type (e.g. question number for events related to questions, etc.)
  - `event_global_time`: the global time when the event took place
