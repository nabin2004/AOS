from uuid import uuid4
import pytest
from pydantic import ValidationError

from educlaw.animateworkflow.contracts import Audience
from educlaw.courses.contracts import (
    Course,
    CourseManifest,
    CourseSyllabus,
    GenerationMode,
    Lecture,
    LectureSpec,
    RenderStatus,
    VisualGrammar,
    slugify,
)
from educlaw.courses.storage import (
    build_manifest,
    export_course_handbook,
    generate_syllabus_markdown,
    list_courses,
    load_course,
    save_course,
)


def test_slugify():
    assert slugify("Linear Algebra 101: Vectors & Matrices!") == "linear-algebra-101-vectors-matrices"
    assert slugify("  --- Special  Characters $$$ --- ") == "special-characters"
    assert slugify("") == "course"


def test_course_syllabus_validation_and_numbering():
    syllabus = CourseSyllabus(
        title="Differential Geometry",
        topic="Manifolds and Tensors",
        subject="Mathematics",
        target_audience=Audience.EXPLORING,
        overview="A visual journey into curved spaces.",
        learning_outcomes=["Understand manifolds", "Calculate metric tensors"],
        lectures=[
            LectureSpec(
                lecture_number=99,  # Should be normalized to 1
                title="Introduction to Smooth Manifolds",
                description="What is a manifold and why do we care?",
                key_concepts=["Charts", "Atlases", "Smoothness"],
            ),
            LectureSpec(
                lecture_number=99,  # Should be normalized to 2
                title="Tangent Spaces and Differential Forms",
                description="Vectors on curved surfaces.",
                key_concepts=["Tangent vectors", "Cotangent space"],
            ),
        ],
    )

    assert syllabus.slug == "differential-geometry"
    assert syllabus.lectures[0].lecture_number == 1
    assert syllabus.lectures[1].lecture_number == 2


def test_course_creation_and_progress_summary():
    syllabus = CourseSyllabus(
        title="Quantum Mechanics",
        topic="Schrodinger equation",
        subject="Physics",
        overview="Quantum intuition from wave mechanics to operators.",
        lectures=[
            LectureSpec(
                lecture_number=1,
                title="Wave-Particle Duality",
                description="From double slits to de Broglie waves.",
                key_concepts=["Wavefunctions", "Interference"],
            ),
            LectureSpec(
                lecture_number=2,
                title="Schrodinger Wave Equation",
                description="Time-dependent and independent forms.",
                key_concepts=["Hamiltonian", "Eigenstates"],
            ),
        ],
    )

    course = Course.from_syllabus(syllabus)
    assert len(course.lectures) == 2
    assert course.lectures[0].status == RenderStatus.PENDING
    assert course.progress_summary["pending"] == 2
    assert course.progress_summary["rendered"] == 0

    # Test get_lecture
    lec1 = course.get_lecture(1)
    assert lec1 is not None
    assert lec1.spec.title == "Wave-Particle Duality"
    assert course.get_lecture(99) is None


def test_storage_save_load_list_and_export(tmp_path):
    syllabus = CourseSyllabus(
        title="Machine Learning Foundations",
        topic="Gradient Descent & Backprop",
        subject="Computer Science",
        overview="Visualizing optimization in parameter space.",
        learning_outcomes=["Derive gradient descent", "Visualize loss surfaces"],
        lectures=[
            LectureSpec(
                lecture_number=1,
                title="Loss Surfaces & Gradients",
                description="Navigating high-dimensional terrain.",
                key_concepts=["Gradient vector", "Learning rate"],
            ),
            LectureSpec(
                lecture_number=2,
                title="Backpropagation Visualized",
                description="Reverse-mode automatic differentiation.",
                key_concepts=["Chain rule", "Computational graph"],
            ),
        ],
    )
    course = Course.from_syllabus(syllabus, workspace_dir=tmp_path)
    course.lectures[0].study_notes = "## Notes for Lecture 1\nGradient descent formula: $\\theta_{t+1} = \\theta_t - \\eta \\nabla L$"

    saved_dir = save_course(course, workspace_dir=tmp_path)
    assert saved_dir.exists()
    assert (saved_dir / "course.json").exists()
    assert (saved_dir / "course_manifest.json").exists()
    assert (saved_dir / "syllabus.md").exists()
    assert (saved_dir / "lecture_01" / "notes.md").exists()

    # Test load
    loaded = load_course(course.slug, workspace_dir=tmp_path)
    assert loaded is not None
    assert loaded.title == course.title
    assert len(loaded.lectures) == 2
    assert loaded.lectures[0].study_notes is not None

    # Test list
    manifests = list_courses(workspace_dir=tmp_path)
    assert len(manifests) == 1
    assert manifests[0].slug == "machine-learning-foundations"
    assert manifests[0].total_lectures == 2

    # Test export handbook
    handbook_file = tmp_path / "handbook.md"
    export_course_handbook(loaded, output_file=handbook_file)
    assert handbook_file.exists()
    content = handbook_file.read_text(encoding="utf-8")
    assert "Machine Learning Foundations" in content
    assert "Gradient descent formula" in content
