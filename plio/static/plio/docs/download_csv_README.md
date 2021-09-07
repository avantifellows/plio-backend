# Plio Report

This document aims to explain how you can use the downloaded report. Before we talk about the `.csv` files that are present in this report, we first need to understand how the data for each plio is stored.

## Plio Data Organization

First, we'll clarify the meaning of a few terms that appear in this document.

`plio`: an interactive video - in this case, the one for which you have downloaded the report.

`item`: every interaction that you have added is considered an `item`. Each `item` has a `type` associated with it. Currently, the only `type` that we support for `item`s is `question`. Each `question` can further have its own type (`mcq`, `subjective`, etc.).

`session`: every time a user opens a plio, a new session is created. The same user can have multiple sessions for each plio. This is necessary because users can have interruptions due to intermittent network and might have to come back to the plio several times. For each new session, we resume the user from where they left off in the last session. Hence, if a user has already answered a question, it will be shown as answered in their next session for the same plio.

`session_answer`: one `session_answer` refers to the response that a user has given to one of the interactions in a particular session. The interaction that a `session_answer` belongs to can be found using the `item_id` attribute of each `session_answer`. If a `session_answer` is empty, it means that the user has not given any response. By default, a `session_answer` is created for all the interactions (`items`) that you have added to the plio. So, for example, if your plio has 3 multiple-choice questions and 2 subjective questions, 5 `session_answer`s are created by default for every session. As the user answers these questions, the `session_answer`s get updated.

