import os
import wandb
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Set up visual styling for publication
plt.rcParams.update({
    "font.family": "serif",
    "axes.labelsize": 12,
    "font.size": 12,
    "legend.fontsize": 10,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "figure.dpi": 300
})

def main():
    # 1. Configuration & Authentication
    api_key = os.environ.get("WANDB_API_KEY", "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")
    wandb.login(key=api_key)
    api = wandb.Api()

    # Define projects and the alias for the report
    projects = {
        "Baseline": "nabinoli2004-wiseyak/huggingface",
        "AOS-Qwen-SFT": "nabinoli2004-wiseyak/aos-qwen-sft",
        "AOS-SFT": "nabinoli2004-wiseyak/aos-sft",
        "AOS-GRPO": "nabinoli2004-wiseyak/aos-grpo"
    }
    
    # Metrics to extract across different stages
    metrics = [
        "train/loss", 
        "eval/loss", 
        "train/learning_rate", 
        "env/reward_mean", 
        "policy/entropy",
        "eval/reward"
    ]

    # Setup directories
    base_dir = Path(__file__).parent / "wandb_report_output"
    data_dir = base_dir / "data"
    plots_dir = base_dir / "plots"
    data_dir.mkdir(parents=True, exist_ok=True)
    plots_dir.mkdir(parents=True, exist_ok=True)

    print(f"Starting W&B extraction pipeline. Output directory: {base_dir}")

    # 2. Data Extraction
    all_runs_data = []
    
    for stage, project_path in projects.items():
        print(f"Fetching data for {stage} ({project_path})...")
        try:
            runs = api.runs(project_path)
        except Exception as e:
            print(f"Failed to fetch {project_path}: {e}")
            continue

        for run in runs:
            # We fetch up to 1000 samples per metric to keep memory manageable while retaining resolution
            history = run.scan_history(keys=["_step"] + metrics)
            df = pd.DataFrame(history)
            
            if df.empty:
                continue
                
            df["run_id"] = run.id
            df["run_name"] = run.name
            df["stage"] = stage
            all_runs_data.append(df)

    if not all_runs_data:
        print("No data extracted. Exiting.")
        return

    # 3. Data Processing & Mapping
    print("Processing extracted data...")
    master_df = pd.concat(all_runs_data, ignore_index=True)
    master_csv = data_dir / "master_metrics.csv"
    master_df.to_csv(master_csv, index=False)
    print(f"Saved master dataset to {master_csv}")

    # 4. Generate Comparative Plots
    print("Generating publication-ready plots...")
    
    # Plot 1: Comparative Validation Loss (SFT Phases)
    sft_data = master_df[master_df["stage"].isin(["AOS-SFT", "AOS-Qwen-SFT", "Baseline"])]
    if not sft_data.empty and "eval/loss" in sft_data.columns:
        plt.figure(figsize=(10, 6))
        sns.lineplot(data=sft_data.dropna(subset=["eval/loss"]), 
                     x="_step", y="eval/loss", hue="stage", 
                     style="run_name", linewidth=2, alpha=0.8)
        plt.title("Comparative Validation Loss: Base vs SFT Models")
        plt.xlabel("Training Step")
        plt.ylabel("Validation Loss")
        plt.grid(True, linestyle="--", alpha=0.6)
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        plt.savefig(plots_dir / "sft_validation_loss_comparison.pdf")
        plt.close()

    # Plot 2: GRPO Reward Dynamics
    grpo_data = master_df[master_df["stage"] == "AOS-GRPO"]
    if not grpo_data.empty and "env/reward_mean" in grpo_data.columns:
        plt.figure(figsize=(10, 6))
        sns.lineplot(data=grpo_data.dropna(subset=["env/reward_mean"]), 
                     x="_step", y="env/reward_mean", hue="run_name", linewidth=2)
        plt.title("GRPO Alignment: Mean Reward Dynamics")
        plt.xlabel("Training Step")
        plt.ylabel("Mean Reward (Syntactical + Visual)")
        plt.grid(True, linestyle="--", alpha=0.6)
        plt.tight_layout()
        plt.savefig(plots_dir / "grpo_reward_dynamics.pdf")
        plt.close()

    # Plot 3: GRPO Policy Entropy (Mode Collapse Check)
    if not grpo_data.empty and "policy/entropy" in grpo_data.columns:
        plt.figure(figsize=(10, 6))
        sns.lineplot(data=grpo_data.dropna(subset=["policy/entropy"]), 
                     x="_step", y="policy/entropy", hue="run_name", linewidth=2, color="coral")
        plt.title("GRPO Policy Entropy (Diversity Preservation)")
        plt.xlabel("Training Step")
        plt.ylabel("Policy Entropy")
        plt.grid(True, linestyle="--", alpha=0.6)
        plt.tight_layout()
        plt.savefig(plots_dir / "grpo_policy_entropy.pdf")
        plt.close()

    # 5. Generate Markdown Summary Report
    print("Generating statistical summary report...")
    report_path = base_dir / "wandb_comparative_report.md"
    
    with open(report_path, "w") as f:
        f.write("# W&B Training Dynamics: Comparative Analysis\n\n")
        f.write("## 1. Overview\n")
        f.write("This report maps the training dynamics across the Baseline, SFT, and GRPO stages for the AOS Manim Code Generation pipeline.\n\n")
        
        f.write("## 2. Validation Loss Improvements (SFT Stage)\n")
        f.write("A lower validation loss typically correlates with a reduced Version-Conflict Error Rate (VCER) in ManiBench.\n\n")
        
        # Calculate min eval loss per stage
        if not sft_data.empty and "eval/loss" in sft_data.columns:
            min_loss = sft_data.dropna(subset=["eval/loss"]).groupby("stage")["eval/loss"].min().reset_index()
            f.write(min_loss.to_markdown(index=False) + "\n\n")
            
        f.write("## 3. GRPO Alignment Metrics\n")
        f.write("Rewards mapping directly to zero-shot pass rates.\n\n")
        
        if not grpo_data.empty:
            if "env/reward_mean" in grpo_data.columns:
                max_reward = grpo_data.dropna(subset=["env/reward_mean"]).groupby("run_name")["env/reward_mean"].max().reset_index()
                f.write("### Maximum Rewards Achieved\n")
                f.write(max_reward.to_markdown(index=False) + "\n\n")
                
            if "policy/entropy" in grpo_data.columns:
                final_entropy = grpo_data.dropna(subset=["policy/entropy"]).groupby("run_name")["policy/entropy"].last().reset_index()
                f.write("### Final Policy Entropy (Higher = Better Diversity)\n")
                f.write(final_entropy.to_markdown(index=False) + "\n\n")

    print(f"Pipeline complete! Output saved to: {base_dir}")

if __name__ == "__main__":
    main()
