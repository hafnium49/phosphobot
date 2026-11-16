"""
The two dependencies that name the arm a request is for.

- arm_required: for endpoints that move an arm or change its settings. A request
  that names no arm is refused (422): there is no default arm.
- arm_or_first: for reads. A request that names no arm means robot 0.

An arm is named by `robot_id` (its position in the list of robots, which changes
when the list does), by `serial`, or by both; see RobotConnectionManager.resolve.
"""

from dataclasses import dataclass
from typing import List, Optional

from fastapi import Depends, HTTPException

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


def robot_by_serial(robots: list, serial: str) -> BaseRobot:
    """
    The one robot of the list with this serial.
    Refuses 'no_serial' and a serial held by two robots (400), and a serial that
    no robot has (404).
    """
    if serial == "no_serial":
        raise HTTPException(
            status_code=400, detail="'no_serial' does not name a robot."
        )
    matches: List[BaseRobot] = [
        robot for robot in robots if getattr(robot, "SERIAL_ID", None) == serial
    ]
    if len(matches) > 1:
        raise HTTPException(
            status_code=400,
            detail=f"Serial {serial} is held by {len(matches)} robots.",
        )
    if not matches:
        raise HTTPException(
            status_code=404, detail=f"No robot with serial {serial} connected."
        )
    return matches[0]
