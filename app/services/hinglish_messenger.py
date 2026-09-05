import logging
from datetime import datetime

logger = logging.getLogger(__name__)

HINGLISH_TEMPLATES = {
    'retry_reminder': {
        'whatsapp': {
            'subject': 'Payment retry available',
            'message': (
                'Hi {customer_name}! Aapka payment of ₹{amount} for {product} '
                'fail ho gaya hai. Don\'t worry — humne retry ke liye ready kiya hai. '
                'Abhi pay karein: {payment_link}\n'
                '- RecoverAI'
            )
        },
        'sms': 'Payment of ₹{amount} failed. Retry now: {payment_link} - RecoverAI',
        'email_subject': 'Aapka payment pending hai — {product}',
        'email_body': (
            '<h3>Hi {customer_name},</h3>'
            '<p>Aapka <strong>₹{amount}</strong> ka payment for <strong>{product}</strong> '
            'fail ho gaya hai.</p>'
            '<p>Humne isse retry ke liye ready kiya hai. Neeche diye gaye button se '
            'turant pay karein:</p>'
            '<a href="{payment_link}" style="background:#0d6efd;color:white;'
            'padding:12px 24px;text-decoration:none;border-radius:6px;'
            'display:inline-block;">Pay Now</a>'
            '<p style="margin-top:20px;color:#666;font-size:12px;">'
            'Agar aap already pay kar chuke hain toh isko ignore karein.</p>'
        )
    },
    'insufficient_funds': {
        'whatsapp': {
            'subject': 'Insufficient balance',
            'message': (
                'Hi {customer_name}! ₹{amount} ka payment fail hua kyunki '
                'balance kam tha. Please apne account mein paisa daalein aur '
                'dobara try karein: {payment_link}\n'
                '- RecoverAI'
            )
        },
        'sms': '₹{amount} payment failed (insufficient balance). Add funds & retry: {payment_link}',
        'email_subject': 'Balance kam hai — payment pending',
        'email_body': (
            '<h3>Hi {customer_name},</h3>'
            '<p>Aapka <strong>₹{amount}</strong> ka payment fail hua hai '
            'kyunki account mein sufficient balance nahi tha.</p>'
            '<p>Please apne account mein paisa daalein aur neeche click karein:</p>'
            '<a href="{payment_link}" style="background:#0d6efd;color:white;'
            'padding:12px 24px;text-decoration:none;border-radius:6px;'
            'display:inline-block;">Retry Payment</a>'
        )
    },
    'card_expired': {
        'whatsapp': {
            'subject': 'Card expired',
            'message': (
                'Hi {customer_name}! Aapka card expire ho chuka hai, isliye '
                '₹{amount} ka payment fail hua. Please naya card update karein '
                'ya doosra payment method use karein: {payment_link}\n'
                '- RecoverAI'
            )
        },
        'sms': 'Your card is expired. Update payment method for ₹{amount}: {payment_link}',
        'email_subject': 'Card expired — update karein',
        'email_body': (
            '<h3>Hi {customer_name},</h3>'
            '<p>Aapka registered card expire ho chuka hai.</p>'
            '<p>₹{amount} ka payment complete karne ke liye please naya card '
            'ya doosra payment method add karein:</p>'
            '<a href="{payment_link}" style="background:#0d6efd;color:white;'
            'padding:12px 24px;text-decoration:none;border-radius:6px;'
            'display:inline-block;">Update Payment Method</a>'
        )
    },
    'mandate_revoked': {
        'whatsapp': {
            'subject': 'Mandate cancelled',
            'message': (
                'Hi {customer_name}! Aapka UPI mandate cancel ho chuka hai. '
                'Isliye ₹{amount} ka auto-debit fail hua. Dobara mandate set '
                'karein: {payment_link}\n'
                '- RecoverAI'
            )
        },
        'sms': 'UPI mandate cancelled. ₹{amount} auto-debit failed. Re-authorize: {payment_link}',
        'email_subject': 'UPI mandate cancelled',
        'email_body': (
            '<h3>Hi {customer_name},</h3>'
            '<p>Aapka UPI auto-debit mandate cancel ho chuka hai.</p>'
            '<p>₹{amount} ka payment continue karne ke liye please dobara '
            'mandate authorize karein:</p>'
            '<a href="{payment_link}" style="background:#0d6efd;color:white;'
            'padding:12px 24px;text-decoration:none;border-radius:6px;'
            'display:inline-block;">Re-authorize Mandate</a>'
        )
    },
    'final_notice': {
        'whatsapp': {
            'subject': 'Final notice',
            'message': (
                'Hi {customer_name}, yeh hamari last reminder hai. ₹{amount} ka '
                'payment pending hai. Agar 24 ghante mein pay nahi kiya toh '
                'service block ho sakti hai: {payment_link}\n'
                '- RecoverAI'
            )
        },
        'sms': 'FINAL NOTICE: ₹{amount} payment pending. Pay within 24h to avoid service block: {payment_link}',
        'email_subject': 'FINAL NOTICE — ₹{amount} payment pending',
        'email_body': (
            '<h3 style="color:red;">Final Notice</h3>'
            '<p>Hi {customer_name},</p>'
            '<p>Yeh hamari <strong>last reminder</strong> hai. Aapka <strong>₹{amount}</strong> '
            'ka payment abhi bhi pending hai.</p>'
            '<p>Agar 24 ghante mein payment nahi hota toh aapki service block ho sakti hai.</p>'
            '<a href="{payment_link}" style="background:#dc3545;color:white;'
            'padding:12px 24px;text-decoration:none;border-radius:6px;'
            'display:inline-block;">Pay Now — Final Notice</a>'
        )
    }
}

REASON_TEMPLATE_MAP = {
    'temporary_failure': 'retry_reminder',
    'insufficient_funds': 'insufficient_funds',
    'card_expired': 'card_expired',
    'authentication_failed': 'retry_reminder',
    'technical_error': 'retry_reminder',
    'bank_declined': 'retry_reminder',
    'mandate_revoked': 'mandate_revoked',
    'mandate_expired': 'mandate_revoked',
    'network_timeout': 'retry_reminder',
}


class HinglishMessenger:
    @staticmethod
    def get_template(failure_reason, is_final=False):
        if is_final:
            template_key = 'final_notice'
        else:
            template_key = REASON_TEMPLATE_MAP.get(failure_reason, 'retry_reminder')

        return HINGLISH_TEMPLATES.get(template_key, HINGLISH_TEMPLATES['retry_reminder'])

    @staticmethod
    def compose_message(failure_reason, channel, context, is_final=False):
        template = HinglishMessenger.get_template(failure_reason, is_final)

        if channel == 'whatsapp':
            msg = template.get('whatsapp', {}).get('message', '')
        elif channel == 'sms':
            msg = template.get('sms', '')
        elif channel == 'email':
            msg = template.get('email_body', '')
        else:
            msg = template.get('whatsapp', {}).get('message', '')

        try:
            return msg.format(**context)
        except KeyError as e:
            logger.warning(f"Template key missing: {e}")
            return msg

    @staticmethod
    def compose_email_subject(failure_reason, context, is_final=False):
        template = HinglishMessenger.get_template(failure_reason, is_final)
        subject = template.get('email_subject', 'Payment pending')
        try:
            return subject.format(**context)
        except KeyError:
            return subject

    @staticmethod
    def get_available_channels():
        return ['whatsapp', 'sms', 'email']
