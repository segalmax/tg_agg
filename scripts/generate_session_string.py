#!/usr/bin/env python3
"""
Generate a Telegram session string and push it to Railway.

Required env vars (add to .env):
  API_ID    — from https://my.telegram.org
  API_HASH  — from https://my.telegram.org
  PHONE     — your phone number in international format, e.g. +1234567890
"""
import os
import sys
import subprocess
from dotenv import load_dotenv
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

load_dotenv(os.path.join(os.path.dirname(__file__), "../tg_site/.env"))

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
PHONE = os.getenv("PHONE")

if not API_ID or not API_HASH or not PHONE:
    print("❌ Missing required env vars: API_ID, API_HASH, PHONE")
    print("   Add them to tg_site/.env and re-run.")
    sys.exit(1)

print("🔐 Generating Telegram session — you'll receive an OTP via Telegram...")
print()

client = TelegramClient(StringSession(), int(API_ID), API_HASH)
client.start(phone=PHONE)
session_string = client.session.save()
client.disconnect()

print()
print("✅ Session generated — pushing to Railway...")
result = subprocess.run(
    ["railway", "variables", "--service", "telegram-monitor", "--set", f"SESSION_STRING={session_string}"],
    capture_output=True, text=True
)
if result.returncode == 0:
    print("✅ SESSION_STRING set on Railway. telegram-monitor will redeploy automatically.")
else:
    print(f"❌ Failed to set Railway variable: {result.stderr}")
    print("   Set it manually:")
    print(f'   railway variables --service telegram-monitor --set "SESSION_STRING={session_string}"')
