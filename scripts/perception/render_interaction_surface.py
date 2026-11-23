"""Local tip/mouth visual comparison; geometry colors are semantic, not sensor RGB."""
import argparse
import base64
import json
from pathlib import Path
import numpy as np


def semantic_colors(kind,a,parts):
    color=np.tile([165,180,196],(len(a['points_m']),1)).astype('uint8')
    for part in np.unique(a['part_id']):
        name=parts[int(part)]['name'].lower();mask=a['part_id']==part
        if kind=='module':
            if 'lower shell' in name:color[mask]=[255,147,65]
            elif 'upper grooves' in name:color[mask]=[91,202,255]
            elif 'side wall' in name:color[mask]=[175,190,210]
        else:
            if 'cage bottom' in name:
                floor=mask&(abs(a['normals'][:,2])>.65);color[mask]=[82,186,255];color[floor]=[255,153,70]
            elif 'upper mouth' in name or 'folded vertical' in name:color[mask]=[190,140,255]
            elif 'rolled edge' in name or 'mouth floor rib' in name:color[mask]=[255,153,70]
            elif 'housing printed' in name:color[mask]=[130,225,180]
            elif 'pcb' in name:color[mask]=[77,133,105]
    return color


def pack(kind,arrays,parts,feature=False):
    dtype=np.dtype([('xyz','<f4',(3,)),('rgb','u1',(3,)),('semantic','u1',(3,)),('feature','u1'),('pad','u1')])
    a=np.zeros(len(arrays['points_m']),dtype=dtype);a['xyz']=arrays['points_m'];a['rgb']=arrays['rgb'];a['semantic']=semantic_colors(kind,arrays,parts);a['feature']=int(feature)
    return {'data':base64.b64encode(a.tobytes()).decode(),'count':len(a),'stride':20}


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);a=p.parse_args();root=a.run
    manifest=json.loads((root/'templates/manifest.json').read_text());compact=json.loads((root/'network_templates/manifest.json').read_text());payload={'models':{},'network':compact}
    for kind,report in manifest['models'].items():
        surface=np.load(root/f'templates/{kind}_surface.npz');edges=np.load(root/f'templates/{kind}_edges.npz');old=np.load(root/f'templates/{kind}_old_local.npz')
        n=compact['recommended_counts'][kind];network=np.load(root/f'network_templates/{kind}_{n}.npz')
        global_points={k:network[k][network['representation_level']==0] for k in ['points_m','normals','rgb','part_id']}
        roi=np.asarray(report['roi_m']);outside=~((global_points['points_m']>=roi[0])&(global_points['points_m']<=roi[1])).all(1)
        global_old={k:v[outside] for k,v in global_points.items()}
        network_surface={k:network[k][network['representation_level']==1] for k in ['points_m','normals','rgb','part_id']};network_edges={k:network[k][network['representation_level']==2] for k in ['points_m','normals','rgb','part_id']}
        bounds=[surface['points_m'].min(0).tolist(),surface['points_m'].max(0).tolist()]
        whole_bounds=[network['points_m'].min(0).tolist(),network['points_m'].max(0).tolist()]
        payload['models'][kind]={'global':pack(kind,global_points,report['parts']),'global_old':pack(kind,global_old,report['parts']),
            'surface':pack(kind,surface,report['parts']),'edges':pack(kind,edges,report['parts'],True),
            'old':pack(kind,old,report['parts']),'compact_surface':pack(kind,network_surface,report['parts']),
            'compact_edges':pack(kind,network_edges,report['parts'],True),'bounds':bounds,'whole_bounds':whole_bounds,
            'report':{k:v for k,v in report.items() if k not in ['parts','per_part']}}
    html=Path(__file__).with_name('interaction_surface_viewer.html').read_text().replace('__PAYLOAD__',json.dumps(payload,separators=(',',':')))
    (root/'index.html').write_text(html);print(root/'index.html')


if __name__=='__main__':main()
