"""Export one strict-core RGB/mask and its complete camera-frame surface labels."""
import argparse,json,shutil
from pathlib import Path
import numpy as np
from build_surface_representation import write_ply
from generate_sim_wrist_dataset import sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--sample-id',type=int,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();data=a.run/'data_strict'
 row=next((json.loads(s) for s in (data/'records.jsonl').read_text().splitlines() if json.loads(s)['sample_id']==a.sample_id),None)
 if row is None:raise ValueError('Sample is absent from the strict core; inspect coverage.csv for its tier')
 cfg=json.loads((data/'config.json').read_text());manifest=Path(cfg['pointcloud_templates']);spec=json.loads(manifest.read_text());parent=json.loads((a.run/'data/label_audit.json').read_text());assert sha(manifest)==parent['template_manifest_sha256'];assert sha(data/row['image'])==row['image_sha256']
 a.output.mkdir(parents=True,exist_ok=False);shutil.copy2(data/row['image'],a.output/'image.jpg');shutil.copy2(data/row['instance_mask'],a.output/'instance_mask.png');arrays={};counts={}
 for name,n in spec['recommended_counts'].items():
  source=np.load(manifest.parent/f'{name}_{n}.npz');T=np.array(row['T_camera_from_'+name]);points=source['points_m']@T[:3,:3].T+T[:3,3];normals=source['normals']@T[:3,:3].T;levels=source['representation_level'];rgb=np.tile([170,185,200],(n,1)).astype(np.uint8);rgb[levels>0]=[30,220,255] if name=='module' else [255,160,35];assert np.isfinite(points).all() and len(points)==n
  arrays[name+'_points_m']=points;arrays[name+'_normals']=normals;arrays[name+'_representation_level']=levels;write_ply(a.output/f'{name}_camera.ply',{'points_m':points,'rgb':rgb});counts[name]=n
 np.savez_compressed(a.output/'complete_surfaces.npz',**arrays);(a.output/'annotation.json').write_text(json.dumps({'source_row':row,'source_dataset':str(data),'camera_calibration':json.loads((data/'calibration.json').read_text()),'coordinate_frame':'wrist optical camera: x right, y down, z forward','units':'meters','point_counts':counts,'template_manifest':str(manifest),'template_manifest_sha256':sha(manifest),'mask_values':{'0':'background including gripper','1':'visible rigid module','2':'visible socket assembly'},'pointcloud_includes_hidden_surfaces':True,'network_prediction':False},indent=2));print(counts)
if __name__=='__main__':main()
