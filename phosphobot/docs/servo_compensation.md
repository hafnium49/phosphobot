# Servo compensation (opt-in)

An addition of this fork, for the SO-100 / SO-101 (`SO100Hardware`). It is off unless
a request asks for it: without the query parameter `compensate`, `POST /joints/write`
writes and answers exactly what it did before (tests pin the motor units and the
response bytes of the base commit).

## What it does

A measured model of the servos predicts, per arm joint, where a servo ends relative to
its command: a constant, the sag under gravity, a lag times the commanded speed, and a
friction band on the side the joint comes from. A compensated write sends the request
minus that predicted error, so that the servo ends on the request. It is feed-forward:
it reads the requests only, never the arm. The gripper is not modelled and is written
as requested. Each joint's correction is bounded to 60 ticks: the runtime clips it, a
config file may tighten the bound (`max_ticks`) and never widen it, and the server itself
compares every command with its request in motor units before it writes (below).

The model's equation and the stream logic are `phosphobot/hardware/servo_compensation.py`,
a verbatim copy of a file of another repository (source, commit and sha256 in its header;
a test pins the sha256 of the copy). The server's part is `phosphobot/compensated_write.py`.

## Enabling it

Start the server with the environment variable `PHOSPHOBOT_SERVO_COMPENSATION` set to
the path of the config file (schema 1: per arm serial the parameters, signs and offsets,
the gravity chain, `max_ticks`).

- The file is read once, at the first request that asks for compensation, and a log line
  says what was loaded (`Servo compensation config loaded from ...`).
- Variable unset: requests that ask for compensation are refused with 409
  (`servo compensation is not configured on this server (PHOSPHOBOT_SERVO_COMPENSATION is unset)`).
- File unreadable, not JSON, of another schema, with a `max_ticks` that is not a number
  in (0, 60], or with an arm whose `validation_passed` is not true: they are refused
  with 500, and an error is logged. The file is not read again: correct it and restart
  the server.
- In both cases the server runs as usual and every other request is unchanged.

## The request

`POST /joints/write?compensate=full|static[&final=true]` (with `robot_id` and/or
`serial` as usual), body `{"angles": [six angles], "unit": "rad"}`.

- `static`: the constant and the sag. No speed is used.
- `full`: also the lag and the friction. Speed and direction come from the successive
  requests of the arm's stream, stamped with the server's `time.monotonic()` when each
  request is handled.

The server keeps one stream per arm and per value of `compensate`. A request with the
other value starts that stream anew.

`final` (default `false`) says that this request is the last one of its move. Its
command carries no speed term: the constant, the sag and the friction on the side the
joint arrives from. No rest command follows, and the timer of the request before is
cancelled. With `static` it is accepted and changes nothing in the command.

A caller that knows the last point of its move should name it. The rest timer (below)
is the fallback for a stream that just stops, and it leaves a short overshoot: until it
fires, the servo follows a command that leads past the request (measured 2026-11-24 on
the right arm: 15 to 31 ticks for about 0.15 s when a 0.3 rad/s line stops dead).

The response has one more field, only on compensated writes:

```json
{"status": "ok", "robot_id": 1, "serial": "5A68009540", "bus_write": true,
 "compensation": {"terms": "full", "correction_ticks": [0, 1, -7, -3, 1], "final": false}}
```

`correction_ticks`: motor units of the command minus motor units of the request, for the
five arm joints, as written. `final`: as requested.

## Refusals

A request that asks for compensation and cannot have it is refused and nothing is
written. There is no fallback to an uncompensated write.

