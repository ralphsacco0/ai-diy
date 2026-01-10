# AI-DIY Multi-Tenant Architecture Specification

**Status**: Architecture Specification  
**Created**: 2026-01-09  
**Purpose**: Complete technical specification for scaling AI-DIY to multi-tenant SaaS platform  

---

## Executive Summary

This document outlines the transformation of AI-DIY from a single-user application to a multi-tenant SaaS platform where each customer receives their own isolated instance. The architecture uses Railway for individual instance deployment and Cloudflare for security and access management.

### Core Concept
**"Spin-Off Architecture"**: One main provisioning instance that spins up isolated customer instances on demand.

---

## Architecture Overview

### Visual Architecture
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Customer A    │    │   Customer B     │    │   Customer C    │
│  customerA.ai-  │    │  customerB.ai-   │    │  customerC.ai-  │
│     diy.ai      │    │     diy.ai       │    │     diy.ai      │
│                 │    │                  │    │                 │
│ ┌─────────────┐ │    │ ┌──────────────┐ │    │ ┌─────────────┐ │
│ │ Railway     │ │    │ │ Railway      │ │    │ │ Railway     │ │
│ │ Project:    │ │    │ │ Project:     │ │    │ │ Project:    │ │
│ │ ai-diy-     │ │    │ │ ai-diy-      │ │    │ │ ai-diy-     │ │
│ │ customerA   │ │    │ │ customerB    │ │    │ │ customerC   │ │
│ └─────────────┘ │    │ └──────────────┘ │    │ └─────────────┘ │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │  Main Instance  │
                    │    ai-diy.ai    │
                    │                 │
                    │ ┌─────────────┐ │
                    │ │ Railway     │ │
                    │ │ Project:    │ │
                    │ │ ai-diy      │ │
                    │ └─────────────┘ │
                    │ • Provisioning │
                    │ • Billing     │
                    │ • Management  │
                    │ • Updates     │
                    └─────────────────┘
```

### Key Components

#### 1. Main Instance (`ai-diy`)
- **Purpose**: Provisioning, billing, and management hub
- **Location**: `ai-diy.ai` → Railway project `ai-diy`
- **Functions**:
  - Customer signup and onboarding
  - Automated instance provisioning
  - Billing and subscription management
  - Updates deployment to all customer instances
  - Administrative dashboard

#### 2. Customer Instances (`ai-diy-customerX`)
- **Purpose**: Individual customer workspaces
- **Location**: `customerX.ai-diy.ai` → Railway project `ai-diy-customerX`
- **Features**:
  - Complete AI-DIY platform isolation
  - Independent data storage
  - Separate execution environments
  - Individual authentication via Cloudflare

---

## Critical Security Enforcement

### ⚠️ Security Gap Resolution

**Issue**: Railway instances respond to anyone who hits `*.up.railway.app` unless explicitly blocked.

**Solution**: Implement mandatory access validation for all Railway instances.

### 1. Blocking Direct Railway Access

#### Implementation Requirement
**All Railway instances MUST validate Cloudflare Access headers before serving any content.**

#### Technical Implementation
```python
# Middleware in main.py (required for ALL instances)
@app.middleware("http")
async def validate_cloudflare_access(request: Request, call_next):
    # Check if request came through Cloudflare Access
    cf_jwt = request.headers.get("Cf-Access-Jwt-Assertion")
    
    if not cf_jwt:
        # Direct Railway access - require HTTP Basic Auth as fallback
        auth_header = request.headers.get("Authorization")
        if not auth_header or not validate_basic_auth(auth_header):
            raise HTTPException(status_code=401, detail="Direct access blocked")
    
    # Validate Cloudflare JWT
    if cf_jwt and not validate_cf_jwt(cf_jwt):
        raise HTTPException(status_code=401, detail="Invalid Cloudflare token")
    
    response = await call_next(request)
    return response

def validate_cf_jwt(jwt_token: str) -> bool:
    """Validate Cloudflare Access JWT token"""
    try:
        # Decode and validate JWT with Cloudflare public key
        payload = jwt.decode(jwt_token, get_cf_public_key(), algorithms=["RS256"])
        return payload.get("aud") == os.getenv("CLOUDFLARE_AUDIENCE")
    except:
        return False
