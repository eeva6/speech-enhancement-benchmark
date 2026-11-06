import json, glob, pandas as pd
from selab.run_r6 import select
s=set(m["id"] for m in select(json.load(open("mixtures/r5/meta.json")),"s345"))
w=pd.concat([pd.read_csv(p) for p in glob.glob("results/r6/wer_r5.csv")+glob.glob("results/r6/wer_r5.part*.csv")]+[pd.read_csv(p) for p in glob.glob("results/r5/wer_r5.csv")+glob.glob("results/r5/wer_r5.part*.csv")]).drop_duplicates(["method","id"])
ms=["noisy","ds_est","ds_td_rt","sd4_rt__w6","sd8_rt","ds_td_ref","sd4_ref__w6","sd8_ref"]
print({m:int(((w.method==m)&w.id.isin(s)).sum()) for m in ms})
ws=pd.concat([pd.read_csv(p) for p in glob.glob("results/r6/wer_r5sim*.csv")]) if glob.glob("results/r6/wer_r5sim*.csv") else None
if ws is not None: print("sim", ws.method.value_counts().to_dict())
