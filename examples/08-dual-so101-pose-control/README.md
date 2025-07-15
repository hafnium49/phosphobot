# SO-101 Pose Control Examples

This example demonstrates how to control SO-101 robotic arms using direct pose commands (position + orientation). **Fully consolidated and refactored with single/dual robot support, critical bug fixes, and streamlined architecture.**

## 🚀 Quick Start

### **Single Robot Setup** ✅
```bash
# Basic movements and demos (use --single flag)
python3 dual_arm_basic.py --single

# Interactive manual control (use --single flag)
python3 interactive_control.py --single

# Testing suite (specific tests)
python3 dual_robot_testing_suite.py --legacy
```

### **Dual Robot Setup** ✅
```bash
# Basic dual arm control
python3 dual_arm_basic.py

# Interactive dual arm control
python3 interactive_control.py

# Advanced coordination and choreography
python3 dual_arm_advanced_demos.py

# Comprehensive testing suite
python3 dual_robot_testing_suite.py
```

## 📊 Consolidated Structure

| File | Status | Description | Single Robot | Dual Robot |
|------|--------|-------------|--------------|------------|
| `dual_so101_controller.py` | ✅ **CORE** | Controller library | ✅ Works | ✅ Works |
| `dual_arm_basic.py` | ✅ **ENHANCED** | Basic demo with --single support | ✅ Perfect | ✅ **TESTED** |
| `interactive_control.py` | ✅ **ENHANCED** | Interactive control with --single support | ✅ Perfect | ✅ **TESTED** |
| `dual_robot_testing_suite.py` | ✅ **CONSOLIDATED** | All testing functionality | ✅ Works | ✅ **VERIFIED** |
| `dual_arm_advanced_demos.py` | ✅ **CONSOLIDATED** | Advanced coordination & choreography | N/A | ✅ **TESTED** |

## 🎯 Refactoring Achievement

### **📈 Consolidation Results:**
- **Before**: 9 Python files with overlapping functionality
- **After**: 5 Python files with clear separation of concerns  
- **Reduction**: 44% fewer files while preserving all functionality
- **Benefits**: Easier maintenance, cleaner structure, unified interfaces

### **🔧 Files Consolidated:**

**Testing Suite** (`dual_robot_testing_suite.py`):
- ✅ `comprehensive_dual_arm_test.py` → Comprehensive testing
- ✅ `test_robot_id_fix.py` → Robot ID verification
- ✅ `visual_verification_test.py` → Visual verification
- ✅ `test_legacy_dual_robot.py` → Legacy API testing

**Advanced Demos** (`dual_arm_advanced_demos.py`):
- ✅ `dual_arm_coordination.py` → Coordination patterns
- ✅ `dual_arm_dance_demo.py` → Dance choreography
- ✅ Added handoff simulation and mirror movements

## 🎛️ Command Reference

### **Testing Suite Options:**
```bash
# Run all tests
python3 dual_robot_testing_suite.py

# Specific test categories
python3 dual_robot_testing_suite.py --robot-id-fix     # Robot ID bug verification
python3 dual_robot_testing_suite.py --visual           # Sequential movement test
python3 dual_robot_testing_suite.py --legacy           # Legacy API compatibility
python3 dual_robot_testing_suite.py --comprehensive    # Full functionality test
```

### **Advanced Demo Options:**
```bash
# Run all demonstrations
python3 dual_arm_advanced_demos.py

# Specific demo categories
python3 dual_arm_advanced_demos.py --coordination      # Synchronized patterns
python3 dual_arm_advanced_demos.py --dance             # Choreographed sequences
python3 dual_arm_advanced_demos.py --mirror            # Mirror movements
python3 dual_arm_advanced_demos.py --handoff           # Object handoff simulation
```

---

## 🔧 Development History & Critical Fixes

### **🚨 CRITICAL FIX: Robot ID Parameter Bug**

**Problem**: During dual robot testing, only the right arm (robot_id=1) was moving consistently. Commands sent to robot_id=0 appeared to be received but not executed.

**Root Cause**: The PhosphoBot API requires `robot_id` as a **URL query parameter**, not in the JSON body.

**Before Fix (BROKEN):**
```python
# INCORRECT: robot_id in JSON body
payload = {"x": 25, "y": 0, "z": 20, "robot_id": robot_id}  # Wrong!
response = session.post(f"{server_url}/move/absolute", json=payload)
```

