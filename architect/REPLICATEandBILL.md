# AI-DIY Multi-Tenant Replication and Billing Plan

**Status**: Implementation Plan  
**Created**: 2026-01-09  
**Purpose**: Document strategy for scaling AI-DIY to multi-tenant SaaS with billing  

---

## Executive Overview

This plan outlines the transformation of AI-DIY from a single-user application to a scalable multi-tenant SaaS platform. The solution provides per-user instances with complete data isolation, Cloudflare-based security, and automated billing at $5/month base fee + $1/hour usage.

### Key Goals
- **Complete Isolation**: Each user gets dedicated Railway instance and storage
- **Lightweight Operations**: Minimal code changes, maximum automation
- **Professional Security**: Enterprise-grade authentication via Cloudflare Access
- **Profitable Billing**: $5/month + $1/hour with clear cost structure

### Architecture Flow
```
Customer → Cloudflare Access → Dedicated Railway Instance → AI-DIY Platform
```

---

## Phase 1: Security Enhancement (Low Risk)

### Objective
Replace HTTP Basic Auth with Cloudflare Access on existing production instance.

### Implementation Steps

#### 1.1 Domain Setup
- [ ] Acquire custom domain (e.g., `ai-diy.com`)
- [ ] Configure DNS to point to Cloudflare
- [ ] Set up SSL certificates (handled by Cloudflare)

#### 1.2 Cloudflare Access Configuration
- [ ] Sign up for Cloudflare Zero Trust (Free plan for first 50 users)
- [ ] Create Access policy for existing Railway URL
- [ ] Configure SSO providers (Google, GitHub, etc.)
- [ ] Test authentication flow
- [ ] Keep HTTP Basic Auth as backup during transition

#### 1.3 Testing & Validation
- [ ] Verify existing functionality works through Cloudflare
- [ ] Test user authentication flow
- [ ] Confirm generated apps still accessible via `/yourapp/`
- [ ] Document any required changes

### Success Criteria
- All existing users can authenticate through Cloudflare
- No loss of functionality in AI-DIY platform
- Improved security metrics (no more basic auth)

---

## Phase 2: Multi-Tenant Architecture Development

### Objective
Create experimental environment to test per-user instance provisioning and management.

### Implementation Steps

#### 2.1 Experimental Project Setup
- [ ] Create new Railway project: `ai-diy-multi-tenant-test`
- [ ] Clone existing codebase to new project
- [ ] Set up separate domain/subdomain for testing
- [ ] Configure Cloudflare Access for test environment

#### 2.2 Multi-Tenant Modifications
- [ ] Add user identification middleware
- [ ] Implement dynamic volume routing per user
- [ ] Create user provisioning scripts
- [ ] Test instance isolation and data separation

#### 2.3 Usage Tracking Infrastructure
- [ ] Implement Railway API integration for uptime monitoring
- [ ] Add Cloudflare session tracking
- [ ] Create usage logging system
- [ ] Develop hourly aggregation logic

### Success Criteria
- Can provision new user instances automatically
- Usage tracking accurately captures active hours
- Complete data isolation between test users

---

## Phase 3: Billing System Implementation

### Objective
Implement automated billing with $5/month base fee + $1/hour usage model.

### Implementation Steps

#### 3.1 Billing Infrastructure
- [ ] Set up Stripe account for payment processing
- [ ] Create customer management system
- [ ] Implement subscription management ($5/month recurring)
- [ ] Develop usage-based billing engine ($1/hour)

#### 3.2 Usage Calculation Logic
```javascript
// Hourly usage determination
function calculateHourlyUsage(userId, date) {
  const railwayUptime = getRailwayUptime(userId, date);  // Instance running
  const cloudflareSessions = getCloudflareSessions(userId, date);  // User logged in
  const sprintActivity = getSprintActivity(userId, date);  // Active development
  
  // Any activity = billable hour
  const isBillable = railwayUptime || cloudflareSessions || sprintActivity;
  return isBillable ? 1 : 0;
}
```

#### 3.3 Automated Invoicing
- [ ] Daily usage aggregation job
- [ ] Monthly invoice generation
- [ ] Automated payment processing
- [ ] Dunning management for failed payments

### Success Criteria
- Accurate hourly usage calculation
- Automated monthly billing
- Clear customer invoices and usage reports

---

## Phase 4: Customer Onboarding Automation

