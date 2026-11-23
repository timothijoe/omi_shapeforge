"""Geometry checks that protect holes and the source mesh envelope."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

AVAILABLE = all(importlib.util.find_spec(x) for x in ("numpy", "trimesh", "mujoco", "rtree"))
if AVAILABLE:
    import numpy as np
    import trimesh
    from omi_shapeforge.sim.mesh_contact_probe import piece_meshes
    from omi_shapeforge.sim.repair_collision_export import cap_boundary_loops


@unittest.skipUnless(AVAILABLE, "optional mesh audit environment required")
class MeshAuditTests(unittest.TestCase):
    def test_u_channel_split_preserves_void_that_single_hull_fills(self):
        boxes = [trimesh.creation.box(bounds=b) for b in (
            [[-10.3, -56, -4.4], [9.3, 1.6, -4.1]],
            [[-10.3, -56, -4.1], [-10, 1.6, 5.75]],
            [[9, -56, -4.1], [9.3, 1.6, 5.75]])]
        source = trimesh.util.concatenate(boxes)
        part = {"mesh": source, "index": 4}
        pieces, _ = piece_meshes(part, "socket", Path("unused"), True)
        self.assertAlmostEqual(sum(m.volume for m in pieces), source.volume, places=6)
        center = [[-.5, -20, .7]]
        self.assertTrue(source.convex_hull.contains(center)[0])
        self.assertFalse(any(p.contains(center)[0] for p in pieces))
        for point in [[-10.15, -20, .7], [9.15, -20, .7], [-.5, -20, -4.25]]:
            self.assertTrue(any(p.contains([point])[0] for p in pieces))

    def test_cap_planar_tube_ends_without_changing_vertices_or_bounds(self):
        cylinder = trimesh.creation.cylinder(radius=.05, height=10, sections=8)
        side = cylinder.submesh([np.flatnonzero(abs(cylinder.face_normals[:, 2]) < .5)], append=True, repair=False)
        side.remove_unreferenced_vertices()
        before = side.vertices.copy()
        self.assertFalse(side.is_watertight)
        result, caps = cap_boundary_loops(side)
        self.assertEqual(caps, 2)
        self.assertTrue(result.is_watertight and result.is_winding_consistent)
        np.testing.assert_array_equal(result.vertices[:len(before)], before)
        np.testing.assert_allclose(result.bounds, side.bounds, rtol=0, atol=1e-12)
        self.assertGreater(result.volume, 0)
        np.testing.assert_array_equal(side.vertices, before)

    def test_missing_or_stale_decomposition_cannot_silently_fill_a_hole(self):
        source = trimesh.creation.box()
        part = {"mesh": source, "index": 33}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(FileNotFoundError):
                piece_meshes(part, "socket", root, True)
            folder = root / "socket_033"
            folder.mkdir()
            (folder / "record.json").write_text(json.dumps(dict(geometry_sha256="stale", pieces=1)))
            with self.assertRaises(ValueError):
                piece_meshes(part, "socket", root, True)
