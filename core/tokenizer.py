"""
core/tokenizer.py

count_tokens(text) -> int

HOW WE COUNT (the real way)
---------------------------
AWS Bedrock exposes a `CountTokens` API that runs the *actual* Anthropic Claude
tokenizer on the server. We call it directly, so the number we get back is the
real, exact token count for the Claude model you have enabled -- not a guess.

    client.count_tokens(
        modelId=<your Claude model id>,
        input={"converse": {"messages": [{"role": "user",
                                          "content": [{"text": text}]}]}},
    ) -> {"inputTokens": <exact int>}

THE SPARE TIRE (fallback)
-------------------------
If no AWS credentials are configured yet (e.g. while you're still building the
lab offline), calling AWS would crash. Rather than crash, we fall back to a
documented approximation -- words * 1.3 -- and print a clear warning so you
ALWAYS know when a number is estimated vs. real. This fallback is never silent.

Model id and region come from core.settings (which loads .env). IMPORTANT:
CountTokens needs the BASE foundation-model id (e.g. `anthropic.claude-3-5-haiku-
20241022-v1:0`); it rejects the cross-region INFERENCE PROFILE id we use for
Converse (`us.anthropic.claude-3-5-haiku-...`). So we strip the geo prefix before
counting -- with that, Haiku 3.5 returns EXACT counts. The words*1.3 estimate is
now only a true offline fallback (no creds / network).
"""

import sys
import functools

from core.settings import settings

# Approximate tokens-per-word, used ONLY as an offline fallback.
_TOKENS_PER_WORD = 1.3

# Cross-region inference-profile prefixes; CountTokens wants the base id without them.
_PROFILE_PREFIXES = ("us.", "eu.", "apac.", "us-gov.")

_warned_once = False


def _foundation_model_id(model_id: str) -> str:
    """Strip a cross-region inference-profile prefix to get the base model id.

    `us.anthropic.claude-3-5-haiku-...` -> `anthropic.claude-3-5-haiku-...`.
    Converse accepts the profile id, but CountTokens requires the base id.
    """
    for prefix in _PROFILE_PREFIXES:
        if model_id.startswith(prefix):
            return model_id[len(prefix):]
    return model_id


@functools.lru_cache(maxsize=1)
def _client():
    """Lazily build one cached bedrock-runtime client."""
    import boto3
    return boto3.client("bedrock-runtime", region_name=settings.aws_region)


def _approximate(text: str) -> int:
    """Offline spare tire: words * 1.3. Clearly an estimate."""
    global _warned_once
    if not _warned_once:
        print(
            "[tokenizer] WARNING: real CountTokens failed -- falling back to the "
            "words*1.3 ESTIMATE. Likely cause: no creds/network, or the model id "
            "is unsupported. Exact per-call counts still come from usage.inputTokens.",
            file=sys.stderr,
        )
        _warned_once = True
    return int(round(len(text.split()) * _TOKENS_PER_WORD))


def count_tokens(text: str) -> int:
    """Return the token count of `text`.

    Uses the real Bedrock CountTokens API (exact) against the BASE model id. Falls
    back to a words*1.3 estimate (with a one-time warning) only if that fails.
    """
    if not text:
        return 0
    try:
        resp = _client().count_tokens(
            modelId=_foundation_model_id(settings.bedrock_model_id),
            input={
                "converse": {
                    "messages": [{"role": "user", "content": [{"text": text}]}]
                }
            },
        )
        return int(resp["inputTokens"])
    except Exception:
        # No creds / offline / model not enabled -> graceful, loud fallback.
        return _approximate(text)
