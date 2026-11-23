"""Geometry contract for the measured throat; no historical asset mutations."""
import importlib.util
import unittest

AVAILABLE = all(importlib.util.find_spec(k) for k in ("numpy", "mujoco", "trimesh"))
if AVAILABLE:
    import numpy as np
    import trimesh
    from omi_shapeforge.sim.measured_contact_asset import socket_vertices, clip_proxy_to_bounds


@unittest.skipUnless(AVAILABLE, "mesh runtime required")
class MeasuredThroatTests(unittest.TestCase):
    def test_inflated_convex_proxy_cannot_create_false_mouth_obstruction(self):
        source_bounds = np.array([[-.0087, -.035, .0022], [.0087, .035, .0041]])
        inflated = trimesh.creation.box(bounds=[[-.0091, -.0354, .002], [.0091, .0354, .0044]])
        clipped = clip_proxy_to_bounds(inflated, source_bounds)
        self.assertIsNotNone(clipped)
        self.assertTrue(clipped.is_watertight)
        np.testing.assert_allclose(clipped.bounds, source_bounds, atol=1e-12)
        self.assertAlmostEqual(clipped.volume, np.prod(np.ptp(source_bounds,axis=0)), places=14)
        outside = trimesh.creation.box(bounds=[[.02, 0, 0], [.03, .01, .01]])
        self.assertIsNone(clip_proxy_to_bounds(outside, source_bounds))

    def test_measured_throat_and_front_left_offset_preserve_outer_sheet_thickness(self):
        # Four X planes: outer wall, inner wall, inner wall, outer wall.
        x = np.array([-10.3, -10., 9., 9.3])
        points = np.c_[x, np.zeros(4), np.full(4, -4.1)] / 1000
        transformed = socket_vertices(points, width_mm=18.8, height_mm=8.8, center_x_mm=-.3) * 1000
        np.testing.assert_allclose(transformed[:, 0], [-10., -9.7, 9.1, 9.4], atol=1e-10)
        self.assertAlmostEqual(transformed[2, 0]-transformed[1, 0], 18.8)
        self.assertAlmostEqual(16.-transformed[2, 0], 6.9)
        self.assertAlmostEqual(transformed[1, 0]-transformed[0, 0], .3)
        self.assertAlmostEqual(transformed[3, 0]-transformed[2, 0], .3)

    def test_height_change_keeps_floor_and_roof_sheet_thickness_and_depth(self):
        z = np.array([-4.4, -4.1, 5.5, 5.85])
        points = np.c_[np.zeros(4), np.array([-56., -12., .1, 1.85]), z] / 1000
        transformed = socket_vertices(points, width_mm=18.8, height_mm=8.8, center_x_mm=-.3) * 1000
        np.testing.assert_allclose(transformed[:, 2], [-4.4, -4.1, 4.7, 5.05], atol=1e-10)
        np.testing.assert_allclose(transformed[:, 1], points[:, 1]*1000, atol=1e-10)
        self.assertAlmostEqual(transformed[2, 2]-transformed[1, 2], 8.8)
        self.assertAlmostEqual(transformed[3, 2]-transformed[2, 2], .35)
