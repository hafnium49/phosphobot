# mypy: ignore-errors
# ---------------------------------------------------------------------------------------------
# VERBATIM COPY: the runtime of the servo compensation. Do not edit anything below the line
# "END OF HEADER": phosphobot/tests/phosphobot/servo_compensation/test_runtime_copy.py pins the
# sha256 of everything after that line to the sha256 of the source file.
#
#   source   tools/servo_compensation.py of https://github.com/hafnium49/so101-nmpc-control
#   commit   83423ae7f96dc1ff7157a7b4a03afa2fc71c40df
#   sha256   f2b6c4bd295062fc53e006792da7a1f4c7d89ca47c193ad684968fd2cb887df7
#
# To update: replace everything below the line with the new source file, and change the commit
# and sha256 here and the pin of the test.
#
# Used here: Compensator.from_config, Stream, GravityChain and the constants (numpy only).
# Not used here: what needs MuJoCo or the source repository's other tools (Compensator.from_file,
# chain_from_mujoco, export_config) and the bench wrapper CompensatingDriver.
# What the server adds around it (the config file, one stream per arm, the rest timer, the
# refusals) is phosphobot/phosphobot/compensated_write.py; see phosphobot/docs/servo_compensation.md.
# ----- END OF HEADER -----
"""SO-101 servo compensation: the frozen actuator model inverted in the command path (the "physics AI" the actuator
roadmap ends on; user, 2026-11-24). No robot I/O here.

The model (tools/actuator_fit.py, fitted on bench recordings; config/actuator_model/so101_actuator_v1.json) predicts,
per arm joint j, where a servo ends relative to its command, in ticks:

    err_j = bias_j - s_j K g_j(q) / kp_j - lag_j v_j - (psi0_j + psic_j |g_j(q)|) dir_j

(bias: a constant; sag: gravity torque over the servo's stiffness; lag: times the commanded speed; friction: a band on
the side the joint comes from). The compensation sends, instead of the request q, the command q - err(q): to first
order the servo then ends on q. It is feed-forward only: it reads the request, never the arm, so it cannot oscillate
with the servo. The gripper is not modelled and is never changed.

    Compensator   one arm's parameters, signs, offsets and gravity model: error_ticks(), command()
    Stream        commands in time order: speed and direction from the successive requests; rest() takes the speed
                  term back when the requests stop
    CompensatingDriver   a bench driver (tools/pose_bench_drivers.py) whose command() sends the compensated request

Terms can be taken alone: STATIC = ("bias", "sag") needs no speed; "lag" and "friction" complete it. Each joint's total
correction is clipped to max_ticks (60: twice the largest correction the fitted poses and paths ask for).

The lag used is the one of recorded pairs (lag_s.regression = the servo's own lag plus the hold of a 15-20 Hz command
stream), because a caller's stream holds each command the same way; a caller that streams much faster would pass
lag="value".
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Callable, Sequence

import numpy as np

JOINTS = ("shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll")
K = 4095 / (2 * np.pi)                 # ticks per radian
V0 = 20.0                              # ticks/s: the fit's speed scale of the friction direction, tanh(v / V0)
TERMS = ("bias", "sag", "lag", "friction")
STATIC = ("bias", "sag")
MAX_TICKS = 60.0
MAX_DT_S = 0.2                         # a request after a longer pause counts as one step of this length (not a crawl)
MIN_DT_S = 0.02                        # two requests closer than this: the speed is taken over this time
REST_TICKS_S = 1.0                     # below this commanded speed the joint is at rest: no lag term, the last direction kept
INTERVALS = 5                          # the speed is the step over the median of this many last intervals between requests
REST_AFTER_S = 0.05                    # a read this long after the last command finds the stream stopped (bench driver)


class Compensator:
    def __init__(self, params: dict[str, dict], signs: Sequence[float], offsets: Sequence[float],
                 gravity: Callable[[Sequence[float]], np.ndarray], max_ticks: float = MAX_TICKS):
        """params: per joint name {"kp" N m/rad, "lag_s", "psi0" ticks, "psic" ticks/(N m), "bias_ticks"}."""
        self.params = {n: {k: float(v) for k, v in params[n].items()} for n in JOINTS}
        self.signs, self.offsets = [float(v) for v in signs], [float(v) for v in offsets]
        self.gravity, self.max_ticks = gravity, float(max_ticks)
        col = lambda k: np.array([self.params[n][k] for n in JOINTS])
        self._kp, self._lag, self._psi0, self._psic, self._bias = col("kp"), col("lag_s"), col("psi0"), col("psic"), col("bias_ticks")
        self._s = np.array(self.signs[:5])

    @classmethod
    def from_file(cls, path: Path, key: str, gravity=None, lag: str = "regression", max_ticks: float = MAX_TICKS) -> "Compensator":
        """One set of an actuator model file. lag: "regression" (recorded pairs, the stream's hold included) or
        "value" (the servo's own). gravity: default the twin's (tools/actuator_fit.gravity_model)."""
        d = json.loads(Path(path).read_text())
        if key not in d.get("sets", {}):
            raise ValueError(f"{path}: no set {key}; it has {', '.join(sorted(d.get('sets', {})))}")
        s = d["sets"][key]
        if lag not in ("regression", "value"):
            raise ValueError(f"lag must be 'regression' or 'value', got {lag!r}")
        params = {}
        for n in JOINTS:
            j = s["joints"][n]
            lag_s = j["lag_s"].get("regression") if lag == "regression" else None
            params[n] = {"kp": j["kp_nm_per_rad"]["value"], "lag_s": j["lag_s"]["value"] if lag_s is None else lag_s,
                         "psi0": j["psi0_ticks"]["value"], "psic": j["psic_ticks_per_nm"]["value"], "bias_ticks": j["bias_ticks"]["value"]}
        if gravity is None:
            import actuator_fit
            gravity = actuator_fit.gravity_model()
        return cls(params, s["calibration"]["signs"], s["calibration"]["offsets"], gravity, max_ticks)

    @classmethod
    def from_config(cls, path: Path, serial: str) -> "Compensator":
        """One arm of an export_config file: numpy only (the gravity chain is in the file)."""
        cfg = json.loads(Path(path).read_text())
        if cfg.get("schema") != CONFIG_SCHEMA:
            raise ValueError(f"{path}: schema {cfg.get('schema')!r}, this reader knows {CONFIG_SCHEMA}")
        if serial not in cfg.get("arms", {}):
            raise ValueError(f"{path}: no arm {serial}; it has {', '.join(sorted(cfg.get('arms', {})))}")
        a = cfg["arms"][serial]
        return cls(a["params"], a["signs"], a["offsets"], GravityChain(cfg["chain"]), cfg.get("max_ticks", MAX_TICKS))

    def error_ticks(self, q_rad: Sequence[float], v_ticks_s, direction, terms: Sequence[str] = TERMS) -> np.ndarray:
        """The model's predicted achieved - commanded for the five arm joints at request q (rad, six values),
        commanded speed v (ticks/s) and friction direction (-1..1, tanh(v / V0) while moving)."""
        unknown = [t for t in terms if t not in TERMS]
        if unknown:
            raise ValueError(f"unknown term(s) {unknown}; the terms are {TERMS}")
        g = np.asarray(self.gravity(q_rad), float)[:5]
        v, d = np.asarray(v_ticks_s, float)[:5], np.asarray(direction, float)[:5]
        err = np.zeros(5)
        if "bias" in terms:
            err += self._bias
        if "sag" in terms:
            err -= self._s * K * g / self._kp
        if "lag" in terms:
            err -= self._lag * v
        if "friction" in terms:
            err -= (self._psi0 + self._psic * np.abs(g)) * d
        return err

    def command(self, q_rad: Sequence[float], v_ticks_s, direction, terms: Sequence[str] = TERMS) -> list[float]:
        """The command to send for request q: q - err in ticks, each joint's correction clipped to max_ticks; the
        gripper as requested."""
        q = [float(v) for v in q_rad]
        corr = np.clip(-self.error_ticks(q, v_ticks_s, direction, terms), -self.max_ticks, self.max_ticks)
        return [q[j] + float(corr[j]) / (self._s[j] * K) for j in range(5)] + q[5:6]


# ---------------------------------------------------------------- gravity without MuJoCo
GRAVITY = (0.0, 0.0, -9.81)
CHAIN_JOINTS = (*JOINTS, "gripper")


def _quat_to_mat(q) -> np.ndarray:
    w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def _axis_rot(axis: np.ndarray, angle: float) -> np.ndarray:
    a = axis / np.linalg.norm(axis)
    kx = np.array([[0.0, -a[2], a[1]], [a[2], 0.0, -a[0]], [-a[1], a[0], 0.0]])
    return np.eye(3) + np.sin(angle) * kx + (1.0 - np.cos(angle)) * (kx @ kx)


def chain_from_mujoco(xml: Path | None = None) -> dict:
    """The arm's kinematic chain as plain numbers, from the twin's XML (needs MuJoCo; run where the model is fitted):
    the bodies that move with the six joints, parents first, each with its pose in its parent, its hinge (index of
    the joint, axis and anchor in the body's frame) if it has one, its mass and centre of mass."""
    import mujoco
    if xml is None:
        import actuator_fit
        xml = actuator_fit.TWIN_XML
    m = mujoco.MjModel.from_xml_path(str(xml)); d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    jid = [mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, n) for n in CHAIN_JOINTS]
    if min(jid) < 0:
        raise ValueError(f"{xml} lacks one of the joints {CHAIN_JOINTS}")
    jbody = {int(m.jnt_bodyid[j]): k for k, j in enumerate(jid)}

    def moves(b):                                              # the body or one of its ancestors carries an arm joint
        while b > 0:
            if b in jbody:
                return True
            b = int(m.body_parentid[b])
        return False
    ids = [b for b in range(1, m.nbody) if moves(b)]           # MuJoCo numbers parents before children
    index = {b: i for i, b in enumerate(ids)}
    bodies = []
    for b in ids:
        parent = int(m.body_parentid[b])
        body = {"name": mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_BODY, b), "parent": index.get(parent, -1),
                "pos": m.body_pos[b].tolist(), "quat": m.body_quat[b].tolist(), "mass": float(m.body_mass[b]), "ipos": m.body_ipos[b].tolist(),
                "joint": None}
        if parent not in index:                                 # the chain's root: its parent does not move; bake that pose in
            body["parent_pos"], body["parent_quat"] = d.xpos[parent].tolist(), d.xquat[parent].tolist()
        if b in jbody:
            j = jid[jbody[b]]
            if m.jnt_type[j] != mujoco.mjtJoint.mjJNT_HINGE or int(m.body_jntnum[b]) != 1:
                raise ValueError(f"body {body['name']}: expected exactly one hinge joint")
            body["joint"] = {"index": jbody[b], "axis": m.jnt_axis[j].tolist(), "anchor": m.jnt_pos[j].tolist()}
        bodies.append(body)
    return {"joints": list(CHAIN_JOINTS), "gravity": list(GRAVITY), "bodies": bodies, "source": Path(xml).name}


class GravityChain:
    """q (six joint angles, rad) -> the gravity torque on the five arm joints at rest (N m), with numpy alone, from
    chain_from_mujoco's numbers. It equals the twin's qfrc_bias at rest (a test holds the two together)."""

    def __init__(self, chain: dict):
        self.bodies = chain["bodies"]
        self.g = np.array(chain.get("gravity", GRAVITY), float)

    def __call__(self, q: Sequence[float]) -> np.ndarray:
        q = np.asarray(q, float)
        R, p, com = [None] * len(self.bodies), [None] * len(self.bodies), [None] * len(self.bodies)
        hinge: dict[int, tuple] = {}                            # joint index -> (axis, anchor) in the world, body index
        for i, b in enumerate(self.bodies):
            if b["parent"] < 0:
                Rp, pp = _quat_to_mat(b["parent_quat"]), np.array(b["parent_pos"], float)
            else:
                Rp, pp = R[b["parent"]], p[b["parent"]]
            Ri, pi = Rp @ _quat_to_mat(b["quat"]), pp + Rp @ np.array(b["pos"], float)
            if b["joint"] is not None:
                axis, anchor = np.array(b["joint"]["axis"], float), np.array(b["joint"]["anchor"], float)
                anchor_w = pi + Ri @ anchor
                hinge[b["joint"]["index"]] = (Ri @ axis / np.linalg.norm(axis), anchor_w, i)
                Ri = Ri @ _axis_rot(axis, float(q[b["joint"]["index"]]))
                pi = anchor_w - Ri @ anchor
            R[i], p[i], com[i] = Ri, pi, pi + Ri @ np.array(b["ipos"], float)
        below = [set() for _ in self.bodies]                    # body -> itself and its descendants
        for i in range(len(self.bodies) - 1, -1, -1):
            below[i].add(i)
            if self.bodies[i]["parent"] >= 0:
                below[self.bodies[i]["parent"]] |= below[i]
        tau = np.zeros(5)
        for k in range(5):
            axis_w, anchor_w, i = hinge[k]
            tau[k] = -sum(self.bodies[c]["mass"] * float(np.dot(np.cross(axis_w, com[c] - anchor_w), self.g)) for c in below[i])
        return tau


# ---------------------------------------------------------------- one file for a driver
CONFIG_SCHEMA = 1


def export_config(model_file: Path, out: Path, label: str = "s4", xml: Path | None = None) -> dict:
    """Write the one file a driver needs: per arm (by serial) the parameters, signs and offsets of the model's set
    <serial>:<label>, the gravity chain, the terms and the bounds. Needs MuJoCo (for the chain); the file does not."""
    d = json.loads(Path(model_file).read_text())
    arms = {}
    for key, s in d["sets"].items():
        serial, _, lab = key.partition(":")
        if lab != label:
            continue
        c = Compensator.from_file(model_file, key, gravity=lambda q: np.zeros(5))
        arms[serial] = {"set": key, "params": c.params, "signs": c.signs, "offsets": c.offsets,
                        "calibration_sha256": s["calibration"].get("sha256"), "validation_passed": bool(s["validation"]["passed"])}
    cfg = {"schema": CONFIG_SCHEMA, "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "model_file": Path(model_file).name,
           "model_version": d.get("model_version"), "model_sha256": hashlib.sha256(Path(model_file).read_bytes()).hexdigest(),
           "lag": "regression", "terms": list(TERMS), "static_terms": list(STATIC), "max_ticks": MAX_TICKS,
           "timing": {"v0_ticks_s": V0, "max_dt_s": MAX_DT_S, "min_dt_s": MIN_DT_S, "rest_ticks_s": REST_TICKS_S, "intervals": INTERVALS,
                      "rest_after_s": REST_AFTER_S},
           "arms": arms, "chain": chain_from_mujoco(xml)}
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(cfg, indent=1) + "\n")
    return cfg


