"""Tests for the OOP animation pipeline architecture."""

from __future__ import annotations

import pytest
from pydantic_graph import BaseNode, Graph

from animation_pipeline import (
    AnimationGraphBuilder,
    AnimationPipelineAgent,
    AnimationPipelineRunner,
    AnimationState,
    BaseAnimationNode,
    ClassifyNode,
    CodeAgentNode,
    PipelineArtifactManager,
    PipelineResult,
    PlanLectureNode,
    PlanTeachingScriptNode,
    animation_agent,
    animation_graph,
    run_pipeline,
)
import agent_graph


def test_oop_hierarchy():
    """Verify that all pipeline nodes adhere to OOP inheritance and mixins."""
    nodes = [ClassifyNode, PlanLectureNode, PlanTeachingScriptNode, CodeAgentNode]
    for node_cls in nodes:
        assert issubclass(node_cls, BaseNode), f"{node_cls} must subclass BaseNode"
        assert issubclass(node_cls, BaseAnimationNode), f"{node_cls} must subclass BaseAnimationNode"


def test_builder_constructs_valid_graph():
    """Verify that AnimationGraphBuilder produces a correctly structured graph."""
    builder = AnimationGraphBuilder(name="Test Graph")
    graph = builder.build()
    assert isinstance(graph, Graph)
    assert graph.name == "Test Graph"
    assert "ClassifyNode" in graph.nodes
    assert "PlanLectureNode" in graph.nodes
    assert "PlanTeachingScriptNode" in graph.nodes
    assert "CodeAgentNode" in graph.nodes


def test_artifact_manager_initialization(tmp_path):
    """Verify PipelineArtifactManager encapsulation."""
    manager = PipelineArtifactManager()
    found = manager.find_compiled_video(tmp_path)
    assert found is None


def test_runner_initialization():
    """Verify AnimationPipelineRunner initializes with custom or default graph."""
    runner = AnimationPipelineRunner()
    assert runner.graph is not None
    assert runner.artifact_manager is not None


def test_agent_initialization():
    """Verify AnimationPipelineAgent wraps the Pydantic AI agent and tools."""
    agent_wrapper = AnimationPipelineAgent()
    assert agent_wrapper.agent is not None
    assert agent_wrapper.agent.name == "Manim Animation Pipeline"
    assert hasattr(agent_wrapper.agent, "run")
    assert agent_wrapper.runner is not None


def test_facade_backward_compatibility():
    """Verify agent_graph facade re-exports all expected interfaces seamlessly."""
    assert agent_graph.animation_graph is animation_graph
    assert agent_graph.animation_agent is animation_agent
    assert agent_graph.AnimationState is AnimationState
    assert agent_graph.PipelineResult is PipelineResult
    assert agent_graph.run_pipeline is not None
    assert agent_graph.ClassifyNode is ClassifyNode
    assert agent_graph.CodeAgent is CodeAgentNode
