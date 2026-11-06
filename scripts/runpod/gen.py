import torch, time, sys
from diffusers import WanPipeline, AutoencoderKLWan
from diffusers.utils import export_to_video
mid = 'Wan-AI/Wan2.2-TI2V-5B-Diffusers'
vae = AutoencoderKLWan.from_pretrained(mid, subfolder='vae', torch_dtype=torch.float32)
pipe = WanPipeline.from_pretrained(mid, vae=vae, torch_dtype=torch.bfloat16)
pipe.enable_model_cpu_offload(); pipe.vae.enable_tiling(); pipe.vae.enable_slicing()
prompt = ('A locked-off tripod shot from the front, full body visible, of a calm woman in dark simple clothes sitting cross-legged on a floor cushion in a plain bright room. '
          'A small bronze singing bowl sits on the floor beside her right knee, and nothing blocks her body. She breathes slowly, turns her head and leans gently to the side, reaches down with her right hand holding a short thin wooden stick, softly taps the small bowl, lifts her hand away, returns her hand to her knee and sits still, breathing. '
          'Slow continuous natural movement, the whole time, realistic documentary footage, sharp focus.')
neg = 'large bowl, bowl in front of body, big hammer, camera movement, zoom, cuts, text, watermark, blurry, extra limbs, extra fingers, deformed hands, fast motion, cartoon'
for i, seed in enumerate((31, 47)):
    t = time.time()
    v = pipe(prompt=prompt, negative_prompt=neg, height=704, width=1280, num_frames=121, guidance_scale=5.0, num_inference_steps=40, generator=torch.Generator('cuda').manual_seed(seed)).frames[0]
    export_to_video(v, f'/root/next{i}.mp4', fps=24); print('clip', i, round(time.time() - t), 's', flush=True)