class Stream:
    """Requests in time order -> commands. Speed is the step from the previous request over the usual time between
    requests (the median of the last INTERVALS intervals, each within MIN_DT_S..MAX_DT_S; a longer pause is a break
    and does not count); at rest the friction term keeps the direction the joint last came from.

    A stream that stops must call rest(): the last command of a move carries lag x speed, and a servo left with it
    rests that far past the request (2026-11-24, block 2: 27 ticks on the base and the wrist roll)."""

    def __init__(self, comp: Compensator, terms: Sequence[str] = TERMS):
        self.comp, self.terms = comp, tuple(terms)
        self.reset()

    def reset(self) -> None:
        """What came before is void (the arm was relieved, or another program moved it)."""
        self._q = self._t = None
        self._dir = np.zeros(5)
        self._intervals: list[float] = []
        self.pending = False             # True while the last command carries a speed term that rest() must take back

    def step(self, q_rad: Sequence[float], t: float) -> list[float]:
        q = np.asarray(q_rad, float)
        v = np.zeros(5)
        if self._q is not None:
            gap = float(t) - self._t
            if gap <= MAX_DT_S:
                self._intervals = (self._intervals + [max(MIN_DT_S, gap)])[-INTERVALS:]
            dt = float(np.median(self._intervals)) if self._intervals else MAX_DT_S
            v = self.comp._s * K * (q[:5] - self._q[:5]) / dt
        moving = np.abs(v) >= REST_TICKS_S
        self._dir = np.where(moving, np.tanh(v / V0), self._dir)
        self._q, self._t = q, float(t)
        self.pending = bool(moving.any()) and "lag" in self.terms
        return self.comp.command(q_rad, v, self._dir, self.terms)

    def rest(self, t: float) -> list[float] | None:
        """The command for a stream that has stopped: the last request at speed 0, the friction side kept. None when
        the last command carried no speed term (nothing to take back)."""
        if not self.pending or self._q is None:
            return None
        self.pending = False
        return self.comp.command(list(self._q), np.zeros(5), self._dir, self.terms)


