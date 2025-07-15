#!/usr/bin/env python3
"""
Quick test script to verify SO-101 pose to AI control setup.

This script checks:
1. Dependencies are installed
2. Robot connection is available 
3. Basic functionality works

Usage: python test_setup.py
"""

import sys
import subprocess

def check_dependencies():
    """Check if required dependencies are installed."""
    print("🔍 Checking dependencies...")
    try:
        import httpx
        import argparse
        print("✅ All required dependencies found")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("💡 Run: pip install -r requirements.txt")
        return False

def check_imports():
    """Check if our modules can be imported."""
    print("📦 Checking module imports...")
    try:
        from so101_pose_to_ai_control import SO101PoseToAIController
        print("✅ SO101PoseToAIController import successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def check_server_connection():
    """Check if phosphobot server is running."""
    print("🌐 Checking server connection...")
    try:
        from so101_pose_to_ai_control import SO101PoseToAIController
        controller = SO101PoseToAIController()
        if controller.check_connection():
            controller.close()
            return True
        else:
            return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        print("💡 Make sure to run: phosphobot run")
        return False

def main():
    print("🤖 SO-101 Pose to AI Control - Setup Test")
    print("=" * 50)
    
    all_good = True
    
    # Check dependencies
    if not check_dependencies():
        all_good = False
    
    print()
    
    # Check imports  
    if not check_imports():
        all_good = False
        
    print()
    
    # Check server connection
    if not check_server_connection():
        all_good = False
        
    print()
    print("=" * 50)
    
    if all_good:
        print("🎉 SUCCESS: Setup verification complete!")
        print("✅ Ready to use SO-101 pose to AI control")
        print()
        print("🚀 Next steps:")
        print("   python so101_demo.py              # Interactive demo")
        print("   python so101_practical_example.py # Real model example")
        return 0
    else:
        print("❌ FAILED: Setup issues detected")
        print("💡 Fix the issues above and run the test again")
        return 1

if __name__ == "__main__":
    sys.exit(main())