```

#### Security Layers
```
Layer 1: Cloudflare Access (primary security)
Layer 2: JWT validation (enforce Cloudflare origin)  
Layer 3: HTTP Basic Auth (emergency access)
```

### 2. DNS/Routing Mechanics

#### Option A: Individual DNS Records (Recommended)
**Setup**: One CNAME record per customer
```
customer1.ai-diy.ai → CNAME → ai-diy-customer1.up.railway.app
customer2.ai-diy.ai → CNAME → ai-diy-customer2.up.railway.app
customer3.ai-diy.ai → CNAME → ai-diy-customer3.up.railway.app
```

**Pros**:
- Simple to implement
- Clear customer ownership
- Easy troubleshooting
- Individual SSL certificates

**Cons**:
- Manual DNS setup per customer
- More DNS records to manage

#### Option B: Wildcard DNS with Router
**Setup**: Single wildcard record with routing logic
```
*.ai-diy.ai → CNAME → ai-diy-router.up.railway.app
Router logic: Parse subdomain → Route to appropriate Railway project
```

**Pros**:
- Automated setup
- Single DNS record
- Centralized routing control

**Cons**:
- Complex routing logic
- Single point of failure
- Harder customer isolation

#### Chosen Approach: Option A (Individual DNS Records)

**Rationale**:
- **Security**: Complete customer isolation at DNS level
- **Simplicity**: No complex routing logic needed
- **Reliability**: Each customer has independent DNS
- **Scalability**: Cloudflare can handle thousands of records

### 3. Automated DNS Management

#### Provisioning Script Enhancement
```bash
#!/bin/bash
# provision_customer.sh <customer_id> <subdomain>

CUSTOMER_ID=$1
SUBDOMAIN=$2

# Create Railway project
railway create "ai-diy-$CUSTOMER_ID"
RAILWAY_URL=$(railway domain --project "ai-diy-$CUSTOMER_ID")

# Create DNS record via Cloudflare API
curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
  -H "Authorization: Bearer $CF_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{
    "type": "CNAME",
    "name": "'$SUBDOMAIN'",
    "content": "'$RAILWAY_URL'",
    "ttl": 3600,
    "proxied": true
  }'

# Create Cloudflare Access policy
curl -X POST "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/access/apps" \
  -H "Authorization: Bearer $CF_API_TOKEN" \
  --data '{
    "name": "AI-DIY - '$SUBDOMAIN'",
    "domain": "'$SUBDOMAIN'.ai-diy.ai",
    "type": "self_hosted"
  }'
```

### 3. Cloudflare Configuration Strategy

#### Overview
Cloudflare is used as a centralized security and routing layer in front of all AI-DIY customer instances. To avoid manual operational overhead and configuration drift, Cloudflare is configured once per environment and is not modified on a per-customer basis during normal onboarding.

This is achieved through the use of a single wildcard Cloudflare Access Application and standardized DNS patterns.

#### One-Time Cloudflare Setup
The following Cloudflare configuration is performed once:

- **Domain Delegation**: The `ai-diy.ai` domain is delegated to Cloudflare DNS
- **Wildcard Access Application**: A single Cloudflare Access Application is created to protect `*.ai-diy.ai`
- **Authentication Methods**: Define authentication methods (email OTP, SSO, etc.)
- **Access Policies**: Define policies to control who may access customer workspaces
- **Identity Assertions**: Configure Cloudflare Access to forward authenticated requests with signed identity assertions

After this initial setup, Cloudflare enforces authentication and access control automatically for all matching subdomains.

#### Per-Customer Onboarding (No Manual Cloudflare Changes)
When a new customer signs up:

1. **Provision Railway**: New Railway deployment for the customer
2. **Create DNS Record**: Following standard pattern:
   ```
   customerX.ai-diy.ai → customerX.up.railway.app
   ```
3. **Proxy Through Cloudflare**: DNS record is proxied through Cloudflare

**No additional Cloudflare Access Applications, policies, or manual dashboard changes are required.**

Because the wildcard Access Application already applies to `*.ai-diy.ai`, all newly created customer subdomains are automatically protected by Cloudflare authentication and security policies.

#### Operational Guarantees
This approach ensures that:

- **Configuration Stability**: Cloudflare configuration remains consistent
- **Automated Onboarding**: Customer signup requires no manual Cloudflare interaction
- **Uniform Security**: All customer workspaces protected by same controls
- **Human-Free Scaling**: System scales without creating operational bottlenecks

**Cloudflare is treated as infrastructure, not as a per-customer operational dependency.**

#### Security Note
Customer Railway origin URLs (`*.up.railway.app`) are considered private origins. The application layer rejects requests that do not include valid Cloudflare Access identity assertions, preventing direct access that bypasses Cloudflare. Requests lacking valid Cloudflare Access assertions are rejected with an authorization error.

#### Environment Scope
This configuration strategy applies independently per environment (Development, Production, etc.). Each environment has its own Cloudflare configuration but follows the same one-time setup pattern.

**Customer self-service onboarding and billing are addressed in a separate Phase 2 document.**

---

## Technical Infrastructure

### Railway Project Structure

#### Main Instance: `ai-diy`
```
Railway Project: ai-diy
├── AI-DIY Platform Code
├── Provisioning System
├── Billing Integration (Stripe)
├── Customer Management Dashboard
├── Deployment Scripts
└── instances.txt (customer tracking)
```

#### Customer Instance: `ai-diy-customerX`
```
Railway Project: ai-diy-customerX
├── AI-DIY Platform Code (identical to main)
├── Customer Data Storage
├── Generated Apps Workspace
├── Execution Environment
└── Isolated Database
```

### Data Isolation Model

#### Complete Separation
```
Customer A: /app/development/src/static/appdocs/
├── visions/
├── backlog/
├── sprints/
├── execution-sandbox/
└── (all customer A data)

