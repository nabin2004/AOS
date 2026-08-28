---
footer: AOS Manim Slides
---

---
layout: title
title: Iterative Methods
subtitle: Gradient descent, Newton, and search
author: AOS Manim
date: 2026
---

# Iterative Methods

---
layout: section
section_number: 1
title: Optimization
subtitle: First-order and second-order updates
---

# Optimization

---
layout: two-column
title: Gradient Descent
---

# Gradient Descent

We want to minimize a differentiable objective.

$$
f(x) = x^2
$$

The update follows the negative gradient:

$$
x_{n+1} = x_n - \eta \nabla f(x_n)
$$

```diagram
gradient_descent(f=x**2, x=1.5)
```

> Move in the direction of the negative gradient.

---
layout: equation-focus
title: Newton's Method
---

# Newton's Method

Newton's method iteratively improves an estimate of a root.

$$
x_{n+1}=x_n-\frac{f(x_n)}{f'(x_n)}
$$

For a square root of two, solve \( f(x) = x^2 - 2 \).

---
layout: diagram-focus
title: Newton on x^2 - 2
voiceover: |
  Watch Newton on x squared minus two.
  <bookmark mark='d0'/>Start from the curve and the initial guess.
  <bookmark mark='d0s0'/>Each tangent hits the axis at the next iterate.
---

# Newton on x^2 - 2

:::diagram
newton_method(f=x**2-2, x0=1.5)
:::

Each tangent hits the axis at the next iterate.

---
layout: title-content
title: Chain Rule
voiceover: |
  The chain rule composes linear maps.
  <bookmark mark='eq0'/>The derivative of a composition is the product of the two derivatives.
  <bookmark mark='li0'/>Evaluate the outer derivative at the inner value.
  <bookmark mark='li1'/>The inner derivative scales the infinitesimal.
---

# Chain Rule

If \( y = f(g(x)) \), differentiation composes linear maps:

$$
\frac{dy}{dx} = f'(g(x))\, g'(x)
$$

- Outer derivative evaluated at the inner value
- Inner derivative scales the infinitesimal

---
layout: code-focus
title: Binary Search
---

# Binary Search

Halve a sorted range until the target is found.

```python
def binary_search(arr, target):
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        if arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
```

```diagram
binary_search(arr=[1,3,4,7,9,11,15], target=7)
```
