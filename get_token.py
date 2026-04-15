#!/usr/bin/env python3
"""
One-time helper to obtain Gmail OAuth2 credentials for the email daemon.

Run this LOCALLY (not on the server) where a browser is accessible.

Prerequisites:
  pip install google-auth-oauthlib

Steps:
  1. Go to https://console.cloud.google.com/
  2. Create a project (or select an existing one)
  3. Enable the Gmail API:  APIs & Services → Library → Gmail API → Enable
  4. Create OAuth2 credentials:
       APIs & Services → Credentials → Create Credentials → OAuth client ID
       Application type: Desktop app
  5. Download the JSON file and save it as  client_secret.json  next to this script
  6. Run:  python get_token.py
  7. A browser window will open — log in as ieuroboticslab@gmail.com and grant access
  8. Copy the three values printed at the end into the .env file on the server

Note: the refresh token does NOT expire as long as the app is used at least once
every 6 months.  No 2-step verification required after this initial setup.
"""

import json
import sys

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("ERROR: google-auth-oauthlib is not installed.")
    print("Run:  pip install google-auth-oauthlib")
    sys.exit(1)

SCOPES = ['https://mail.google.com/']
CLIENT_SECRET_FILE = 'client_secret.json'


def main():
    try:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, scopes=SCOPES)
    except FileNotFoundError:
        print(f"ERROR: {CLIENT_SECRET_FILE} not found.")
        print("Download it from Google Cloud Console and place it next to this script.")
        sys.exit(1)

    print("Opening browser for Google authentication...")
    creds = flow.run_local_server(port=0)

    print("\n" + "=" * 50)
    print("Add these three variables to your .env file:")
    print("=" * 50)
    print(f"GMAIL_CLIENT_ID={creds.client_id}")
    print(f"GMAIL_CLIENT_SECRET={creds.client_secret}")
    print(f"GMAIL_REFRESH_TOKEN={creds.refresh_token}")
    print("=" * 50)
    print("\nAlso remove or leave empty the old EMAIL_PASSWORD line.")


if __name__ == '__main__':
    main()
