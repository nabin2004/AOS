# W&B Training Dynamics: Comparative Analysis

## 1. Overview
This report maps the training dynamics across the Baseline, SFT, and GRPO stages for the AOS Manim Code Generation pipeline.

## 2. Validation Loss Improvements (SFT Stage)
A lower validation loss typically correlates with a reduced Version-Conflict Error Rate (VCER) in ManiBench.

| stage        |   eval/loss |
|:-------------|------------:|
| AOS-Qwen-SFT |   0.0321649 |

## 3. GRPO Alignment Metrics
Rewards mapping directly to zero-shot pass rates.

