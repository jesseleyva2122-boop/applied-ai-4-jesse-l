"""Seeded staffing/pickup comparisons with independent environments and t CIs."""

import argparse, json, random, time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import numpy as np
from scipy.stats import t
from environment.warehouse_env import WarehouseEnv
from agents.previous_layout_agent import SkeletonOptimizationAgent as Previous
from agents.skeleton_rl_agent import SkeletonOptimizationAgent as Final
from agents.standardized_agents import get_standardized_agents


def episode(spec):
    name, seed, length = spec
    random.seed(seed)
    np.random.seed(seed)
    env = WarehouseEnv(episode_length=length, seed=seed)
    obs, _ = env.reset(seed=seed)
    if name == "previous_layout":
        agent = Previous(env)
    elif name in (
        "skeleton_optimization",
        "low_wage",
        "cap8",
        "cap12",
        "staffing_only",
        "routing_only",
        "value_focus",
        "distance_focus",
    ):
        agent = Final(
            env,
            max_workers={"cap8": 8, "cap12": 12}.get(name, 12),
            wage_action=1 if name == "low_wage" else 4,
            routing=name != "staffing_only",
            distance_weight={"value_focus": 0.15, "distance_focus": 2.0}.get(name, 0.5),
        )
        if name == "routing_only":
            old = Previous(env)
            agent.optimize_staffing = lambda: old._get_naive_staffing_action(None, None)
            env._unlimited_hiring = False
    else:
        agent = get_standardized_agents(env)[name]
    agent.reset()
    start = time.perf_counter()
    peak = 0
    steps = 0
    while True:
        action = agent.get_action(obs)
        obs, reward, done, truncated, info = env.step(action)
        steps += 1
        peak = max(peak, len(env.employees))
        if done or truncated:
            break
    row = {
        "agent": name,
        "seed": seed,
        "profit": float(info["profit"]),
        "revenue": env.total_revenue,
        "costs": env.total_costs,
        "completion_rate": float(info["completion_rate"]),
        "orders_completed": info["orders_completed"],
        "steps": steps,
        "peak_employees": peak,
        "final_workers": sum(not e.is_manager for e in env.employees),
        "staffing_actions": getattr(agent, "staffing_history", []),
        "relocations": len(env.relocations_history),
        "wall_seconds": time.perf_counter() - start,
    }
    env.close()
    return row


def summarize(rows, names):
    stats = {}
    for name in names:
        runs = sorted([r for r in rows if r["agent"] == name], key=lambda r: r["seed"])
        v = np.array([r["profit"] for r in runs])
        n = len(v)
        half = (
            float(t.ppf(0.975, n - 1) * v.std(ddof=1) / np.sqrt(n)) if n > 1 else None
        )
        stats[name] = {
            "mean_profit": float(v.mean()),
            "total_profit": float(v.sum()),
            "ci95_half_width": half,
            "ci95": (
                [float(v.mean() - half), float(v.mean() + half)]
                if half is not None
                else None
            ),
            "mean_completion_rate": float(
                np.mean([r["completion_rate"] for r in runs])
            ),
            "episodes": runs,
        }
    for rank, (name, s) in enumerate(
        sorted(stats.items(), key=lambda x: x[1]["mean_profit"], reverse=True), 1
    ):
        s["rank"] = rank
    return stats


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--episodes", type=int, default=10)
    p.add_argument("--seed", type=int, default=9100)
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--length", type=int, default=3000)
    p.add_argument(
        "--agents",
        default="previous_layout,skeleton_optimization,greedy_std,random_std,fixed_std,intelligent_hiring,intelligent_queue,distance_based,aggressive_swap",
    )
    p.add_argument("--output", default="results/assignment6/benchmark.json")
    a = p.parse_args()
    names = a.agents.split(",")
    rows = []
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        fs = [
            pool.submit(episode, (name, seed, a.length))
            for name in names
            for seed in range(a.seed, a.seed + a.episodes)
        ]
        for f in as_completed(fs):
            r = f.result()
            rows.append(r)
            print(
                f"{r['agent']} {r['seed']} profit={r['profit']:.2f} steps={r['steps']}",
                flush=True,
            )
    stats = summarize(rows, names)
    paired = {}
    if "previous_layout" in stats:
        base = np.array([r["profit"] for r in stats["previous_layout"]["episodes"]])
        for name, s in stats.items():
            if name == "previous_layout":
                continue
            delta = np.array([r["profit"] for r in s["episodes"]]) - base
            n = len(delta)
            half = (
                float(t.ppf(0.975, n - 1) * delta.std(ddof=1) / np.sqrt(n))
                if n > 1
                else None
            )
            paired[name] = {
                "mean_gain": float(delta.mean()),
                "ci95": (
                    [float(delta.mean() - half), float(delta.mean() + half)]
                    if half is not None
                    else None
                ),
            }
    payload = {
        "episode_length": a.length,
        "seeds": list(range(a.seed, a.seed + a.episodes)),
        "method": "Independent fresh environments; Python/NumPy seeded; Student t with sample SD; demand adapts to policy, so common seeds are not identical orders.",
        "results": stats,
        "paired_vs_previous": paired,
    }
    path = Path(a.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))
    for name, s in sorted(stats.items(), key=lambda kv: kv[1]["rank"]):
        print(s["rank"], name, s["mean_profit"], s["ci95"])


if __name__ == "__main__":
    main()
