"""Tests for exact ROI clipping, true-edge provenance and multiscale loss."""
import unittest
import numpy as np
import torch
import trimesh
from build_interaction_surface import clip_triangle,clipped_mesh,real_edges,lattice,clip_segment
from image_to_surface_network import supervised_surface_loss


def model(mesh):
    n=len(mesh.faces)
    return {'triangles':mesh.triangles,'normals':mesh.face_normals,'areas':mesh.area_faces,
            'colors':np.ones((n,3)),'part_id':np.zeros(n,np.int16),'parts':[{'name':'fixture'}]}


class InteractionSurfaceTests(unittest.TestCase):
    def test_crossing_face_kept_even_if_centroid_outside(self):
        tri=np.array([[-2.,0,0],[2.,0,0],[-2.,2,0]])
        bounds=np.array([[0,-.1,-.1],[.5,1,.1]])
        self.assertLess(tri.mean(0)[0],bounds[0,0])
        fragments=clip_triangle(tri,bounds);self.assertTrue(fragments)
        for points,bary in fragments:
            np.testing.assert_allclose(bary@tri,points,atol=1e-12)
            self.assertTrue((points>=bounds[0]-1e-12).all() and (points<=bounds[1]+1e-12).all())
            np.testing.assert_allclose(points[:,2],0)

    def test_roi_does_not_cap_an_empty_volume(self):
        m=model(trimesh.creation.box(extents=[2,2,2]))
        with self.assertRaises(ValueError):clipped_mesh(m,np.array([[-.5,-.5,-.5],[.5,.5,.5]]))
        bounds=np.array([[-.25,-2,-2],[.25,2,2]])
        triangles,barys,faces=clipped_mesh(m,bounds)
        p=triangles.reshape(-1,3)
        self.assertTrue(np.all(np.minimum(abs(abs(p[:,1])-1),abs(abs(p[:,2])-1))<1e-10))
        seg,_=real_edges(m,bounds)
        # Only original x-directed cube edges survive; no new cap perimeter.
        self.assertEqual(len(seg),4)
        np.testing.assert_allclose(abs(seg[:,:,1:]),1,atol=1e-10)

    def test_surface_grid_barycentrics_and_thin_faces_remain_distinct(self):
        triangle=np.array([[0,0,0],[.01,0,0],[.002,.003,0]])
        bary=lattice(triangle,.0002)
        self.assertTrue((bary>=-1e-10).all());np.testing.assert_allclose(bary.sum(1),1)
        upper=bary@triangle+[0,0,.00002];lower=bary@triangle-[0,0,.00002]
        self.assertGreater(np.min(upper[:,2])-np.max(lower[:,2]),.000039)
        self.assertIsNone(clip_segment(np.array([2.,2,2]),np.array([3.,2,2]),np.array([[-1,-1,-1],[1,1,1]])))

    def test_loss_is_not_dominated_by_number_of_background_points(self):
        def loss(repeats):
            pts=torch.zeros((repeats+5,3));T=torch.eye(4)[None];pred=pts[None].clone();pred[:,:repeats]=.01
            levels=torch.tensor([0]*repeats+[1]*3+[2]*2)[None]
            return supervised_surface_loss({'module':{'points_m':pred,'representation_level':levels}},{'module':T},{'module':pts})
        torch.testing.assert_close(loss(2),loss(200))
        self.assertAlmostEqual(float(loss(2)),1.9,places=5)


if __name__=='__main__':unittest.main()
