---
marp: true
theme: uncover
_class: invert
math: katex
paginate: true
---

# CS231n: Deep Learning for Computer Vision

Lecture 1: Introduction

Welcome to CS231n! I'm your instructor, and I'll be guiding you through this course.

---
# Intro to data science

$\text{Data Science}$ = $\text{Statistics}$ + $\text{Computer Science}$ + $\text{Domain Expertise}$


$$e^{ix} = \cos x + i \sin x$$

---
# Code Walkthrough

```python
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

df = pd.read_csv('data.csv')
plt.figure(figsize=(10, 6))
```

```Javascript
const data = [1, 2, 3, 4, 5];
console.log(data.map(x => x * 2));
console.log("Hello, World!");
```

--- 
# Citation

According to recent findings, Marp simplifies technical slide creation [[Sam, et. al.]](#1). 
However, it requires manual formatting for bibliographies [[Oli, et. al.]](#2).

<!-- _footer: "1. Sam et al., Journal of Slides, 2025" -->
<!-- _footer: "2. Oli et al., Journal of Slides, 2025" -->
---

## Welcome to CS231n

Welcome to CS231n – the 10th anniversary edition! We're excited to have you here.

CS231n celebrates its 10th anniversary in 2025, and this is the 2026 edition.

<!-- DIAGRAM: 10th anniversary logo/timeline graphic with years 2015→2025 -->

---

## CS231n – 2026 Edition

This is the 2026 edition of CS231n, taught by Fei-Fei Li, Ehsan Adeli, Zane Durante, Justin Johnson, and Tiange Xiang.

Key drivers of the modern AI revolution:
- Neural networks
- GPUs
- Big Data

<!-- DIAGRAM: Icon set or simple illustrations for each driver (neural network symbol, GPU chip, data cloud) -->

---

## Artificial Intelligence

![AI Venn diagram](assets/venn_ai_ml_dl_cv.png)

Artificial Intelligence is the broad field. Machine Learning is a subset. Computer Vision is a subset of ML.

<!-- DIAGRAM: Nested Venn diagram with circles: AI (largest), ML (inside AI), DL (inside ML), CV (inside DL). Highlight "This class" in CV. -->

---

## Artificial Intelligence → Machine Learning

Machine Learning is a subfield of AI.

<!-- DIAGRAM: Simple two-circle Venn (AI outer, ML inner) or flowchart arrow. -->

---

## Artificial Intelligence → Machine Learning → Deep Learning

Deep Learning is a subfield of Machine Learning.

<!-- DIAGRAM: Three nested circles (AI > ML > DL) with labels. -->

---

## Artificial Intelligence → Machine Learning → Deep Learning → Computer Vision

Computer Vision is a subfield of Deep Learning.

<!-- DIAGRAM: Four nested circles (AI > ML > DL > CV). -->

---

## This class

This class sits at the intersection of Computer Vision and Deep Learning.

<!-- DIAGRAM: Highlight the CV circle within the DL circle with a star or "This class" label. -->

---

## This class (continued)

We will cover deep learning techniques applied to computer vision tasks.

<!-- DIAGRAM: Icon for "deep learning" (neural network) and "computer vision" (eye/camera) with an arrow. -->

---

## This class (continued)

We will learn how to build and train deep neural networks for vision.

<!-- DIAGRAM: Simple neural network diagram (input → hidden layers → output) with an image input. -->

---

## This class (continued)

We will understand the theory and practice of modern computer vision.

---

## This class (continued)

Computer Vision draws from many disciplines:
- Computer Science
- Biology
- Psychology
- Mathematics
- Physics
- Neuroscience

<!-- DIAGRAM: Word cloud or interconnected nodes representing these disciplines. -->

---

## Today’s Agenda

- A brief history of computer vision and deep learning
- CS231n overview

<!-- DIAGRAM: Simple timeline icon with two main points. -->

---

## Evolution’s Big Bang: Cambrian Explosion, 530–540 million years B.C.

![Cambrian explosion image 1](assets/cambrian_fossils.jpg)
![Cambrian explosion image 2](assets/trilobite.jpg)
![Cambrian explosion image 3](assets/eye_evolution.jpg)

The Cambrian Explosion marked a sudden burst of visual intelligence in the animal kingdom.

<!-- DIAGRAM: Collage of Cambrian fossils, early eye evolution, and maybe a phylogenetic tree. -->

---

## Camera Obscura

![Camera Obscura images](assets/camera_obscura.jpg)

Early understanding of optics and image formation dates back to Leonardo da Vinci and earlier.

<!-- DIAGRAM: Diagram of camera obscura原理, or historical images. -->

---

## Computer Vision is everywhere!

![CV applications collage](assets/cv_applications.jpg)

Computer vision is integrated into countless applications today.

<!-- DIAGRAM: Collage of images: self-driving cars, medical imaging, face recognition, AR/VR, etc. -->

---

## Human development depends on visual intelligence

Visual perception is fundamental to human development and survival.

<!-- DIAGRAM: Image of a baby looking/pointing, or developmental milestones. -->

---

## Humans build civilization using visual intelligence

All of human civilization, from agriculture to architecture, relies on visual intelligence.

<!-- DIAGRAM: Ancient structures (e.g., pyramids) or modern cities. -->

---

## Where did we come from?

A brief history of the field of computer vision.

<!-- DIAGRAM: Timeline of major milestones (Hubel & Wiesel, Roberts, Marr, etc.) to be expanded later. -->

---

## Hubel and Wiesel, 1959

![Hubel & Wiesel experiments](assets/hubel_wiesel_diagram.png)

- Simple cells: respond to specific rotation and orientation
- Complex cells: respond to light orientation and movement, some translation invariance

1959: Hubel & Wiesel discovered the hierarchical organization of visual cortex.

<!-- DIAGRAM: Diagram showing recording electrode in cat visual cortex, stimuli (bar orientations), and response curves. -->

---

## Larry Roberts, 1963

![Roberts' edge detection](assets/roberts_edge_detection.png)

1963: Larry Roberts published "Machine Perception of Three-Dimensional Solids".

<!-- DIAGRAM: Original image, differentiated image, feature points selected (as in the paper). -->

---

## David Marr, 1970s

![Marr's stages of visual representation](assets/marr_stages.png)

David Marr proposed a computational framework for vision:
- Input image → Primal Sketch → 2½-D Sketch → 3-D Model

<!-- DIAGRAM: Flowchart with images representing each stage. -->

---

## Recognition via Parts (1970s)

![Generalized cylinders and pictorial structures](assets/recognition_parts.png)

- Generalized Cylinders (Brooks & Binford, 1979)
- Pictorial Structures (Fischler & Elshlager, 1973)

<!-- DIAGRAM: Examples of generalized cylinders and pictorial structures (stick figures). -->

---

## Recognition via Edge Detection (1980s)

![Canny and Lowe edge detection](assets/edge_detection.png)

- John Canny (1986) – edge detection
- David Lowe (1987) – object recognition

<!-- DIAGRAM: Sample image with edges detected using Canny; comparison of different edge detectors. -->

---

## Arriving at an “AI winter”

- Enthusiasm (and funding!) for AI research dwindled
- "Expert Systems" failed to deliver on their promises
- But subfields of AI continued to grow:
  - Computer vision, NLP, robotics, computational biology, etc.

<!-- DIAGRAM: Graph of funding over time with a dip labeled "AI Winter". -->

---

## In the meantime… seminal work in cognitive and neuroscience

Cognitive neuroscience provided critical insights into human visual recognition.

<!-- DIAGRAM: Brain images (fMRI) or schematic of visual pathways. -->

---

## I. Biederman, Science, 1972

Biederman's work on recognition-by-components.

<!-- DIAGRAM: Recognition-by-components (geons) examples. -->

---

## Rapid Serial Visual Perception (RSVP) – Potter, 1970s

Experiments showing the speed of human visual recognition.

<!-- DIAGRAM: RSVP paradigm: series of images shown rapidly with time axis. -->

---

## Thorpe et al., Nature, 1996 – 150 ms !!

Human brain can identify images in just 150 milliseconds.

<!-- DIAGRAM: Reaction time graph showing 150 ms. -->

---

## Neural correlates of object & scene recognition

- Kanwisher et al., J. Neuro., 1997 – Fusiform Face Area (FFA)
- Epstein & Kanwisher, Nature, 1998 – Parahippocampal Place Area (PPA)

<!-- DIAGRAM: Brain diagram highlighting FFA and PPA. -->

---

## Visual recognition is a fundamental task for visual intelligence

Recognition is central to all visual tasks.

---

## Recognition via Grouping (1990s)

Normalized Cuts – Shi and Malik, 1997.

<!-- DIAGRAM: Image segmentation example using normalized cuts. -->

---

## Recognition via Matching (2000s)

- SIFT – David Lowe, 1999
- Viola & Jones face detection, 2001

<!-- DIAGRAM: SIFT keypoint matching example; Viola-Jones face detection results. -->

---

## Perceptron (1958)

Frank Rosenblatt, ~1957.

<!-- DIAGRAM: Perceptron diagram: input vector, weights, summation, threshold. -->

---

## Minsky and Papert, 1969

Showed that Perceptrons could not learn the XOR function, causing disillusionment.

<!-- DIAGRAM: XOR truth table and decision boundary plot showing linear separability. -->
$$
\text{XOR: } \begin{array}{cc|c}
x_1 & x_2 & y \\
0 & 0 & 0 \\
0 & 1 & 1 \\
1 & 0 & 1 \\
1 & 1 & 0
\end{array}
$$
<!-- Typst alternative: `#table(columns: 3, ...)` -->

---

## Neocognitron: Fukushima, 1980

Computational model inspired by Hubel and Wiesel; had no practical training algorithm.

<!-- DIAGRAM: Neocognitron architecture (layers of S-cells and C-cells). -->

---

## Backprop: Rumelhart, Hinton, and Williams, 1986

Introduced backpropagation for computing gradients in neural networks.

<!-- DIAGRAM: Neural network with backprop arrows showing error flow. -->
$$
\text{Backpropagation: } \delta^{(l)} = \left( (w^{(l+1)})^T \delta^{(l+1)} \right) \odot f'(z^{(l)})
$$
<!-- Typst alternative: `$ delta^(l) = ((w^(l+1))^T delta^(l+1)) odot f'(z^(l)) $` -->

---

## Convolutional Networks: LeCun et al., 1998

LeNet-5 applied backprop to a Neocognitron-like architecture; used for handwritten digit recognition.

<!-- DIAGRAM: LeNet-5 architecture (convolutional layers, pooling, fully connected). -->

---

## 2000s: “Deep Learning”

Researchers tried to train deeper networks but it was not mainstream yet.

- Hinton and Salakhutdinov, 2006
- Bengio et al., 2007
- Lee et al., 2009
- Glorot and Bengio, 2010

No good dataset available until ImageNet.

---

## ImageNet (2009)

- 15M images, 22k categories (Deng et al., Fei-Fei, CVPR 2009)
- SUN, LabelMe, PASCAL VOC, Caltech101 also contributed.

<!-- DIAGRAM: Logos or thumbnails of each dataset. -->

---

## ImageNet Challenge

1,000 object classes, 1,431,167 images.

<!-- DIAGRAM: Sample images from ImageNet classes (dog, cat, etc.). -->

---

## AlexNet, 2012

AlexNet wins ImageNet challenge with deep CNN, sparking the deep learning revolution.

<!-- DIAGRAM: AlexNet architecture diagram (8 layers, ReLU, dropout, etc.). -->

---

## 2012 to Present: Deep Learning Explosion

Publications at top CV conference have skyrocketed.

- Submitted papers: from ~2000 to over 14,000
- Accepted papers: from ~500 to over 3000

<!-- DIAGRAM: Line chart showing submitted/accepted papers over years. -->

---

## 2012 to Present: Deep Learning is Everywhere

- AlexNet (2012) → ResNet (2015) → Vision Transformer (2021) → Diffusion Transformer (2023)

Image classification to image generation.

<!-- DIAGRAM: Timeline of major models with mini architectures. -->

---

## Object Detection and Segmentation

- Faster R-CNN (Ren et al., NeurIPS 2016)
- Segment Anything (Kirillov et al., ICCV 2023)

<!-- DIAGRAM: Example outputs of object detection and segmentation. -->

---

## Video Understanding and Activity Recognition

Recent works on video and activity recognition.

<!-- DIAGRAM: Example frames from video with action labels. -->

---

## Human Mesh Reconstruction, Game Playing

Deep learning applied to human pose estimation and game playing (AlphaGo/AlphaZero).

<!-- DIAGRAM: Human mesh reconstruction output; AlphaGo board. -->

---

## Image Captioning

Early captioning (Vinyals et al., Karpathy & Fei-Fei, 2015) vs. modern detailed captioning (Gemini 3, 2026).

<!-- DIAGRAM: Side-by-side comparison of old vs. new captions for same image. -->

---

## DL in Science and Medicine

Medical imaging, galaxy classification, protein folding (AlphaFold).

<!-- DIAGRAM: Examples: medical scan, galaxy image, protein structure. -->

---

## Generative Models

GANs, DALL·E, and other generative models.

<!-- DIAGRAM: GAN architecture or sample generated images. -->

---

## AI’s Explosive Growth & Impact

- Startups developing AI systems
- Enterprise AI revenue
- Attendance at AI conferences

<!-- DIAGRAM: Three bar charts or growth curves. -->

---

## Despite the successes, computer vision still has a long way to go

Challenges remain in robustness, generalization, and reasoning.

<!-- DIAGRAM: Visual examples of CV failures (e.g., adversarial examples). -->

---

## Data is critical for Deep Learning algorithms

Understanding, reasoning, and generation are key to visual intelligence.

<!-- DIAGRAM: Triangle with "Data", "Algorithms", "Computation" or "Understanding", "Reasoning", "Generation". -->

---

## Computer Vision Can Cause Harm

- Harmful stereotypes in hiring algorithms
- Affect people's lives

<!-- DIAGRAM: Example of biased AI output. -->

---

## Computer Vision Can Save Lives

Applications in healthcare: intensive care, patient monitoring, senior care, mental health.

<!-- DIAGRAM: Collage of healthcare applications. -->

---

## Spatial Intelligence

Catalyzing a virtuous cycle of seeing, learning, and doing.

<!-- DIAGRAM: Cycle diagram: Seeing → Learning → Doing → (back to Seeing). -->

---

## World Modeling

Input → 3D reconstruction → output; representing the world.

<!-- DIAGRAM: Input image → 3D model → rendered novel views. -->

---

## And there is a lot we don’t know how to do

Humans can easily perform tasks that remain difficult for machines.

<!-- DIAGRAM: Example of a task easy for humans but hard for AI (e.g., understanding a messy scene). -->

---

## Today’s Agenda (recap)

- A brief history of computer vision & deep learning
- CS231n overview

<!-- DIAGRAM: Summary diagram of topics covered. -->

<!--
EQUATION SUMMARY:
- XOR truth table (Minsky & Papert)
- Backpropagation gradient formula
- Possibly convolution definition if needed.
-->
