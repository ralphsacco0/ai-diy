# AI-DIY Customer Self-Service & Billing Supplement

**Status**: Business & Technical Specification  
**Created**: 2026-01-10  
**Purpose**: Complete customer self-service workflow with billing integration  

---

## Executive Overview

This supplement defines the complete customer self-service experience including registration, payment, account management, and automated lifecycle management. It integrates directly with the multi-tenant architecture defined in the main specification.

### Business Model
- **Base Fee**: $5/month per customer
- **Usage Fee**: $2/hour (updated from $1 based on your latest requirement)
- **Self-Service**: Complete automated signup and management
- **Churn Prevention**: Easy cancellation with retention options

---

## Customer Lifecycle Integration

### Where It Fits in Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MAIN INSTANCE (ai-diy.ai)                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   Marketing     │  │  Self-Service   │  │   Billing   │ │
│  │   Website       │  │   Portal        │  │   System    │ │
│  │                 │  │                 │  │             │ │
│  │ • Landing pages │  │ • Registration  │  │ • Stripe    │ │
│  │ • Features      │  │ • Payment       │  │ • Invoicing │ │
│  │ • Pricing       │  │ • Account Mgmt  │  │ • Dunning   │ │
│  │ • Testimonials  │  │ • Cancellation  │  │ • Reporting │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
                                 │
                    Automated Provisioning Trigger
                                 │
┌─────────────────────────────────────────────────────────────┐
│                CUSTOMER INSTANCE (customerX.ai-diy.ai)      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   AI-DIY App    │  │   Customer      │  │   Usage     │ │
│  │   Platform      │  │   Dashboard     │  │   Tracking  │ │
│  │                 │  │                 │  │             │ │
│  │ • Meetings      │  │ • Profile       │  │ • Activity  │ │
│  │ • Sprints       │  │ • Billing       │  │ • Hours     │ │
│  │ • Generated     │  │ • Usage         │  │ • Reports   │ │
│  │   Apps          │  │ • Settings      │  │ • API Data  │ │
│  │ • Storage       │  │ • Delete Account│  │             │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## Self-Service Registration Flow

### Step 1: Landing & Pricing
```
URL: https://ai-diy.ai
Components:
├── Hero section with value proposition
├── Pricing calculator ($5/month + $2/hour)
├── Feature comparison
├── Customer testimonials
└── "Start Free Trial" CTA
```

### Step 2: Account Creation
```
URL: https://ai-diy.ai/signup
Form Fields:
├── Full Name
├── Email Address
├── Company Name (optional)
├── Desired Subdomain: ____.ai-diy.ai
├── Password
└── Terms & Conditions checkbox
```

### Step 3: Payment Information
```
URL: https://ai-diy.ai/payment
Integration: Stripe Elements
Fields:
├── Credit Card Number
├── Expiration Date
├── CVC
├── Billing Address
└── "Subscribe for $5/month + $2/hour usage"
```

### Step 4: Legal Agreements
```
Required Agreements:
├── Terms of Service
├── Privacy Policy
├── Acceptable Use Policy
├── Billing Agreement
└── Service Level Agreement
```

---

## Technical Implementation

### Registration Form Frontend
```html
<!-- signup.html -->
<form id="signupForm" class="max-w-md mx-auto">
  <div class="mb-4">
    <label class="block text-gray-700 text-sm font-bold mb-2">
      Full Name
    </label>
    <input type="text" id="fullName" required
           class="shadow appearance-none border rounded w-full py-2 px-3">
  </div>
  
  <div class="mb-4">
    <label class="block text-gray-700 text-sm font-bold mb-2">
      Email Address
    </label>
    <input type="email" id="email" required
           class="shadow appearance-none border rounded w-full py-2 px-3">
  </div>
  
  <div class="mb-4">
    <label class="block text-gray-700 text-sm font-bold mb-2">
      Company Name
    </label>
    <input type="text" id="companyName"
           class="shadow appearance-none border rounded w-full py-2 px-3">
  </div>
  
  <div class="mb-4">
    <label class="block text-gray-700 text-sm font-bold mb-2">
      Desired Subdomain
    </label>
    <div class="flex">
      <input type="text" id="subdomain" required
             class="shadow appearance-none border rounded-l w-full py-2 px-3">
      <span class="bg-gray-200 border border-l-0 border-gray-300 rounded-r px-3 py-2">
        .ai-diy.ai
      </span>
    </div>
    <p class="text-xs text-gray-600 mt-1">
      This will be your unique URL: company.ai-diy.ai
    </p>
  </div>
  
  <div class="mb-6">
    <label class="flex items-center">
      <input type="checkbox" id="terms" required
             class="mr-2 leading-tight">
      <span class="text-sm">
        I agree to the <a href="/terms" class="underline">Terms of Service</a> 
        and <a href="/privacy" class="underline">Privacy Policy</a>
      </span>
    </label>
  </div>
  
  <button type="submit" 
          class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded w-full">
    Continue to Payment
  </button>
</form>
```

