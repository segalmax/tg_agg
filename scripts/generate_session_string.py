#!/usr/bin/env python3
"""
Generate a Telegram session string for Railway deployment.
This creates a NEW session (separate from your local one).
"""
import os
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

# API credentials
API_ID = int(os.getenv("API_ID", "25486530"))
API_HASH = os.getenv("API_HASH", "178cf13588f57714d72abed67409221a")
PHONE = "+972509909987"

print("=" * 70)
print("🔐 Telegram Session String Generator for Railway")
print("=" * 70)
print()
print("This will create a NEW session (separate from your local one)")
print("You'll receive an OTP code via Telegram")
print()

# Use StringSession (in-memory, no file)
client = TelegramClient(StringSession(), API_ID, API_HASH)
client.start(phone=PHONE)

print("✅ Connected to Telegram")
print()

# Get the session string
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
print("📋 To add to Railway:")
print("1. Go to Railway dashboard → telegram-monitor service")
print("2. Click Variables")
print("3. Add: SESSION_STRING = <paste the string above>")
print()
print("Or via CLI:")
print(f'railway variables --service telegram-monitor --set "SESSION_STRING={session_string}"')
print()

