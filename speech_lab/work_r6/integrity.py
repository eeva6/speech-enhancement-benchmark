import glob, numpy as np, soundfile as sf, os, sys
bad=[]
for f in glob.glob('outputs/r5/r6_tracks/*/*.npz'):
    try: z=np.load(f); [z[k] for k in z.files]
    except Exception as e: bad.append(f)
pats=['outputs/r5/*__*/*.wav','outputs/r5sim/*/*.wav','outputs/r5/ds_est/*.wav','outputs/r5/noisy/*.wav']+[f'outputs/r5/{m}/*.wav' for m in 'ds_td_rt sd4_rtn sd4_rt gm4_rt rtf4_rt gm8_rt rtf8_rt'.split()]
for p in pats:
    for f in glob.glob(p):
        try:
            x,_=sf.read(f)
            if len(x)<1000 or not np.isfinite(x).all(): bad.append(f)
        except Exception: bad.append(f)
for f in bad: os.remove(f)
print('removed',len(bad),bad[:30])