class CompensatingDriver:
    """A bench driver whose command(q) sends the compensated request. Everything else (reads, checks, torque, the
    send-time stamp) is the wrapped driver's own; relieve() and torque_on() also reset the stream, because they set
    the servo's goal to where the arm is. A read() that comes REST_AFTER_S or more after the last command finds the
    stream stopped and sends its rest command first (the bench reads right after a command while it moves, and one
    interval later when it starts to record a resting arm). A driver in the command path of a server would do the
    same from a timer."""

    def __init__(self, inner, comp: Compensator, terms: Sequence[str] = TERMS, now=time.monotonic):
        self.inner, self.stream, self._now = inner, Stream(comp, terms), now
        self._t_command = None

    def command(self, q_rad: Sequence[float]) -> None:
        t = self._now()
        self.inner.command(self.stream.step(q_rad, t))
        self._t_command = t

    def read(self, *a, **k):
        if self.stream.pending and self._t_command is not None and self._now() - self._t_command >= REST_AFTER_S:
            q = self.stream.rest(self._now())
            if q is not None:
                self.inner.command(q)
        return self.inner.read(*a, **k)

    def relieve(self, *a, **k):
        self.stream.reset()
        return self.inner.relieve(*a, **k)

    def torque_on(self, *a, **k):
        self.stream.reset()
        return self.inner.torque_on(*a, **k)

    def __getattr__(self, name):
        return getattr(self.inner, name)
