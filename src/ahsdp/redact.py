import re
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"\b(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?)?\d{3,4}[\s-]?\d{3,4}\b")
TOKEN_RE = re.compile(r"\b(?:Bearer\s+|token[:=])?[A-F0-9]{20,}\b", re.I)
def mask(s, kinds):
    if "email" in kinds: s = EMAIL_RE.sub("[REDACTED_EMAIL]", s)
    if "phone" in kinds: s = PHONE_RE.sub("[REDACTED_PHONE]", s)
    if "token" in kinds: s = TOKEN_RE.sub("[REDACTED_TOKEN]", s)
    return s
