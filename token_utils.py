import tiktoken
import sys

def count_tokens(text: str, model_encoding: str = "cl100k_base") -> int:
    """
    Calculates the exact integer token size of a raw text string locally.
    Defaults to the cl100k_base encoding scheme used by modern OpenAI/Groq models.
    """
    if not text or not isinstance(text, str):
        return 0
        
    try:
        # Load the local token dictionary map
        encoding = tiktoken.get_encoding(model_encoding)
        # Convert the string into token arrays and count the array length
        return len(encoding.encode(text))
    except Exception as e:
        print(f"[TOKEN ERROR] Failed to calculate token size locally: {str(e)}", file=sys.stderr)
        return 0

# ----------------------------------------------------------------------
# LOCAL RUNNER CHECKPOINT
# ----------------------------------------------------------------------
if __name__ == "__main__":
    sample_text = "Hello, please check my insurance policy parameters for plan P101."
    tokens = count_tokens(sample_text)
    print(f"🧮 Integer Token Length: {tokens} tokens")