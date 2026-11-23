"""Open a derived USD for visual inspection; timeline starts paused, source is not saved."""
import argparse,sys
from pathlib import Path

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--scene',type=Path,required=True)
p.add_argument('--title',default='WG-r10 + OM-r08 | asset inspection');a=p.parse_args()
if not a.scene.is_file():p.error('scene not found')
sys.path.insert(0,'/data/omi_runtime/envs/isaac_contact_support');sys.argv=[sys.argv[0]]
from isaacsim import SimulationApp
root=Path('/data/isaac-sim-5.1.0');extra=['--/app/extensions/registryEnabled=false','--/app/window/title='+a.title]
for f in ['exts','extscache','kit/exts','kit/extscore']:extra+=['--ext-folder',str(root/f)]
app=SimulationApp(dict(headless=False,width=1280,height=960,limit_cpu_threads=4,multi_gpu=False,extra_args=extra),experience=str(root/'apps/isaacsim.exp.base.python.kit'))
try:
    import omni.usd,omni.timeline
    from omni.kit.viewport.utility import get_active_viewport
    import omni.replicator.core as rep
    context=omni.usd.get_context();context.open_stage(str(a.scene.resolve()))
    omni.timeline.get_timeline_interface().stop()
    rep.settings.set_render_rtx_realtime(antialiasing='DLAA')
    for _ in range(20):app.update()
    viewport=get_active_viewport()
    if viewport:viewport.camera_path='/World/Overview'
    print('VIEWER_READY',str(a.scene.resolve()),flush=True)
    while app.is_running():app.update()
finally:app.close()
