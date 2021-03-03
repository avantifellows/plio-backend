import urllib
import requests
from typing import List
import numpy as np

from plio.secrets import YT_API_KEY


def get_video_durations_from_ids(video_ids: List[str]):
    """Gets video durations for YouTube videos from their ids"""
    BASE_URL = 'https://youtube.googleapis.com/youtube/v3/videos'
    params = {
        "part": "contentDetails",
        "key": YT_API_KEY
    }
    base_query_string = urllib.parse.urlencode(params)

    # YouTube API only accepts upto 50 objects at a time
    steps = np.arange(0, len(video_ids), 50)

    # stores all the durations
    durations = []

    for step in steps:
        query_string = base_query_string + ''.join(
            [f'&id={video_id}' for video_id in video_ids[step: step + 50]])

        url = f'{BASE_URL}?{query_string}'
        response = requests.get(url).json()
    
        for item in response['items']:
            # should be of the form PT3M34S
            duration_str = item['contentDetails']['duration']

            # remove PT
            duration_str = duration_str[2:]

            duration = 0

            # count hours
            if 'H' in duration_str:
                hour_index = duration_str.find('H')
                hour_time = int(duration_str[:hour_index])
                duration_str = duration_str[hour_index + 1:]
                duration += hour_time * 3600
            
            # count minutes
            if 'M' in duration_str:
                minutes_index = duration_str.find('M')
                minutes_time = int(duration_str[:minutes_index])
                duration_str = duration_str[minutes_index + 1:]
                duration += minutes_time * 60

            # count seconds
            if 'S' in duration_str:
                duration += int(duration_str[:-1])
            
            durations.append(duration)

    return durations