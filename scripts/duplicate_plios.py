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

# List of plio UUIDs to duplicate
PLIO_UUIDS_TO_DUPLICATE = []

# Output file for new plio UUIDs
OUTPUT_FILE = "new_plio_uuids.txt"
# --- End of Configuration ---


def duplicate_plio(plio_uuid: str) -> str | None:
    """
    Calls the duplicate API for a given plio UUID.
    Returns the new plio's UUID if successful, otherwise None.
    """
    url = f"{BASE_URL}/plios/{plio_uuid}/duplicate/"
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "organization": ORGANIZATION,
        "Content-Type": "application/json",
    }

    print(f"Duplicating plio: {plio_uuid}")

    try:
        # The duplicate endpoint is a POST request.
        response = requests.post(url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        new_plio_data = response.json()
        new_plio_uuid = new_plio_data.get("uuid")

        if new_plio_uuid:
            print(
                f"Successfully duplicated plio {plio_uuid}. New UUID: {new_plio_uuid}"
            )
            return new_plio_uuid
        else:
            print(f"Error: 'uuid' not found in response for plio {plio_uuid}.")
            print(f"Response: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while duplicating plio {plio_uuid}: {e}")
        if e.response:
            print(f"Response status: {e.response.status_code}")
            print(f"Response text: {e.response.text}")
        return None


def main():
    """
    Main function to duplicate plios and save new UUIDs.
    """
    if AUTH_TOKEN == "your_auth_token_here" or ORGANIZATION == "your_organization_here":
        print(
            "Please configure AUTH_TOKEN and ORGANIZATION in the script or as environment variables."
        )
        return

    new_uuids = []
    for uuid in PLIO_UUIDS_TO_DUPLICATE:
        new_uuid = duplicate_plio(uuid)
        if new_uuid:
            new_uuids.append(new_uuid)

    if new_uuids:
        with open(OUTPUT_FILE, "w") as f:
            for uuid in new_uuids:
                f.write(f"{uuid}\n")
        print(f"\nSuccessfully created {len(new_uuids)} new plios.")
        print(f"The new UUIDs have been written to {OUTPUT_FILE}")
    else:
        print("\nNo plios were duplicated.")


if __name__ == "__main__":
    main()
