import re
import unicodedata
from typing import List

BOOKING_HOSTS = (
    'calendly.com',
    'cal.com',
    'zohobookings.com',
    'savvycal.com',
    'tidycal.com',
    'meetings.hubspot.com',
    'wa.me',
    'api.whatsapp.com',
)

_ZERO_WIDTH_CHARS = dict.fromkeys(map(ord, '\u200b\u200c\u200d\u2060\ufeff'))

_BOOKING_LINK = re.compile(
    r'(?<![\w.@-])(?:[\w-]+\.)*(?:' + '|'.join(re.escape(host) for host in BOOKING_HOSTS) + r')(?![\w-]|\.\w)'
)

_SIGNALS = {
    'call_to_action': [
        re.compile(r'\b(?:book|schedule|grab|pick|set up)\s+(?:a|some)\s+'
                   r'(?:quick\s+|short\s+|free\s+|\d+[- ]?min(?:ute)?\s+)?(?:time|call|chat|demo|slot|meeting)\s+'
                   r'(?:with (?:me|us|our team)\b|here\s*:|below\b)'),
        re.compile(r'\bhop on a (?:quick )?call with (?:me|us)\b'),
    ],
    'vendor_pitch': [
        re.compile(r"\b(?:i'm|i’m|im|i am)\s+(?:[\w'-]+(?:\s+[\w'-]+)?,\s+)?(?:the\s+)?(?:co-?)?founder of\b"),
        re.compile(r'\bwe help (?:\w+ ){0,2}?(?:businesses|companies|brands|startups)\b'),
    ],
    'offer_guarantee': [
        re.compile(r'\bguarantee[sd]?\s+(?:\w+\s+){0,3}?'
                   r'(?:results|leads|mqls|traffic|meetings|sign-?ups|rankings?|roi)\b'),
        re.compile(r'\b(?:results|leads|roi)\s+guaranteed\b'),
        re.compile(r'\bmoney[- ]back\b'),
        re.compile(r'\brefund you\b'),
        re.compile(r'\b(?:just|only)\s+(?:in|for)\s+\$\s?\d'),
    ],
    'lead_gen_jargon': [
        re.compile(r'\bmqls?\b'),
        re.compile(r'\bicp\b'),
        re.compile(r'\b(?:qualified|b2b) leads\b'),
        re.compile(r'\blead generation\b'),
        re.compile(r'\b(?:1st|first) rank\b'),
        re.compile(r'\b(?:targeted outreach|outreach campaigns?)\b'),
        re.compile(r'\bseo (?:services|audit|agency|package|optimization)\b'),
        re.compile(r'\b(?:boost|improve) your (?:seo|search rankings?)\b'),
    ],
}

_FLAG_THRESHOLD = 3


def _normalize(text):
    return unicodedata.normalize('NFKC', text).translate(_ZERO_WIDTH_CHARS).casefold()


def find_signals(subject: str, description: str) -> List[str]:
    text = _normalize(f'{subject}\n{description}')

    signals = [name for name, patterns in _SIGNALS.items() if any(p.search(text) for p in patterns)]
    if _BOOKING_LINK.search(text):
        signals.insert(0, 'booking_link')

    return signals


def detect_solicitation(subject: str, description: str) -> List[str]:
    """
    Check a support submission for commercial solicitation (vendor pitches, booking links, lead-gen offers).
    Signals match on commercial intent, not writing style, and at least three distinct signals are required.

    :param subject: The submission's subject.
    :param description: The submission's description.
    :return: The matched signals if the submission is suspected spam, otherwise an empty list.
    """
    signals = find_signals(subject, description)

    return signals if len(signals) >= _FLAG_THRESHOLD else []
