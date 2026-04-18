#!/usr/bin/env python3
"""
OneDrive OAuth Setup Script

This script helps you set up OAuth authentication for OneDrive without rclone.
Run this script to complete the initial OAuth setup.
"""

import sys
from pathlib import Path

# Add the parent directory to the path so we can import transaction
sys.path.insert(0, str(Path(__file__).parent))

# from transaction import setup_oauth_authentication, CLIENT_ID, CLIENT_SECRET, REDIRECT_URI
from stackops.utils.cloud.onedrive.auth import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, setup_oauth_authentication


def main():
    """Main setup function."""
    print("🔧 OneDrive OAuth Setup")
    print("=" * 40)

    # Check if environment variables are set
    if CLIENT_ID == "your_client_id_here":
        print("\n❌ ONEDRIVE_CLIENT_ID environment variable not set!")
        print("\n📋 Azure App Registration Setup:")
        print("1. Go to https://portal.azure.com")
        print("2. Navigate to 'Azure Active Directory' > 'App registrations'")
        print("3. Click 'New registration'")
        print("4. Name: 'OneDrive API Access'")
        print("5. Supported account types: 'Personal Microsoft accounts only'")
        print("6. Redirect URI: 'Web' -> 'http://localhost:8080/callback'")
        print("7. Click 'Register'")
        print("\n📋 After registration:")
        print("8. Copy the 'Application (client) ID'")
        print("9. Go to 'API permissions' > 'Add a permission'")
        print("10. Select 'Microsoft Graph' > 'Delegated permissions'")
        print("11. Add 'Files.ReadWrite.All' and 'offline_access'")
        print("12. Click 'Grant admin consent' (if required)")
        print("\n📋 Set environment variables:")
        print("   export ONEDRIVE_CLIENT_ID='your_client_id_here'")
        print("   export ONEDRIVE_REDIRECT_URI='http://localhost:8080/callback'")
        print("\n🔄 Then run this script again.")
        return

    print(f"✅ Client ID: {CLIENT_ID}")
    print(f"✅ Redirect URI: {REDIRECT_URI}")

    if CLIENT_SECRET and CLIENT_SECRET != "your_client_secret_here":
        print("✅ Client Secret: [SET]")
    else:
        print("ℹ️  Client Secret: [NOT SET - Using public client mode]")

    print("\n🚀 Starting OAuth setup...")
    setup_oauth_authentication()


if __name__ == "__main__":
    main()
