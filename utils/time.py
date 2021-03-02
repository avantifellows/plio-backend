from typing import Union
from datetime import datetime
import pytz


def convert_to_ist(
        date: Union[str, datetime], return_string: bool = False,
        date_format: str = '%Y-%m-%d %H:%M:%S'):
    """Returns the given date in IST

    :param date: input date that is to be converted
    :type date: Union[str, datetime]
    :param return_string: whether to return the value as a string;
        defaults to False
    :type return_string: bool, optional
    :param date_format: string format to use to convert string date
        to datetime object; only used if date is a string and assumes
        string time is assumed to be in local timezone;
        defaults to '%Y-%m-%d %H:%M:%S'
    :type date_format: str, optional
    """
    assert isinstance(date, (str, datetime))

    ist = pytz.timezone('Asia/Kolkata')

    # try to convert to datetime object if date is a string
    if isinstance(date, str):
        date = datetime.strptime(date, date_format)

    return date.astimezone(ist)
