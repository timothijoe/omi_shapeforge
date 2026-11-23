"""Evaluate frozen old weights and new weights on identical contact-test images."""
import argparse,json
from pathlib import Path
import numpy as np,torch
from torch.utils.data import DataLoader
from image_to_surface_network import ImageToCompleteSurface
from train_sim_wrist_surface import Frames,training_statistics,evaluate,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--old',type=Path,required=True);a=p.parse_args();torch.set_num_threads(4)
 data=a.run/'data';rows=list(map(json.loads,(data/'records.jsonl').read_text().splitlines()));test=[r for r in rows if r['split']=='test'];train=[r for r in rows if r['split']=='train'];stats=training_statistics(train);mean=torch.tensor([stats[n]['mean_T'] for n in ['module','socket']],dtype=torch.float32);loader=DataLoader(Frames(data,test),batch_size=16,num_workers=4,persistent_workers=True);out=a.run/'transfer_evaluation';out.mkdir(exist_ok=False);report={'same_test_frame_ids':[r['id'] for r in test],'models':{},'new_test_used_for_checkpoint_selection':False,'old_prior_and_decoder_preserved':True}
 for name,checkpoint in [('old_frozen',a.old),('contact_finetuned',a.run/'train/best.pt')]:
  state=torch.load(checkpoint,map_location='cpu',weights_only=True);cfg=state['config'];model=ImageToCompleteSurface(cfg['templates'],cfg['calibration']);model.load_state_dict(state['model'],strict=True);model=model.cuda();metrics,arrays=evaluate(model,loader,'cuda',mean);np.savez_compressed(out/f'{name}_predictions.npz',**arrays);report['models'][name]={'checkpoint':str(checkpoint),'sha256':sha(checkpoint),'metrics':metrics};del model;torch.cuda.empty_cache()
 (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report['models']),flush=True)
if __name__=='__main__':main()