### Backend Registration API
```python
# api/registration.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import stripe
import requests

router = APIRouter()

class RegistrationRequest(BaseModel):
    full_name: str
    email: str
    company_name: str = None
    subdomain: str
    password: str
    terms_accepted: bool

@router.post("/api/register")
async def register_customer(request: RegistrationRequest):
    # 1. Validate subdomain availability
    if not await is_subdomain_available(request.subdomain):
        raise HTTPException(status_code=400, detail="Subdomain not available")
    
    # 2. Create Stripe customer
    stripe_customer = stripe.Customer.create(
        name=request.full_name,
        email=request.email,
        metadata={
            "company_name": request.company_name,
            "subdomain": request.subdomain
        }
    )
    
    # 3. Create subscription
    subscription = stripe.Subscription.create(
        customer=stripe_customer.id,
        items=[{"price": "price_base_fee_5usd"}],
        payment_behavior="default_incomplete",
        expand=["latest_invoice.payment_intent"],
        metadata={"subdomain": request.subdomain}
    )
    
    # 4. Save customer record
    customer_record = {
        "stripe_customer_id": stripe_customer.id,
        "subscription_id": subscription.id,
        "full_name": request.full_name,
        "email": request.email,
        "company_name": request.company_name,
        "subdomain": request.subdomain,
        "status": "pending_payment",
        "created_at": datetime.utcnow()
    }
    
    await save_customer_record(customer_record)
    
    # 5. Return client secret for payment confirmation
    return {
        "customer_id": stripe_customer.id,
        "subscription_id": subscription.id,
        "client_secret": subscription.latest_invoice.payment_intent.client_secret
    }

@router.post("/api/confirm-registration")
async def confirm_registration(subscription_id: str):
    # 1. Verify payment was successful
    subscription = stripe.Subscription.retrieve(subscription_id)
    if subscription.status != "active":
        raise HTTPException(status_code=400, detail="Payment not completed")
    
    # 2. Get customer record
    customer = await get_customer_by_subscription(subscription_id)
    
    # 3. Trigger provisioning
    provisioning_result = await provision_customer_instance(customer)
    
    # 4. Update customer status
    await update_customer_status(customer["id"], "active")
    
    # 5. Send welcome email
    await send_welcome_email(customer["email"], customer["subdomain"])
    
    return {
        "status": "success",
        "instance_url": f"https://{customer['subdomain']}.ai-diy.ai",
        "login_url": f"https://{customer['subdomain']}.ai-diy.ai"
    }
```

### Automated Provisioning Integration
```python
# services/provisioning.py
async def provision_customer_instance(customer):
    """Provision new customer instance after successful payment"""
    
    subdomain = customer["subdomain"]
    customer_id = customer["id"]
    
    # 1. Create Railway project
    railway_project = f"ai-diy-{customer_id}"
    await create_railway_project(railway_project)
    
    # 2. Deploy AI-DIY code
    await deploy_to_railway(railway_project)
    
    # 3. Get Railway URL
    railway_url = await get_railway_domain(railway_project)
    
    # 4. Create DNS record
    await create_dns_record(subdomain, railway_url)
    
    # 5. Set up Cloudflare Access
    await create_cloudflare_access_policy(subdomain, railway_url)
    
    # 6. Add to instances list
    await add_customer_instance(customer_id, railway_project, subdomain)
    
    # 7. Initialize usage tracking
    await initialize_usage_tracking(customer_id)
    
    return {
        "project_name": railway_project,
        "instance_url": f"https://{subdomain}.ai-diy.ai",
        "railway_url": railway_url
    }
```