### Objective
Create seamless customer signup and provisioning process.

### Implementation Steps

#### 4.1 Signup Flow
- [ ] Create customer registration landing page
- [ ] Implement payment method collection (Stripe)
- [ ] Build automated provisioning system
- [ ] Set up welcome email sequence

#### 4.2 Automated Provisioning Script
```bash
#!/bin/bash
# provision_user.sh <user_id> <email> <subdomain>

USER_ID=$1
EMAIL=$2
SUBDOMAIN=$3

# 1. Create Railway project
railway create ai-diy-$USER_ID

# 2. Deploy AI-DIY codebase
railway up

# 3. Configure environment variables
railway variables set USER_ID=$USER_ID

# 4. Set up Cloudflare Access policy
cloudflare access-policy create $SUBDOMAIN $EMAIL

# 5. Send welcome email
send_welcome_email $EMAIL $SUBDOMAIN
```

#### 4.3 User Management Dashboard
- [ ] Customer list and status overview
- [ ] Usage metrics and billing reports
- [ ] Support access and troubleshooting tools
- [ ] Bulk operations for user management

### Success Criteria
- New users can self-service sign up
- Automatic provisioning within 5 minutes
- Complete user dashboard for management

---

## Cost Analysis and Profitability

### Per-User Cost Structure
- **Railway**: ~$0.006/hour when active
- **Cloudflare**: $0 (first 50 users), $7/user/month (51+ users)
- **Stripe**: 2.9% + $0.30 per transaction

### Revenue Model
- **Base Fee**: $5/month recurring
- **Usage**: $1/hour (any part of hour = full hour)

### Profit Calculations
```
Users 1-50:
- Monthly profit per user: $5.00 - $0.00 = $5.00
- Hourly profit per active hour: $1.00 - $0.006 = $0.994

Users 51+:
- Monthly profit per user: $5.00 - $7.00 = -$2.00
- Hourly profit per active hour: $1.00 - $0.006 = $0.994
- Break-even: ~2 active hours/month covers Cloudflare cost
```

---

## Risk Mitigation

### Technical Risks
- **Railway API Changes**: Monitor API updates, maintain fallback procedures
- **Cloudflare Service Outage**: Maintain documentation for manual user provisioning
- **Usage Tracking Accuracy**: Implement redundant tracking methods

### Business Risks
- **Customer Churn**: Focus on product value, maintain competitive pricing
- **Cost Overruns**: Monitor Railway usage closely, implement usage alerts
- **Payment Failures**: Robust dunning process, multiple payment retry attempts

### Operational Risks
- **Scaling Challenges**: Automate all manual processes, document procedures
- **Support Overhead**: Clear user isolation, comprehensive troubleshooting guides
- **Data Privacy**: Ensure complete data separation, comply with regulations

---

## Implementation Timeline

### Week 1-2: Phase 1 (Security)
- Domain setup and Cloudflare configuration
- Test and validate authentication flow

### Week 3-4: Phase 2 (Architecture)
- Experimental project setup
- Multi-tenant modifications and testing

### Week 5-6: Phase 3 (Billing)
- Stripe integration and billing infrastructure
- Usage tracking and invoicing automation

### Week 7-8: Phase 4 (Onboarding)
- Customer signup flow
- Provisioning automation and dashboard

### Week 9-10: Testing & Launch
- End-to-end testing with beta users
- Documentation refinement and production launch

---

## Success Metrics

### Technical Metrics
- [ ] User provisioning time < 5 minutes
- [ ] 99.9% authentication uptime
- [ ] Usage tracking accuracy > 99%

### Business Metrics
- [ ] Customer acquisition cost < $50
- [ ] Monthly recurring revenue growth > 20%
- [ ] Customer churn rate < 5%

### Operational Metrics
- [ ] Support tickets per user < 1/month
- [ ] Manual intervention rate < 1%
- [ ] System uptime > 99.5%

---

## Next Steps

1. **Immediate**: Begin Phase 1 - Cloudflare security setup
2. **Research**: Evaluate domain options and Stripe integration requirements
3. **Documentation**: Create detailed technical specifications for each phase
4. **Testing**: Set up experimental environment for multi-tenant development

---

*This document serves as the master plan for transforming AI-DIY into a scalable multi-tenant SaaS platform. All implementation should reference this document for guidance and validation.*
