"""Control-sampled minimum separating translation for two oriented boxes.

Independent geometry diagnostic. This is not the PhysX contact-point separation
and does not claim to measure the maximum overlap between control samples.
"""
import numpy as np


def box_overlap_mm(center_a, rotation_a, half_a, center_b, rotation_b, half_b):
    a,b=np.asarray(rotation_a),np.asarray(rotation_b)
    axes=[a[:,i] for i in range(3)]+[b[:,i] for i in range(3)]
    axes += [np.cross(a[:,i],b[:,j]) for i in range(3) for j in range(3)]
    axes=np.array([v/np.linalg.norm(v) for v in axes if np.linalg.norm(v)>1e-9])
    distances=np.abs(axes@(np.asarray(center_b)-center_a))
    overlaps=np.abs(axes@a)@half_a+np.abs(axes@b)@half_b-distances
    return float(max(0.,np.min(overlaps))*1000)