`event`: we save various events that take place while a user is watching a plio. For example, playing a video, pausing a video, skipping a video, answering a question etc. There is a time associated with each event and for each user, the events should be present in a sequential manner in time so that you can get a complete picture of how each user is interacting with your video. For the full list of event types and their meanings, refer to [Events](#events).



## Folder Organization

This section will clarify what each of the `.csv` files in the folder contains:

- `plio-meta-details.csv`: this file contains the meta information for the plio. The meaning of each column is given below:

  - `id`: the unique identifier for the plio
  - `name`: the name of the plio as set by you
  - `video`: the link of the YouTube video used to create the plio

  Example:
  | id         | name                    | video                                       |
  |------------|-------------------------|---------------------------------------------|
  | ash1lasnan | Introduction to Circles | https://www.youtube.com/watch?v=m9dpeG2rKdY |

- `plio-interaction-details.csv`: contains the details of each interaction (referred to as `item` as explained above) added to the plio. The columns represent the following:

  - `item_id`: the unique identifier for the interaction item
  - `item_type`: the type of the interaction (e.g. `question`)
  - `item_time`: the time in the video when the interaction would appear

  If the `item_type` is `question`, the following columns are also present:

  - `question_type`: the type of question (e.g. `mcq`)
  - `question_text`: the text of the question itself
  - `question_options`: the options for the question
  - `question_correct_answer`: the correct answer for the given question. For `question_type = mcq`, this represents the index of the correct answer among the `question_options`.

  Example:
  | item_id | item_type | item_time | question_type | question_text                                   | question_options                                             | question_correct_answer |
  | ------- | --------- | --------- | ------------- | ----------------------------------------------- | ------------------------------------------------------------ | ----------------------- |
  | 2783    | question  | 10        | Subjective    | What is the difference between hips and glutes? |                                                              |                         |
  | 2788    | question  | 20        | Mcc           | NaOH + HCl → ?                                  | [   "A) NaOHHCl ",    "B) Na + OH + H + Cl ",    "C) NaCl + H20 ",    "D) NaOH2Cl" ] | 2                       |

- `responses.csv`: contains the responses to each interaction by every user in every session. The columns represent the following:

  - `session_id`: the unique identifier for the session
  - `user_identifier`: the unique identifier for the user associated with this session. To preserve user privacy, this field would not contain any Personally Identifiable Information (PII) and would instead be a hashed value. However, the same user will have the same hashed value across different plios. So, you can still safely identify user trends across plios without harming user privacy.
  - `answer`: the user's actual answer to the interaction
  - `item_id`: the unique identifier of the interaction that this answer belongs to. You can compare this value with the `id` column in `plio-interaction-details.csv` to identify which item did this answer belong to.

  Example:
  | session_id | user_identifier                  | answer | item_id |
  | ---------- | -------------------------------- | ------ | ------- |
  | 902        | a532400ed62e772b9dc0b86f46e583ff | 0      | 2781    |
  | 902        | a532400ed62e772b9dc0b86f46e583ff | 1      | 2782    |
  | 1131       | fae0b27c451c728867a567e8c1bb4e53 | 0      | 2781    |


- `sessions.csv`: contains the details of each session of every user. The columns represent the following:

  - `session_id`: the unique identifier for the session
  - `user_identifier`: the unique identifier for the user associated with this session
  - `watch_time`: the amount of time the user has watched the video (in seconds) - the most recent session of any user includes the total time across all previous sessions by that user.
  - `retention`: the retention array over the video for the given user. The length of the array is the number of seconds of the video and each value represents how many times the user has visited that particular second of the video while watching the plio. For example, if your video is 4 minutes long, each row of this column will have 240 values (one for each second). If a user did not reach the end of the video, the values towards the end would be 0. If a user has rewatched the first 10 seconds 5 times, the first 10 values would be 5. Ignore this field if it contains something like `NaN, NaN, ...`.

  Example:
  | session_id | retention                                  | watch_time | user_identifier                  |
  | ---------- | ------------------------------------------ | ---------- | -------------------------------- |
  | 1951       | 1,1,1,10,1,2,...,0,0,0,0,0,1,1,1,1,0,0,0,0 | 50         | addfa9b7e234254d26e9c7f2af1005cb |

- `events.csv`: contains the details of each event in each session of every user. The columns represent the following:

  - `session_id`: the unique identifier for the session
  - `user_identifier`: the unique identifier for the user associated with this session
  - `event_type`: the type of the event (e.g. `played`, `paused`, etc.). The full list of event types and their meanings can be found in the [Events](#events) section.
  - `event_player_time`: the current time in the video when the event was triggered (in seconds)
  - `event_details`: further details for the event based on the event type (e.g. question number for events related to questions, etc.)
     **Note: The indexes present in the event details, like `itemIndex` and `optionIndex` are [0-indexed](https://en.wikipedia.org/wiki/Zero-based_numbering), i.e. `itemIndex: 1` would mean the second item and so on**.
  - `event_global_time`: the global time when the event took place to help you track the order in which the events took place.

  Example
  | session_id | user_identifier                  | event_type      | event_player_time | event_details                      |
  | ---------- | -------------------------------- | --------------- | ----------------- | ---------------------------------- |
  | 770        | d64a340bcb633f536d56e51874281454 | option_selected | 2.5               | {"itemIndex": 1, "optionIndex": 1} |
  | 770        | d64a340bcb633f536d56e51874281454 | video_seeked    | 0.08              | {"currentTime": 0.08}              |
  | 3844       | 4b0250793549726d5c1ea3906726ebfe | paused          | 122               | {}                                 |


## Events

The full list of event types and their meanings can be found below:

| Event Type        | Meaning of the event type
| ----------------- | ------------------------------------------------------------ |
| ready             | The video was loaded                                         |
| played            | The video was played                                         |
| paused            | The video was paused                                         |
| enter_fullscreen  | User entered the fullscreen mode of the video                |
| exit_fullscreen   | User exited the fullscreen mode of the video                 |
| item_opened       | One item (interaction) has popped up for the user            |
| option_selected   | The user has selected an option in a question                |
| question_skipped  | The user has skipped a question                              |
| question_answered | The user has submitted the answer to a question              |
| question_proceed  | The user has proceeded after submitting the answer to a question |
| question_revised  | The user clicked on "revise" when the question popped up     |
| video_seeking     | The user is dragging the seek bar of the video (skipping some part of the video) |
| video_seeked      | The user has completed dragging the seek bar of the video    |
| watching          | The user is watching the plio at the current moment          |
