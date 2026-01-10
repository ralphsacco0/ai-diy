#!/usr/bin/env python3
"""
AI-DIY Customer Provisioning Script - Re-runnable Version

This script provisions a new customer workspace by:
1. Creating/verifying Railway custom domain
2. Creating/verifying Cloudflare DNS record (CNAME, proxied)
3. Creating/verifying Cloudflare Access application
4. Creating/verifying Cloudflare Access policy

This version is safe to re-run and will handle existing resources gracefully.

Usage: python provision_customer_rerunnable.py <customer_slug> <customer_email> <origin_host>
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

def create_or_verify_railway_domain(project_id, api_token, customer_slug, zone_name):
    """Create or verify custom domain in Railway project"""
    
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
        
        # Find the web service
        service_id = None
        for service in services:
            if service.get("name") in ["web", "api", "app"] or len(services) == 1:
                service_id = service["id"]
                break
        
        if not service_id:
            service_id = services[0]["id"] if services else None
        
        if not service_id:
            print("❌ No services found in Railway project")
            sys.exit(1)
        
        # Check if domain already exists
        domains_url = f"https://api.railway.app/v2/services/{service_id}/domains"
        response = requests.get(domains_url, headers=headers)
        response.raise_for_status()
        existing_domains = response.json()
        
        target_domain = f"{customer_slug}.{zone_name}"
        
        for domain in existing_domains:
            if domain.get("domain") == target_domain:
                print(f"✅ Railway custom domain already exists: {target_domain}")
                return domain.get("id"), service_id
        
        # Create new domain
        domain_payload = {
            "domain": target_domain
        }
        
        print(f"🚂 Creating Railway custom domain: {target_domain}")
        
        response = requests.post(domains_url, headers=headers, json=domain_payload)
        response.raise_for_status()
        
        result = response.json()
        railway_domain_id = result.get("id")
        
        print(f"✅ Railway custom domain created successfully")
        print(f"   Railway will automatically issue SSL certificate")
        print(f"   Domain should be active within 30-90 seconds")
        
        return railway_domain_id, service_id
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to create/verify Railway domain: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")
        sys.exit(1)

def create_or_verify_dns_record(zone_id, api_token, customer_slug, origin_host, zone_name):
    """Create or verify Cloudflare DNS record (CNAME, proxied)"""
    
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    # First, check if record already exists
    list_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?type=CNAME&name={customer_slug}"
    
    try:
        response = requests.get(list_url, headers=headers)
        response.raise_for_status()
        existing_records = response.json()["result"]
        
        if existing_records:
            existing_record = existing_records[0]
            print(f"✅ DNS record already exists: {customer_slug}.{zone_name} → {existing_record['content']}")
            
            # Check if it points to the correct origin
            if existing_record['content'] == origin_host:
                print(f"   ✅ Points to correct origin: {origin_host}")
                return existing_record['id']
            else:
                print(f"   ⚠️  Points to wrong origin: {existing_record['content']}")
                print(f"   🔄 Updating to point to: {origin_host}")
                
                # Update existing record
                update_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{existing_record['id']}"
                update_payload = {
                    "type": "CNAME",
                    "name": customer_slug,
                    "content": origin_host,
                    "ttl": 1,
                    "proxied": True
                }
                
                response = requests.put(update_url, headers=headers, json=update_payload)
                response.raise_for_status()
                
                print(f"   ✅ DNS record updated successfully")
                return existing_record['id']
        
        # Create new record
        payload = {
            "type": "CNAME",
            "name": customer_slug,
            "content": origin_host,
            "ttl": 1,  # Auto TTL
            "proxied": True  # Orange cloud ON
        }
        
        print(f"🌐 Creating DNS record: {customer_slug}.{zone_name} → {origin_host}")
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        dns_record_id = result["result"]["id"]
        
        print(f"✅ DNS record created successfully (ID: {dns_record_id})")
        print(f"   URL will be: https://{customer_slug}.{zone_name}")
        
        return dns_record_id
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to create/verify DNS record: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")
        sys.exit(1)

def create_or_verify_access_app(account_id, api_token, customer_slug, zone_name):
    """Create or verify Cloudflare Access application"""
    
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/access/apps"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    target_domain = f"{customer_slug}.{zone_name}"
    
    try:
        # First, check if app already exists
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        existing_apps = response.json()["result"]
        
        for app in existing_apps:
            if app.get("domain") == target_domain:
                print(f"✅ Access application already exists: {app['name']}")
                return app["id"]
        
        # Create new app
        payload = {
            "name": f"AI-DIY – {customer_slug.title()} Workspace",
            "domain": target_domain,
            "type": "self_hosted",
            "session_duration": "24h"
        }
        
        print(f"🔐 Creating Access application for {target_domain}")
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        app_id = result["result"]["id"]
        
        print(f"✅ Access application created successfully (ID: {app_id})")
        
        return app_id
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to create/verify Access application: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")
        sys.exit(1)

def create_or_verify_access_policy(account_id, api_token, app_id, customer_email):
    """Create or verify Cloudflare Access policy (allow one email)"""
    
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/access/apps/{app_id}/policies"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    try:
        # First, check if policy already exists
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        existing_policies = response.json()["result"]
        
        for policy in existing_policies:
            # Check if this policy allows the specific email
            if policy.get("decision") == "allow":
                include_section = policy.get("include", [])
                for include_item in include_section:
                    if "email" in include_item and include_item["email"].get("email") == customer_email:
                        print(f"✅ Access policy already exists: {policy['name']}")
                        return policy["id"]
        
        # Create new policy
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
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        policy_id = result["result"]["id"]
        
        print(f"✅ Access policy created successfully (ID: {policy_id})")
        
        return policy_id
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to create/verify Access policy: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")
        sys.exit(1)

def main():
    """Main provisioning function"""
    
    if len(sys.argv) != 4:
        print("Usage: python provision_customer_rerunnable.py <customer_slug> <customer_email> <origin_host>")
        print("Example: python provision_customer_rerunnable.py ralph ralphsacco0@gmail.com ai-diy-dev-production.up.railway.app")
        sys.exit(1)
    
    customer_slug = sys.argv[1]
    customer_email = sys.argv[2]
    origin_host = sys.argv[3]
    
    print(f"🔄 Starting AI-DIY customer provisioning (re-runnable)...")
    print(f"   Customer: {customer_slug} ({customer_email})")
    print(f"   Origin: {origin_host}")
    print()
    
    # Get environment variables
    zone_id, account_id, cf_api_token, zone_name, railway_api_token, railway_project_id = get_required_env_vars()
    
    # Step 1: Add/verify custom domain in Railway
    railway_domain_id, service_id = create_or_verify_railway_domain(railway_project_id, railway_api_token, customer_slug, zone_name)
    
    # Step 2: Create/verify DNS record
    dns_record_id = create_or_verify_dns_record(zone_id, cf_api_token, customer_slug, origin_host, zone_name)
    
    # Step 3: Create/verify Access application  
    app_id = create_or_verify_access_app(account_id, cf_api_token, customer_slug, zone_name)
    
    # Step 4: Create/verify Access policy
    policy_id = create_or_verify_access_policy(account_id, cf_api_token, app_id, customer_email)
    
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
    print("✅ This script is safe to re-run - it will verify existing resources")

if __name__ == "__main__":
    main()
