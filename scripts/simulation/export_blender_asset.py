"""Run in Blender: export evaluated optical-module parts for simulation."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--package', type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
output = args.output.resolve()
output.mkdir(parents=True, exist_ok=False)
(output / 'meshes').mkdir()
collection = bpy.data.collections['Photo + stereo + connected groove reference']
depsgraph = bpy.context.evaluated_depsgraph_get()
parts = []
all_vertices = []
for index, obj in enumerate(collection.objects):
    if obj.type not in ('MESH', 'CURVE'):
        continue
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    vertices = np.array([evaluated.matrix_world @ v.co for v in mesh.vertices], dtype=np.float64)
    faces = np.array([tri.vertices[:] for tri in mesh.loop_triangles], dtype=np.int64)
    if not len(vertices) or not len(faces):
        evaluated.to_mesh_clear()
        continue
    if not np.isfinite(vertices).all():
        raise ValueError('Non-finite geometry: ' + obj.name)
    filename = f'meshes/part_{index:02d}.obj'
    with (output / filename).open('w') as stream:
        stream.write('# OMI ShapeForge; evaluated source geometry, coordinates in meters\n')
        for vertex in vertices:
            stream.write('v ' + ' '.join(format(float(x), '.10g') for x in vertex) + '\n')
        for face in faces:
            stream.write('f ' + ' '.join(str(int(x) + 1) for x in face) + '\n')
    rgba = [0.55, 0.58, 0.62, 1.0]
    if mesh.materials and mesh.materials[0]:
        material = mesh.materials[0]
        rgba = list(material.diffuse_color)
        if material.use_nodes:
            principled = next((node for node in material.node_tree.nodes
                               if node.type == 'BSDF_PRINCIPLED'), None)
            if principled:
                rgba = list(principled.inputs['Base Color'].default_value)
    rgba = [float(x) for x in rgba]
    rgba[3] = 1.0
    parts.append({'name': obj.name, 'mesh': filename, 'rgba': rgba,
                  'vertices': len(vertices), 'triangles': len(faces)})
    all_vertices.append(vertices)
    evaluated.to_mesh_clear()
vertices = np.concatenate(all_vertices)
if np.max(np.ptp(vertices, axis=0)) > 0.3:
    raise ValueError('Unexpected asset scale; expected a handheld object in meters')
with np.load(args.package / 'models/rigid_match_mesh.npz', allow_pickle=False) as rigid:
    low, high = rigid['vertices'].min(axis=0), rigid['vertices'].max(axis=0)
source = Path(bpy.data.filepath)
manifest = {
    'asset': 'optical_module_connected_groove', 'units': 'meters',
    'source_blend': str(source),
    'source_blend_sha256': hashlib.file_digest(source.open('rb'), 'sha256').hexdigest(),
    'blender_version': bpy.app.version_string, 'parts': parts,
    'visual_bounds_m': [vertices.min(axis=0).tolist(), vertices.max(axis=0).tolist()],
    'collision_box_center_m': ((low + high) / 2).tolist(),
    'collision_box_halfsize_m': ((high - low) / 2).tolist(),
    'collision_model': 'Single box around the rigid matching mesh; does not preserve groove contacts.',
    'mass_kg': 0.02, 'mass_provenance': 'Assumed for demonstration; not measured.',
    'flexible_components': 'Visual components are rigidly attached in this initial scene.',
    'physical_accuracy_validated': False,
}
(output / 'asset.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({'status': 'exported_evaluated_geometry', 'parts': len(parts),
                  'visual_bounds_m': manifest['visual_bounds_m'], 'output': str(output)}, indent=2))
