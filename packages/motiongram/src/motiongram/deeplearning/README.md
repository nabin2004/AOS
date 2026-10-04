# MotionGram Deep Learning Explainer Module

Premium, modular visual components for teaching deep learning concepts in explainer videos. Every component is a `@dataclass(slots=True)` **`Node`** subclass — flat composition, zero global state, and full **timeline/animator** compatibility.

## Design philosophy

1. **Pure nodes** — geometry and labels live in `draw_world`; no hidden clocks or frame mutations in `update()`.
2. **Animator-driven motion** — animate `progress`, `input_val`, `active_row`, `kernel_row`, etc. via `Scene.add_animation` and `AnimateAttribute` / `AnimateIntAttribute`.
3. **Skia-safe drawing** — all canvas calls use `getattr(canvas, "method", None)` so nodes compile cleanly on null/ASCII backends.

## Quick start

```python
from motiongram import Scene
from motiongram.deeplearning import (
    AnimateAttribute,
    AnimateIntAttribute,
    ActivationFunctions,
    Convolutions,
    HiddenLayers,
    Matrices,
)
from motiongram.deeplearning.linear_algebra import MatrixMultiplication

scene = Scene(width=1280, height=720, fps=30, duration=6.0)

# Weight matrix
weights = Matrices(
    x=80,
    y=120,
    values=[[0.2, -0.5, 0.1], [0.8, 0.3, -0.2], [0.0, 0.6, 0.4]],
    label="W",
    highlight_row=0,
)
scene.add_node(weights)

# Animate row highlight through matrix multiply
mm = MatrixMultiplication(
    x=80,
    y=320,
    matrix_a=[[1, 2], [3, 4]],
    matrix_b=[[5, 6], [7, 8]],
    active_row=0,
    active_col=0,
)
scene.add_node(mm)
scene.add_animation(0.0, 3.0, mm, AnimateIntAttribute("active_row", 0, 1))
scene.add_animation(0.0, 3.0, mm, AnimateIntAttribute("active_col", 0, 1))

# ReLU plot with sweeping input
relu = ActivationFunctions(x=700, y=120, activation="relu", input_val=-2.0)
scene.add_node(relu)
scene.add_animation(0.0, 4.0, relu, AnimateAttribute("input_val", -2.0, 3.0))

# Convolution sliding window
conv = Convolutions(
    x=700,
    y=320,
    input_grid=[[1, 0, 1], [0, 1, 0], [1, 1, 0]],
    kernel=[[1, 0], [0, 1]],
    kernel_row=0,
    kernel_col=0,
)
scene.add_node(conv)
scene.add_animation(0.0, 5.0, conv, AnimateIntAttribute("kernel_col", 0, 1))
```

See `examples/deeplearning_showcase.py` for a full Skia render demo.

## Module map

| Module | Components | Topics |
|--------|------------|--------|
| `linear_algebra` | `Scalars`, `Vectors`, `Matrices`, `Tensors`, `DotProducts`, `VectorProducts`, `MatrixMultiplication` | Tensors, dot products, matmul |
| `calculus` | `Derivatives`, `Differentiation`, `PartialDerivatives`, `Gradients`, `ChainRule` | Slopes, GD, chain rule |
| `mlp` | `HiddenLayers`, `ActivationFunctions`, `ForwardProp`, `BackwardProp`, `ComputationalGraphs`, `VanishingGradients`, `ExplodingGradients`, `ParamInit`, `EarlyStopping`, `Regularization`, `Dropout` | MLPs, activations, backprop |
| `cnns` | `Convolutions`, `Channels`, `ConvolutionalLayers`, `FeatureMap`, `ReceptiveField`, `Padding`, `Stride`, `Pooling`, `ModernCNN` | CNN mechanics |
| `data_manipulation` | `Indexing`, `Slicing`, `Operations`, `Broadcasting`, `Vectorization` | NumPy-style ops |
| `generalization` | `Error`, `TrainingError`, `GeneralizationError`, `Underfitting`, `Overfitting`, `ModelSelection` | Bias–variance, model selection |
| `metrics` | `Metrics`, `Prediction` | Confusion matrix, classification output |
| `autodiff` | `ComputationTape`, `DualNumberNode`, `TapeVisualizer` | Forward/reverse mode AD |
| `algos` | Slide nodes + `DataSet`, `Model`, `Training`, `LossFunction`, `OptimizationAlgorithm`, `TrainTestSplit`, `CrossVal`, `TrainingLoop` | Lecture structure & ML pipeline |
| `animators` | `AnimateAttribute`, `AnimateIntAttribute` | Generic property interpolation |

## Animatable properties (common)

| Property | Used by | Effect |
|----------|---------|--------|
| `progress` | `DotProducts`, `Gradients`, `ForwardProp`, `Broadcasting`, … | Step-through reveal (0 → 1) |
| `input_val` | `ActivationFunctions`, `Derivatives` | Cursor / tangent position |
| `active_row`, `active_col` | `MatrixMultiplication`, `Convolutions` | Highlight matmul / kernel path |
| `kernel_row`, `kernel_col` | `Convolutions`, `Stride` | Sliding window position |
| `h_val` | `Differentiation` | Secant → tangent limit |
| `dropped_indices` | `Dropout` | Which neurons are inactive |

## Shared utilities

- **`_draw.py`** — `DLTheme` palette and helpers (`draw_round_cell`, `draw_arrow`, `draw_grid_cells`, …).
- **`animators.py`** — `AnimateAttribute(attr, v0, v1)` and `AnimateIntAttribute` for timeline segments.

## Theming

Default colors follow a premium dark IDE palette (`#21252b` background, `#61afef` blue accents, `#98c379` green highlights, `#e5c07b` active states). Override any `*_color` field on a node for custom branding.

## Testing

```bash
pytest tests/unit/test_deeplearning.py -q
```

Tests verify construction, `draw_world` on null canvas, and animator-driven property changes.
