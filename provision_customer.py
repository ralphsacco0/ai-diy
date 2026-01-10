#!/usr/bin/env python3
"""
AI-DIY Customer Provisioning Script

This script provisions a new customer workspace by:
1. Creating Cloudflare DNS record (CNAME, proxied)
2. Creating Cloudflare Access application
3. Creating Cloudflare Access policy

Usage: python provision_customer.py <customer_slug> <customer_email> <origin_host>

Example: python provision_customer.py ralph ralphsacco0@gmail.com ai-diy-dev-production.up.railway.app
"""

import os
import sys
import requests
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_required_env_vars():
    """Get required environment variables"""
    zone_id = os.getenv("CLOUDFLARE_ZONE_ID")
    account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID") 
    cf_api_token = os.getenv("CLOUDFLARE_API_TOKEN")
    zone_name = os.getenv("CLOUDFLARE_ZONE_NAME", "ai-diy.ai")
    railway_api_token = os.getenv("RAILWAY_API_TOKEN")
    railway_project_id = os.getenv("RAILWAY_PROJECT_ID")
    
    if not all([zone_id, account_id, cf_api_token, railway_api_token, railway_project_id]):
        print("❌ Missing required environment variables:")
        print("   CLOUDFLARE_ZONE_ID")
        print("   CLOUDFLARE_ACCOUNT_ID") 
        print("   CLOUDFLARE_API_TOKEN")
        print("   RAILWAY_API_TOKEN")
        print("   RAILWAY_PROJECT_ID")
        sys.exit(1)
    
    return zone_id, account_id, cf_api_token, zone_name, railway_api_token, railway_project_id

def create_railway_domain(project_id, api_token, customer_slug, zone_name):
    """Create custom domain in Railway project"""
    
    # First, get the service ID for the web service
    services_url = f"https://api.railway.app/v2/projects/{project_id}/services"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    try:
        # Get services to find the web service
        response = requests.get(services_url, headers=headers)
        response.raise_for_status()
        services = response.json()
        
        # Find the web service (usually the first one or named 'web')
        service_id = None
        for service in services:
            if service.get("name") in ["web", "api", "app"] or len(services) == 1:
                service_id = service["id"]
                break
        
        if not service_id:
            # Fall back to first service
            service_id = services[0]["id"] if services else None
        
        if not service_id:
            print("❌ No services found in Railway project")
            sys.exit(1)
        
        # Create custom domain
        domain_url = f"https://api.railway.app/v2/services/{service_id}/domains"
        domain_payload = {
            "domain": f"{customer_slug}.{zone_name}"
        }
        
        print(f"🚂 Adding custom domain to Railway: {customer_slug}.{zone_name}")
        
        response = requests.post(domain_url, headers=headers, json=domain_payload)
        response.raise_for_status()
        
        result = response.json()
        railway_domain_id = result.get("id")
        
        print(f"✅ Railway custom domain created successfully")
        print(f"   Railway will automatically issue SSL certificate")
        print(f"   Domain should be active within 30-90 seconds")
        
        return railway_domain_id, service_id
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to create Railway domain: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")
        sys.exit(1)

def create_dns_record(zone_id, api_token, customer_slug, origin_host, zone_name):
    """Create Cloudflare DNS record (CNAME, proxied)"""
    
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "type": "CNAME",
        "name": customer_slug,
        "content": origin_host,
        "ttl": 1,  # Auto TTL
        "proxied": True  # Orange cloud ON
    }
    
    print(f"🌐 Creating DNS record: {customer_slug}.{zone_name} → {origin_host}")
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        dns_record_id = result["result"]["id"]
        
        print(f"✅ DNS record created successfully (ID: {dns_record_id})")
        print(f"   URL will be: https://{customer_slug}.{zone_name}")
        
        return dns_record_id
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to create DNS record: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")
        sys.exit(1)

def create_access_app(account_id, api_token, customer_slug, zone_name):
    """Create Cloudflare Access application"""
    
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/access/apps"
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "name": f"AI-DIY – {customer_slug.title()} Workspace",
        "domain": f"{customer_slug}.{zone_name}",
        "type": "self_hosted",
        "session_duration": "24h"
    }
    
    print(f"🔐 Creating Access application for {customer_slug}.{zone_name}")
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        app_id = result["result"]["id"]
        
        print(f"✅ Access application created successfully (ID: {app_id})")
        
        return app_id
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to create Access application: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")
        sys.exit(1)

