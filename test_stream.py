import os
import sys
from groq import Groq

def test_groq_streaming_call():
    print("[PROCESSING] Connecting to official Groq Cloud API gateway...")
    
    # 1. Initialize the official native Groq client
    client = Groq(
        api_key="API_KEY_REDACTED_FOR_SECURITY"  # Replace
    )

    test_question = "What is a brief summary of how high-speed LPU chips process tokens?"
    
    print(f"\n[QUERY]: \"{test_question}\"")
    print("-" * 60)
    print("STREAMING LIVE TO TERMINAL (Watch words arrive):")
    print("-" * 60 + "\n")

    try:
        # 2. Trigger the Chat Completion API with stream=True enabled
        completion_stream = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a concise engineering technical support assistant."},
                {"role": "user", "content": test_question}
            ],
            temperature=0.0,
            stream=True  # TEACHER REQUIREMENT: Activates token-by-token cloud streaming
        )

        # 3. Loop through individual token updates as they hit your computer network socket
        for chunk in completion_stream:
            # Extract text updates from the data chunk structure layers safely
            token_text = chunk.choices[0].delta.content
            
            if token_text:
                # Flush the stream right to the active terminal screen immediately
                sys.stdout.write(token_text)
                sys.stdout.flush()
                
        print("\n\n" + "-" * 60)
        print("[SUCCESS] Token streaming verification execution complete!")

    except Exception as e:
        print(f"\n[CRITICAL ERROR] Stream pipeline connection failure: {str(e)}")

if __name__ == "__main__":
    test_groq_streaming_call()