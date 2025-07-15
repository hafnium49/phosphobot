from backend.modules.mic import record_audio
from backend.modules.whisper_transcriber import transcribe_audio
from backend.modules.llm import get_llm_response
from backend.modules.tts import speak_streaming

def main():
    print("🎙️ Speak to Phosphobot... (say 'exit' to quit)")

    while True:
        audio_path = record_audio()
        text = transcribe_audio(audio_path)

        print(f"\n📝 You said: {text}")

        if "exit" in text.lower():
            print("👋 Exiting.")
            break

        result = get_llm_response(text)

        print(f"\n🤖 Reply: {result['reply']}")
        speak_streaming(result["reply"], lambda word: print(f"Speaking: {word}"))  # 👈 la voix de Phosphobot

        print(f"📦 Command: {result['command']}\n")


if __name__ == "__main__":
    main()
