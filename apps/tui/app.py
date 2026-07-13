"""AOS TUI: browse, search, and play saved lectures/courses.

Run with: uv run --package tui python apps/tui/app.py
"""
import webbrowser

import store
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import DataTable, Footer, Header, Input, TabbedContent, TabPane

LECTURE_COLUMNS = ("id", "topic", "subject", "duration (min)", "course", "created_at")
COURSE_COLUMNS = ("id", "topic", "subject", "duration (min)", "episodes", "created_at")


def _lecture_row(r) -> tuple:
    return (r.id, r.topic, r.subject, f"{r.duration_minutes:.0f}", r.course_id or "-", r.created_at)


def _course_row(r) -> tuple:
    return (r.id, r.topic, r.subject, f"{r.duration_minutes:.0f}", str(r.total_episodes), r.created_at)


class AOSApp(App):
    """Browse/search/play AOS lectures and courses."""

    CSS = """
    Input { margin: 0 1; }
    DataTable { height: 1fr; }
    """

    BINDINGS = [
        Binding("l", "show_tab('lectures-tab')", "Lectures"),
        Binding("c", "show_tab('courses-tab')", "Courses"),
        Binding("/", "focus_search", "Search"),
        Binding("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(initial="lectures-tab"):
            with TabPane("Lectures", id="lectures-tab"):
                with Vertical():
                    yield Input(placeholder="Search lectures...", id="lectures-search")
                    yield DataTable(id="lectures-table", cursor_type="row")
            with TabPane("Courses", id="courses-tab"):
                with Vertical():
                    yield Input(placeholder="Search courses...", id="courses-search")
                    yield DataTable(id="courses-table", cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
        lectures_table = self.query_one("#lectures-table", DataTable)
        lectures_table.add_columns(*LECTURE_COLUMNS)
        courses_table = self.query_one("#courses-table", DataTable)
        courses_table.add_columns(*COURSE_COLUMNS)
        self._refresh_lectures()
        self._refresh_courses()

    def _refresh_lectures(self, query: str = "") -> None:
        table = self.query_one("#lectures-table", DataTable)
        table.clear()
        records = store.search_lectures(query) if query else store.list_lectures()
        for r in records:
            table.add_row(*_lecture_row(r), key=r.id)

    def _refresh_courses(self, query: str = "") -> None:
        table = self.query_one("#courses-table", DataTable)
        table.clear()
        records = store.search_courses(query) if query else store.list_courses()
        for r in records:
            table.add_row(*_course_row(r), key=r.id)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "lectures-search":
            self._refresh_lectures(event.value)
        elif event.input.id == "courses-search":
            self._refresh_courses(event.value)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        item_id = event.row_key.value
        if item_id is None:
            return
        self._play(item_id)

    def _play(self, item_id: str) -> None:
        result = store.resolve(item_id)
        if result is None:
            self.notify(f"No lecture/course matches '{item_id}'", severity="error")
            return
        kind, record = result
        if kind == "lecture":
            path = store.render_lecture_player(record)
        else:
            episodes = [store.load_lecture(eid) for eid in record.episode_ids]
            path = store.render_course_player(record, [e for e in episodes if e is not None])
        webbrowser.open(path.resolve().as_uri())
        self.notify(f"Opened {path.name}")

    def action_show_tab(self, tab_id: str) -> None:
        self.query_one(TabbedContent).active = tab_id

    def action_focus_search(self) -> None:
        active = self.query_one(TabbedContent).active
        search_id = "lectures-search" if active == "lectures-tab" else "courses-search"
        self.query_one(f"#{search_id}", Input).focus()


def main() -> None:
    AOSApp().run()


if __name__ == "__main__":
    main()
