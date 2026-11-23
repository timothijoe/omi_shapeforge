"""Render real V3 mesh results back into original fisheye images for review."""
import argparse
import csv
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from estimate_wrist_module_pose import load_parts, render_mesh


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, required=True)
    a = p.parse_args(); root = a.run
    (root/'overlays').mkdir(exist_ok=True)
    inp = json.loads((root/'inputs.json').read_text())
    cal = json.loads(Path(inp['calibration']).read_text())
    K, D = np.array(cal['K']), np.array(cal['D'])
    rect = np.load(root/'rectification.npz')
    raw_from_rect = np.eye(4); raw_from_rect[:3, :3] = rect['R_rect_from_raw'].T
    _, parts = load_parts(Path('/data/omi_runtime/runs/v3_socket_insertion_20261120T073119Z/inputs'))
    ids = {'000.npz','001.npz','002.npz','003.npz','004.npz','006.npz','008.npz','010.npz','014.npz'}
    parts = [part for part in parts if Path(part['file']).name in ids]
    initial = np.array(json.loads((root/'initial_pose.json').read_text())['T_rect_from_model'])
    pixels = json.loads((root/'pixel_refinement_results.json').read_text())['records']
    pixel_lookup = {x['frame']: x for x in pixels}
    fp = json.loads((root/'foundationpose_results.json').read_text())
    global_lookup = {x['frame']: x for x in fp['variants'].get('global_registration', [])}
    seeded_lookup = {x['frame']: x for x in fp['variants'].get('initialized_refinement', [])}
    font_path = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
    font = ImageFont.truetype(font_path, 22); small = ImageFont.truetype(font_path, 17)
    cap = cv2.VideoCapture(inp['input'])
    def source(i):
        cap.set(cv2.CAP_PROP_POS_FRAMES, inp['source_frames'][i]); ok, image = cap.read()
        if not ok: raise ValueError(i)
        return image
    def mask_outline(image, i):
        m = cv2.imread(str(root/'masks/1'/f'{i:06d}.png'), 0)
        contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        out = image.copy()
        for contour in contours:
            uv = contour[:, 0]; uv = np.c_[rect['map_x'][uv[:,1], uv[:,0]], rect['map_y'][uv[:,1], uv[:,0]]]
            cv2.polylines(out, [np.rint(uv).astype(np.int32)], True, (255, 220, 30), 2, cv2.LINE_AA)
        return out
    def mesh_overlay(image, T_rect):
        T = raw_from_rect @ np.array(T_rect)
        pose = np.r_[cv2.Rodrigues(T[:3, :3])[0].ravel(), T[:3, 3]*1000]
        return render_mesh(image, parts, pose, K, D)[0]
    def crop(image, size=(340, 470)):
        tile = Image.fromarray(cv2.cvtColor(image[620:880, 880:1068], cv2.COLOR_BGR2RGB))
        return tile.resize(size, Image.Resampling.LANCZOS)
    cards = {}
    for i in pixel_lookup:
        image = source(i)
        overlays = [mask_outline(image, i), mesh_overlay(image, initial),
                    mesh_overlay(image, global_lookup[i]['T_rect_from_model']),
                    mesh_overlay(image, pixel_lookup[i]['T_rect_from_model'])]
        for name, overlay in zip(['sam2', 'initial', 'foundationpose', 'pixel_refined'], overlays):
            cv2.imwrite(str(root/'overlays'/f'{i:06d}_{name}.png'), overlay)
        seeded = mesh_overlay(image, seeded_lookup[i]['T_rect_from_model'])
        cv2.imwrite(str(root/'overlays'/f'{i:06d}_foundationpose_seeded.png'), seeded)
        cards[i] = overlays
    headers = ['SAM2 主体分割', '此前几何初值的 mesh', 'V2D＋预测深度：失败示例', 'SAM2＋我们的像素精修']
    def figure(indices, path):
        width, row_height = 1440, 530
        canvas = Image.new('RGB', (width, 110+row_height*len(indices)+80), '#14202d')
        draw = ImageDraw.Draw(canvas)
        draw.text((18, 12), '真实腕部鱼眼图 · 固定 V3 金属主体，绿色挂件不参与', font=font, fill='white')
        for col, title in enumerate(headers): draw.text((18+col*355, 58), title, font=small, fill='#dce8ef')
        for row, i in enumerate(indices):
            y=100+row*row_height
            for col, overlay in enumerate(cards[i]): canvas.paste(crop(overlay), (18+col*355, y))
            record=pixel_lookup[i]
            line=f"原视频帧 {inp['source_frames'][i]} · SAM2 掩码 IoU：初值 {record['sam2_iou_before']:.2f} → 像素精修 {record['sam2_iou_after']:.2f}；V2D 全局解 {global_lookup[i]['sam2_mask_iou']:.2f}"
            draw.text((18,y+480),line,font=small,fill='white')
        draw.text((18,canvas.height-66),'IoU 是对 SAM2 掩码的拟合指标，不是独立位姿精度；像素精修是自编适配层。',font=small,fill='#f9c477')
        draw.text((18,canvas.height-38),'此轮初值来自既有图像 PnP，尚未接入头部点云外参。',font=small,fill='#f9c477')
        canvas.save(path)
    figure([0],root/'first_frame_comparison.png')
    figure([0,30,60],root/'keyframes_comparison.png')
    # Compare both official FoundationPose variants transparently.
    canvas=Image.new('RGB',(1080,640),'#14202d');draw=ImageDraw.Draw(canvas)
    for col,(name,label) in enumerate([('initial','原初值'),('foundationpose_seeded','V2D 从初值精修：偏移'),('foundationpose','V2D 全局初始化：偏移')]):
        draw.text((15+col*355,20),label,font=small,fill='white')
        im=cv2.imread(str(root/'overlays'/f'000000_{name}.png'));canvas.paste(crop(im),(15+col*355,60))
    draw.text((18,558),'输入深度来自 MoGe 单目预测，首帧主体中位深度约 0.66 m。',font=small,fill='#f9c477')
    draw.text((18,592),'没有修改 mesh 尺寸来迁就预测深度；两条官方位姿分支均未通过目视贴合检查。',font=small,fill='#f9c477')
    canvas.save(root/'foundationpose_failure_comparison.png')
    all_path=root/'pixel_refinement_all_frames.json'
    if all_path.exists():
        all_records=json.loads(all_path.read_text())['records']
        writer=cv2.VideoWriter(str(root/'comparison.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),10.,(1080,640))
        with (root/'pixel_poses.csv').open('w') as f:
            csvout=csv.writer(f);csvout.writerow(['source_frame','tx_mm','ty_mm','tz_mm','rvec_x_rad','rvec_y_rad','rvec_z_rad','mask_iou_before','mask_iou_after'])
            for record in all_records:
                i=record['frame'];image=source(i);T=raw_from_rect@np.array(record['T_rect_from_model'])
                csvout.writerow([inp['source_frames'][i],*(T[:3,3]*1000),*cv2.Rodrigues(T[:3,:3])[0].ravel(),record['sam2_iou_before'],record['sam2_iou_after']])
                ims=[mask_outline(image,i),mesh_overlay(image,initial),mesh_overlay(image,record['T_rect_from_model'])]
                frame=Image.new('RGB',(1080,640),'#14202d');draw=ImageDraw.Draw(frame)
                for col,(im,label) in enumerate(zip(ims,['SAM2 主体','初始 mesh','像素精修后的 mesh'])):
                    draw.text((15+col*355,18),label,font=font,fill='white');frame.paste(crop(im),(15+col*355,65))
                draw.text((18,558),f"原帧 {inp['source_frames'][i]} · 拟合 IoU {record['sam2_iou_before']:.2f} → {record['sam2_iou_after']:.2f}",font=font,fill='white')
                draw.text((18,600),'V2D SAM2＋自编像素精修；非 FoundationPose 成功结果，非位姿真值。',font=small,fill='#f9c477')
                writer.write(cv2.cvtColor(np.array(frame),cv2.COLOR_RGB2BGR))
        writer.release()
    cap.release()
    print(root/'first_frame_comparison.png')


if __name__=='__main__':
    main()
