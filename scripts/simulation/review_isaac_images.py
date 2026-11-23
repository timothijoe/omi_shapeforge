"""Same-pose render ablations, with native images and immutable physics inputs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time
import traceback


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-run',type=Path,required=True);p.add_argument('--transfer',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--variants',nargs='+',default=['baseline_128','native_768','normals_768','refined_768','pathtraced_768'])
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
    sys.path.insert(0,'/data/omi_runtime/envs/isaac_contact_support')
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
    shutil.copy2(__file__,a.output/Path(__file__).name)
    shutil.copy2(Path(__file__).resolve().parents[2]/'src/omi_shapeforge/sim/isaac_appearance.py',a.output/'isaac_appearance.py')
    root=Path('/data/isaac-sim-5.1.0');sys.argv=[sys.argv[0]]
    from isaacsim import SimulationApp
    extra=['--/app/extensions/registryEnabled=false']
    for f in ('exts','extscache','kit/exts','kit/extscore'):extra+=['--ext-folder',str(root/f)]
    app=SimulationApp(dict(headless=True,width=1280,height=960,limit_cpu_threads=4,multi_gpu=False,extra_args=extra),experience=str(root/'apps/isaacsim.exp.base.python.kit'))
    failed=False
    try:
        import numpy as np
        import carb.settings
        import omni.usd
        import omni.replicator.core as rep
        from pxr import Usd,UsdPhysics,UsdGeom
        from PIL import Image
        from omi_shapeforge.sim.isaac_appearance import apply_recipe,geometry_digest
        scene=a.source_run/'initial_pose.usda';source_hash=hashlib.sha256(scene.read_bytes()).hexdigest()
        packet=json.loads((a.transfer/'transfer.json').read_text());audit=json.loads((a.source_run/'scene_manifest.json').read_text())
        results=[];context=omni.usd.get_context()
        for variant in a.variants:
            start=time.monotonic();out=a.output/variant;out.mkdir(exist_ok=False)
            context.open_stage(str(scene));stage=context.get_stage();before=geometry_digest(stage)
            recipe=None
            if variant.startswith('normals'):recipe=apply_recipe(stage,packet,audit,a.transfer,'normals')
            elif variant.startswith(('refined','pathtraced')):recipe=apply_recipe(stage,packet,audit,a.transfer,'refined')
            assert geometry_digest(stage)==before,'visual recipe changed geometry/transforms'
            stage.GetRootLayer().Export(str(out/'scene.usdc'))
            # Frozen-pose visual study only. Do not step or use these pictures as dynamics evidence.
            for prim in stage.Traverse():
                if prim.HasAPI(UsdPhysics.RigidBodyAPI):UsdPhysics.RigidBodyAPI(prim).CreateRigidBodyEnabledAttr(False)
            for _ in range(3):app.update()
            if variant.startswith('pathtraced'):
                rep.settings.set_render_pathtraced(samples_per_pixel=64)
                carb.settings.get_settings().set('/rtx/pathtracing/optixDenoiser/enabled',True)
            else:rep.settings.set_render_rtx_realtime(antialiasing='DLSS' if variant=='baseline_128' else 'DLAA')
            annotations={};products=[];image_info={}
            for name,path in audit['cameras'].items():
                if name not in ('head_rgb','wrist_rgb','overview'):continue
                resolution=((640,480) if name=='overview' else (128,128)) if variant=='baseline_128' else ((1280,960) if name=='overview' else (768,768))
                product=rep.create.render_product(path,resolution);products.append(product)
                annot=rep.AnnotatorRegistry.get_annotator('rgb');annot.attach(product);annotations[name]=annot
                image_info[name]=dict(resolution=list(resolution),camera_path=path)
            for _ in range(4 if variant.startswith('pathtraced') else 8):
                rep.orchestrator.step(delta_time=0.,pause_timeline=True,rt_subframes=4)
            assert geometry_digest(stage)==before,'render advanced or changed scene pose'
            for name,annot in annotations.items():
                im=annot.get_data()[:,:,:3].copy()
                assert im.shape[:2]==tuple(reversed(image_info[name]['resolution'])) and np.ptp(im)>0
                Image.fromarray(im).save(out/f'{name}.png')
                image_info[name].update(mean=float(im.mean()),clipped_high_fraction=float(np.mean(np.max(im,axis=2)>=250)))
                if name!='overview' and variant!='baseline_128':
                    Image.fromarray(im).resize((128,128),Image.Resampling.LANCZOS).save(out/f'{name}_downsample128.png')
                annot.detach()
            for product in products:product.destroy()
            result=dict(variant=variant,elapsed_seconds=time.monotonic()-start,images=image_info,geometry_digest=before,
                geometry_unchanged=True,physics_executed=False,recipe=recipe)
            (out/'report.json').write_text(json.dumps(result,indent=2)+'\n');results.append(result)
            print('RENDERED',variant,round(result['elapsed_seconds'],2),flush=True)
            context.close_stage()
        assert hashlib.sha256(scene.read_bytes()).hexdigest()==source_hash
        report=dict(source_scene=str(scene),source_sha256=source_hash,source_unchanged=True,variants=results,
            scope='same-pose frozen rendering ablations, not real-camera calibration or live training',
            references=['https://docs.omniverse.nvidia.com/materials-and-rendering/latest/rtx-renderer_pt.html',
                'https://docs.omniverse.nvidia.com/materials-and-rendering/latest/templates/UsdPreviewSurface.html'])
        (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    except BaseException as exc:
        failed=True;traceback.print_exc();(a.output/'failure.json').write_text(json.dumps(dict(error=repr(exc),traceback=traceback.format_exc()),indent=2))
    finally:app._app.post_quit(1 if failed else 0);app.close()


if __name__=='__main__':main()
