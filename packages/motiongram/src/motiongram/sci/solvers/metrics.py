"""Derived metrics calculator (e.g. Euclidean distance for chaotic divergence)."""

from __future__ import annotations

import hashlib
import json

import numpy as np

from motiongram.sci.schema import DataSourceSpec
from motiongram.sci.solvers.base import DataResult, DataSource
from motiongram.sci.solvers.cache import load_cached_result, save_cached_result


class DerivedMetric(DataSource):
    """Calculates derived metrics from one or more upstream data results."""

    def cache_key(
        self,
        spec: DataSourceSpec,
        quality: str = "final",
        input_results: dict[str, DataResult] | None = None,
    ) -> str:
        """Calculate deterministic cache key for derived metric."""
        inputs_summary = {}
        if input_results:
            for inp in spec.inputs:
                res = input_results.get(inp)
                if res is not None:
                    inputs_summary[inp] = {
                        "count": len(res.points),
                        "first": res.points[0].tolist() if len(res.points) > 0 else [],
                        "last": res.points[-1].tolist() if len(res.points) > 0 else [],
                    }
        payload = {
            "source": spec.source,
            "operation": spec.operation,
            "inputs": spec.inputs,
            "inputs_summary": inputs_summary,
            "quality": quality,
        }
        raw_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(raw_bytes).hexdigest()

    def solve(
        self,
        spec: DataSourceSpec,
        quality: str = "final",
        input_results: dict[str, DataResult] | None = None,
    ) -> DataResult:
        """Compute derived metric from upstream data results."""
        key = self.cache_key(spec, quality, input_results=input_results)
        cached = load_cached_result(key)
        if cached is not None:
            return cached


        if not input_results:
            raise ValueError(f"Input results required to compute derived metric '{spec.id}'.")

        if spec.operation == "euclidean_distance":
            if len(spec.inputs) < 2:
                raise ValueError("Euclidean distance requires at least 2 input datasets.")
            res_a = input_results.get(spec.inputs[0])
            res_b = input_results.get(spec.inputs[1])
            if not res_a or not res_b:
                raise ValueError(
                    f"Inputs '{spec.inputs[0]}' and '{spec.inputs[1]}' must be computed first."
                )

            pts_a = res_a.points
            pts_b = res_b.points
            min_len = min(len(pts_a), len(pts_b))
            diff = pts_a[:min_len] - pts_b[:min_len]
            distances = np.linalg.norm(diff, axis=1)

            t = res_a.time[:min_len] if res_a.time is not None else np.arange(min_len)
            # Store as (N, 3): [t, distance, 0] for plotting
            metric_pts = np.column_stack([t, distances, np.zeros_like(distances)])

            result = DataResult(
                points=metric_pts,
                time=t,
                metadata={
                    "operation": "euclidean_distance",
                    "max_distance": float(np.max(distances)),
                    "final_distance": float(distances[-1]),
                },
                status="success",
            )
            result.validate()
            save_cached_result(key, result)
            return result

        raise ValueError(f"Unsupported metric operation: '{spec.operation}'")