---

## Billing System Integration

### Stripe Configuration
```python
# config/stripe.py
import stripe

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Prices (in cents)
BASE_FEE_PRICE = 500  # $5.00
HOURLY_RATE = 200    # $2.00

# Create prices if they don't exist
BASE_FEE_PRICE_ID = "price_base_fee_5usd"
HOURLY_METER_ID = "price_hourly_2usd"

async def create_billing_subscription(customer_id: str, payment_method_id: str):
    """Create subscription with base fee + usage-based billing"""
    
    subscription = stripe.Subscription.create(
        customer=customer_id,
        items=[
            {"price": BASE_FEE_PRICE_ID},
            {"price": HOURLY_METER_ID, "quantity": 0}  # Will be updated hourly
        ],
        default_payment_method=payment_method_id,
        expand=["latest_invoice.payment_intent"]
    )
    
    return subscription

async def record_usage(customer_id: str, hours: int):
    """Record hourly usage for billing"""
    
    subscription = await get_customer_subscription(customer_id)
    
    stripe.SubscriptionItem.create_usage_record(
        subscription["items"]["data"][1]["id"],  # Hourly meter item
        quantity=hours * 100,  # Stripe uses units (100 = $1.00)
        action="set"
    )
```

### Usage Tracking System
```python
# services/usage_tracking.py
async def track_customer_usage():
    """Daily job to track usage and bill customers"""
    
    customers = await get_all_active_customers()
    
    for customer in customers:
        # Get usage from multiple sources
        railway_usage = await get_railway_usage(customer["id"])
        cloudflare_sessions = await get_cloudflare_sessions(customer["id"])
        sprint_activity = await get_sprint_activity(customer["id"])
        
        # Calculate billable hours
        billable_hours = calculate_billable_hours(
            railway_usage, cloudflare_sessions, sprint_activity
        )
        
        if billable_hours > 0:
            # Record usage in Stripe
            await record_usage(customer["stripe_customer_id"], billable_hours)
            
            # Update local usage log
            await log_usage(customer["id"], billable_hours, date.today())

def calculate_billable_hours(railway, cloudflare, sprint):
    """Any activity in an hour = billable hour"""
    
    active_hours = set()
    
    # Add hours from Railway uptime
    active_hours.update(railway["active_hours"])
    
    # Add hours from Cloudflare sessions
    active_hours.update(cloudflare["active_hours"])
    
    # Add hours from sprint execution
    active_hours.update(sprint["active_hours"])
    
    return len(active_hours)
```

---

## Account Management Portal

