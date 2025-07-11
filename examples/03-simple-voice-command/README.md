# PhosphoBot: Voice Command Example

Control your robot with simple voice commands. This example includes multiple versions to handle different system configurations.

## Prerequisites

- Python 3.6+
- A robot running the PhosphoBot server
- Required Python packages (install via `pip install -r requirements.txt`)
- Microphone connected to your computer (for audio version only)

## Available Scripts

### 1. voice_command_text.py (Recommended)
A text-based version that works without audio dependencies:
```bash
python voice_command_text.py         # Interactive text input
python voice_command_text.py demo    # Automatic demonstration  
python voice_command_text.py test    # Test movement commands
python voice_command_text.py help    # Show usage information
```

### 2. voice_command_fixed.py
Enhanced version with audio fallback:
```bash
python voice_command_fixed.py --text  # Force text mode
python voice_command_fixed.py         # Auto-detect (audio or text)
```

### 3. voice_command.py (Original)
Original audio-based version (may have dependency issues):
```bash
python voice_command.py
```

## How to Run

### Quick Start (Recommended)
1. Ensure your robot is powered on and the PhosphoBot server is running
2. Install basic dependencies:
   ```bash
   pip install requests
   ```
3. Run the text-based version:
   ```bash
   python voice_command_text.py demo
   ```

### Full Audio Setup
1. Install all dependencies:
   ```bash
   pip install -r requirements.txt
   pip install pocketsphinx
   ```
2. Install system audio libraries (Linux):
   ```bash
   sudo apt-get install portaudio19-dev
   ```
3. Make sure your system has granted microphone access permissions
4. Run the audio version:
   ```bash
   python voice_command_fixed.py
   ```
5. Press and hold SPACEBAR to record your voice command
6. Release SPACEBAR to process the command
7. Press ESC to exit the program

## Available Commands

The robot responds to these voice commands (works in all versions):

- "left" or "that": Moves a box to the left
- "right", "write", or "riots": Moves a box to the right
- "wave", "hello", "say", "what", "wait", or "ways": Makes the robot wave

## Implementation Details

### Text-Based Version (voice_command_text.py)
- Uses keyboard input instead of microphone
- Demonstrates the same command logic as the audio version
- Works without any audio dependencies
- Provides demo, test, and interactive modes

### Fixed Version (voice_command_fixed.py)  
- Automatically detects if audio dependencies are available
- Falls back to text input if audio fails
- Uses direct movement API calls as backup for missing recordings
- Handles system library issues gracefully

### Original Version (voice_command.py)
- Uses CMUSphinx for offline speech recognition
- Records audio while the SPACEBAR is held down
- Processes voice commands through simple keyword matching
- Requires pre-recorded movement patterns stored as JSON files

## Troubleshooting

### Audio Issues
If you encounter audio dependency errors:
1. Use the text-based version: `python voice_command_text.py`
2. Install system audio libraries: `sudo apt-get install portaudio19-dev`
3. Try the fixed version: `python voice_command_fixed.py --text`

### Missing Recording Files
The system automatically falls back to direct movement commands if recording files are missing:
- push_left.json → Direct left movement
- push_right.json → Direct right movement  
- wave.json → Direct waving sequence

### Robot Connection
Ensure the PhosphoBot server is running:
```bash
# Check server status
curl http://localhost:80/status
```
