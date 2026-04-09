import requests
import os

# --- Configuration ---
# The base URL of the API. You might need to change this for local development.
BASE_URL = "https://backend.plio.in/api/v1"

# Your authorization token (Bearer token).
# It's recommended to use an environment variable for this for security.
# Example: export PLIO_AUTH_TOKEN='your_token'
AUTH_TOKEN = os.environ.get("PLIO_AUTH_TOKEN", "")

# The organization header value
ORGANIZATION = "scertH"

# List of plio UUIDs to publish
PLIO_UUIDS_TO_PUBLISH = []

# --- End of Configuration ---


def publish_plio(plio_uuid: str) -> bool:
    """
    Calls the API to mark a plio as published.
    Returns True if successful, otherwise False.
    """
    url = f"{BASE_URL}/plios/{plio_uuid}/"
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "organization": ORGANIZATION,
        "Content-Type": "application/json",
    }
    data = {"status": "published"}

    print(f"Publishing plio: {plio_uuid}")

    try:
        # The endpoint to update a plio is a PATCH request.
        response = requests.patch(url, headers=headers, json=data)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        print(f"Successfully published plio {plio_uuid}.")
        return True

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while publishing plio {plio_uuid}: {e}")
        if e.response:
            print(f"Response status: {e.response.status_code}")
            print(f"Response text: {e.response.text}")
        return False


def main():
    """
    Main function to publish plios.
    """
    if AUTH_TOKEN == "your_auth_token_here" or ORGANIZATION == "your_organization_here":
        print(
            "Please configure AUTH_TOKEN and ORGANIZATION in the script or as environment variables."
        )
        return

    if not PLIO_UUIDS_TO_PUBLISH:
        print(
            "Please add the plio UUIDs you want to publish to the PLIO_UUIDS_TO_PUBLISH list."
        )
        return

    published_count = 0
    for uuid in PLIO_UUIDS_TO_PUBLISH:
        if publish_plio(uuid):
            published_count += 1

    print(
        f"\nFinished. {published_count}/{len(PLIO_UUIDS_TO_PUBLISH)} plios were published successfully."
    )


if __name__ == "__main__":
    main()
