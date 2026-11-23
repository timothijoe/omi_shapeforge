"""Bound the teacher's axial approach without changing task success thresholds."""
import numpy as np


def limit_approach(action, scale, insertion_axis, remaining_mm, phase, *, minimum_mm=.01):
    if not 0 < minimum_mm <= .1:raise ValueError('minimum approach increment must be in (0, 0.1] mm')
    result=np.asarray(action,dtype=float).copy()
    if phase!='insert' or remaining_mm>=2.:
        return result.astype(np.float32),dict(active=False)
    axis=np.asarray(insertion_axis,dtype=float)
    axis=axis/np.linalg.norm(axis)
    delta=result[:3]*np.asarray(scale[:3])
    axial=float(delta@axis)
    limit_mm=float(np.clip(max(remaining_mm,0.)*.2,minimum_mm,.1))
    limited=min(axial,limit_mm/1000)
    result[:3]=(delta+axis*(limited-axial))/scale[:3]
    result=np.clip(result,-1,1)
    return result.astype(np.float32),dict(active=True,remaining_mm=float(remaining_mm),
        axial_limit_mm=limit_mm,requested_axial_mm=axial*1000,limited_axial_mm=limited*1000)
