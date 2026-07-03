"""
! @file anomaly_injector.py
! @brief Physically-grounded, labelled anomaly / false-data-injection (FDI) engine.

@details
STGen generates *normal* sensor streams from physically-validated models
(Ornstein-Uhlenbeck thermal drift, MEMS noise floors, kinematic clamps; see
``sensor_generator.py``). This module produces the adversarial counterpart: it
perturbs the physically-modelled value of selected (malicious) nodes so that the
result deliberately *violates a named physical invariant* of the normal model.

Because the normal baseline is statistically validated against the Intel Berkeley
deployment, an anomaly here is not an arbitrary corruption — it is a *quantified,
physically-defined departure from a validated model*, and every injected sample
carries a ground-truth label. That is what makes the generated attacks
scientifically checkable (see ``run_anomaly_validation.py``).

Design properties (industry-grade requirements):
  * Deterministic & reproducible — a single seed drives device selection and all
    per-message decisions (no reliance on the global ``random`` state).
  * Physically grounded — each attack crosses a specific invariant
    (absolute range, operating range, temporal step bound, or noise floor) that
    is defined once in ``PHYSICAL_INVARIANTS`` and reused by the validator.
  * Ground-truth labelled — every record gets ``{is_attack, attack_type,
    true_value, injected_value, ...}``; labels are persisted to JSONL.
  * Side-effect free on normal runs — when no ``adversarial`` config block is
    present the generator path is byte-identical to before.

Scope: STGen operates above OSI Layer 4, so these are *application/transport-layer*
data-plane anomalies (false data injection), not PHY/MAC/L3 attacks.

@author STGen Development Team
@version 1.0
"""
from __future__ import annotations

import json
import math
import random
import time
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_LOG = logging.getLogger("anomaly_injector")


# =============================================================================
# Physical invariants of the normal model (shared with the validator)
# =============================================================================
# For each modality:
#   range      : absolute physical sensor range [lo, hi]. Crossing it is a hard,
#                first-principles violation (out-of-range FDI).
#   operating  : the normal indoor operating envelope used for calibration; a
#                value outside it but inside `range` is a *stealthy* anomaly.
#   noise      : nominal per-sample standard deviation of the validated stream
#                (the noise floor); a variance attack must exceed it by `intensity`.
#   max_step   : largest plausible change between two consecutive samples; an
#                impossible-jump attack must exceed it.
# Values trace to sensor_generator.py constants and the IBRL calibration
# (temp std ~= 3.38 C, voltage clamp [1.5, 3.5] V, light OU clamp hi = 1e5 lux).
PHYSICAL_INVARIANTS: Dict[str, Dict[str, Any]] = {
    "temp":        {"range": (-40.0, 85.0),  "operating": (10.0, 40.0),  "noise": 3.38, "max_step": 5.0,   "unit": "C"},
    "temperature": {"range": (-40.0, 85.0),  "operating": (10.0, 40.0),  "noise": 3.38, "max_step": 5.0,   "unit": "C"},
    "humidity":    {"range": (0.0, 100.0),   "operating": (15.0, 85.0),  "noise": 6.28, "max_step": 12.0,  "unit": "%"},
    "light":       {"range": (0.0, 100000.0),"operating": (0.0, 1500.0), "noise": 80.0, "max_step": 700.0, "unit": "lux"},
    "lux":         {"range": (0.0, 100000.0),"operating": (0.0, 1500.0), "noise": 80.0, "max_step": 700.0, "unit": "lux"},
    "voltage":     {"range": (1.5, 3.5),     "operating": (2.3, 2.8),    "noise": 0.12, "max_step": 0.2,   "unit": "V"},
    "pressure":    {"range": (300.0, 1100.0),"operating": (980.0, 1040.0),"noise": 10.0,"max_step": 20.0,  "unit": "hPa"},
    "co2":         {"range": (300.0, 5000.0),"operating": (400.0, 1200.0),"noise": 100.0,"max_step": 200.0,"unit": "ppm"},
    "sound":       {"range": (0.0, 140.0),   "operating": (30.0, 90.0),  "noise": 15.0, "max_step": 30.0,  "unit": "dB"},
}

# The attack families this engine knows how to synthesise.
ATTACK_TYPES = (
    "fdi_spoof",        # out-of-absolute-range injection (hard invariant break)
    "out_of_range",     # alias of fdi_spoof
    "bias_drift",       # slow additive ramp -> leaves operating range (stealthy)
    "stuck_at",         # frozen value (zero innovation variance)
    "replay",           # re-emit an earlier valid value
    "impossible_jump",  # step larger than max_step (temporal invariant break)
    "variance_burst",   # noise far above the sensor noise floor
)


