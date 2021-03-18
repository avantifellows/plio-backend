import json
import requests
from typing import List, Dict
from os.path import splitext, basename
import pandas as pd
from tqdm import tqdm
from datetime import datetime, timezone

from plio.settings import CMS_URL, CMS_TOKEN, GET_CMS_PROBLEM_URL
from .time import convert_to_ist


def convert_objects_to_df(objects: List):
    """Returns list of objects as pandas DataFrame"""
    # will contain the list of dictionaries that will
    # form the DataFrame
    objects_df = []

    # convert JSON string to JSON object
    for info in tqdm(objects):
        info["response"] = json.loads(info["response"])

        # dict which will contain flattened key-value pairs
        object_dict = {}

        for key, value in info.items():
            if key == "response":
                continue

            object_dict[key] = value

        # set the id for the object
        object_dict["id"] = id_from_object_key(info["key"])

        # flatten the key-value pairs under response
        for key, value in info["response"].items():
            object_dict[key] = value

        objects_df.append(object_dict)

    return pd.DataFrame(objects_df)


def id_from_object_key(key: str):
    """Returns the ID corresponding to the object key"""
    return splitext(basename(key))[0]


def fetch_items_from_sources(items: List[Dict]):
    """
    Handles and prepares the questions coming from
    other sources. Example - CMS
    """
    problem_ids = []

    for item in items:
        source_metadata = item["metadata"]["source"]
        if "CMS" == source_metadata["name"]:
            problem_ids.append(source_metadata["problem_id"])
        else:
            problem_ids.append([])

    if not problem_ids:
        return items

    response = requests.request(
        "GET",
        url=CMS_URL + GET_CMS_PROBLEM_URL,
        headers={
            "Authorization": "Bearer " + CMS_TOKEN,
            "Content-Type": "application/json",
        },
        data=json.dumps({"problem_ids": problem_ids}),
    ).json()

    response_index = 0
    for index, problem_id in enumerate(problem_ids):
        if not problem_id:
            continue

        # convert a CMS question to a plio item
        items[index] = convert_cms_question_to_plio_item(
            response[response_index], items[index]
        )

        # increment response index
        response_index += 1

    return items


def convert_cms_question_to_plio_item(problem_data: Dict, item: Dict):
    """
    Convert the given CMS question to the format of a plio item
    """
    # extract the question text
    item["details"]["text"] = problem_data.get("text", "")
    # extract the option text
    item["details"]["options"] = [
        option.get("text", "") for option in problem_data.get("options", [])
    ]
    # extract the correct answers from index
    item["details"]["correct_answer"] = int(problem_data.get("answer", [""])[0]) - 1

    return item
