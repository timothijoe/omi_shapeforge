"""Segment module/cap/grippers after suppressing the added printed patch.

One manually specified set of foreground/background prompts is used for this
known wrist/grasp view. It is not a general no-prompt segmentation interface.
"""
import argparse
import json
import os
from pathlib import Path
import cv2
import numpy as np
from structural_edge_pose import StructuralDetector


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-run',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--weights',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);(a.output/'clean_images').mkdir()
    meta=json.loads((a.source_run/'inputs.json').read_text());cal=json.loads(Path(meta['calibration']).read_text());detector=StructuralDetector(cal)
    origin=np.array([800,540]);cap=cv2.VideoCapture(meta['video'])
    for i,frame in enumerate(meta['source_frames']):
        cap.set(cv2.CAP_PROP_POS_FRAMES,frame);ok,image=cap.read()
        if not ok:raise ValueError(frame)
        image[detector.exclusion_mask(image.shape)>0]=128
        cv2.imwrite(str(a.output/'clean_images'/f'{i:06d}.jpg'),image[540:980,800:1160],[cv2.IMWRITE_JPEG_QUALITY,99])
    cap.release()
    objects=[(1,'metal_module',[[970,704],[970,751]],[[919,744],[1035,747],[970,660],[974,850],[970,798]]),
             (2,'rigid_black_end',[[970,798]],[[970,750],[943,800],[1003,803],[970,825],[1035,750]]),
             (3,'left_gripper',[[910,750],[911,870]],[[970,730],[970,798],[951,850],[1040,750]]),
             (4,'right_gripper',[[1040,750],[1040,870]],[[970,730],[970,798],[990,850],[910,750]])]
    prompts=[]
    for oid,name,positive,negative in objects:
        points=np.array(positive+negative)-origin
        prompts.append({'frame_index':0,'object_id':oid,'points':[{'x':float(x),'y':float(y)} for x,y in points],
                        'point_labels':[1]*len(positive)+[0]*len(negative)})
    (a.output/'prompts.json').write_text(json.dumps({'prompts':prompts},indent=2))
    (a.output/'inputs.json').write_text(json.dumps({'source':str(a.source_run),'video':meta['video'],
        'source_frames':meta['source_frames'],'crop_origin':origin.tolist(),'crop_size':[360,440],
        'printed_patch_removed_before_segmentation':True,'object_ids':{name:oid for oid,name,_,_ in objects},
        'first_frame_semantic_prompts_manual':True},indent=2))
    os.environ['CONFIG_FILE']='configs/sam2.1/sam2.1_hiera_s.yaml';os.environ['CHECKPOINT_FILE']='sam2.1_hiera_small.pt'
    from v2d.sam2.lib.video_to_masks import video_to_masks
    video_to_masks(str(a.output/'clean_images'),str(a.output/'prompts.json'),str(a.output/'masks'),str(a.weights))


if __name__=='__main__':main()
