"""Reproduce independent seeded episodes and Student-t confidence intervals."""
import argparse,json,random
from concurrent.futures import ProcessPoolExecutor,as_completed
from pathlib import Path
import numpy as np
from scipy.stats import t
from environment.warehouse_env import WarehouseEnv
from agents.original_skeleton import SkeletonOptimizationAgent as Original
from agents.skeleton_rl_agent import SkeletonOptimizationAgent as Final
from agents.standardized_agents import get_standardized_agents
from agents.layout_optimizer import LayoutOptimizer

def episode(spec):
    name,seed=spec
    random.seed(seed);np.random.seed(seed)
    env=WarehouseEnv(episode_length=3000,seed=seed)
    obs,_=env.reset(seed=seed)
    if name=="original_skeleton": agent=Original(env)
    elif name in ("no_layout","frequency_only","association","skeleton_optimization"):
        agent=Final(env)
        interval,weight,relocation={"no_layout":(100000,0,0),"frequency_only":(100,0,0),"association":(100,.15,0),"skeleton_optimization":(100,0,0)}[name]
        agent.layout_optimizer=LayoutOptimizer(env,interval,weight,relocation)
    else: agent=get_standardized_agents(env)[name]
    agent.reset();steps=0
    while True:
        obs,_,done,truncated,info=env.step(agent.get_action(obs));steps+=1
        if done or truncated:break
    row={"agent":name,"seed":seed,"profit":float(info["profit"]),"completion_rate":float(info["completion_rate"]),"steps":steps,"relocations_started":len(env.relocations_history),"layout_decisions":len(getattr(getattr(agent,"layout_optimizer",None),"decisions",[]))}
    env.close();return row

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--episodes",type=int,default=10);p.add_argument("--seed",type=int,default=6100)
    p.add_argument("--workers",type=int,default=8)
    p.add_argument("--agents",default="original_skeleton,no_layout,frequency_only,association,skeleton_optimization")
    p.add_argument("--output",default="results/layout_experiments.json")
    a=p.parse_args();names=a.agents.split(",");rows=[]
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        fs=[pool.submit(episode,(name,seed)) for name in names for seed in range(a.seed,a.seed+a.episodes)]
        for f in as_completed(fs):
            row=f.result();rows.append(row)
            print(f'{row["agent"]} seed={row["seed"]} profit={row["profit"]:.2f} steps={row["steps"]}',flush=True)
    stats={}
    for name in names:
        runs=sorted([r for r in rows if r["agent"]==name],key=lambda r:r["seed"])
        v=np.array([r["profit"] for r in runs])
        half=float(t.ppf(.975,len(v)-1)*np.std(v,ddof=1)/np.sqrt(len(v))) if len(v)>1 else None
        stats[name]={"mean_profit":float(v.mean()),"total_profit":float(v.sum()),"ci95_half_width":half,"episodes":runs}
    payload={"episode_length":3000,"seeds":list(range(a.seed,a.seed+a.episodes)),"interval_method":"Student t, sample SD ddof=1; independent episode means","results":stats}
    path=Path(a.output);path.parent.mkdir(exist_ok=True);path.write_text(json.dumps(payload,indent=2))
    for rank,(name,s) in enumerate(sorted(stats.items(),key=lambda kv:kv[1]["mean_profit"],reverse=True),1):print(rank,name,s["mean_profit"],s["ci95_half_width"])
if __name__=="__main__":main()
