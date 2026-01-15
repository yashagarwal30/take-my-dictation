# Take My Dictation - API Documentation

**Version:** 1.0.0
**Base URL:** `http://localhost:8000` (development)

Complete API reference for the Take My Dictation voice transcription service.

---

## Table of Contents

1. [Authentication](#authentication)
2. [Trial Flow](#trial-flow)
3. [User Management](#user-management)
4. [Recordings](#recordings)
5. [Transcriptions](#transcriptions)
6. [Summaries](#summaries)
7. [Payments & Subscriptions](#payments--subscriptions)
8. [Analytics (Admin)](#analytics-admin)
9. [Admin Panel](#admin-panel)
10. [Error Handling](#error-handling)

---

## Authentication

### Register New User
**POST** `/auth/register`

Create a new paid user account with email verification.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "message": "Registration successful. Please verify your email.",
  "user_id": "uuid",
  "email": "user@example.com"
}
```

### Send Verification Code
**POST** `/auth/send-verification`

Send 6-digit verification code to email.

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "message": "Verification code sent to user@example.com",
  "expires_in_minutes": 15
}
```

### Verify Email
**POST** `/auth/verify-email`

Verify email with 6-digit code.

**Request Body:**
```json
{
  "email": "user@example.com",
  "code": "123456"
}
```

**Response:**
```json
{
  "message": "Email verified successfully",
  "verified": true
}
```

### Login
**POST** `/auth/login`

Login with email and password.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "access_token": "jwt_token_here",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "subscription_tier": "BASIC"
  }
}
```

---

## Trial Flow

### Start Free Trial
**POST** `/trials/start`

Start a 10-minute free trial with email only (no password required).

**Request Body:**
```json
{
  "trial_email": "trial@example.com"
}
```

**Response:**
```json
{
  "access_token": "trial_jwt_token",
  "token_type": "bearer",
  "trial_user": {
    "id": "uuid",
    "trial_email": "trial@example.com",
    "trial_minutes_limit": 10.0,
    "trial_minutes_remaining": 10.0
  },
  "message": "Trial started successfully. You have 10 minutes of free recording time."
}
```

### Get Trial Usage
**GET** `/trials/usage`

Check remaining trial time (requires trial token).

**Headers:**
```
Authorization: Bearer {trial_token}
```

**Response:**
```json
{
  "trial_minutes_used": 3.5,
  "trial_minutes_limit": 10.0,
  "trial_minutes_remaining": 6.5,
  "usage_percentage": 35.0,
  "limit_exceeded": false
}
```

### Convert Trial to Paid
**POST** `/auth/convert-trial`

Convert trial account to paid subscription.

**Headers:**
```
Authorization: Bearer {trial_token}
```

**Request Body:**
```json
{
  "password": "newpassword123",
  "subscription_tier": "BASIC"
}
```

**Response:**
```json
{
  "message": "Trial converted to paid account",
  "user_id": "uuid",
  "subscription_tier": "BASIC"
}
```

---

## User Management

### Get Current User
**GET** `/users/me`

Get current authenticated user's information.

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "subscription_tier": "BASIC",
  "monthly_hours_used": 5.5,
  "monthly_hours_limit": 10.0,
  "monthly_hours_remaining": 4.5,
  "usage_reset_at": "2026-02-15T00:00:00Z"
}
```

### Get Usage Statistics
**GET** `/users/usage`

Get detailed usage statistics for current user.

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "user_type": "paid",
  "subscription_tier": "BASIC",
  "monthly_hours_used": 5.5,
  "monthly_hours_limit": 10.0,
  "monthly_hours_remaining": 4.5,
  "usage_percentage": 55.0,
  "reset_date": "2026-02-15T00:00:00Z",
  "subscription_anniversary_date": 15
}
```

---

## Recordings

### Upload Recording
**POST** `/recordings/upload`

Upload audio file for transcription.

**Headers:**
```
Authorization: Bearer {access_token}
Content-Type: multipart/form-data
```

**Form Data:**
```
file: <audio_file.mp3>
custom_name: "Meeting Notes Jan 15" (optional)
```

**Response:**
```json
{
  "id": "recording_uuid",
  "filename": "audio_file.mp3",
  "file_size": 2048576,
  "duration": 300.5,
  "status": "uploaded",
  "custom_name": "Meeting Notes Jan 15",
  "created_at": "2026-01-15T10:00:00Z"
}
```

### Get User Recordings
**GET** `/recordings`

Get all recordings for current user.

**Headers:**
```
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `skip`: Pagination offset (default: 0)
- `limit`: Max results (default: 50)

**Response:**
```json
{
  "total": 25,
  "recordings": [
    {
      "id": "uuid",
      "filename": "recording1.mp3",
      "custom_name": "Team Meeting",
      "duration": 1800.0,
      "status": "completed",
      "can_regenerate": true,
      "audio_delete_at": "2026-01-25T00:00:00Z",
      "created_at": "2026-01-15T10:00:00Z"
    }
  ]
}
```

### Rename Recording
**PUT** `/recordings/{recording_id}/rename`

Update custom name for a recording.

**Request Body:**
```json
{
  "custom_name": "Updated Meeting Name"
}
```

**Response:**
```json
{
  "success": true,
  "recording_id": "uuid",
  "custom_name": "Updated Meeting Name"
}
```

---

## Transcriptions

### Create Transcription
**POST** `/transcriptions`

Create transcription from uploaded recording.

**Request Body:**
```json
{
  "recording_id": "recording_uuid"
}
```

**Response:**
```json
{
  "id": "transcription_uuid",
  "recording_id": "recording_uuid",
  "text": "Full transcription text...",
  "word_count": 1500,
  "status": "completed",
  "created_at": "2026-01-15T10:05:00Z"
}
```

### Get Transcription
**GET** `/transcriptions/{transcription_id}`

Get specific transcription.

**Response:**
```json
{
  "id": "uuid",
  "recording_id": "recording_uuid",
  "text": "Transcription text...",
  "word_count": 1500,
  "status": "completed"
}
```

---

## Summaries

### Create Summary
**POST** `/summaries`

Generate AI summary from transcription.

**Request Body:**
```json
{
  "transcription_id": "transcription_uuid",
  "format": "MEETING_NOTES",
  "custom_prompt": "Focus on action items" (optional)
}
```

**Formats:**
- `QUICK_SUMMARY`: Concise overview
- `MEETING_NOTES`: Structured meeting notes
- `PRODUCT_SPEC`: Product specification format
- `MOM`: Minutes of Meeting (formal)

**Response:**
```json
{
  "id": "summary_uuid",
  "transcription_id": "transcription_uuid",
  "format": "MEETING_NOTES",
  "text": "Summary content...",
  "word_count": 250,
  "status": "completed"
}
```

### Regenerate Summary
**POST** `/summaries/regenerate`

Create new summary with different format (Pro users only, requires audio retention).

**Request Body:**
```json
{
  "recording_id": "recording_uuid",
  "format": "PRODUCT_SPEC"
}
```

### Rename Summary
**PUT** `/summaries/{summary_id}/rename`

Update custom name for a summary.

**Request Body:**
```json
{
  "custom_name": "Q1 Strategy Meeting"
}
```

### Export Summary
**GET** `/summaries/{summary_id}/export?format=word`

Export summary as Word or PDF.

**Query Parameters:**
- `format`: `word` or `pdf`

**Response:** Binary file download

---

## Payments & Subscriptions

### Get Pricing Plans
**GET** `/payments/plans`

Get available subscription plans.

**Response:**
```json
{
  "plans": [
    {
      "name": "Basic",
      "monthly_price": 9.99,
      "annual_price": 99.00,
      "hours_per_month": 10,
      "features": ["10 hours/month", "Basic summaries", "Download as PDF/Word"]
    },
    {
      "name": "Pro",
      "monthly_price": 19.99,
      "annual_price": 199.00,
      "hours_per_month": 50,
      "features": ["50 hours/month", "All summary formats", "10-day audio retention", "Regenerate summaries"]
    }
  ]
}
```

### Create Checkout Session
**POST** `/payments/create-checkout-session`

Create Stripe checkout session for subscription.

**Request Body:**
```json
{
  "plan": "BASIC",
  "interval": "monthly"
}
```

**Response:**
```json
{
  "checkout_url": "https://checkout.stripe.com/...",
  "session_id": "stripe_session_id"
}
```

### Change Subscription Plan
**POST** `/payments/change-plan`

Upgrade or downgrade subscription.

**Request Body:**
```json
{
  "new_plan": "PRO"
}
```

---

## Analytics (Admin)

### Get Analytics Overview
**GET** `/analytics/overview`

Get comprehensive analytics dashboard (admin only).

**Headers:**
```
Authorization: Bearer {admin_token}
```

**Response:**
```json
{
  "overview": {
    "total_paid_users": 150,
    "total_trial_users": 45,
    "total_recordings": 3200,
    "total_summaries": 2800
  },
  "trial_conversion": {
    "trial_starts": 120,
    "conversions": 35,
    "conversion_rate_percent": 29.17
  },
  "usage_by_tier": {
    "BASIC": {
      "user_count": 80,
      "avg_hours_used": 6.5
    },
    "PRO": {
      "user_count": 70,
      "avg_hours_used": 22.3
    }
  }
}
```

### Get Conversion Metrics
**GET** `/analytics/conversions?days=30`

### Get Usage by Tier
**GET** `/analytics/usage-by-tier`

### Get Popular Formats
**GET** `/analytics/popular-formats?days=30`

### Get Churn Rate
**GET** `/analytics/churn?days=30`

---

## Admin Panel

### Get Admin Dashboard
**GET** `/admin/dashboard`

Comprehensive admin dashboard with all metrics.

### Get All Users
**GET** `/admin/users?skip=0&limit=50&tier=BASIC&search=john`

List all users with filtering and pagination.

**Query Parameters:**
- `skip`: Offset for pagination
- `limit`: Max results (1-100)
- `tier`: Filter by tier (FREE, BASIC, PRO, TRIAL)
- `search`: Search by email

### Get User Details
**GET** `/admin/users/{user_id}`

Get detailed information about specific user.

### Update User Limits
**PUT** `/admin/users/{user_id}/limits`

Manually adjust user limits for support.

**Request Body:**
```json
{
  "monthly_hours_limit": 15.0,
  "monthly_hours_used": 5.0
}
```

---

## Error Handling

### Standard Error Response
```json
{
  "detail": "Error message here"
}
```

### HTTP Status Codes
- `200`: Success
- `201`: Created
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden (usage limit, feature gate)
- `404`: Not Found
- `422`: Validation Error
- `500`: Server Error

### Common Error Messages

**Trial Limit Exceeded:**
```json
{
  "detail": "Trial limit exceeded. You've used your free 10 minutes. Subscribe for unlimited recording."
}
```

**Usage Limit Reached:**
```json
{
  "detail": "Monthly limit reached. Resets on February 15, 2026."
}
```

**Feature Gated:**
```json
{
  "detail": "Audio retention is only available for Pro users. Upgrade to Pro to enable 10-day audio retention."
}
```

---

## Rate Limiting

All endpoints are rate-limited:
- Auth endpoints: 5 requests/minute
- Trial endpoints: 10 requests/minute
- Upload endpoints: 20 requests/minute

Rate limit headers included in responses:
```
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 3
X-RateLimit-Reset: 1642251600
```

---

## Webhooks

### Stripe Webhook
**POST** `/payments/webhook`

Stripe sends payment events here. Validates signature and processes:
- `checkout.session.completed`: Activate subscription
- `customer.subscription.updated`: Update tier
- `customer.subscription.deleted`: Cancel subscription

---

## Development

**API Documentation (Interactive):** `http://localhost:8000/docs`
**OpenAPI Schema:** `http://localhost:8000/openapi.json`

**Testing:**
```bash
# Run tests
python -m pytest

# Run specific test suite
python test_monthly_reset.py
python test_audio_cleanup.py
```

---

## Support

For API support or questions:
- Email: support@takemydictation.ai
- Documentation: https://docs.takemydictation.ai
- GitHub Issues: https://github.com/yashagarwal30/take-my-dictation/issues

---

**Last Updated:** January 15, 2026
**API Version:** 1.0.0
