from hashlib import sha256


def hash_function(string: str) -> str:
    """Returns the SHA-256 hash value for the string

    :param string: string to be hashed
    :type string: str
    :return: SHA-256 hashed value
    :rtype: str
    """
    return sha256(string.encode('utf-8')).hexdigest()