**After Fix (WORKING):**
```python
# CORRECT: robot_id as URL query parameter
payload = {"x": 25, "y": 0, "z": 20}
response = session.post(f"{server_url}/move/absolute?robot_id={robot_id}", json=payload)
```

**Result**: ✅ Both arms now move independently and correctly

### **💼 File Consolidation Project**

**Problem**: Directory had 9 Python files with significant functional overlap, making maintenance difficult.

**Solution**: Consolidated related functionality into logical suites with unified interfaces.

**Benefits Achieved:**
- ✅ **Simplified Structure**: 44% fewer files to maintain
- ✅ **Unified Interface**: Command-line flags for different modes and tests
- ✅ **No Lost Functionality**: All original features preserved and enhanced
- ✅ **Better Organization**: Clear separation between basic, testing, and advanced features

### **🛠️ Original API Compatibility Fixes**

**Issues Resolved:**
1. **HTTP Client**: Changed from `httpx` to `requests` (matches other examples)
2. **Coordinate System**: Fixed meter to centimeter conversion  
3. **API Endpoints**: Disabled broken `/pose` endpoint
4. **Error Handling**: Added comprehensive exception handling
5. **Single Robot Support**: Added `--single` flag support throughout

---

## 💻 Prerequisites

- **Single SO-101 robot** (recommended) or **dual SO-101 robots**
- **PhosphoBot server** running (`phosphobot run`)
- **Python 3.10+** with required packages

## 📦 Installation

```bash
# Required packages (already included in PhosphoBot environment)
pip install requests numpy opencv-python

# Test installation
cd /home/hafnium/phosphobot/examples/08-dual-so101-pose-control
python3 dual_robot_testing_suite.py --legacy
```

## 🎮 Usage Examples

### **1. Basic Testing (Start Here)**
```bash
# Test controller functions and API compatibility
python3 dual_robot_testing_suite.py --legacy
```
**Output**: Tests absolute movement, relative movement, gripper control, coordinate conversion

### **2. Single Robot Control**
```bash
# Basic demo for single robot
python3 dual_arm_basic.py --single
```
**Features**: Multiple positions, gripper control, movement patterns, centered positioning

### **3. Interactive Single Robot Control**
```bash
# Real-time manual control
python3 interactive_control.py --single
```
**Controls**: WASD movement, gripper control, step size adjustment, safe positioning

### **4. Dual Robot Coordination**
```bash
# Basic dual robot demo
python3 dual_arm_basic.py
```
**Features**: Coordinated movements, synchronized positioning, left/right arm coordination

### **5. Advanced Demonstrations**
```bash
# Full coordination and choreography suite
python3 dual_arm_advanced_demos.py
```
**Features**: Synchronized patterns, dance sequences, handoff simulations, mirror movements

### **6. Comprehensive Testing**
```bash
# Complete test verification
python3 dual_robot_testing_suite.py
```
**Features**: Robot ID fix verification, visual verification, legacy API testing, full functionality test

---

## 🔄 Key Concepts

### **Coordinate System**
- **X-axis**: Forward/backward (positive = forward)
- **Y-axis**: Left/right (positive = left)  
- **Z-axis**: Up/down (positive = up)
- **Orientations**: Euler angles in degrees (rx, ry, rz)

### **Units**
- **Absolute positions**: Meters (converted to centimeters internally)
- **Relative positions**: Centimeters
- **Orientations**: Degrees
- **Gripper**: 0 = closed, 1 = open

### **Robot IDs & API Parameter Placement**
- **robot_id=0**: Primary robot (left arm in dual setup)
- **robot_id=1**: Secondary robot (right arm in dual setup)
- **⚠️ CRITICAL**: robot_id must be passed as URL query parameter: `?robot_id={robot_id}`

---

## 🚀 API Integration

### **Working Endpoints**
```python
# Robot initialization
POST /move/init

# Absolute positioning (with robot_id query parameter)
POST /move/absolute?robot_id=0
{
    "x": 25,     # centimeters
    "y": 0,      # centimeters  
    "z": 20,     # centimeters
    "rx": 0,     # degrees
    "ry": 0,     # degrees
    "rz": 0,     # degrees
    "open": 0    # 0=closed, 1=open
}

# Relative movement
POST /move/relative?robot_id=0
{
    "dx": 5,     # centimeters
    "dy": 0,     # centimeters
    "dz": 5,     # centimeters
    "open": 1
}
```

