import re
import sys

def redact_pii(text: str) -> str:
    """
    Identifies and masks sensitive PHI/PII vectors inside log trace dumps.
    Covers alphanumeric member IDs, tracking claim codes, emails, and names.
    """
    if not text or not isinstance(text, str):
        return text

    redacted = text

    # 1. Redact Alphanumeric Member ID Patterns (e.g., P101, P102, P9999)
    redacted = re.sub(r'\b[pP]\d{3,5}\b', '[REDACTED_MEMBER_ID]', redacted)

    # 2. Redact Insurance Claim Tracking Codes (e.g., CLM9901, clm9902)
    redacted = re.sub(r'\b[cC][lL][mM]\d{4,6}\b', '[REDACTED_CLAIM_ID]', redacted)

    # 3. Redact Electronic Mail Signatures
    redacted = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', '[REDACTED_EMAIL]', redacted)

    # 4. Redact Name Structures following standard customer phrases
    redacted = re.sub(
        r'(?i)\b(my name is|member is|member:)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b',
        r'\1 [REDACTED_NAME]',
        redacted
    )

    return redacted

# ----------------------------------------------------------------------
# AUTOMATED LOGIC VALIDATION UNIT TESTS
# ----------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("🧪 EXECUTING REDACTION PATTERN REGRESSION TESTS")
    print("=" * 60)

    # 3 Target sample strings containing dummy identifiers vs expectations
    test_cases = [
        (
            "Hello, my name is Ada Lovelace and my member ID is P101.",
            "Hello, my name is [REDACTED_NAME] and my member ID is [REDACTED_MEMBER_ID]."
        ),
        (
            "Please audit the payment ledger metrics for claim CLM9901 immediately.",
            "Please audit the payment ledger metrics for claim [REDACTED_CLAIM_ID] immediately."
        ),
        (
            "Forward the premium billing balance statements straight to john.doe@email.com.",
            "Forward the premium billing balance statements straight to [REDACTED_EMAIL]."
        )
    ]

    failures = 0
    for idx, (raw_input, expected) in enumerate(test_cases, start=1):
        output = redact_pii(raw_input)
        if output == expected:
            print(f"✅ Test Case #{idx}: PASSED")
        else:
            print(f"❌ Test Case #{idx}: FAILED")
            print(f"   Input:    {raw_input}")
            print(f"   Expected: {expected}")
            print(f"   Got:      {output}")
            failures += 1

    print("=" * 60)
    if failures == 0:
        print("🎉 ALL PHI/PII REDACTION PATTERNS VALIDATED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print(f"🛑 RECOVERY BLOCKED: {failures} filter configurations failed matching benchmarks.")
        sys.exit(1)
