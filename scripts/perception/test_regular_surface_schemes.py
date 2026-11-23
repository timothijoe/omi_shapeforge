"""Shared planar grids must be regular across triangles and preserve holes."""
import unittest
import numpy as np
from build_regular_surface_schemes import planar_sample,focus_part_ids,FOCUS_ROI
from build_interaction_surface import clipped_mesh


def mesh(triangles,names=None,part_ids=None):
    t=np.array(triangles,float);n=len(t)
    return {'triangles':t,'normals':np.zeros((n,3)),'colors':np.ones((n,3)),
            'part_id':np.zeros(n,int) if part_ids is None else np.array(part_ids),
            'parts':[{'name':s} for s in (names or ['surface'])]}


def sample(m,pitch):
    n=len(m['triangles']);return planar_sample(m,m['triangles'],np.repeat(np.eye(3)[None],n,axis=0),np.arange(n),pitch)


class RegularSurfaceTests(unittest.TestCase):
    def test_two_triangles_make_one_continuous_square_grid(self):
        m=mesh([[[0,0,0],[.01,0,0],[.01,.01,0]],[[0,0,0],[.01,.01,0],[0,.01,0]]])
        a,r=sample(m,.002)
        self.assertEqual(len(a['points_m']),36)
        self.assertTrue(a['on_regular_grid'].all())
        np.testing.assert_allclose(a['points_m'][:,:2]/.002,np.round(a['points_m'][:,:2]/.002),atol=1e-6)
        self.assertEqual(r['plane_count'],1)

    def test_inner_hole_stays_empty(self):
        triangles=[]
        for x0,y0,x1,y1 in [(-2,-2,-1,2),(1,-2,2,2),(-1,-2,1,-1),(-1,1,1,2)]:
            a,b,c,d=[x0,y0,0],[x1,y0,0],[x1,y1,0],[x0,y1,0];triangles.extend([[a,b,c],[a,c,d]])
        points,_=sample(mesh(triangles),.5);p=points['points_m']
        self.assertEqual(len(p),72)
        self.assertFalse(((abs(p[:,0])<.9)&(abs(p[:,1])<.9)).any())

    def test_tiny_facets_keep_a_valid_representative_not_nan_normal(self):
        m=mesh([[[.00011,.00011,0],[.00012,.00011,0],[.00011,.00012,0]]]);a,r=sample(m,.001)
        self.assertEqual(len(a['points_m']),1);self.assertEqual(r['tiny_plane_fallback_points'],1)
        self.assertTrue(np.isfinite(a['normals']).all());np.testing.assert_allclose(np.linalg.norm(a['normals'],axis=1),1)

    def test_focus_socket_filter_excludes_board_stand_and_rear(self):
        m={'parts':[{'name':n} for n in ['PCB upper soldermask','Lower printed stand','Cage rear connector polymer','Cage upper mouth rim','Cage bottom and thin sidewalls','Housing printed frame']]}
        self.assertEqual(focus_part_ids('socket',m).tolist(),[3,4,5])


if __name__=='__main__':unittest.main()
