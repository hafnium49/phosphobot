#!/usr/bin/env python3
"""
Voice Command Example - Fixed Version

This is an enhanced version of the original voice_command.py that:
1. Falls back to direct movement API calls when recording files are missing
2. Handles audio dependency issues gracefully
3. Provides better error messages and user guidance
"""

import requests
import time
import os
import sys

# Try to import audio dependencies, but continue without them if they fail
HAS_AUDIO = True
AUDIO_ERROR = None

try:
    import sounddevice as sd
    import scipy.io.wavfile as wavfile
    import numpy as np
    import keyboard
    import speech_recognition as sr
except ImportError as e:
    HAS_AUDIO = False
    AUDIO_ERROR = f"Import error: {e}"
except OSError as e:
    HAS_AUDIO = False  
    AUDIO_ERROR = f"System library error: {e}"
except Exception as e:
    HAS_AUDIO = False
    AUDIO_ERROR = f"Unexpected error: {e}"

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RECORDING_FILES = {
    "push_left": os.path.join(BASE_DIR, "push_left.json"),
    "push_right": os.path.join(BASE_DIR, "push_right.json"), 
    "wave": os.path.join(BASE_DIR, "wave.json")
}


class AudioRecorder:
    """Audio recorder class - only works if audio dependencies are available."""
    
    def __init__(self, sample_rate=44100, channels=1):
        if not HAS_AUDIO:
            raise RuntimeError("Audio dependencies not available")
        
        self.sample_rate = sample_rate
        self.channels = channels
        self.recording = False
        self.recorded_audio = []
        self.recognizer = sr.Recognizer()

    def start_recording(self):
        self.recording = True
        self.recorded_audio = []
        print("Recording started...")
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            callback=self.audio_callback,
        )
        self.stream.start()

    def stop_recording(self):
        self.recording = False
        self.stream.stop()
        print("Recording stopped.")
        return self.convert_to_text()

    def audio_callback(self, indata, frames, time, status):
        if status:
            print(status)
        if self.recording:
            self.recorded_audio.append(indata.copy())

    def save_audio(self):
        if not self.recorded_audio:
            return None

        # Combine recorded audio chunks
        audio_data = np.concatenate(self.recorded_audio, axis=0)

        # Normalize audio to prevent clipping
        audio_data = audio_data / np.max(np.abs(audio_data))

        # Scale to 16-bit range
        scaled_audio = (audio_data * 32767).astype(np.int16)

        # Save to a WAV file
        filename = "recorded_audio.wav"
        wavfile.write(filename, self.sample_rate, scaled_audio)

        return filename

    def convert_to_text(self):
        filename = self.save_audio()
        if not filename:
            return None

        try:
            # Use CMUSphinx for offline recognition
            with sr.AudioFile(filename) as source:
                audio = self.recognizer.record(source)
                text = self.recognizer.recognize_sphinx(audio)

                if text:
                    print("Recognized Text:", text)
                    # Call action function
                    decide_action(text)
                    return text

                print("No text recognized")
                return None

        except sr.UnknownValueError:
            print("Could not understand audio")
            return None
        except sr.RequestError as e:
            print(f"Recognition error: {e}")
            return None
        finally:
            # Remove temporary audio file
            if filename and os.path.exists(filename):
                os.remove(filename)


def api_call(endpoint: str, data: dict | None = None):
    """Make API call to the phosphobot server."""
    try:
        response = requests.post(
            f"http://localhost:80/{endpoint}",
            json=data,
        )
        if response.status_code == 200:
            print(f"✅ API call to {endpoint} successful")
        else:
            print(f"❌ API call to {endpoint} failed: {response.status_code}")
        return response
    except requests.RequestException as e:
        print(f"❌ Failed to send data to {endpoint}: {e}")
        return None


def move_box_left():
    """Move box left - try recording first, fallback to direct movement."""
    print("🔄 Executing: Move box left")
    
    # Try recording file first
    if os.path.exists(RECORDING_FILES["push_left"]):
        response = api_call("recording/play", {"episode_path": RECORDING_FILES["push_left"]})
        if response and response.status_code == 200:
            return
    
    # Fallback to direct movement
    print("   Using direct movement (recording not available)")
    api_call("move/relative", {
        "x": 0, "y": 5, "z": 0, "rx": 0, "ry": 0, "rz": 0, 
        "open": 0, "robot_id": 1
    })


def move_box_right():
    """Move box right - try recording first, fallback to direct movement."""
    print("🔄 Executing: Move box right")
    
    # Try recording file first
    if os.path.exists(RECORDING_FILES["push_right"]):
        response = api_call("recording/play", {"episode_path": RECORDING_FILES["push_right"]})
        if response and response.status_code == 200:
            return
    
    # Fallback to direct movement
    print("   Using direct movement (recording not available)")
    api_call("move/relative", {
        "x": 0, "y": -5, "z": 0, "rx": 0, "ry": 0, "rz": 0, 
        "open": 0, "robot_id": 1
    })