Customer B: /app/development/src/static/appdocs/
├── visions/
├── backlog/
├── sprints/
├── execution-sandbox/
└── (all customer B data)
```

**No data sharing between customers under any circumstances.**

---

## Customer Lifecycle

### 1. Customer Acquisition
```
Flow:
1. Customer lands on ai-diy.ai (marketing site)
2. Clicks "Sign Up" or "Start Free Trial"
3. Enters billing information (Stripe)
4. Chooses subdomain: company.ai-diy.ai
5. Completes registration
```

### 2. Automated Provisioning
```
Provisioning Script Triggered:
1. Create Railway project: ai-diy-company
2. Deploy AI-DIY code to new project
3. Configure Cloudflare Access policy
4. Set up billing subscription
5. Create customer record in main instance
6. Send welcome email with login instructions
7. Add to instances.txt for future updates
```

### 3. Customer Usage
```
Customer Experience:
1. Login at company.ai-diy.ai (Cloudflare Access)
2. Use complete AI-DIY platform
3. Create visions, run sprints, generate apps
4. All data isolated to their instance
5. Billed monthly + hourly usage
```

### 4. Ongoing Management
```
Instance Management:
1. Main instance monitors all customer instances
2. Updates deployed to all instances simultaneously
3. Usage tracked for billing
4. Support handled per instance
5. Scale by adding new instances
```

---

## Security Architecture

### Cloudflare Access Implementation

#### Authentication Flow
```
Customer → Cloudflare Access → Railway Instance
├── SSO providers (Google, GitHub, etc.)
├── Per-customer Access policies
├── Session management
└── Zero-trust security
```

#### Access Control
- **Main Instance**: Public marketing + authenticated admin
- **Customer Instances**: Fully authenticated via Cloudflare
- **No Shared Authentication**: Each customer isolated

### Network Security
```
Internet → Cloudflare (WAF + DDoS) → Railway (Private)
├── SSL/TLS termination at Cloudflare
├── Railway instances never exposed directly
├── Per-customer subdomain isolation
└── Zero-trust access policies
```

---

## Billing System

### Pricing Model
```
Base Fee: $5/month per customer
Usage Fee: $1/hour (any part of hour = full hour)

Billable Hour Definition:
├── Generated app is running (port 3000 active)
├── Sprint execution in progress
├── User logged in through Cloudflare
└── API calls being made
```

### Usage Tracking
```
Data Sources:
1. Railway API: Instance uptime monitoring
2. Cloudflare: User session tracking
3. AI-DIY: Sprint and activity logging
4. Aggregation: Daily calculation per customer
```

### Billing Automation
```
Monthly Process:
1. Calculate base fee + usage hours
2. Generate invoice via Stripe
3. Charge customer on file
4. Handle failed payments (dunning)
5. Send usage reports
```

---

## Deployment and Updates

### Development Workflow
```
Two-Tier System:
├── Development: ai-diy-dev-production (your sandbox)
└── Production: ai-diy (main instance)

Process:
1. Develop and test on dev instance
2. When stable, deploy to main instance
3. Main instance handles customer updates
```

### Customer Update Deployment
```
Bulk Update Process:
1. Main instance has latest code
2. Trigger deploy-all-instances.sh
3. Script reads instances.txt
4. Deploy to each customer sequentially
5. Stop on failure, report issues
6. Verify all instances updated
```

### Instance Management
```
instances.txt Format:
ai-diy-customer1
ai-diy-customer2
ai-diy-customer3