def create_access_policy(account_id, api_token, app_id, customer_email):
    """Create Cloudflare Access policy (allow one email)"""
    
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/access/apps/{app_id}/policies"
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "name": f"Allow {customer_email}",
        "decision": "allow",
        "include": [
            {
                "email": {
                    "email": customer_email
                }
            }
        ]
    }
    
    print(f"👤 Creating Access policy for {customer_email}")
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        policy_id = result["result"]["id"]
        
        print(f"✅ Access policy created successfully (ID: {policy_id})")
        
        return policy_id
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to create Access policy: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")
        sys.exit(1)

def create_dns_record(zone_id, api_token, customer_slug, origin_host, zone_name):
    """Create Cloudflare DNS record (CNAME, proxied)"""
    
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "type": "CNAME",
        "name": customer_slug,
        "content": origin_host,
        "ttl": 1,  # Auto TTL
        "proxied": True  # Orange cloud ON
    }
    
    print(f"🌐 Creating DNS record: {customer_slug}.{zone_name} → {origin_host}")
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        dns_record_id = result["result"]["id"]
        
        print(f"✅ DNS record created successfully (ID: {dns_record_id})")
        print(f"   URL will be: https://{customer_slug}.{zone_name}")
        
        return dns_record_id
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to create DNS record: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")
        sys.exit(1)

def create_access_app(account_id, api_token, customer_slug, zone_name):
    """Create Cloudflare Access application"""
    
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/access/apps"
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "name": f"AI-DIY – {customer_slug.title()} Workspace",
        "domain": f"{customer_slug}.{zone_name}",
        "type": "self_hosted",
        "session_duration": "24h"
    }
    
    print(f"🔐 Creating Access application for {customer_slug}.{zone_name}")
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        app_id = result["result"]["id"]
        
        print(f"✅ Access application created successfully (ID: {app_id})")
        
        return app_id
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to create Access application: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")
        sys.exit(1)

def create_access_policy(account_id, api_token, app_id, customer_email):
    """Create Cloudflare Access policy (allow one email)"""
    
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/access/apps/{app_id}/policies"
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "name": f"Allow {customer_email}",
        "decision": "allow",
        "include": [
            {
                "email": {
                    "email": customer_email
                }
            }
        ]
    }
    
    print(f"👤 Creating Access policy for {customer_email}")
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        policy_id = result["result"]["id"]
        
        print(f"✅ Access policy created successfully (ID: {policy_id})")
        
        return policy_id
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to create Access policy: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")
        sys.exit(1)

def main():
    """Main provisioning function"""
    
    if len(sys.argv) != 4:
        print("Usage: python provision_customer.py <customer_slug> <customer_email> <origin_host>")
        print("Example: python provision_customer.py ralph ralphsacco0@gmail.com ai-diy-dev-production.up.railway.app")
        sys.exit(1)
    
    customer_slug = sys.argv[1]
    customer_email = sys.argv[2]
    origin_host = sys.argv[3]
    
    print(f"🚀 Starting AI-DIY customer provisioning...")
    print(f"   Customer: {customer_slug} ({customer_email})")
    print(f"   Origin: {origin_host}")
    print()
    
    # Get environment variables
    zone_id, account_id, cf_api_token, zone_name, railway_api_token, railway_project_id = get_required_env_vars()
    
    # Step 1: Add custom domain to Railway
    railway_domain_id, service_id = create_railway_domain(railway_project_id, railway_api_token, customer_slug, zone_name)
    
    # Step 2: Create DNS record
    dns_record_id = create_dns_record(zone_id, cf_api_token, customer_slug, origin_host, zone_name)
    
    # Step 3: Create Access application  
    app_id = create_access_app(account_id, cf_api_token, customer_slug, zone_name)
    
    # Step 4: Create Access policy
    policy_id = create_access_policy(account_id, cf_api_token, app_id, customer_email)
    
    print()
    print("🎉 Provisioning completed successfully!")
    print()
    print("📋 Summary:")
    print(f"   URL: https://{customer_slug}.{zone_name}")
    print(f"   Railway Domain ID: {railway_domain_id}")
    print(f"   Railway Service ID: {service_id}")
    print(f"   DNS Record ID: {dns_record_id}")
    print(f"   Access App ID: {app_id}")
    print(f"   Access Policy ID: {policy_id}")
    print()
    print("🔗 Next steps:")
    print(f"   1. Wait 30-90 seconds for Railway SSL certificate")
    print(f"   2. Visit: https://{customer_slug}.{zone_name}")
    print("   3. Enter your email when prompted")
    print("   4. Check email for OTP code")
    print("   5. You should be routed to your AI-DIY instance")
    print()
    print("⚠️  Note: Railway domain activation may take up to 2 minutes")

if __name__ == "__main__":
    main()
