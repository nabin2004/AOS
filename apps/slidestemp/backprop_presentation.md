---
title: "The Learning Paradigm"
layout: "title-content"
voiceover: "In deep learning, neural networks act as universal function approximators. <bookmark mark='h0'/> Today we will uncover how they learn. <bookmark mark='li0'/> First, signals propagate forward to generate predictions. <bookmark mark='li1'/> Next, a loss function computes the exact penalty for mistakes. <bookmark mark='li2'/> Finally, the optimizer updates internal weights to minimize future error."
---

# How Machines Learn

- Neural networks map high-dimensional inputs to target outputs.
- A loss function measures the discrepancy between prediction and reality.
- Optimization algorithms adjust internal parameters to minimize error.

---
title: "Optimization Landscape"
layout: "title-content"
voiceover: "Imagine standing on a foggy hillside. <bookmark mark='h0'/> That hill is our loss surface. <bookmark mark='li0'/> The loss represents the height of the mountain we must descend. <bookmark mark='li1'/> The gradient tells us the steepest uphill slope under our feet. <bookmark mark='li2'/> By taking controlled steps in the exact opposite direction, we reach the optimal valley."
---

# Navigating the Loss Surface

- The loss surface is a high-dimensional mathematical landscape.
- The gradient vector points in the direction of steepest ascent.
- We take negative gradient steps scaled by the learning rate.

---
title: "Credit Assignment"
layout: "title-content"
voiceover: "How do we know which specific weight caused the mistake? <bookmark mark='h0'/> Calculus gives us the answer through the chain rule. <bookmark mark='li0'/> Because neural networks are compositions of functions, derivatives multiply backwards. <bookmark mark='li1'/> Each layer passes gradients to the previous layer recursively. <bookmark mark='li2'/> This allows every single neuron to receive credit proportional to its influence."
---

# The Chain Rule of Calculus

- Deep networks compose thousands of consecutive mathematical operations.
- Derivatives decompose composite functions via the chain rule.
- Every weight receives credit proportional to its downstream impact.

---
title: "The Feynman Approach"
layout: "title-content"
voiceover: "As the legendary physicist Richard Feynman once reminded us. <bookmark mark='h0'/> Genuine mastery requires genuine curiosity. <bookmark mark='li0'/> Study what interests you with an open and irreverent mind. <bookmark mark='li1'/> Build mental models from ground truth rather than memorizing formulas. <bookmark mark='li2'/> When you understand backpropagation from first principles, modern AI becomes completely transparent."
---

# First-Principles Understanding

- "Study what interests you in the most undisciplined, irreverent manner possible."
- True intuition comes from building mathematical concepts from scratch.
- Never mistake computational complexity for conceptual understanding.

---
layout: "section"
title: "Summary & Next Steps"
voiceover: "That concludes our conceptual foundation of backpropagation. In our upcoming session, we will derive the exact matrix equations and write the backward pass in pure Python."
---
