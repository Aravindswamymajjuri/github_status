import csv
import io
import sys
from copy import deepcopy
from pathlib import Path
from types import ModuleType, SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class _SessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


class _DummyContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _DummyProgress:
    def progress(self, _value):
        return None


def _identity_decorator(*args, **kwargs):
    if args and callable(args[0]) and len(args) == 1 and not kwargs:
        return args[0]

    def _decorator(func):
        return func

    return _decorator


def _build_streamlit_stub():
    st_mod = ModuleType("streamlit")
    st_mod.session_state = _SessionState()

    def _columns(spec):
        if isinstance(spec, int):
            count = spec
        else:
            count = len(spec)
        return [_DummyContext() for _ in range(count)]

    def _tabs(items):
        return [_DummyContext() for _ in items]

    def _selectbox(_label, options, index=0, **_kwargs):
        if not options:
            return None
        return options[index]

    def _radio(_label, options, index=0, **_kwargs):
        if not options:
            return None
        return options[index]

    def _text_input(_label, value="", **_kwargs):
        return value

    def _date_input(_label, value=None, **_kwargs):
        return value

    st_mod.cache_data = _identity_decorator
    st_mod.dialog = _identity_decorator
    st_mod.set_page_config = lambda **_kwargs: None
    st_mod.columns = _columns
    st_mod.tabs = _tabs
    st_mod.selectbox = _selectbox
    st_mod.radio = _radio
    st_mod.text_input = _text_input
    st_mod.text_area = _text_input
    st_mod.date_input = _date_input
    st_mod.button = lambda *_args, **_kwargs: False
    st_mod.spinner = lambda *_args, **_kwargs: _DummyContext()
    st_mod.container = lambda *_args, **_kwargs: _DummyContext()
    st_mod.expander = lambda *_args, **_kwargs: _DummyContext()
    st_mod.progress = lambda *_args, **_kwargs: _DummyProgress()
    st_mod.download_button = lambda *_args, **_kwargs: None
    st_mod.plotly_chart = lambda *_args, **_kwargs: None
    st_mod.dataframe = lambda *_args, **_kwargs: None
    st_mod.metric = lambda *_args, **_kwargs: None
    st_mod.markdown = lambda *_args, **_kwargs: None
    st_mod.write = lambda *_args, **_kwargs: None
    st_mod.caption = lambda *_args, **_kwargs: None
    st_mod.success = lambda *_args, **_kwargs: None
    st_mod.error = lambda *_args, **_kwargs: None
    st_mod.info = lambda *_args, **_kwargs: None
    st_mod.warning = lambda *_args, **_kwargs: None
    st_mod.subheader = lambda *_args, **_kwargs: None
    st_mod.title = lambda *_args, **_kwargs: None
    st_mod.image = lambda *_args, **_kwargs: None
    st_mod.rerun = lambda *_args, **_kwargs: None
    st_mod.stop = lambda *_args, **_kwargs: None

    sidebar = SimpleNamespace(
        header=lambda *_args, **_kwargs: None,
        text_input=_text_input,
        radio=_radio,
        markdown=lambda *_args, **_kwargs: None,
        info=lambda *_args, **_kwargs: None,
    )
    st_mod.sidebar = sidebar
    return st_mod


class _FakeDataFrame:
    def __init__(self, rows=None):
        if rows is None:
            rows = []
        if isinstance(rows, dict):
            keys = list(rows.keys())
            length = len(rows[keys[0]]) if keys else 0
            self._rows = [{k: rows[k][i] for k in keys} for i in range(length)]
        else:
            self._rows = list(rows)
        self.columns = []
        for row in self._rows:
            if isinstance(row, dict):
                for key in row.keys():
                    if key not in self.columns:
                        self.columns.append(key)

    def iterrows(self):
        for idx, row in enumerate(self._rows):
            yield idx, row

    def copy(self):
        return _FakeDataFrame(deepcopy(self._rows))

    def to_csv(self, path, index=False):
        output_keys = list(self.columns)
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=output_keys)
            writer.writeheader()
            for row in self._rows:
                writer.writerow(row)

    def to_excel(self, *_args, **_kwargs):
        return None

    def __len__(self):
        return len(self._rows)


class _FakeExcelWriter:
    def __init__(self, *_args, **_kwargs):
        self.buffer = io.BytesIO()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _fake_read_csv(path):
    with open(path, "r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return _FakeDataFrame(list(reader))


def _build_pandas_stub():
    pd_mod = ModuleType("pandas")
    pd_mod.DataFrame = _FakeDataFrame
    pd_mod.ExcelWriter = _FakeExcelWriter
    pd_mod.read_csv = _fake_read_csv
    return pd_mod


def _build_plotly_stub():
    plotly_mod = ModuleType("plotly")
    go_mod = ModuleType("plotly.graph_objects")

    class Pie:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class Figure:
        def __init__(self, data=None):
            self.data = data or []
            self.layout = {}

        def update_layout(self, **kwargs):
            self.layout.update(kwargs)

    go_mod.Pie = Pie
    go_mod.Figure = Figure
    plotly_mod.graph_objects = go_mod
    return plotly_mod, go_mod


def _build_gitlab_stub():
    gitlab_mod = ModuleType("gitlab")

    class GitlabAuthenticationError(Exception):
        pass

    class GitlabConnectionError(Exception):
        pass

    class GitlabGetError(Exception):
        def __init__(self, *args, response=None):
            super().__init__(*args)
            self.response = response

    class Gitlab:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def auth(self):
            return None

    gitlab_mod.Gitlab = Gitlab
    gitlab_mod.GitlabGetError = GitlabGetError
    gitlab_mod.exceptions = SimpleNamespace(
        GitlabAuthenticationError=GitlabAuthenticationError,
        GitlabConnectionError=GitlabConnectionError,
    )
    return gitlab_mod


if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = _build_streamlit_stub()

if "pandas" not in sys.modules:
    sys.modules["pandas"] = _build_pandas_stub()

if "plotly" not in sys.modules or "plotly.graph_objects" not in sys.modules:
    plotly_stub, go_stub = _build_plotly_stub()
    sys.modules["plotly"] = plotly_stub
    sys.modules["plotly.graph_objects"] = go_stub

if "gitlab" not in sys.modules:
    sys.modules["gitlab"] = _build_gitlab_stub()
