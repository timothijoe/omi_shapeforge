"""Create point-count comparison artifacts and an offline interactive viewer."""
import argparse
import base64
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def encode(a):return base64.b64encode(np.asarray(a,dtype='<f4').tobytes()).decode()


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);a=p.parse_args();root=a.run
    manifest=json.loads((root/'templates_v2/manifest.json').read_text());report=json.loads((root/'prototype/report.json').read_text());prediction=np.load(root/'prototype/UNTRAINED_predictions.npz')
    payload={'models':{},'recommended':manifest['recommended_counts'],'predictions':[],'report':report};allpoints=[]
    fig=plt.figure(figsize=(15,9),facecolor='#111d29')
    for row,name in enumerate(['module','socket']):
        meta=manifest['models'][name];master=np.load(root/'templates_v2'/f'{name}_16384.npz')
        packed=np.c_[master['points_m'],master['rgb']/255,master['region_id']]
        payload['models'][name]={'cloud':encode(packed),'bounds':meta['bounds_m'],'levels':meta['levels']}
        for col,n in enumerate([512,2048,8192]):
            ax=fig.add_subplot(2,3,row*3+col+1,projection='3d');ax.set_facecolor('#111d29');q=master['points_m'][:n]*1000
            ax.scatter(q[:,0],q[:,1],q[:,2],c=master['rgb'][:n]/255,s=2 if n<2048 else .7,depthshade=False)
            bounds=np.array(meta['bounds_m'])*1000;center=bounds.mean(0);extent=(bounds[1]-bounds[0]).max()*.55
            ax.set_xlim(center[0]-extent,center[0]+extent);ax.set_ylim(center[1]-extent,center[1]+extent);ax.set_zlim(center[2]-extent,center[2]+extent);ax.set_box_aspect([1,1,1]);ax.set_axis_off();ax.view_init(elev=25,azim=-65)
            ax.set_title(f'{name.title()} | {n:,} points',color='white',pad=0)
        points=prediction[name+'_points_m'];allpoints.append(points);color=np.tile([1,.65,.28] if name=='module' else [.3,.85,1],(len(points),1));cloud=np.c_[points,color,np.zeros(len(points))]
        payload['predictions'].append({'name':name,'cloud':encode(cloud),'projected':prediction[name+'_projected_pixels'].round(2).tolist()})
    allpoints=np.concatenate(allpoints);payload['prediction_bounds']=[allpoints.min(0).tolist(),allpoints.max(0).tolist()]
    fig.suptitle('Complete mesh-surface templates — point-count comparison (not network predictions)',color='white',fontsize=17)
    fig.tight_layout();fig.savefig(root/'point_count_comparison.png',dpi=160,facecolor=fig.get_facecolor());plt.close(fig)
    html=Path(__file__).with_name('surface_representation_viewer.html').read_text().replace('__PAYLOAD__',json.dumps(payload,separators=(',',':')))
    (root/'index.html').write_text(html);print(root/'index.html')


if __name__=='__main__':main()
