import asyncio
import time
import traceback
from typing import Any, Dict, List, Literal, Optional, Tuple, cast

import numpy as np
import serial
from fastapi import HTTPException
from loguru import logger
from serial.tools.list_ports_common import ListPortInfo

from phosphobot.configs import SimulationMode, config
from phosphobot.control_signal import ControlSignal
from phosphobot.hardware.base import BaseManipulator
from phosphobot.hardware.motors.feetech import FeetechMotorsBus  # type: ignore
from phosphobot.models import RobotConfigStatus
from phosphobot.utils import get_resources_path


class SO100Hardware(BaseManipulator):
    name = "so-100"

    URDF_FILE_PATH = str(
        get_resources_path() / "urdf" / "so-100" / "urdf" / "so-100.urdf"
    )

    AXIS_ORIENTATION = [0, 0, 1, 1]

    END_EFFECTOR_LINK_INDEX = 4
    GRIPPER_JOINT_INDEX = 5

    # Feetech settings
    motors: Dict[str, List[object]] = {
        # name: (index, model)
        "shoulder_pan": [1, "sts3215"],
        "shoulder_lift": [2, "sts3215"],
        "elbow_flex": [3, "sts3215"],
        "wrist_flex": [4, "sts3215"],
        "wrist_roll": [5, "sts3215"],
        "gripper": [6, "sts3215"],
    }

    SERVO_IDS = [1, 2, 3, 4, 5, 6]
    BAUDRATE = 1000000  # Baud rate
    RESOLUTION = 4096  # 12-bit resolution

    # Measured offset on the servos
    CALIBRATION_POSITION = [
        np.pi / 2,
        np.pi / 2,
        -np.pi / 2,
        -np.pi / 2,
        np.pi / 2,
        np.pi / 2,
    ]
    SLEEP_POSITION = [
        -0.09359567856848712,
        -1.6632412388236073,
        1.4683781047547897,
        0.5799863360473464,
        0.72268138697963,
        0.018412264636423696,
    ]

    # Tracking of motor communication errors
    motor_communication_errors: int = 0

    _gravity_task: Optional[asyncio.Task] = None

    # Last Torque_Enable read from the bus: (values, time.monotonic() of the read).
    # Dropped by every torque write and by disconnect.
    _torque_enabled_cache: Optional[Tuple[List[bool], float]] = None
    # time.monotonic() of the last successful bus read of all positions
    last_position_read_monotonic: Optional[float] = None

    @property
    def servo_id_to_motor_name(self) -> Dict[int, str]:
        output: Dict[int, str] = {cast(int, v[0]): k for k, v in self.motors.items()}
        return output

    @classmethod
    def from_port(cls, port: ListPortInfo, **kwargs: Any) -> Optional["SO100Hardware"]:
        """
        Detect if the device is a SO-100 robot.π
        """
        # The Feetech UART board CH340 has PID 29987
        if port.pid == 21971 or port.pid == 29987:
            # The serial number is not always available
            serial_number = port.serial_number or "no_serial"
            robot = cls(device_name=port.device, serial_id=serial_number)
            return robot
        return None

    async def connect(self) -> None:
        """
        Connect to the robot.
        """
        if not hasattr(self, "device_name"):
            logger.warning(
                "Can't connect: no plugged robot detected (no device_name). Please plug the robot, then restart the server."
            )
            return None

        try:
            assert (
                self.device_name is not None
            ), "Device name must be set before connecting."
            # Create serial connection
            self.motors_bus = FeetechMotorsBus(
                port=self.device_name, motors=self.motors
            )
            self.motors_bus.connect()
        except serial.SerialException as e:
            if "Access is denied" in str(e):
                logger.warning(
                    f"Failed to add robot connection: {e}\n{traceback.format_exc()}"
                )
            elif "Permission denied" in str(e):
                logger.warning(
                    f"Failed to add robot connection: {e}\n{traceback.format_exc()}"
                )
            else:
                logger.warning(
                    f"Failed to add robot connection (SerialException): {e}\n{traceback.format_exc()}"
                )
            return None
        self.init_config()
        self._max_temperature_cache: dict = {}
        self.is_connected = True

    def disconnect(self) -> None:
        """
        Disconnect the robot.
        """
        try:
            self.motors_bus.disconnect()
        except Exception as e:
            logger.warning(f"Error disconnecting motors: {e}")
        self.is_connected = False
        self._torque_enabled_cache = None

    def read_torque_enabled(
        self, max_age_s: float = 0.25
    ) -> Tuple[Optional[List[bool]], Optional[float]]:
        """
        Read Torque_Enable of the six servos, in servo order.

        One bus read serves every caller for max_age_s seconds.

        Returns the values and their age in seconds, or (None, None) when the arm
        is off the bus or the read failed.
        """
        if not self.is_connected:
            return None, None

        cache = self._torque_enabled_cache
        if cache is not None:
            age_s = time.monotonic() - cache[1]
            if age_s <= max_age_s:
                return cache[0], age_s

        try:
            torque_status = self.motors_bus.read(
                "Torque_Enable", motor_names=list(self.motors.keys())
            )
            self.motor_communication_errors = 0
        except Exception as e:
            logger.warning(f"Error reading torque status: {e}")
            self.update_motor_errors()
            return None, None

        torque_enabled = [bool(value) for value in torque_status]
        self._torque_enabled_cache = (torque_enabled, time.monotonic())
        return torque_enabled, 0.0

    def read_raw(self) -> dict:
        """
        Read present position, goal position and torque enable straight from the
        servos, addressed by servo id.

        The positions are the 16-bit words as read (bit 15 is the sign, not
        decoded): this path applies neither the rotation unwrapping of
        FeetechMotorsBus.read nor the calibration.

        Raises ConnectionError when the arm is off the bus or any read failed.
        """
        if not self.is_connected:
            raise ConnectionError(
                f"arm {getattr(self, 'SERIAL_ID', None)} is not on the bus"
            )

        words = {}
        try:
            for data_name in ("Present_Position", "Goal_Position", "Torque_Enable"):
                words[data_name] = self.motors_bus.read_with_motor_ids(
                    self.motors_bus.motor_models, list(self.SERVO_IDS), data_name
                )
            self.motor_communication_errors = 0
        except Exception as e:
            logger.warning(f"Error reading raw registers: {e}")
            self.update_motor_errors()
            raise ConnectionError(f"raw read failed: {e}") from e

        return {
            "present_position": [int(word) for word in words["Present_Position"]],
            "goal_position": [int(word) for word in words["Goal_Position"]],
            "torque_enabled": [bool(word) for word in words["Torque_Enable"]],
        }

    def _torque_reads_back_as(self, enabled: bool) -> bool:
        """
        Read Torque_Enable from the bus (never from the cache) and compare.
        """
        torque_enabled, _ = self.read_torque_enabled(max_age_s=0)
        if torque_enabled is None:
            return False
        if any(value != enabled for value in torque_enabled):
            logger.warning(
                f"Torque_Enable read back {torque_enabled}, wanted {enabled} on all servos"
            )
            return False
        return True

    def enable_torque(self) -> bool:
        """
        Enable torque and write the PID gains of the calibration.

        Returns True only when Torque_Enable reads back as 1 on all six servos and
        no write failed. False when the arm is off the bus (nothing was written).
        """
        if not self.is_connected:
            return False
        if self.config is None:
            logger.warning("Robot config is not initialized. Cannot enable torque.")
            return False

        self._torque_enabled_cache = None
        try:
            self.motors_bus.write("Torque_Enable", 1)
            for servo_id, c in enumerate(self.config.pid_gains):
                self._set_pid_gains_motors(
                    servo_id + 1,
                    p_gain=int(c.p_gain),
                    i_gain=int(c.i_gain),
                    d_gain=int(c.d_gain),
                )
            self.motor_communication_errors = 0
        except Exception as e:
            logger.warning(f"Error enabling torque: {e}")
            self.update_motor_errors()
            return False
        return self._torque_reads_back_as(True)

    def disable_torque(self) -> bool:
        """
        Disable torque.

        Returns True only when Torque_Enable reads back as 0 on all six servos.
        False when the arm is off the bus (nothing was written).
        """
        if not self.is_connected:
            return False
        self._torque_enabled_cache = None
        try:
            self.motors_bus.write("Torque_Enable", 0)
            self.motor_communication_errors = 0
        except Exception as e:
            logger.warning(f"Error disabling torque: {e}")
            self.update_motor_errors()
            return False
        return self._torque_reads_back_as(False)

    def _set_pid_gains_motors(
        self, servo_id: int, p_gain: int = 32, i_gain: int = 0, d_gain: int = 32
    ) -> None:
        """
        Set the PID gains for the Feetech servo.

        :servo_id: Joint ID (0-6)
        :param p_gain: Proportional gain (0-255)
        :param i_gain: Integral gain (0-255)
        :param d_gain: Derivative gain (0-255)

        Raises if the torque status cannot be read or a gain cannot be written:
        the gains were then not set.
        """
        try:
            torque_status = self.motors_bus.read(
                "Torque_Enable", motor_names=list(self.motors.keys())
            )
        except Exception as e:
            logger.warning(f"Error reading torque status: {e}")
            raise

        if torque_status.all() == 1:
            self.motors_bus.write(
                "P_Coefficient",
                p_gain,
                motor_names=self.servo_id_to_motor_name[servo_id],
            )
            self.motors_bus.write(
                "I_Coefficient",
                i_gain,
                motor_names=self.servo_id_to_motor_name[servo_id],
            )
            self.motors_bus.write(
                "D_Coefficient",
                d_gain,
                motor_names=self.servo_id_to_motor_name[servo_id],
            )

        else:
            logger.warning(
                "Motors torque is disabled. Motors must have torque enabled to change PID coefficients. Enable torque first."
            )

    def _try_set_pid_gains_motors(
        self, servo_id: int, p_gain: int = 32, i_gain: int = 0, d_gain: int = 32
    ) -> bool:
        """
        _set_pid_gains_motors for the loops that set the gains of several servos
        and must go on (gravity compensation, leader-follower): a servo whose gains
        could not be set is logged and skipped.

        Returns False for that servo.
        """
        try:
            self._set_pid_gains_motors(
                servo_id, p_gain=p_gain, i_gain=i_gain, d_gain=d_gain
            )
            return True
        except Exception as e:
            logger.warning(f"PID gains of servo {servo_id} were not set: {e}")
            return False

    def _get_pid_gains_motor(self, servo_id: int) -> Optional[Tuple[int, int, int]]:
        """
        Get the PID gains for the Feetech servo.

        :servo_id: Joint ID (0-6)
        :return: Tuple of (p_gain, i_gain, d_gain)
        """
        try:
            p_gain = self.motors_bus.read(
                "P_Coefficient", motor_names=self.servo_id_to_motor_name[servo_id]
            )
            i_gain = self.motors_bus.read(
                "I_Coefficient", motor_names=self.servo_id_to_motor_name[servo_id]
            )
            d_gain = self.motors_bus.read(
                "D_Coefficient", motor_names=self.servo_id_to_motor_name[servo_id]
            )
            return int(p_gain), int(i_gain), int(d_gain)
        except Exception as e:
            logger.warning(f"Error reading PID gains: {e}")
            self.update_motor_errors()
            return None

    def update_motor_errors(self) -> None:
        """
        Every time a motor communication error is detected, increment the error counter.
        If the counter reaches a certain threshold, disconnect the robot.
        """
        if not self.is_connected:
            return

        self.motor_communication_errors += 1
        if self.motor_communication_errors > 10:
            logger.error("Too many communication errors. Disconnecting robot.")
            self.disconnect()

    def read_motor_position(self, servo_id: int, **kwargs: Any) -> Optional[int]:
        """
        Read the position of a Feetech servo.
        """
        if not self.is_connected:
            return None
        try:
            position = self.motors_bus.read(
                "Present_Position",
                motor_names=self.servo_id_to_motor_name[servo_id],
            )
            self.motor_communication_errors = 0
            return position
        except Exception as e:
            logger.warning(f"Error reading motor position: {e}")
            self.update_motor_errors()
            return None

    def write_motor_position(self, servo_id: int, units: int, **kwargs: Any) -> bool:
        """
        Write a position to a Feetech servo.

        Returns True when the bus write was issued without error, False when it
        was skipped (arm off the bus) or raised.
        """
        if not self.is_connected:
            return False

        try:
            self.motors_bus.write(
                "Goal_Position",
                values=[units],
                motor_names=self.servo_id_to_motor_name[servo_id],
            )
            self.motor_communication_errors = 0
            return True
        except Exception as e:
            logger.warning(f"Error writing motor position: {e}")
            self.update_motor_errors()
            return False

    def write_group_motor_position(
        self, q_target: np.ndarray, enable_gripper: bool = True
    ) -> bool:
        """
        Write a position to all motors of the robot.

        Returns True when the bus write was issued without error, False when it
        was skipped (arm off the bus) or raised.
        """
        if not self.is_connected:
            return False

        values = q_target.tolist()
        motor_names = list(self.motors.keys())

        # Gripper is the last parameter of q_target (last motor)
        if not enable_gripper:
            values = values[:-1]
            motor_names = motor_names[:-1]

        try:
            self.motors_bus.write(
                "Goal_Position", values=values, motor_names=motor_names
            )
            self.motor_communication_errors = 0
            return True
        except Exception as e:
            logger.warning(f"Error writing motor position: {e}")
            self.update_motor_errors()
            return False

    def read_group_motor_position(self) -> np.ndarray:
        """
        Read the position of all motors of the robot.
        """
        if not self.is_connected:
            return np.ones(6) * np.nan

        motor_names = list(self.motors.keys())
        try:
            motor_positions = self.motors_bus.read(
                "Present_Position", motor_names=motor_names
            )
            self.motor_communication_errors = 0
            self.last_position_read_monotonic = time.monotonic()
        except Exception as e:
            logger.warning(f"Error reading motor position: {e}")
            self.update_motor_errors()
            motor_positions = None

        if motor_positions is None:
            return np.ones(6) * np.nan
        return motor_positions

    def read_motor_torque(self, servo_id: int, **kwargs: Any) -> Optional[float]:
        """
        Read the torque of a Feetech servo.
        """
        if not self.is_connected:
            return None
        try:
            torque = self.motors_bus.read(
                "Present_Current",
                motor_names=self.servo_id_to_motor_name[servo_id],
            )
            self.motor_communication_errors = 0
            return torque
        except Exception as e:
            logger.warning(f"Error reading motor torque for servo {servo_id}: {e}")
            self.update_motor_errors()
            return None

    def read_motor_voltage(self, servo_id: int, **kwargs: Any) -> Optional[float]:
        """
        Read the voltage of a Feetech servo.
        """
        if not self.is_connected:
            return None
        try:
            voltage = self.motors_bus.read(
                "Present_Voltage",
                motor_names=self.servo_id_to_motor_name[servo_id],
            )
            self.motor_communication_errors = 0
            return float(np.asarray(voltage).flat[0]) / 10.0  # unit is 0.1V
        except Exception as e:
            logger.warning(f"Error reading motor voltage for servo {servo_id}: {e}")
            self.update_motor_errors()
            return None

    def status(self) -> RobotConfigStatus:
        temperature = self.current_temperature()
        torque_enabled, torque_age_s = self.read_torque_enabled()
        return RobotConfigStatus(
            name=self.name,
            device_name=getattr(self, "SERIAL_ID", None),
            temperature=temperature,
            serial=getattr(self, "SERIAL_ID", None),
            bus_connected=bool(self.is_connected),
            # Where /joints/read would take the positions from right now
            readback_source=(
                "hardware" if self.is_connected and not self.is_moving else "simulation"
            ),
            torque_enabled=torque_enabled,
            torque_age_ms=None if torque_age_s is None else torque_age_s * 1000,
            status_unix_s=time.time(),
        )

    def read_motor_temperature(
        self, servo_id: int, **kwargs: Any
    ) -> Optional[Tuple[float, float]]:
        """
        Read the temperature of a Feetech servo.
        """
        if not self.is_connected:
            return None
        try:
            present_temperature = self.motors_bus.read(
                "Present_Temperature",
                motor_names=self.servo_id_to_motor_name[servo_id],
            )
            if servo_id not in self._max_temperature_cache:
                max_temp = self.motors_bus.read(
                    "Max_Temperature_Limit",
                    motor_names=self.servo_id_to_motor_name[servo_id],
                )
                self._max_temperature_cache[servo_id] = float(max_temp.item())
            self.motor_communication_errors = 0

            return (
                float(present_temperature.item()),
                self._max_temperature_cache[servo_id],
            )  # unit is Celsius
        except Exception as e:
            logger.warning(f"Error reading motor temperature for servo {servo_id}: {e}")
            self.update_motor_errors()
            return None

    def write_group_motor_maximum_temperature(
        self, maximum_temperature_target: List[int], **kwargs: Any
    ) -> None:
        """
        Write the maximum temperature of all motors of a robot.
        """
        if not self.is_connected:
            return None
        values = maximum_temperature_target
        motor_names = list(self.motors.keys())
        try:
            self.motors_bus.write(
                "Lock", values=[0] * len(motor_names), motor_names=motor_names
            )
            self.motors_bus.write(
                "Max_Temperature_Limit", values=values, motor_names=motor_names
            )
            self.motors_bus.write(
                "Lock", values=[1] * len(motor_names), motor_names=motor_names
            )
            self._max_temperature_cache = {}
            self.motor_communication_errors = 0
        except Exception as e:
            logger.warning(f"Error writing motor temperature: {e}")
            self.update_motor_errors()
            return None

    async def calibrate(self) -> tuple[Literal["success", "in_progress", "error"], str]:
        """
        Compute and save offsets and signs for the motors.

        This method has to be called multiple time, moving the robot to the same position as in the simulation beforehand.
        """

        if not self.is_connected:
            self.calibration_current_step = 0
            logger.warning(
                "Robot is not connected. Cannot calibrate. Calibration sequence reset to 0."
            )
            return (
                "error",
                "Robot is not connected. Cannot calibrate. Calibration sequence reset to 0.",
            )

        voltage = self.current_voltage()
        if voltage is None:
            logger.warning("Cannot read voltage. Calibration sequence reset to 0.")
            self.calibration_current_step = 0
            self.config = None
            return (
                "error",
                "Cannot read voltage. Plug your robot to power.",
            )

        motor_voltage = np.mean(voltage)

        if np.abs(motor_voltage - 12.0) > np.abs(motor_voltage - 6.0):
            motor_voltage = 6
        else:
            motor_voltage = 12

        # Load default config
        voltage_as_str: str = f"{motor_voltage}V"
        default_config = self.get_default_base_robot_config(voltage=voltage_as_str)
        if default_config is not None:
            self.config = default_config
            self.config.pid_gains = default_config.pid_gains
            self.config.gripping_threshold = int(default_config.gripping_threshold)
            self.config.non_gripping_threshold = int(
                default_config.non_gripping_threshold
            )
        else:
            raise ValueError(
                f"Default config file not found for {self.name} at {voltage_as_str}."
            )

        self.disable_torque()

        # TODO: force pybullet to appear in headless to give the user instructions
        sim_helper_text = ""
        if config.SIM_MODE == SimulationMode.gui:
            sim_helper_text = "For reference, look at the simulation."
        else:
            sim_helper_text = "For reference, look in the instructions manual."

        if self.calibration_current_step == 0:
            # The first position is the initial position
            self.set_simulation_positions(np.zeros(self.num_actuated_joints))

            self.calibration_current_step += 1

            return (
                "in_progress",
                f"Step {self.calibration_current_step}/{self.calibration_max_steps}: Place the robot in POSITION 1. {sim_helper_text} Verify the gripper position.",
            )

        if self.calibration_current_step == 1:
            # Set the offset to the middle of the motor range
            self.calibrate_motors()
            self.config.servos_offsets = self.read_joints_position(
                unit="motor_units", source="robot"
            ).tolist()
            logger.info(
                f"Initial joint positions (motor units): {self.config.servos_offsets}"
            )
            # If the joint positions are NaN or None, we cannot continue
            if np.isnan(self.config.servos_offsets).any() or np.any(
                self.config.servos_offsets is None
            ):
                self.calibration_current_step = 0
                return (
                    "error",
                    "Calibration failed: joint positions are NaN. Please check that every wire of the robot is plugged correctly.",
                )

            # The second position is the calibration position
            self.set_simulation_positions(np.array(self.CALIBRATION_POSITION))
            self.calibration_current_step += 1

            return (
                "in_progress",
                f"Step {self.calibration_current_step}/{self.calibration_max_steps}: Place the robot in POSITION 2. {sim_helper_text} Verify the gripper position.",
            )

        if self.calibration_current_step == 2:
            self.config.servos_calibration_position = self.read_joints_position(
                unit="motor_units", source="robot"
            ).tolist()
            logger.info(
                f"Current joint positions (motor units): {self.config.servos_calibration_position}"
            )
            # If the joint positions are NaN or None, we cannot continue
            if np.isnan(self.config.servos_calibration_position).any() or np.any(
                self.config.servos_calibration_position is None
            ):
                self.calibration_current_step = 0
                return (
                    "error",
                    "Calibration failed: joint positions are NaN. Please check that every wire of the robot is plugged correctly.",
                )

            # If any of the joint positions are the same as the offsets, we cannot continue
            if np.any(
                np.array(self.config.servos_calibration_position)
                == np.array(self.config.servos_offsets)
            ):
                self.calibration_current_step = 0
                return (
                    "error",
                    "Calibration failed: joint positions are the same as the offsets. Please check that every wire of the robot is plugged correctly.",
                )

            self.config.servos_offsets_signs = np.sign(
                (
                    np.array(self.config.servos_calibration_position)
                    - np.array(self.config.servos_offsets)
                )
                / np.array(self.CALIBRATION_POSITION)
            ).tolist()
            logger.info(f"Motor signs computed: {self.config.servos_offsets_signs}")

            # Save to file
            path = self.config.save_local(serial_id=self.SERIAL_ID)
            self.calibration_current_step = 0

            return (
                "success",
                f"Step {self.calibration_max_steps}/{self.calibration_max_steps}: Calibration completed successfully. Offsets and signs saved to {path}",
            )

        raise ValueError(
            f"Invalid calibration step: {self.calibration_current_step}, must be between 0 and {self.calibration_max_steps - 1}"
        )

    def calibrate_motors(self, **kwargs: Any) -> None:
        """
        This is called during the calibration phase of the robot.
        It sets the offset of all motors to self.RESOLUTION/2.
        """
        if not self.is_connected:
            logger.warning("Robot is not connected.")
            return None

        self._torque_enabled_cache = None
        self.motors_bus.write("Torque_Enable", 128)
        time.sleep(1)

    async def gravity_compensation_loop(
        self,
        control_signal: ControlSignal,
    ) -> None:
        """
        Background task that implements gravity compensation control:
        - Applies gravity compensation to the robot
        """
        try:
            await self._gravity_compensation_loop(control_signal)
        finally:
            # However the loop ended, it is not running anymore
            control_signal.stop()

    async def _gravity_compensation_loop(
        self,
        control_signal: ControlSignal,
    ) -> None:
        # Set up PID gains for leader's gravity compensation
        current_voltage = self.current_voltage()
        if current_voltage is None:
            logger.warning(
                "Unable to read motor voltage. Check that your robot is plugged to power."
            )
            return
        motor_voltage = np.mean(current_voltage)
        voltage = "6V" if motor_voltage < 9.0 else "12V"

        # Define PID gains for all six motors
        p_gains = [3, 6, 6, 3, 3, 3]
        d_gains = [9, 9, 9, 9, 9, 9]
        default_p_gains = [12, 20, 20, 20, 20, 20]
        default_d_gains = [36, 36, 36, 32, 32, 32]
        alpha = np.array([0, 0.2, 0.2, 0.1, 0.2, 0.2])

        if voltage == "12V":
            p_gains = [int(p / 2) for p in p_gains]
            d_gains = [int(d / 2) for d in d_gains]
            default_p_gains = [6, 6, 6, 10, 10, 10]
            default_d_gains = [30, 15, 15, 30, 30, 30]

        # Enable torque if using gravity compensation
        self.enable_torque()

        # Apply custom PID gains to leader for all six motors
        for i in range(6):
            self._try_set_pid_gains_motors(
                servo_id=i + 1,
                p_gain=p_gains[i],
                i_gain=0,
                d_gain=d_gains[i],
            )
            await asyncio.sleep(0.05)

        # Control loop parameters
        num_joints = len(self.actuated_joints)
        joint_indices = list(range(num_joints))
        loop_period = 1 / 50

        # Main control loop
        while control_signal.is_in_loop():
            start_time = time.perf_counter()

            # Get leader's current joint positions
            pos_rad = self.read_joints_position(unit="rad")

            # Update PyBullet simulation for gravity calculation
            for i, idx in enumerate(joint_indices):
                self.sim.set_joint_state(self.p_robot_id, idx, pos_rad[i])
            self.sim.step()

            # Calculate gravity compensation torque
            positions = list(pos_rad)
            velocities = [0.0] * num_joints
            accelerations = [0.0] * num_joints
            tau_g = self.sim.inverse_dynamics(
                self.p_robot_id,
                positions,
                velocities,
                accelerations,
            )

            # Apply gravity compensation to leader
            theta_des_rad = pos_rad + alpha[:num_joints] * np.array(tau_g)
            self.write_joint_positions(theta_des_rad.tolist(), unit="rad")

            # Maintain loop frequency
            elapsed = time.perf_counter() - start_time
            sleep_time = max(0, loop_period - elapsed)
            await asyncio.sleep(sleep_time)

        # Cleanup: Reset leader's PID gains to default for all six motors
        for i in range(6):  # Changed from 4 to 6
            self._try_set_pid_gains_motors(
                servo_id=i + 1,
                p_gain=default_p_gains[i],
                i_gain=0,
                d_gain=default_d_gains[i],
            )
            await asyncio.sleep(0.05)
        logger.info("Gravity control stopped")
