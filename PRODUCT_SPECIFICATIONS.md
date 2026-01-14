# Take My Dictation - Product Specifications
**THE HOLY GRAIL - No deviation allowed without approval**

---

## User Flows

### Free Trial User Flow
1. Lands on takemydictation.ai
2. Enters email (no verification needed)
3. Records audio (up to 10 minutes - one-time free trial)
4. Clicks Stop → Processing happens (10-20 seconds)
5. Gets full transcript displayed
6. Chooses summary format from buttons
7. Views generated summary on temporary page
8. Can download as Word/PDF immediately
9. Sees "Subscribe to save summaries and get unlimited recording" message
10. If returns with same email → "You've used your free 10 minutes. Subscribe for unlimited recording."

### Paid User Flow (Basic/Pro)
1. User decides to subscribe
2. Enters password (creates account)
3. Receives 6-digit verification code via email
4. Enters code to verify email
5. Chooses plan (Basic or Pro, Monthly or Annual)
6. Enters payment details via Stripe
7. Payment successful → redirected to dashboard
8. Can record within their monthly hour limit
9. After recording → chooses format → gets summary
10. Can save summary to dashboard with custom name
11. Can download summaries anytime as Word/PDF
12. Pro users: Can choose to save audio for 10 days to regenerate summaries in different formats

---

## Features & Pricing

### Free Trial
- **10 minutes** of recording (one-time use per email)
- All summary formats available
- Download Word/PDF immediately
- No dashboard access
- No login after session ends
- Audio deleted immediately after processing

### Basic Plan - $9.99/month or $99/year
- **10 hours** of recording per month
- All summary formats
- Save summaries to dashboard with custom names
- Download as Word/PDF anytime
- Audio deleted after processing (cannot save audio)
- Hours reset on subscription anniversary date

### Pro Plan - $19.99/month or $199/year
- **50 hours** of recording per month
- All summary formats
- Save summaries to dashboard with custom names
- Download as Word/PDF anytime
- **Can choose to save audio for 10 days** (option shown after summary)
- **Regenerate summaries in different formats** without re-recording
- Hours reset on subscription anniversary date

---

## Summary Format Options

Users can choose from 4 summary formats:

### 1. Meeting Notes
**Structure:**
- Attendees
- Discussion points
- Action items
- Next steps

### 2. Product Spec
**Structure:**
- Problem statement
- Solution
- User stories
- Requirements

### 3. MOM (Minutes of Meeting)
**Structure:**
- Formal meeting minutes format
- Date, time, attendees
- Agenda items
- Decisions made
- Action items with owners

### 4. Quick Summary
**Structure:**
- Concise overview
- Key points only
- Brief and to the point

---

## Audio Storage Policy

### Free Users
- Audio deleted **immediately** after processing
- No storage or retention
- Must re-record for new summary

### Basic Users
- Audio deleted **immediately** after processing
- No storage or retention
- Must re-record for new summary

### Pro Users
- **Option to save audio for 10 days max** (user choice)
- Default: Save for 10 days with option to delete immediately
- UI Message: "Your audio is saved for 10 days so you can regenerate different formats. [Delete now] or it auto-deletes on [date]"
- After 10 days: Automatic deletion via background job
- Can regenerate summaries in any format during 10-day window

---

## Technical Requirements

### User Management
- Trial users: Email only, no password, temporary session
- Paid users: Email + password, email verification required
- Email verification: 6-digit code, 15-minute expiration
- Session management: Short-lived for trials, persistent for paid

### Usage Tracking
- Track recording duration per user
- Accumulate monthly hours used
- Reset on subscription anniversary date
- Enforce limits: 10h (Basic), 50h (Pro)
- Warn at 80% usage
- Block at 100% usage

### Subscription Management
- Support monthly and annual billing
- Proration for plan changes
- Upgrade/downgrade between Basic and Pro
- Stripe integration for payments
- Webhook handling for subscription events

### Audio Management
- Immediate deletion for Free/Basic users
- 10-day retention for Pro users (optional)
- Background job for cleanup
- Physical file deletion from storage
- Keep transcription and summary after audio deletion

### Summary Management
- 4 format options with specific AI prompts
- Custom naming for saved summaries
- Regenerate from saved audio (Pro only)
- Export to Word and PDF
- Save to dashboard (paid users only)

### Rate Limiting
- Trial users: Stricter limits to prevent abuse
- Track by email for trials
- Track by user_id for paid users
- Prevent multiple trial uses with same email

---

## Business Rules

### Trial Limitations
1. One trial per email address (cannot reuse)
2. 10-minute maximum recording length
3. No dashboard access
4. No saving summaries (download only)
5. Session expires after use
6. Must subscribe to save or record more

### Basic Plan Limitations
1. 10 hours per month maximum
2. Cannot save audio
3. Cannot regenerate summaries
4. Must re-record for different format

### Pro Plan Benefits
1. 50 hours per month (5x Basic)
2. Save audio for 10 days
3. Regenerate summaries without re-recording
4. Try different formats on same audio

### Monthly Reset Logic
- Usage resets on subscription anniversary date
- Not calendar month
- Example: Subscribed Jan 15 → resets Feb 15, Mar 15, etc.
- Unused hours do NOT roll over

---

## User Experience Priorities

### Trial Experience
- **Frictionless:** Email only, immediate access
- **Value demonstration:** Show full capabilities
- **Clear upgrade path:** Obvious benefits of subscribing
- **No frustration:** Let them complete the trial experience

### Paid User Experience
- **Worth the money:** Highlight time savings and convenience
- **Dashboard value:** Easy access to all past summaries
- **Pro differentiation:** Clear value in audio retention
- **Usage transparency:** Always show remaining hours

### Conversion Strategy
- Trial users see results immediately
- Upgrade CTA after seeing value
- Emphasize "save summaries" benefit
- Show pricing at key moments
- Make Basic → Pro upgrade easy

---

## Success Metrics

### Trial Metrics
- Trial starts per day
- Trial completion rate
- Trial-to-paid conversion rate
- Average trial duration used

### User Metrics
- Monthly active users by tier
- Average hours used per tier
- Churn rate by tier
- Upgrade rate (Basic → Pro)

### Revenue Metrics
- MRR (Monthly Recurring Revenue)
- ARR (Annual Recurring Revenue)
- ARPU (Average Revenue Per User)
- LTV (Lifetime Value)

### Usage Metrics
- Popular summary formats
- Audio retention usage (Pro)
- Regeneration frequency (Pro)
- Export format preference (Word vs PDF)

---

## Future Considerations (NOT IN SCOPE NOW)

- Team/organization accounts
- API access for developers
- Custom AI prompt templates
- Integration with other tools
- Mobile app
- Real-time transcription
- Speaker identification
- Language translation

---

## Compliance Notes

✅ All features must match this specification exactly
✅ No feature creep without approval
✅ Trial flow is non-negotiable
✅ Pricing is fixed ($9.99/$19.99)
✅ Usage limits are hard constraints
✅ Audio retention policy must be enforced
✅ Email verification required for paid accounts only

**Last Updated:** January 15, 2026
**Version:** 1.0 (HOLY GRAIL)
