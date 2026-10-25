#!/usr/bin/env python3

import argparse
import sys
import time
import warnings
from typing import Optional

# Suppress numpy warnings about empty slices and division
warnings.filterwarnings("ignore", message="Mean of empty slice")
warnings.filterwarnings("ignore", message="invalid value encountered in scalar divide")

from environment.warehouse_env import WarehouseEnv
from agents.baselines import get_baseline_agents
from analytics.simulation_analytics import SimulationAnalytics

def run_demo(agent_name: str = "greedy", render: bool = True, episodes: int = 1):
    """Run a demo of the warehouse environment with a specific agent"""
    
    print(f"Running warehouse simulation with {agent_name} agent...")
    
    # Initialize analytics
    analytics = SimulationAnalytics()
    
    # Create environment
    env_kwargs = {
        'render_mode': 'human' if render else None,
        'episode_length': 2000,  # Shorter episodes for demo
        'order_arrival_rate': 0.5,
    }
    
    env = WarehouseEnv(**env_kwargs)
    
    # Get agent
    if agent_name == "human":
        print("Human control mode not implemented yet")
        return
    elif agent_name == "rl":
        try:
            from stable_baselines3 import PPO
            agent = PPO.load("warehouse_ppo")
            print("Loaded trained RL agent")
        except:
            print("No trained RL agent found. Using greedy agent instead.")
            agent_name = "greedy"
    
    if agent_name != "rl":
        baseline_agents = get_baseline_agents(env)
        if agent_name not in baseline_agents:
            print(f"Unknown agent: {agent_name}")
            print(f"Available agents: {list(baseline_agents.keys())}")
            return
        agent = baseline_agents[agent_name]
    
    # Run episodes
    total_rewards = []
    total_profits = []
    
    for episode in range(episodes):
        print(f"\n--- Episode {episode + 1}/{episodes} ---")
        
        obs, info = env.reset()
        if hasattr(agent, 'reset'):
            agent.reset()
        
        episode_reward = 0
        step_count = 0
        
        try:
            while True:
                # Get action from agent
                if agent_name == "rl":
                    action, _ = agent.predict(obs, deterministic=True)
                else:
                    action = agent.get_action(obs)
                
                # Step environment
                obs, reward, terminated, truncated, info = env.step(action)
                episode_reward += reward
                step_count += 1
                
                # Record metrics for analytics
                order_gen = env.order_generator
                queue_len = info.get('queue_length', 0)
                num_employees = info.get('num_employees', 1)
                
                metrics = {
                    'cumulative_profit': info.get('profit', 0),
                    'queue_length': queue_len,
                    'completion_rate': info.get('completion_rate', 0) * 100,
                    'employee_count': num_employees,
                    'orders_completed': info.get('orders_completed', 0),
                    'orders_cancelled': info.get('orders_cancelled', 0),
                    # Adaptive order generation metrics
                    'customer_satisfaction': order_gen.customer_satisfaction,
                    'time_multiplier': order_gen._get_time_of_day_multiplier(step_count),
                    'satisfaction_multiplier': order_gen._get_satisfaction_multiplier(),
                    'pressure_multiplier': order_gen._get_queue_pressure_multiplier(queue_len, num_employees),
                    'effective_arrival_rate': (order_gen.base_arrival_rate * 
                                             order_gen._get_time_of_day_multiplier(step_count) *
                                             order_gen._get_satisfaction_multiplier() *
                                             order_gen._get_queue_pressure_multiplier(queue_len, num_employees)),
                    'hour_of_day': (step_count % order_gen.day_length) / order_gen.timesteps_per_hour
                }
                analytics.record_timestep(step_count, metrics)
                
                # Record layout swaps if they occurred
                if hasattr(env, 'last_swap_info') and env.last_swap_info:
                    analytics.record_swap(step_count, env.last_swap_info)
                    env.last_swap_info = None  # Clear after recording
                
                # Print periodic updates
                if step_count % 500 == 0:
                    print(f"Step {step_count}: Profit=${info.get('profit', 0):.2f}, "
                          f"Queue={info.get('queue_length', 0)}, "
                          f"Employees={info.get('num_employees', 0)}")
                
                # Render if enabled
                if render:
                    env.render()
                    time.sleep(0.01)  # Small delay for visualization
                
                if terminated or truncated:
                    break
        
        except KeyboardInterrupt:
            print("\nDemo interrupted by user")
            break
        
        # Episode summary
        profit = info.get('profit', 0)
        completion_rate = info.get('completion_rate', 0)
        
        print(f"Episode {episode + 1} completed!")
        print(f"  Total Reward: {episode_reward:.2f}")
        print(f"  Final Profit: ${profit:.2f}")
        print(f"  Completion Rate: {completion_rate:.1%}")
        print(f"  Orders Completed: {info.get('orders_completed', 0)}")
        print(f"  Orders Cancelled: {info.get('orders_cancelled', 0)}")
        
        # Record episode completion
        episode_metrics = {
            'final_profit': profit,
            'total_reward': episode_reward,
            'completion_rate': completion_rate * 100,
            'orders_completed': info.get('orders_completed', 0),
            'orders_cancelled': info.get('orders_cancelled', 0),
            'final_queue_length': info.get('queue_length', 0),
            'final_employees': info.get('num_employees', 0)
        }
        analytics.record_episode_completion(episode + 1, episode_metrics)
        
        total_rewards.append(episode_reward)
        total_profits.append(profit)
    
    # Overall summary
    if len(total_rewards) > 1:
        print(f"\n--- Overall Summary ({episodes} episodes) ---")
        print(f"Average Reward: {sum(total_rewards)/len(total_rewards):.2f}")
        print(f"Average Profit: ${sum(total_profits)/len(total_profits):.2f}")
    
    env.close()
    
    # Show analytics after simulation completion
    print(f"\nDisplaying analytics for {agent_name} agent...")
    analytics.show_analytics(agent_name)