def say_hello():
    """Wave hello - try recording first, fallback to direct movement."""
    print("🔄 Executing: Wave hello")
    
    # Try recording file first
    if os.path.exists(RECORDING_FILES["wave"]):
        response = api_call("recording/play", {"episode_path": RECORDING_FILES["wave"]})
        if response and response.status_code == 200:
            return
    
    # Fallback to direct movement sequence
    print("   Using direct movement (recording not available)")
    movements = [
        {"x": 0, "y": 0, "z": 3, "rx": 0, "ry": 0, "rz": 0, "open": 1, "robot_id": 1},
        {"x": 0, "y": -3, "z": 0, "rx": 0, "ry": 0, "rz": 0, "open": 1, "robot_id": 1},
        {"x": 0, "y": 3, "z": 0, "rx": 0, "ry": 0, "rz": 0, "open": 1, "robot_id": 1},
        {"x": 0, "y": 0, "z": -3, "rx": 0, "ry": 0, "rz": 0, "open": 0, "robot_id": 1}
    ]
    
    for movement in movements:
        api_call("move/relative", movement)
        time.sleep(0.3)


def decide_action(prompt: str):
    """Decide which action to take based on the text prompt."""
    prompt = prompt.lower().strip()
    
    if "left" in prompt or "that" in prompt:
        move_box_left()
        print("✅ Executed: Moving box left")
    elif "right" in prompt or "write" in prompt or "riots" in prompt:
        move_box_right()
        print("✅ Executed: Moving box right")
    elif (
        "wave" in prompt
        or "hello" in prompt
        or "say" in prompt
        or "what" in prompt
        or "wait" in prompt
        or "ways" in prompt
    ):
        say_hello()
        print("✅ Executed: Waving")
    else:
        print(f"❌ No action recognized for: '{prompt}'")


def main_audio():
    """Main function for audio-based voice recognition."""
    if not HAS_AUDIO:
        print("❌ Audio dependencies not available.")
        print(f"   Error: {AUDIO_ERROR}")
        print("   Please install: pip install sounddevice scipy speechrecognition keyboard pocketsphinx")
        print("   Or use the text-based version: python voice_command_text.py")
        return
    
    # Initialize API
    if not api_call("move/init"):
        print("❌ Failed to initialize robot. Is the server running?")
        return
    
    try:
        recorder = AudioRecorder()
    except RuntimeError as e:
        print(f"❌ Failed to initialize audio recorder: {e}")
        return

    print("🎤 Voice Command System Ready!")
    print("Press and hold SPACEBAR to record. Release to stop and transcribe.")
    print("Press ESC to exit the program")

    # Use a flag to prevent multiple event handlers
    is_space_pressed = False

    def on_press(event):
        nonlocal is_space_pressed
        if event.name == "space" and not is_space_pressed:
            is_space_pressed = True
            recorder.start_recording()

    def on_release(event):
        nonlocal is_space_pressed
        if event.name == "space" and is_space_pressed:
            is_space_pressed = False
            recorder.stop_recording()

    # Register keyboard event listeners
    keyboard.on_press_key("space", on_press)
    keyboard.on_release_key("space", on_release)

    # Keep the script running
    try:
        keyboard.wait("esc")  # Press ESC to exit the program
    except KeyboardInterrupt:
        pass
    
    print("\n👋 Voice command system stopped!")


def main_text():
    """Main function for text-based input (fallback mode)."""
    print("🎤 Voice Command System (Text Input Mode)")
    print("=" * 45)
    if not HAS_AUDIO:
        print("Audio not available - using text input instead")
        print(f"   Reason: {AUDIO_ERROR}")
    else:
        print("Running in text mode by request")
    print()
    print("Available commands:")
    print("  - 'left' or 'that': Move box left")
    print("  - 'right', 'write', 'riots': Move box right") 
    print("  - 'wave', 'hello', 'say', 'what', 'wait', 'ways': Wave")
    print("  - 'quit' or 'exit': Exit the program")
    print()
    
    # Initialize robot
    if not api_call("move/init"):
        print("❌ Failed to initialize robot. Is the server running?")
        return
    
    print("✅ Robot initialized! Ready for commands.")
    
    while True:
        try:
            command = input("\n🎙️  Enter command: ").strip()
            
            if command.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            elif command:
                decide_action(command)
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except EOFError:
            print("\n\n👋 Goodbye!")
            break


def main():
    """Main entry point - choose between audio and text mode."""
    if len(sys.argv) > 1 and sys.argv[1] == '--text':
        main_text()
    elif HAS_AUDIO:
        main_audio()
    else:
        main_text()


if __name__ == "__main__":
    main()
