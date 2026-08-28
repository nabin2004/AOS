# aos-manim-physics

STEM physics simulation and computational visualization plugin for AOS Manim.

## Features
- **Kinematics**: `ProjectileVisualizer` (parabolic trajectories, flight time, launch vectors, peak/landing markers).
- **Dynamics**: `FreeBodyDiagram` (vector force balancing, net acceleration), `PendulumVisualizer` (exact non-linear ODE integration with SciPy `solve_ivp`).
- **Validators**: `EnergyConservationValidator` to verify physical energy conservation across ODE time steps.
