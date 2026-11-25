"""Control-sampled minimum separating translation for two oriented boxes.

Independent geometry diagnostic. This is not the PhysX contact-point separation
and does not claim to measure the maximum overlap between control samples.
"""
import numpy as np


def box_overlap_mm(center_a, rotation_a, half_a, center_b, rotation_b, half_b):
    a,b=np.asarray(rotation_a),np.asarray(rotation_b)
    # The same 15 SAT axes, in the same order. Batch cross products and norms
    # instead of invoking NumPy from Python separately for each small vector.
    axes=np.concatenate((a.T,b.T,np.cross(a.T[:,None,:],b.T[None,:,:]).reshape(9,3)))
    lengths=np.linalg.norm(axes,axis=1)
    keep=lengths>1e-9
    axes=axes[keep]/lengths[keep,None]
    distances=np.abs(axes@(np.asarray(center_b)-center_a))
    overlaps=np.abs(axes@a)@half_a+np.abs(axes@b)@half_b-distances
    return float(max(0.,np.min(overlaps))*1000)