### Customer Dashboard
```html
<!-- customer-dashboard.html -->
<div class="max-w-6xl mx-auto p-6">
  <!-- Profile Section -->
  <section class="mb-8">
    <h2 class="text-2xl font-bold mb-4">Profile Information</h2>
    <div class="bg-white rounded-lg shadow p-6">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label class="block text-sm font-medium text-gray-700">Full Name</label>
          <input type="text" id="fullName" value="{{customer.full_name}}" 
                 class="mt-1 block w-full rounded-md border-gray-300 shadow-sm">
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Email</label>
          <input type="email" id="email" value="{{customer.email}}" 
                 class="mt-1 block w-full rounded-md border-gray-300 shadow-sm">
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Company</label>
          <input type="text" id="companyName" value="{{customer.company_name}}" 
                 class="mt-1 block w-full rounded-md border-gray-300 shadow-sm">
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700">Instance URL</label>
          <input type="text" value="https://{{customer.subdomain}}.ai-diy.ai" 
                 readonly class="mt-1 block w-full rounded-md bg-gray-100 border-gray-300">
        </div>
      </div>
      <button onclick="updateProfile()" 
              class="mt-4 bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700">
        Update Profile
      </button>
    </div>
  </section>

  <!-- Billing Section -->
  <section class="mb-8">
    <h2 class="text-2xl font-bold mb-4">Billing & Usage</h2>
    <div class="bg-white rounded-lg shadow p-6">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div class="text-center">
          <p class="text-sm text-gray-600">Current Month Bill</p>
          <p class="text-2xl font-bold">${{billing.current_month_total}}</p>
        </div>
        <div class="text-center">
          <p class="text-sm text-gray-600">Usage Hours</p>
          <p class="text-2xl font-bold">{{billing.current_month_hours}}</p>
        </div>
        <div class="text-center">
          <p class="text-sm text-gray-600">Next Billing Date</p>
          <p class="text-2xl font-bold">{{billing.next_billing_date}}</p>
        </div>
      </div>
      
      <!-- Usage History -->
      <div class="mt-6">
        <h3 class="text-lg font-semibold mb-3">Usage History</h3>
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Usage Hours</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Base Fee</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Usage Total</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Total</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              {% for invoice in billing.invoices %}
              <tr>
                <td class="px-6 py-4 whitespace-nowrap">{{invoice.date}}</td>
                <td class="px-6 py-4 whitespace-nowrap">{{invoice.hours}}</td>
                <td class="px-6 py-4 whitespace-nowrap">$5.00</td>
                <td class="px-6 py-4 whitespace-nowrap">${{invoice.usage_total}}</td>
                <td class="px-6 py-4 whitespace-nowrap font-semibold">${{invoice.total}}</td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </section>

  <!-- Payment Methods -->
  <section class="mb-8">
    <h2 class="text-2xl font-bold mb-4">Payment Methods</h2>
    <div class="bg-white rounded-lg shadow p-6">
      <div id="payment-methods">
        <!-- Payment methods loaded via JavaScript -->
      </div>
      <button onclick="addPaymentMethod()" 
              class="mt-4 bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700">
        Add Payment Method
      </button>
    </div>
  </section>

  <!-- Danger Zone -->
  <section class="mb-8">
    <h2 class="text-2xl font-bold mb-4 text-red-600">Account Management</h2>
    <div class="bg-white rounded-lg shadow p-6 border-2 border-red-200">
      <div class="bg-red-50 border-l-4 border-red-400 p-4 mb-4">
        <div class="flex">
          <div class="ml-3">
            <p class="text-sm text-red-700">
              <strong>Warning:</strong> Deleting your account is permanent and will immediately:
            </p>
            <ul class="list-disc list-inside text-sm text-red-700 mt-2">
              <li>Delete all your data and generated applications</li>
              <li>Cancel your subscription and stop all billing</li>
              <li>Remove access to your instance at {{customer.subdomain}}.ai-diy.ai</li>
              <li>Delete your Railway instance and all associated resources</li>
            </ul>
          </div>
        </div>
      </div>
      
      <button onclick="initiateAccountDeletion()" 
              class="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700">
        Delete My Account
      </button>
    </div>
  </section>
</div>
```

### Account Deletion Process
```python
# api/account_management.py
@router.post("/api/delete-account")
async def delete_account(customer_id: str, confirmation: str):
    """Permanent account deletion with confirmation"""
    
    if confirmation.lower() != "delete my account":
        raise HTTPException(status_code=400, detail="Confirmation text does not match")
    
    customer = await get_customer_by_id(customer_id)
    
    # 1. Cancel Stripe subscription
    stripe.Subscription.delete(customer["subscription_id"])
    
    # 2. Delete Railway instance
    await delete_railway_project(f"ai-diy-{customer_id}")
    
    # 3. Remove DNS record
    await delete_dns_record(customer["subdomain"])
    
    # 4. Remove Cloudflare Access policy
    await delete_cloudflare_access_policy(customer["subdomain"])
    
    # 5. Delete customer data
    await delete_all_customer_data(customer_id)
    
    # 6. Send confirmation email
    await send_deletion_confirmation(customer["email"])
    
    # 7. Log deletion for compliance
    await log_account_deletion(customer_id, customer["email"])
    
    return {"status": "success", "message": "Account permanently deleted"}
```

---

## Legal & Compliance