def get_invariants(sensor_type: str) -> Optional[Dict[str, Any]]:
    """Return the physical-invariant record for a modality, or None if unmodelled."""
    return PHYSICAL_INVARIANTS.get(sensor_type)


def scalar_field(sensor_data: Dict[str, Any]) -> Tuple[Optional[str], Optional[float]]:
    """Locate the primary numeric field of a sensor payload.

    Returns (key, value). Prefers ``value``; otherwise the first numeric field.
    Vector sensors (gps/accel) return (None, None) and are left untouched.
    """
    if isinstance(sensor_data.get("value"), (int, float)):
        return "value", float(sensor_data["value"])
    for k, v in sensor_data.items():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return k, float(v)
    return None, None


# ---- physical-invariant predicates (reused by run_anomaly_validation.py) -----

def violates_range(sensor_type: str, value: float) -> bool:
    inv = get_invariants(sensor_type)
    if inv is None:
        return False
    lo, hi = inv["range"]
    return value < lo or value > hi


def violates_operating(sensor_type: str, value: float) -> bool:
    inv = get_invariants(sensor_type)
    if inv is None:
        return False
    lo, hi = inv["operating"]
    return value < lo or value > hi


def violates_step(sensor_type: str, value: float, prev: Optional[float]) -> bool:
    inv = get_invariants(sensor_type)
    if inv is None or prev is None:
        return False
    return abs(value - prev) > inv["max_step"]


# =============================================================================
# Configuration
# =============================================================================
@dataclass
class AnomalyConfig:
    """Parsed view of the JSON ``adversarial`` block."""
    enabled: bool = True
    seed: Optional[int] = None
    attack: str = "fdi_spoof"
    fraction: float = 0.1                       # fraction of nodes that are malicious
    device_ids: Optional[List[int]] = None      # explicit malicious node indices (overrides fraction)
    intensity: float = 3.0                       # attack magnitude (in noise-floor multiples / step multiples)
    probability: float = 1.0                     # per-message injection probability for a malicious node
    start_s: float = 0.0
    stop_s: float = float("inf")
    label_file: Optional[str] = "results/anomaly_labels.jsonl"

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AnomalyConfig":
        attack = str(d.get("attack", "fdi_spoof")).lower()
        if attack == "out_of_range":
            attack = "fdi_spoof"
        if attack not in ATTACK_TYPES:
            raise ValueError(f"unknown attack '{attack}'; valid: {ATTACK_TYPES}")
        return cls(
            enabled=bool(d.get("enabled", True)),
            seed=d.get("seed"),
            attack=attack,
            fraction=float(d.get("fraction", 0.1)),
            device_ids=d.get("device_ids"),
            intensity=float(d.get("intensity", 3.0)),
            probability=float(d.get("probability", 1.0)),
            start_s=float(d.get("start_s", 0.0)),
            stop_s=float(d.get("stop_s", float("inf"))),
            label_file=d.get("label_file", "results/anomaly_labels.jsonl"),
        )


