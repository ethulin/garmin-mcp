"""Interactive Garmin Connect first-login. Run once to seed tokens."""
import os
import sys
from getpass import getpass
from pathlib import Path

from garminconnect import Garmin, GarminConnectAuthenticationError

TOKEN_PATH = str(Path(os.environ.get("GARMINTOKENS", "~/.garminconnect")).expanduser())


def main():
    if Path(TOKEN_PATH, "oauth1_token.json").exists():
        try:
            Garmin().login(TOKEN_PATH)
            print(f"Resumed existing session. Tokens at: {TOKEN_PATH}")
            return 0
        except GarminConnectAuthenticationError:
            print("Saved tokens invalid, falling back to credential login.")

    email = os.environ.get("GARMIN_EMAIL") or input("Email: ").strip()
    password = os.environ.get("GARMIN_PASSWORD") or getpass("Password: ")

    try:
        garmin = Garmin(
            email=email,
            password=password,
            prompt_mfa=lambda: input("MFA code: ").strip(),
        )
        garmin.login(TOKEN_PATH)
    except GarminConnectAuthenticationError as e:
        print(f"Authentication failed: {e}", file=sys.stderr)
        return 1

    print(f"Login successful. Tokens saved to: {TOKEN_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
