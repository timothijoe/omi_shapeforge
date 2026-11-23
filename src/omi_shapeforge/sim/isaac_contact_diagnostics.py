"""Substep contact diagnostics. Magnitude sums are not wrist-sensor wrenches."""
from collections import defaultdict
import numpy as np
from pxr import PhysicsSchemaTools

from .isaac_contact_runtime import ContactMonitor


class DiagnosticContactMonitor(ContactMonitor):
    def __init__(self, dt, axis, shoulder_pair=None):
        self.axis = np.asarray(axis, dtype=float)
        self.axis /= np.linalg.norm(self.axis)
        super().__init__(dt, shoulder_pair)

    def clear(self):
        super().clear()
        self.substeps = 0
        self.scalar_impulse = 0.
        self.axial_absolute_impulse = 0.
        self.axial_peak = 0.
        self.axial_last = 0.
        self.pair_impulses = defaultdict(float)
        self.last_contact_headers = []

    def start_substep(self):
        super().start_substep()
        self.substeps += 1
        self.axial_last = 0.
        self.last_contact_headers = []

    def callback(self, headers, data):
        super().callback(headers, data)
        for header in headers:
            names = [str(PhysicsSchemaTools.intToSdfPath(header.collider0)),
                     str(PhysicsSchemaTools.intToSdfPath(header.collider1))]
            if not any('sim_module' in name for name in names):
                continue
            pair = ' | '.join(sorted(name.rsplit('/', 1)[-1] for name in names))
            self.last_contact_headers.append(dict(pair=pair, event=str(header.type), points=header.num_contact_data))
            for contact in data[header.contact_data_offset:header.contact_data_offset+header.num_contact_data]:
                impulse = np.asarray(contact.impulse, dtype=float)
                scalar = float(np.linalg.norm(impulse))
                axial = abs(float(impulse @ self.axis))
                self.scalar_impulse += scalar
                self.axial_absolute_impulse += axial
                self.axial_last += axial / self.dt
                self.pair_impulses[pair] += scalar
        self.axial_peak = max(self.axial_peak, self.axial_last)

    def summary(self):
        duration = max(1, self.substeps)*self.dt
        return dict(scalar_contact_sum_mean_N=self.scalar_impulse/duration,
                    axial_absolute_sum_mean_N=self.axial_absolute_impulse/duration,
                    axial_absolute_sum_last_N=self.axial_last,
                    axial_absolute_sum_peak_N=self.axial_peak,
                    contact_pair_mean_N={key: value/duration for key, value in
                        sorted(self.pair_impulses.items(), key=lambda item: -item[1])},
                    physics_substeps=self.substeps,
                    last_contact_headers=self.last_contact_headers,
                    force_definition='sum of point impulse magnitudes or absolute axial projections / dt; not net wrench')
