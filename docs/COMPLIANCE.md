# RecoverAI — Compliance Documentation

## Regulatory Framework

RecoverAI is designed with compliance as a first-class concern, not an afterthought. Every automated decision is bounded by deterministic guardrails that cannot be bypassed by the AI system.

## Key Compliance Controls

### 1. RBI e-Mandate Rules
- **Pre-debit notice**: 24-hour notice before re-presenting a mandate debit
- **AFA threshold**: Transactions above RBI threshold require additional factor authentication
- **Mandate lifecycle**: Mandate revoked/expired → STOP, never retry automatically

### 2. TRAI Regulations
- **Calling hours**: 9 AM – 9 PM IST only
- **DND (Do Not Disturb)**: Respect registered DND numbers
- **Consent**: Only contact customers who have existing relationship
- **Frequency caps**: Maximum 3 contact attempts per payment

### 3. Data Protection
- **No secrets in prompts**: LLM prompts never contain API keys or secrets
- **No real financial data**: All demo data is synthetic
- **Session security**: Secure cookie configuration in production
- **Password hashing**: Werkzeug password hashing (never plaintext)

### 4. Payment Security
- **Test-mode only**: All Razorpay integration uses test credentials
- **Server-side secrets**: API keys never exposed to frontend
- **Webhook verification**: HMAC signature verification on all incoming webhooks
- **Idempotency**: Every action has a unique idempotency key

## Guardrails Matrix

| Gate | Description | Enforcement |
|---|---|---|
| G1 | Transaction already recovered | Block action |
| G2 | Max retry count exceeded | Block action |
| G3 | Amount above auto-limit | Require human approval |
| G4 | Duplicate action detected | Block action |
| G5 | Terminal failure (card expired) | Block retry, send update link |
| G6 | Mandate revoked | Block all auto-actions |
| G7 | Fraud flag present | Escalate to manual review |
| G8 | Outside calling hours | Defer voice, use WhatsApp |
| G9 | DND registered | Block SMS/WhatsApp |

## Stopping Rules

Every stop produces an auditable reason:

1. `TRANSACTION_RECOVERED` — No action needed
2. `MAX_RETRIES_EXCEEDED` — Retry limit reached
3. `RECOVERY_WINDOW_EXPIRED` — Too late to recover
4. `POLICY_CHECK_FAILED` — Policy engine blocked
5. `APPROVAL_REJECTED` — Human denied approval
6. `DUPLICATE_ACTION` — Idempotency protection
7. `INSUFFICIENT_EVIDENCE` — AI lacks confidence
8. `NON_RETRYABLE_FAILURE` — External API permanent failure
9. `MONETARY_LIMIT_EXCEEDED` — Amount too high for auto-action

## Audit Trail

Every decision is recorded in two systems:

### 1. Standard Audit Log
- Event type, actor, timestamp
- Previous/new state, reason
- Model version, correlation ID

### 2. Hash-Chained Ledger
- SHA-256 hash chain (tamper-evident)
- Sequence numbers
- Previous hash reference
- Verification API available

**Tampering with any record breaks the chain at that exact sequence number.**

## Responsible AI

### What the AI does:
- Analyzes transaction context
- Recommends recovery actions
- Provides explanations

### What the AI never does:
- Bypasses policy engine
- Executes payments directly
- Accesses API secrets
- Makes unlimited autonomous decisions

### Fallback guarantee:
When AI is unavailable, the system falls back to deterministic rules and logs the fallback event.
