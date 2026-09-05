import os
import logging
import json

logger = logging.getLogger(__name__)

AI_ACTION_ENUM = ['RETRY', 'SEND_PAYMENT_LINK', 'SEND_REMINDER', 'ESCALATE', 'NO_ACTION']


def get_ai_recommendation(context):
    api_key = os.environ.get('LLM_API_KEY', '')
    if not api_key:
        logger.warning("LLM_API_KEY not set, using fallback")
        return get_fallback_recommendation(context)

    try:
        return _call_llm(context, api_key)
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return get_fallback_recommendation(context)


def _call_llm(context, api_key):
    provider = os.environ.get('LLM_PROVIDER', 'openai')
    model = os.environ.get('LLM_MODEL', 'gpt-3.5-turbo')

    system_prompt = """You are RecoverAI, an autonomous payment recovery agent.
Your role is to recommend the best recovery action for a failed payment.

You MUST choose exactly one action from: RETRY, SEND_PAYMENT_LINK, SEND_REMINDER, ESCALATE, NO_ACTION

Rules:
- RETRY: For temporary failures with good payment history and no previous retries
- SEND_PAYMENT_LINK: When customer needs to complete/continue payment
- SEND_REMINDER: For abandoned or eligible payments with moderate history
- ESCALATE: For high-value, uncertain, or high-risk cases
- NO_ACTION: When probability is very low or action would be unsafe

You MUST respond with valid JSON only:
{
  "action": "ACTION_NAME",
  "confidence": 0.0-1.0,
  "reason": "Brief explanation",
  "requires_human_approval": true/false
}

Never include any text outside the JSON object."""

    user_prompt = f"""Analyze this failed payment and recommend a recovery action:

Transaction: {context.get('transaction_id')}
Amount: ₹{context.get('amount', 0)}
Failure Reason: {context.get('failure_reason', 'unknown')}
Retry Count: {context.get('retry_count', 0)}
Customer Success Rate: {context.get('previous_success_rate', 0)}
Recovery Probability: {context.get('recovery_probability', 0.5)}
Payment Method: {context.get('payment_method', 'unknown')}

Provide your recommendation as JSON."""

    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=300
        )

        content = response.choices[0].message.content.strip()
        if content.startswith('```'):
            content = content.split('\n', 1)[1].rsplit('```', 1)[0].strip()

        result = json.loads(content)
        result['decision_source'] = 'AI_AGENT'
        result['model_version'] = model

        if result.get('action') not in AI_ACTION_ENUM:
            result['action'] = 'ESCALATE'
            result['confidence'] = 0.5
            result['reason'] = f"Invalid action from LLM, escalating. Original: {result.get('action')}"

        if result.get('confidence', 0) < 0.3:
            result['requires_human_approval'] = True

        return result

    except json.JSONDecodeError:
        logger.error("LLM returned invalid JSON")
        return get_fallback_recommendation(context)
    except Exception as e:
        logger.error(f"LLM error: {e}")
        return get_fallback_recommendation(context)


def get_fallback_recommendation(context):
    probability = context.get('recovery_probability', 0.5)
    retry_count = context.get('retry_count', 0)
    amount = context.get('amount', 0)
    failure_reason = context.get('failure_reason', '')
    success_rate = context.get('previous_success_rate', 0.5)

    if retry_count >= 2:
        return {
            'action': 'NO_ACTION',
            'confidence': 0.8,
            'reason': f'Maximum retry attempts reached ({retry_count})',
            'requires_human_approval': False,
            'decision_source': 'FALLBACK_RULE',
            'model_version': 'rule-based-v1'
        }

    if amount > 10000:
        return {
            'action': 'ESCALATE',
            'confidence': 0.7,
            'reason': f'High-value transaction (₹{amount}) requires manual review',
            'requires_human_approval': True,
            'decision_source': 'FALLBACK_RULE',
            'model_version': 'rule-based-v1'
        }

    if failure_reason == 'temporary_failure' and retry_count == 0 and success_rate >= 0.7:
        return {
            'action': 'RETRY',
            'confidence': 0.85,
            'reason': 'Temporary failure with strong payment history and no prior retry',
            'requires_human_approval': False,
            'decision_source': 'FALLBACK_RULE',
            'model_version': 'rule-based-v1'
        }

    if probability >= 0.7 and retry_count == 0:
        return {
            'action': 'RETRY',
            'confidence': round(probability, 2),
            'reason': f'High recovery probability ({probability:.0%}) with no prior retry',
            'requires_human_approval': False,
            'decision_source': 'FALLBACK_RULE',
            'model_version': 'rule-based-v1'
        }

    if probability >= 0.5:
        return {
            'action': 'SEND_PAYMENT_LINK',
            'confidence': round(probability, 2),
            'reason': 'Moderate recovery probability, sending payment link for continuation',
            'requires_human_approval': False,
            'decision_source': 'FALLBACK_RULE',
            'model_version': 'rule-based-v1'
        }

    if probability >= 0.3:
        return {
            'action': 'SEND_REMINDER',
            'confidence': round(probability, 2),
            'reason': 'Lower probability, sending reminder as gentle nudge',
            'requires_human_approval': False,
            'decision_source': 'FALLBACK_RULE',
            'model_version': 'rule-based-v1'
        }

    return {
        'action': 'ESCALATE',
        'confidence': 0.5,
        'reason': 'Insufficient evidence for automated action',
        'requires_human_approval': True,
        'decision_source': 'FALLBACK_RULE',
        'model_version': 'rule-based-v1'
    }
