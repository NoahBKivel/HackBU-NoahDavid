"""Remove credential values from complete native Atlas session evidence."""

import re

_CREDENTIAL = re.compile(
    r"sk-ant-[A-Za-z0-9_-]{20,}|sk-(?:svcacct|proj)-[A-Za-z0-9_-]{20,}"
    r"|ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{22,}"
    r"|AKIA[0-9A-Z]{16}|hf_[A-Za-z0-9]{34}"
)
_ASSIGNMENT = re.compile(
    r"((?:CLAUDE_CODE_OAUTH_TOKEN|\.jwt_secret)\s*[:=]\s*)"
    r"(?:\[credential removed\]|'[^']*'|\"[^\"]*\"|[^\s;,&|]+)", re.I
)
_PEM = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)", re.S
)
_CANARY = re.compile(
    r"^.*(?:BENCHMARK DATA SHOULD NEVER APPEAR|CANARY_(?:STRING|TOKEN)\s*[:=]).*(?:\n|$)", re.M
)


def scrub(value):
    """Redact strings recursively, including reasoning and native tool output."""
    if isinstance(value, dict):
        return {scrub(key): scrub(item) for key, item in value.items()}
    if isinstance(value, list):
        return [scrub(item) for item in value]
    if not isinstance(value, str):
        return value
    value = _PEM.sub("[private key removed]", value)
    value = _ASSIGNMENT.sub(lambda match: match[1] + "[credential removed]", value)
    value = _CREDENTIAL.sub("[credential removed]", value)
    return _CANARY.sub("[canary removed]\n", value)