| Status | Reason |
|--------|--------|
| 400 | `unit` is not `rad`, `joints_ids` is given, not six angles, an angle (or its command) outside -pi..pi, or the robot is not an SO-100/SO-101. Also `final=true` without `compensate`: a caller that believes it is compensated is not served an uncompensated write |
| 409 | `PHOSPHOBOT_SERVO_COMPENSATION` is unset; or the arm's serial is not in the config; or the arm's loaded calibration (the six `servos_offsets_signs` and `servos_offsets`) is not the one in the config for that serial; the detail says which |
| 422 | `compensate` is neither `full` nor `static`, or `final` is not a boolean |
| 500 | the config file cannot be used; or the command computed for this request is more than 60 (+1 for the truncation) motor units from the request on an arm joint, or changes the gripper at all (a fault on the server's side; the detail names the joint and the units) |
| 503 | the arm is off the bus (also with `--only-simulation`: the simulation is never compensated) |
| 502 | the bus write failed; the arm's streams are void |

A request that is refused before the bus was touched (every row but the last) changes
nothing: the arm's stream is as after the last accepted request, the rest command of
that request still comes, and the raw read still reports that request.

## The rest command

The last command of a moving `full` stream carries lag x speed. A servo left with it
rests past the request (up to 27 ticks were measured). So after a `full` write whose
command carries a speed term (not a `final` one), the server starts a one-shot timer for
that arm on its event loop. If no further compensated request for the arm arrives within

    REST_DELAY_S = 1.5 x the stream's usual interval between requests, within 0.08 .. 0.30 s

it writes the stream's rest command once (the last request with the constant and the sag
only: no speed, and no friction side, because the joint ran on while the stop went
unnoticed and comes back), through the same write path. A further compensated request cancels the timer.

Before it writes, the timer reads the bus: `Torque_Enable`, then the six `Goal_Position`
registers (each read tried twice). The rest command is not written when the arm is off
the bus, when torque is not on for all six servos, or when the goal registers are not
the motor units of the stream's last command: then somebody else wrote this arm (a mover
of the server in a thread of its own that slipped between, or another process on the
bus), and its goal is left alone. A rest command that was not written is logged
(`the rest command of arm ... was not written: ...`) and voids the arm's streams.

A client that needs the arm at rest on its request and did not send `final` waits at
least `REST_DELAY_S` after its last request. The timer runs on the server's event loop, which also executes the
requests and their bus I/O one at a time: under load the rest command comes later, not
earlier.

## Anything else that writes the arm's goal

voids the arm's streams and cancels its rest timer: an uncompensated `/joints/write`,
`/torque/toggle` (either way), the move endpoints (`/move/init`, `/move/absolute`,
`/move/relative`, `/move/sleep`, `/move/hello`, `/move/teleop` and the teleoperation
sockets), `/calibrate`, `/robot/disconnect`, a USB drop, and the loops that run inside
the server (leader-follower, gravity compensation, playback, AI control). All of them end
in six methods of `SO100Hardware` (`write_motor_position`, `write_group_motor_position`,
`enable_torque`, `disable_torque`, `calibrate_motors`, `disconnect`), and these call
`SO100Hardware._goal_written`. The next compensated request starts a stream: no speed,
no direction.

## The raw read

`POST /joints/read/raw` has two more fields:

- `requested_position`: the last compensated request, six motor units, converted as an
  uncompensated write converts radians. `goal_position` stays what the register holds:
  the compensated command.
- `compensation`: `"full"` or `"static"`.

Both are `null` when the arm's last goal write was not a compensated one (including
after a compensated write or a rest command that failed).

## Notes for callers

- Do not mix compensated writes with another mover of the same arm. The compensation
  assumes the PID gains of the arm's calibration; the leader-follower and gravity loops
  change them.
- The fork converts radians to motor units with `int()`: request and command are each
  truncated, so the correction as written is within one unit of the model's.
- The simulation mirror of the arm is set to the command, not to the request.

## Tests

```bash
cd phosphobot
uv run pytest tests/phosphobot/servo_compensation -p no:xdist
```

They use the S1a harness (real `SO100Hardware` objects on a fake bus) and its guard: no
test can open a serial port or connect to the rig's services.

To update the runtime: replace everything below the header of
`phosphobot/hardware/servo_compensation.py` with the new source file, and change the
commit and sha256 in the header and in `tests/phosphobot/servo_compensation/test_runtime_copy.py`.