### Required Legal Documents
```html
<!-- Terms of Service Structure -->
<div class="max-w-4xl mx-auto p-6">
  <h1>AI-DIY Terms of Service</h1>
  
  <section>
    <h2>1. Service Description</h2>
    <p>AI-DIY provides a platform for automated application development...</p>
  </section>
  
  <section>
    <h2>2. Billing and Payment</h2>
    <ul>
      <li>Base fee: $5.00 USD per month</li>
      <li>Usage fee: $2.00 USD per hour (any part of an hour counts as full hour)</li>
      <li>Billing occurs monthly on anniversary date</li>
      <li>Usage is tracked and billed in real-time</li>
    </ul>
  </section>
  
  <section>
    <h2>3. Account Responsibilities</h2>
    <p>Customers are responsible for...</p>
  </section>
  
  <section>
    <h2>4. Data and Privacy</h2>
    <p>All customer data is isolated and stored separately...</p>
  </section>
  
  <section>
    <h2>5. Service Availability</h2>
    <p>We strive for 99.5% uptime but do not guarantee availability...</p>
  </section>
  
  <section>
    <h2>6. Cancellation and Refunds</h2>
    <ul>
      <li>Cancel anytime through account dashboard</li>
      <li>No refunds for partial months</li>
      <li>Data deleted immediately upon cancellation</li>
    </ul>
  </section>
  
  <section>
    <h2>7. Limitation of Liability</h2>
    <p>AI-DIY is not liable for...</p>
  </section>
</div>
```

### Compliance Features
```python
# services/compliance.py
async def handle_gdpr_request(email: str, request_type: str):
    """Handle GDPR data requests"""
    
    if request_type == "access":
        customer_data = await get_customer_data_by_email(email)
        return await export_customer_data(customer_data)
    
    elif request_type == "deletion":
        # Similar to delete_account but with GDPR logging
        await initiate_gdpr_deletion(email)
        return {"status": "deletion_initiated"}
    
    elif request_type == "rectification":
        # Handle data correction requests
        return await.rectify_customer_data(email, request_data)

async def log_consent(customer_id: str, consent_type: str, consent_given: bool):
    """Log consent for compliance"""
    
    consent_record = {
        "customer_id": customer_id,
        "consent_type": consent_type,
        "consent_given": consent_given,
        "timestamp": datetime.utcnow(),
        "ip_address": request.client.host
    }
    
    await save_consent_record(consent_record)
```

---

## Integration Points with Main Architecture

### 1. Registration → Provisioning Flow
```
Marketing Website → Registration API → Payment → Provisioning System → Railway Instance
```

### 2. Billing → Usage Tracking Integration
```
Usage Trackers → Daily Aggregation → Stripe Billing → Customer Dashboard
```

### 3. Account Management → Instance Lifecycle
```
Customer Dashboard → Account APIs → Railway Management → DNS/Cloudflare Updates
```

### 4. Compliance → Data Management
```
Legal Requirements → Data Policies → Storage Systems → Deletion Processes
```

---

## Implementation Priority

### Phase 1: Core Registration (Week 1-2)
- [ ] Registration forms and validation
- [ ] Stripe payment integration
- [ ] Basic provisioning system
- [ ] Legal terms and agreements

### Phase 2: Billing & Usage (Week 3-4)
- [ ] Usage tracking implementation
- [ ] Automated billing system
- [ ] Customer dashboard
- [ ] Invoice generation

### Phase 3: Account Management (Week 5-6)
- [ ] Account settings and updates
- [ ] Payment method management
- [ ] Usage reports and analytics
- [ ] Cancellation process

### Phase 4: Compliance & Optimization (Week 7-8)
- [ ] GDPR compliance features
- [ ] Data export tools
- [ ] Advanced analytics
- [ ] Retention and win-back features

---

## Success Metrics

### Registration Metrics
- [ ] Sign-up conversion rate > 15%
- [ ] Payment completion rate > 80%
- [ ] Time-to-first-instance < 10 minutes

### Billing Metrics
- [ ] Payment success rate > 95%
- [ ] Churn rate < 5% monthly
- [ ] Average revenue per user > $15/month

### Self-Service Metrics
- [ ] Support ticket reduction > 50%
- [ ] Account modification success rate > 90%
- [ ] Customer satisfaction > 4.5/5

---

*This supplement integrates directly with the main multi-tenant architecture, providing the complete business and technical foundation for customer self-service operations.*