---

## 🎨 Example Code

### **Basic Movement Pattern**
```python
from dual_so101_controller import DualSO101Controller

# Initialize and test
controller = DualSO101Controller()
controller.initialize_robot()

# Move to position (coordinates in meters, converted automatically)
controller.move_arm_absolute_pose(
    robot_id=0,
    position=[0.25, 0.0, 0.20],  # 25cm forward, centered, 20cm up
    orientation=[0, 0, 0]        # No rotation
)

# Control gripper
controller.control_gripper(robot_id=0, gripper_value=1.0)  # Open
controller.control_gripper(robot_id=0, gripper_value=0.0)  # Close
```

### **Dual Robot Coordination**
```python
# Synchronized dual arm movement
controller.move_arm_absolute_pose(0, [0.25, 0.15, 0.20], [0, 0, 0])   # Left arm
controller.move_arm_absolute_pose(1, [0.25, -0.15, 0.20], [0, 0, 0])  # Right arm
```

### **Mode-Aware Programming**
```python
import sys

# Check for single robot mode
single_mode = "--single" in sys.argv

if single_mode:
    # Single robot - centered positions
    controller.move_arm_absolute_pose(0, [0.25, 0.0, 0.20], [0, 0, 0])
else:
    # Dual robot - left/right positions
    controller.move_arm_absolute_pose(0, [0.25, 0.15, 0.20], [0, 0, 0])   # Left
    controller.move_arm_absolute_pose(1, [0.25, -0.15, 0.20], [0, 0, 0])  # Right
```

---

## 🛠️ Troubleshooting

### **Common Issues**

**1. "Robot initialization failed"**
```bash
# Ensure PhosphoBot server is running
phosphobot run

# Check server status
curl http://localhost:80/move/init
```

**2. "Only one arm moving in dual robot setup"**
- ✅ **FIXED**: This was due to robot_id parameter placement
- Ensure you're using latest consolidated version

**3. "Module not found errors"**
```bash
# Install required packages
pip install requests numpy opencv-python
```

### **Debug Commands**
```bash
# Test API connectivity
curl -X POST http://localhost:80/move/init

# Test robot_id parameter
curl -X POST "http://localhost:80/move/absolute?robot_id=0" -H "Content-Type: application/json" -d '{"x":25,"y":0,"z":20,"open":0}'

# Quick controller test
python3 -c "from dual_so101_controller import DualSO101Controller; c=DualSO101Controller(); print('OK')"
```

---

## 📈 Development Roadmap

### **Completed Features** ✅
- [x] Critical robot_id parameter bug fix
- [x] Single robot support with --single flag
- [x] File consolidation (9 → 5 files)
- [x] Unified command-line interfaces
- [x] Comprehensive testing suite
- [x] Advanced coordination demonstrations
- [x] API compatibility fixes

### **Future Enhancements** 🚀
- [ ] Real-time pose monitoring (when /pose endpoint available)
- [ ] Configuration file support for different robot setups
- [ ] Advanced choreography pattern editor
- [ ] Multi-robot coordination algorithms

---

## 🤝 Contributing

This example has been extensively refactored and tested. When contributing:

1. **Maintain the consolidated structure** - don't add separate files for similar functionality
2. **Test both single and dual robot modes** using `--single` flag
3. **Verify robot_id parameter placement** as URL query parameter
4. **Use the unified command-line interface pattern** for new features
5. **Update this README** with any significant changes

---

## 🎉 Summary

Example 8 provides **complete SO-101 pose control functionality** with:

- ✅ **Streamlined Architecture**: 5 focused files instead of 9 overlapping ones
- ✅ **Universal Support**: Works with single or dual robot setups
- ✅ **Bug-Free Operation**: Critical robot_id parameter issue resolved
- ✅ **Unified Interfaces**: Command-line flags for all modes and tests
- ✅ **Comprehensive Testing**: Full verification suite with modular options
- ✅ **Advanced Demonstrations**: Coordination, choreography, and handoff simulations
- ✅ **Production Ready**: Thoroughly tested, documented, and refactored

**Perfect for learning SO-101 control, testing dual robot coordination, and building advanced robotic applications!** 🤖✨