Management Scripts:
├── deploy-instance.sh <project-name>
├── deploy-all-instances.sh
└── manage-instances.sh [add|remove|list]
```

---

## Scalability Considerations

### Horizontal Scaling
```
Adding Customers:
1. New Railway project per customer
2. New Cloudflare Access policy
3. New billing subscription
4. Add to instances.txt
5. Automatic inclusion in updates
```

### Resource Scaling
```
Per-Customer Resources:
├── Railway: ~$0.006/hour when active
├── Storage: Included in Railway volume
├── Bandwidth: Included in Railway plan
└── Compute: Scales with usage
```

### Operational Scaling
```
As Customer Count Grows:
├── Automated provisioning becomes critical
├── Monitoring and alerting systems
├── Customer support workflows
└── Usage analytics and reporting
```

---

## Implementation Phases

### Phase 1: Foundation (Weeks 1-2)
**Objective**: Set up main instance and provisioning system
- [ ] Deploy main instance (`ai-diy`)
- [ ] Implement Cloudflare Access
- [ ] Create provisioning scripts
- [ ] Set up Stripe billing integration
- [ ] Build customer management dashboard

### Phase 2: Customer Onboarding (Weeks 3-4)
**Objective**: Enable first customer signups
- [ ] Create marketing landing pages
- [ ] Implement signup flow
- [ ] Test automated provisioning
- [ ] Verify billing automation
- [ ] Onboard first beta customers

### Phase 3: Operations (Weeks 5-6)
**Objective**: Scale operations and support
- [ ] Implement usage monitoring
- [ ] Create customer support workflows
- [ ] Set up analytics and reporting
- [ ] Test update deployment system
- [ ] Document operational procedures

### Phase 4: Growth (Weeks 7-8)
**Objective**: Optimize and scale
- [ ] Optimize provisioning speed
- [ ] Implement customer dashboard
- [ ] Add advanced billing features
- [ ] Scale support systems
- [ ] Prepare for increased demand

---

## Risk Analysis

### Technical Risks
**Railway Service Outage**
- **Impact**: All customer instances unavailable
- **Mitigation**: Monitor Railway status, have communication plan

**Cloudflare Service Outage**
- **Impact**: Customers cannot authenticate
- **Mitigation**: Service status page, manual authentication backup

**Deployment Failures**
- **Impact**: Customers don't receive updates
- **Mitigation**: Sequential deployment, rollback procedures

### Business Risks
**Customer Churn**
- **Impact**: Revenue loss, empty instances
- **Mitigation**: Focus on product value, competitive pricing

**Cost Overruns**
- **Impact**: Profitability reduction
- **Mitigation**: Usage monitoring, alerts, cost controls

**Support Overhead**
- **Impact**: Time spent on customer issues
- **Mitigation**: Clear documentation, self-service tools

---

## Success Metrics

### Technical Metrics
- **Provisioning Time**: < 5 minutes per customer
- **Update Success Rate**: > 99%
- **System Uptime**: > 99.5%
- **Security Incidents**: 0 per quarter

### Business Metrics
- **Customer Acquisition Cost**: < $50
- **Monthly Recurring Revenue Growth**: > 20%
- **Customer Churn Rate**: < 5%
- **Profit Margin per Customer**: > 80%

### Operational Metrics
- **Support Tickets per Customer**: < 1/month
- **Manual Intervention Rate**: < 1%
- **Customer Satisfaction**: > 4.5/5

---

## Next Steps

### Immediate Actions
1. **Deploy main instance** (`ai-diy`) with provisioning system
2. **Set up Cloudflare Access** for security
3. **Create deployment scripts** for instance management
4. **Implement billing integration** with Stripe
5. **Test end-to-end provisioning** with first customer

### Documentation Required
1. **Technical Setup Guides** for each component
2. **Customer Onboarding Documentation**
3. **Operational Runbooks** for common tasks
4. **Troubleshooting Guides** for support

### Stakeholder Feedback Points
1. **Architecture Review**: Technical feasibility and scalability
2. **Business Model Review**: Pricing and profitability analysis
3. **Security Review**: Authentication and data isolation
4. **Operations Review**: Support and maintenance requirements

---

## Conclusion

This architecture provides a scalable, secure, and profitable path to multi-tenant SaaS deployment for AI-DIY. The spin-off model ensures complete customer isolation while maintaining operational simplicity through automated provisioning and management.

The design balances technical complexity with business requirements, providing a foundation that can scale from 10 customers to 1000+ customers with minimal architectural changes.

---

*This document serves as the complete technical specification for the AI-DIY multi-tenant transformation. All implementation decisions should reference this document for guidance and validation.*
