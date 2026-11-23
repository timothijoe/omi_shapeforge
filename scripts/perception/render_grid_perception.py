"""Browse the actual finite coverage, including explicitly rejected cells."""
import argparse,json,base64
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import ListedColormap
FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
font_manager.fontManager.addfont(FONT);plt.rcParams['font.family']=font_manager.FontProperties(fname=FONT).get_name();plt.rcParams['axes.unicode_minus']=False

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);a=p.parse_args();r=a.run;out=r/'review';out.mkdir(exist_ok=True);plan=json.loads((r/'plan.json').read_text());complete=json.loads((r/'data/complete.json').read_text());audit=json.loads((r/'data/label_audit.json').read_text());assert audit['accepted_for_sim_supervision']
 rows=list(map(json.loads,(r/'data/records.jsonl').read_text().splitlines()));bad=list(map(json.loads,(r/'data/rejected.jsonl').read_text().splitlines()));strict=json.loads((r/'strict_subset_report.json').read_text()) if (r/'strict_subset_report.json').exists() else None;excluded={x['sample_id'] for x in json.loads((r/'data_strict/excluded_from_strict.json').read_text())} if strict else set();entries=[];grasps=json.loads((r/'data/grasps.json').read_text())
 for row in rows+bad:
  keys=['sample_id','grasp_id','split','requested_module','requested_socket_relation','coverage_families','accepted','reason','actual_module','actual_socket_relation','T_camera_from_module','T_camera_from_socket','keypoints','qa','minimum_surface_mouth_plane_gap_mm'];e={k:row[k] for k in keys if k in row}
  if not row['accepted'] and row.get('reason')=='grasp_configuration_failed':e['failed_grasp_actual']=grasps[row['grasp_id']]['actual_module']
  e['strict_pass']=bool(row['accepted'] and row['sample_id'] not in excluded)
  if row['accepted']:e['image']='data/'+row['image'];e['mask']='data/'+row['instance_mask']
  entries.append(e)
 entries.sort(key=lambda x:x['sample_id']);(out/'catalog.json').write_text(json.dumps(entries,separators=(',',':')))
 templates={};template_root=Path('/data/omi_runtime/runs/contact_wrist_surface_20261123_r01/network_templates');tm=json.loads((template_root/'manifest.json').read_text())
 for name,n in tm['recommended_counts'].items():
  v=np.load(template_root/f'{name}_{n}.npz');packed=np.c_[v['points_m'],v['representation_level']].astype('<f4');templates[name]={'count':n,'data':base64.b64encode(packed.tobytes()).decode()}
 payload={'strict':strict,'plan':plan,'complete':complete,'audit':audit,'templates':templates,'catalog':'review/catalog.json'}
 (r/'index.html').write_text(Path(__file__).with_name('grid_perception_viewer.html').read_text().replace('__DATA__',json.dumps(payload,separators=(',',':'))))
 nominal=[x for x in entries if all(v==0 for v in x['requested_module'].values())];lookup={tuple([x['requested_socket_relation'][k] for k in ['lateral_mm','vertical_mm','tip_gap_mm']]+x['requested_socket_relation']['rotation_socket_xyz_deg']):x for x in nominal}
 fig,axs=plt.subplots(1,4,figsize=(15,4.6));levels=plan['socket_translation']['lateral_mm']
 for ax,gap in zip(axs,[.5,1,2,10]):
  values=np.array([[int(lookup[(x,z,gap,0,0,0)]['accepted']) for x in levels] for z in levels]);ax.imshow(values,origin='lower',extent=[-3.25,3.25,-3.25,3.25],cmap=ListedColormap(['#e89591','#75c5a2']),vmin=0,vmax=1,interpolation='nearest');ax.set_title(f'孔口前 {gap:g} mm');ax.set_xlabel('左右偏移 mm');ax.set_ylabel('上下偏移 mm');ax.set_xticks([-3,-2,-1,0,1,2,3]);ax.set_yticks([-3,-2,-1,0,1,2,3]);ax.set_xticks(np.arange(-3.25,3.26,.5),minor=True);ax.set_yticks(np.arange(-3.25,3.26,.5),minor=True);ax.grid(which='minor',color='white',linewidth=.4)
 fig.suptitle('插座平移网格的有效范围：绿＝收录，红＝拒绝（模块零位、相对转角为0）\n这是几何／夹持／可见性采样检查，不是策略成功率',fontsize=13);fig.tight_layout(rect=[0,0,1,.83]);fig.savefig(out/'socket_valid_region.png',dpi=150,bbox_inches='tight',pad_inches=.15);plt.close(fig)
 # Show deterministic boundary examples at the same crop and scale.
 wanted=[(-3,0,2),(0,0,.5),(3,0,2),(0,-3,2),(0,0,10),(0,3,2),(0,0,40),(3,3,2),(-3,-3,2)];sheet=Image.new('RGB',(1500,1410),'#122431');d=ImageDraw.Draw(sheet);font=ImageFont.truetype(FONT,22);small=ImageFont.truetype(FONT,16);d.text((20,10),'第一版仿真边界样本：图片对应已记录的物理状态',font=font,fill='white')
 for i,key in enumerate(wanted):
  item=lookup[(*key,0,0,0)];x=i%3*500;y=i//3*450+50;d.text((x+16,y),f'左右 {key[0]:+g} / 上下 {key[1]:+g} / 距孔口 {key[2]:g} mm',font=font,fill='white')
  if item['accepted']:
   im=Image.open(r/item['image']).crop((340,240,640,510)).resize((450,405));sheet.paste(im,(x+25,y+35))
  else:d.text((x+20,y+100),'此组合已拒绝：'+item['reason'],font=small,fill='#ffa4a4')
 sheet.save(out/'boundary_examples.jpg',quality=95)
 (out/'render_report.json').write_text(json.dumps({'catalog_entries':len(entries),'accepted_images':len(rows),'rejected_cells':len(bad),'templates':tm['recommended_counts'],'visualization_uses_actual_recorded_transforms':True,'new_training_performed':False},indent=2));print(json.dumps(complete),flush=True)
if __name__=='__main__':main()
