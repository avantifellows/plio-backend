import json
from typing import List
from os.path import splitext, basename
import pandas as pd
from tqdm import tqdm
from datetime import datetime, timezone

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
