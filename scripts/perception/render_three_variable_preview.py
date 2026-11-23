"""Metric side diagrams and a local slider viewer for the 27 grasp previews."""
import argparse,json
from pathlib import Path
import numpy as np,trimesh
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib import font_manager
from shapely.geometry import Polygon
from shapely.ops import unary_union

FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
PAD_Z_RANGE=None
font_manager.fontManager.addfont(FONT);plt.rcParams['font.family']=font_manager.FontProperties(fname=FONT).get_name();plt.rcParams['axes.unicode_minus']=False

def polygons(triangles,T,anchor):
 world=triangles@T[:3,:3].T+T[:3,3];q=(world-anchor)*1000;q=q[:,:,[2,0]];poly=[Polygon(x) for x in q if abs((x[1,0]-x[0,0])*(x[2,1]-x[0,1])-(x[1,1]-x[0,1])*(x[2,0]-x[0,0]))>1e-7];union=unary_union(poly)
 return [np.array(p.exterior.coords) for p in (union.geoms if hasattr(union,'geoms') else [union])]

def draw(ax,polys,baseline,pivot,tip,title):
 ax.add_collection(PolyCollection(polys,facecolors='#54b7e5',edgecolors='#1677a0',linewidths=1,zorder=3))
 for p in baseline:ax.plot(p[:,0],p[:,1],color='#616b74',linestyle='--',lw=1,zorder=4)
 ax.axvspan(*PAD_Z_RANGE,color='#6c7580',alpha=.12,zorder=0);ax.axhline(0,color='#bdc7ce',lw=.8);ax.axvline(0,color='#bdc7ce',lw=.8)
 ax.scatter(*pivot,c='#7c3cbb',marker='+',s=60,zorder=5);ax.scatter(*tip,c='#ff7f20',s=24,zorder=5)
 ax.set_xlim(-40,70);ax.set_ylim(-13,13);ax.set_aspect('equal');ax.set_title(title,fontsize=12);ax.grid(alpha=.18);ax.set_xlabel('前后方向 / mm（+ 朝插入尖端）',fontsize=9);ax.set_ylabel('上下 / mm',fontsize=9);ax.tick_params(labelsize=8)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);a=ap.parse_args();root=a.run;m=json.loads((root/'manifest.json').read_text());rows=m['records'];assert len(rows)==27
 manifest=json.loads(Path('/data/omi_runtime/assets/optical_module_v4/r08/asset_manifest.json').read_text());triangles=np.concatenate([trimesh.load(p['mesh'],force='mesh',process=False).triangles for p in manifest['parts'] if p['component']!='pull_handle'])
 global PAD_Z_RANGE
 anchor=np.array(m['nominal_grasp_reference_in_tool_m'])
 tool=json.loads(Path('/data/omi_runtime/assets/daimon/wrist_gripper_logo_r15/asset_manifest.json').read_text());pad_z=np.concatenate([trimesh.load(p['mesh'],force='mesh',process=False).vertices[:,2] for p in tool['parts'] if '24 convex black contact pad' in p['name']]);PAD_Z_RANGE=(pad_z.min()-anchor[2])*1000,(pad_z.max()-anchor[2])*1000
 pivot=np.array(m['module_grasp_reference_point_m']);lookup={tuple(r['requested'][k] for k in ['fore_aft_mm','height_mm','pitch_deg']):r for r in rows};base=np.array(lookup[(0,0,0)]['target_T_tool_module']);baseline=polygons(triangles,base,anchor);allpolys={}
 for r in rows:
  T=np.array(r['target_T_tool_module']);poly=polygons(triangles,T,anchor);allpolys[r['id']]=poly;q=r['requested'];actual=np.array(r['actual_T_tool_module']);target_anchor=(T[:3,:3]@pivot+T[:3,3]-anchor)*1000;tip=(T[:3,:3]@np.array([0,-.0350931697,0])+T[:3,3]-anchor)*1000
  fig,ax=plt.subplots(figsize=(10,3));draw(ax,poly,baseline,target_anchor[[2,0]],tip[[2,0]],f"目标侧视：前后 {q['fore_aft_mm']:+g} mm / 上下 {q['height_mm']:+g} mm / 俯仰 {q['pitch_deg']:+g}°")
  actual_polys=polygons(triangles,actual,anchor)
  for p in actual_polys:ax.plot(p[:,0],p[:,1],color='#cc305d',lw=.8,zorder=6)
  fig.text(.5,.01,'蓝色：三变量目标　红线：实际夹紧后　灰虚线：零位　紫色+：随平移移动的俯仰参考点',ha='center',fontsize=10);fig.tight_layout(rect=[0,.06,1,1]);rel=f"frames/{r['id']}_side.png";fig.savefig(root/rel,dpi=130);plt.close(fig);r['side_image']=rel
  for mode in ['target','settled']:
   rel=f"frames/{r['id']}_{mode}_detail.jpg";Image.open(root/r[mode+'_image']).crop((400,260,580,440)).resize((700,700)).save(root/rel,quality=96);r[mode+'_detail']=rel
 fig,axs=plt.subplots(3,3,figsize=(16,6.5))
 for row,(keys,title) in enumerate([([(v,0,0) for v in [-3,0,3]],'只改前后'),([(0,v,0) for v in [-1,0,1]],'只改上下'),([(0,0,v) for v in [-4,0,4]],'只改俯仰')]):
  for col,key in enumerate(keys):
   r=lookup[key];T=np.array(r['target_T_tool_module']);p=(T[:3,:3]@pivot+T[:3,3]-anchor)*1000;t=(T[:3,:3]@np.array([0,-.0350931697,0])+T[:3,3]-anchor)*1000;units=['mm','mm','°'];draw(axs[row,col],allpolys[r['id']],baseline,p[[2,0]],t[[2,0]],f'{title}：{key[row]:+g} {units[row]}')
 fig.suptitle('光模块相对夹爪：仅前后、上下、俯仰三个变量\n左右居中；无偏转、无侧倾。所有小图坐标与比例相同，灰虚线为零位。',fontsize=17);fig.tight_layout(rect=[0,.02,1,.87]);fig.savefig(root/'three_variable_side_grid.png',dpi=150);plt.close(fig)
 m['display_crop_xyxy']=[400,260,580,440];m['viewer_records']=rows;(root/'viewer_data.json').write_text(json.dumps(m,ensure_ascii=False,indent=2))
 html=Path(__file__).with_name('three_variable_grasp_preview.html').read_text().replace('__DATA__',json.dumps(m,ensure_ascii=False));(root/'index.html').write_text(html)
 print(json.dumps(m['summary']),flush=True)

if __name__=='__main__':main()