def run_legacy_benchmark(episodes: int = 10):
    """Run benchmark comparison of all agents"""
    
    print(f"Running benchmark with {episodes} episodes per agent...")
    
    env = WarehouseEnv(episode_length=3000)
    baseline_agents = get_baseline_agents(env)
    
    results = {}
    
    for agent_name, agent in baseline_agents.items():
        print(f"\nTesting {agent_name}...", end='', flush=True)
        
        episode_rewards = []
        episode_profits = []
        episode_completion_rates = []
        
        for episode in range(episodes):
            obs, _ = env.reset()
            agent.reset()
            
            episode_reward = 0
            
            while True:
                action = agent.get_action(obs)
                obs, reward, terminated, truncated, info = env.step(action)
                episode_reward += reward
                
                if terminated or truncated:
                    break
            
            episode_rewards.append(episode_reward)
            episode_profits.append(info.get('profit', 0))
            episode_completion_rates.append(info.get('completion_rate', 0))
            
            # Show percentage completion
            percent_complete = int(((episode + 1) / episodes) * 100)
            print(f'\rTesting {agent_name}... [{percent_complete}% complete]', end='', flush=True)
        
        # Calculate statistics with confidence intervals
        avg_reward = sum(episode_rewards) / len(episode_rewards)
        avg_profit = sum(episode_profits) / len(episode_profits)
        avg_completion_rate = sum(episode_completion_rates) / len(episode_completion_rates)
        
        # Calculate 95% confidence intervals
        import numpy as np
        profit_std = np.std(episode_profits)
        profit_ci = 1.96 * profit_std / np.sqrt(len(episode_profits)) if len(episode_profits) > 1 else 0
        
        completion_std = np.std(episode_completion_rates)
        completion_ci = 1.96 * completion_std / np.sqrt(len(episode_completion_rates)) if len(episode_completion_rates) > 1 else 0
        
        results[agent_name] = {
            'avg_reward': avg_reward,
            'avg_profit': avg_profit,
            'avg_completion_rate': avg_completion_rate,
            'profit_ci': profit_ci,
            'completion_ci': completion_ci,
            'rewards': episode_rewards,
            'profits': episode_profits
        }
        
        print(f'\rTesting {agent_name}... Done!                    ')  # Extra spaces to clear percentage
        print(f"  Average Reward: {avg_reward:.2f}")
        print(f"  Average Profit: ${avg_profit:.2f} ± ${profit_ci:.2f}")
        print(f"  Average Completion Rate: {avg_completion_rate:.1%} ± {completion_ci:.1%}")
    
    # Print ranking
    print(f"\n--- Benchmark Results (ranked by profit) ---")
    sorted_agents = sorted(results.items(), key=lambda x: x[1]['avg_profit'], reverse=True)
    
    for i, (name, stats) in enumerate(sorted_agents, 1):
        profit_ci = stats.get('profit_ci', 0)
        completion_ci = stats.get('completion_ci', 0)
        print(f"{i}. {name:15s} | "
              f"Profit: ${stats['avg_profit']:8.2f} ± ${profit_ci:6.2f} | "
              f"Completion: {stats['avg_completion_rate']:6.1%} ± {completion_ci:5.1%}")
    
    env.close()
    return results

def run_benchmark(episodes: int = 10):
    """Reproducible parallel comparison; fresh envs avoid cross-agent leakage."""
    import subprocess
    from pathlib import Path
    subprocess.run([sys.executable, str(Path(__file__).with_name('evaluate_staffing.py')),
                    '--episodes', str(episodes)], check=True)

def main():
    parser = argparse.ArgumentParser(description="Warehouse RL Simulator")
    parser.add_argument("--mode", type=str, default="demo",
                      choices=["demo", "benchmark", "train"],
                      help="Run mode")
    parser.add_argument("--agent", type=str, default="greedy_std",
                      choices=["greedy_std", "random_std", "fixed_std", "intelligent_hiring", "intelligent_queue", "distance_based", "aggressive_swap", "skeleton_optimization", "rl"],
                      help="Agent to use for demo")
    parser.add_argument("--episodes", type=int, default=1,
                      help="Number of episodes to run")
    parser.add_argument("--no-render", action="store_true",
                      help="Disable rendering")
    parser.add_argument("--timesteps", type=int, default=1000000,
                      help="Training timesteps (for train mode)")
    
    args = parser.parse_args()
    
    if args.mode == "demo":
        run_demo(
            agent_name=args.agent,
            render=not args.no_render,
            episodes=args.episodes
        )
    elif args.mode == "benchmark":
        run_benchmark(episodes=args.episodes)
    elif args.mode == "train":
        from training.train import train_ppo_agent
        train_ppo_agent(total_timesteps=args.timesteps)
    else:
        print(f"Unknown mode: {args.mode}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
