"""
The two dependencies that name the arm a request is for.

- arm_required: for endpoints that move an arm or change its settings. A request
  that names no arm is refused (422): there is no default arm.
- arm_or_first: for reads. A request that names no arm means robot 0.

An arm is named by `robot_id` (its position in the list of robots, which changes
when the list does), by `serial`, or by both; see RobotConnectionManager.resolve.
"""

from dataclasses import dataclass
from typing import Optional

from fastapi import Depends

from phosphobot.models import BaseRobot
from phosphobot.robot import RobotConnectionManager, get_rcm


@dataclass
class Arm:
    robot_id: int
    serial: Optional[str]
    robot: BaseRobot


async def _arm(
    rcm: RobotConnectionManager,
    robot_id: Optional[int],
    serial: Optional[str],
    required: bool,
) -> Arm:
    resolved_id, robot = await rcm.resolve(robot_id, serial, required=required)
    return Arm(
        robot_id=resolved_id, serial=getattr(robot, "SERIAL_ID", None), robot=robot
    )


async def arm_required(
    robot_id: Optional[int] = None,
    serial: Optional[str] = None,
    rcm: RobotConnectionManager = Depends(get_rcm),
) -> Arm:
    return await _arm(rcm, robot_id, serial, required=True)


async def arm_or_first(
    robot_id: Optional[int] = None,
    serial: Optional[str] = None,
    rcm: RobotConnectionManager = Depends(get_rcm),
) -> Arm:
    return await _arm(rcm, robot_id, serial, required=False)
