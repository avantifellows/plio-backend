import json
import requests
from typing import List, Dict
from os.path import splitext, basename
import pandas as pd
from tqdm import tqdm

from plio.settings import CMS_URL, CMS_TOKEN, GET_CMS_PROBLEM_URL


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
    updated_items = []
    items_to_update = []
    problem_ids = []

    for item in items:
        source_metadata = item["metadata"]["source"]
        if "CMS" == source_metadata["name"]:
            problem_ids.append(source_metadata["problem_id"])
            items_to_update.append(item)
        else:
            updated_items.append(item)

    if not problem_ids:
        return {"status": "success", "items": items}

    cms_response = fetch_items_from_cms(problem_ids, items_to_update)
    if cms_response["status"] == "error":
        return cms_response

    updated_items.extend(cms_response["items"])

    # return the items ordered by timestamp
    sorted(updated_items, key=lambda item: item["time"])

    return {"status": "success", "items": updated_items}


def fetch_items_from_cms(problem_ids: List[str], items: List[Dict]):
    """Return the given list of problem IDs from the CMS as plio items"""
    # check that the problem IDs have the valid format
    validity = check_cms_problem_ids(problem_ids)

    if not validity["is_valid"]:
        return {"status": "error", "reason": validity["reason"]}

    # fetch problems from the CMS
    response = requests.request(
        "GET",
        url=CMS_URL + GET_CMS_PROBLEM_URL,
        headers={
            "Authorization": "Bearer " + CMS_TOKEN,
            "Content-Type": "application/json",
        },
        data=json.dumps({"problem_ids": problem_ids}),
    ).json()

    # handle the case where the problem IDs are correct format-wise
    # but the problem IDs given don't exist in the CMS
    if len(response) != len(problem_ids):
        return {"status": "error", "reason": "Error with the problem IDs"}

    # the response list is not returned in the same order as the problem ids
    response_id_to_problem_map = {_response["id"]: _response for _response in response}

    # holds the CMS problems as plio items
    plio_cms_items = []
    for index, problem_id in enumerate(problem_ids):
        # convert a CMS question to a plio item
        plio_cms_items.append(
            convert_cms_question_to_plio_item(
                response_id_to_problem_map[problem_id], items[index]
            )
        )

    return {"status": "success", "items": plio_cms_items}


def check_cms_problem_ids(problem_ids: List[str]):
    """Checks if the format of the CMS problem IDs is valid"""
    is_valid = True
    reason = ""

    for problem_id in problem_ids:
        if not problem_id:
            is_valid = False
            reason = "Empty problem IDs are not allowed"
            break

        # CMS problem IDs are all 24 characters long
        if len(problem_id) != 24:
            is_valid = False
            reason = "Each problem ID should be 24 characters long"
            break

    return {"is_valid": is_valid, "reason": reason}


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