# =============================================================================
# The injector
# =============================================================================
class AnomalyInjector:
    """Inject physically-defined, labelled anomalies into a sensor stream."""

    def __init__(self, adversarial_cfg: Dict[str, Any], num_clients: int):
        self.cfg = AnomalyConfig.from_dict(adversarial_cfg)
        self.num_clients = max(1, int(num_clients))
        self._rng = random.Random(self.cfg.seed)

        # Deterministic selection of malicious node indices.
        if self.cfg.device_ids is not None:
            self.malicious = {int(i) for i in self.cfg.device_ids if 0 <= int(i) < self.num_clients}
        else:
            k = max(0, min(self.num_clients, round(self.cfg.fraction * self.num_clients)))
            self.malicious = set(self._rng.sample(range(self.num_clients), k)) if k else set()

        # Per-device scratch state for stateful attacks (drift/stuck/replay/jump).
        self._dev_state: Dict[int, Dict[str, Any]] = {i: {"bias": 0.0, "stuck": None,
                                                           "buf": [], "last_true": None}
                                                      for i in self.malicious}
        self._labels: List[Dict[str, Any]] = []
        self.counts = {"normal": 0, "attack": 0}
        _LOG.info("AnomalyInjector: attack=%s malicious=%d/%d intensity=%.2f seed=%s",
                  self.cfg.attack, len(self.malicious), self.num_clients,
                  self.cfg.intensity, self.cfg.seed)

    # -- public API -----------------------------------------------------------
    def is_malicious(self, dev_index: int) -> bool:
        return dev_index in self.malicious

    def maybe_inject(self, dev_index: int, dev_id: str, sensor_type: str,
                     sensor_data: Dict[str, Any], t_elapsed: float,
                     seq_no: int) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Possibly replace the true reading of a malicious node with an attack value.

        Returns (sensor_data, label). ``sensor_data`` is returned modified in place
        when an attack fires; ``label`` is the ground-truth record for this message.
        """
        key, true_val = scalar_field(sensor_data)
        active = (
            self.cfg.enabled
            and dev_index in self.malicious
            and self.cfg.start_s <= t_elapsed <= self.cfg.stop_s
            and key is not None
            and self._rng.random() < self.cfg.probability
        )
        if not active:
            self.counts["normal"] += 1
            return sensor_data, self._label(False, None, dev_id, sensor_type,
                                            true_val, true_val, t_elapsed, seq_no)

        atk_val = self._apply_attack(dev_index, sensor_type, float(true_val))
        sensor_data[key] = round(atk_val, 4)
        self.counts["attack"] += 1
        label = self._label(True, self.cfg.attack, dev_id, sensor_type,
                            true_val, atk_val, t_elapsed, seq_no)
        self._labels.append(label)
        if len(self._labels) >= 5000:
            self._flush()
        return sensor_data, label

    def summary(self) -> Dict[str, Any]:
        return {
            "attack": self.cfg.attack,
            "intensity": self.cfg.intensity,
            "seed": self.cfg.seed,
            "num_clients": self.num_clients,
            "malicious_nodes": sorted(self.malicious),
            "n_normal": self.counts["normal"],
            "n_attack": self.counts["attack"],
        }

    def close(self) -> None:
        self._flush()

    # -- attack synthesis -----------------------------------------------------
    def _apply_attack(self, dev_index: int, sensor_type: str, true_val: float) -> float:
        inv = get_invariants(sensor_type)
        st = self._dev_state[dev_index]
        a = self.cfg.attack
        I = self.cfg.intensity

        # Fall back to generic bounds if the modality is unmodelled.
        lo, hi = (inv["range"] if inv else (true_val - 100, true_val + 100))
        op_lo, op_hi = (inv["operating"] if inv else (lo, hi))
        noise = inv["noise"] if inv else max(1e-6, abs(true_val) * 0.05)
        max_step = inv["max_step"] if inv else max(1e-6, abs(true_val) * 0.5)

        out: float
        if a in ("fdi_spoof", "out_of_range"):
            # Hard violation: push above the absolute physical maximum.
            out = hi + I * noise
        elif a == "bias_drift":
            # Stealthy additive ramp that accumulates each step until it leaves
            # the operating envelope.
            st["bias"] += 0.1 * I * noise
            out = true_val + st["bias"]
        elif a == "stuck_at":
            if st["stuck"] is None:
                st["stuck"] = true_val
            out = st["stuck"]
        elif a == "replay":
            st["buf"].append(true_val)
            if len(st["buf"]) > 64:
                st["buf"].pop(0)
            out = self._rng.choice(st["buf"]) if st["buf"] else true_val
        elif a == "impossible_jump":
            base = st["last_true"] if st["last_true"] is not None else true_val
            direction = 1.0 if self._rng.random() < 0.5 else -1.0
            out = base + direction * (I + 1.0) * max_step
        elif a == "variance_burst":
            out = true_val + self._rng.gauss(0.0, I * noise)
        else:
            out = true_val

        st["last_true"] = true_val
        return out

    # -- internals ------------------------------------------------------------
    def _label(self, is_attack: bool, attack_type: Optional[str], dev_id: str,
               sensor_type: str, true_val: Optional[float], inj_val: Optional[float],
               t: float, seq: int) -> Dict[str, Any]:
        return {
            "is_attack": bool(is_attack),
            "attack_type": attack_type,
            "device": dev_id,
            "sensor": sensor_type,
            "true_value": None if true_val is None else round(float(true_val), 4),
            "injected_value": None if inj_val is None else round(float(inj_val), 4),
            "t": round(t, 4),
            "seq": seq,
        }

    def _flush(self) -> None:
        if not self._labels or not self.cfg.label_file:
            self._labels = []
            return
        path = Path(self.cfg.label_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as fh:
            for rec in self._labels:
                fh.write(json.dumps(rec) + "\n")
        self._labels = []


def build_from_cfg(cfg: Dict[str, Any]) -> Optional[AnomalyInjector]:
    """Construct an injector from a full experiment cfg, or None if not requested."""
    adv = cfg.get("adversarial")
    if not adv or not adv.get("enabled", True):
        return None
    return AnomalyInjector(adv, num_clients=int(cfg.get("num_clients", 1)))
