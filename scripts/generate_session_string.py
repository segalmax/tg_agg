#!/usr/bin/env python3
"""
Generate a Telegram session string for Railway deployment.
This creates a NEW session (separate from your local one).

Required env vars (add to .env):
  API_ID    — from https://my.telegram.org
  API_HASH  — from https://my.telegram.org
  PHONE     — your phone number in international format, e.g. +1234567890
"""
import os
import sys
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

print("=" * 70)
print("🔐 Telegram Session String Generator for Railway")
print("=" * 70)
print()
print("This will create a NEW session (separate from your local one)")
print("You'll receive an OTP code via Telegram")
print()

client = TelegramClient(StringSession(), int(API_ID), API_HASH)
client.start(phone=PHONE)

print("✅ Connected to Telegram")
print()

session_string = client.session.save()
client.disconnect()

print("=" * 70)
print("✅ SESSION STRING GENERATED!")
print("=" * 70)
print()
print("Copy this string and add it to Railway as an environment variable:")
print()
print("Variable name:  SESSION_STRING")
print("Variable value: (below)")
print()
print(session_string)
print()
print("=" * 70)
print()
print("Or via CLI:")
print(f'railway variables --service telegram-monitor --set "SESSION_STRING=<paste the string above>"')
print()
