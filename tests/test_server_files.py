"""
Tests for the input-file lifecycle on the model server.

Files pushed by /load-files are read once, by the inference request that follows, and nothing else
removes them -- so a leak here fills the node's disk and evicts unrelated pods.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "mdai"))
os.environ.setdefault("MDAI_PATH", ".mdai")

from mdai import server  # noqa: E402


@pytest.fixture
def data_path(tmp_path, monkeypatch):
    path = str(tmp_path / "mdai-data")
    os.makedirs(path)
    monkeypatch.setattr(server, "DATA_PATH", path)
    return path


def _write(data_path, relative):
    path = os.path.join(data_path, relative)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"pixels")
    return path


class TestInputFilePaths:
    def test_flat_list(self):
        files = [{"content_path": "/a"}, {"content_path": "/b"}]
        assert server._input_file_paths(files) == ["/a", "/b"]

    def test_grouped(self):
        files = [[{"content_path": "/a"}], [{"content_path": "/b"}, {"content_path": "/c"}]]
        assert server._input_file_paths(files) == ["/a", "/b", "/c"]

    def test_ignores_in_memory_files(self):
        files = [{"content": b"x", "content_path": None}, {"content_path": "/b"}]
        assert server._input_file_paths(files) == ["/b"]

    def test_empty(self):
        assert server._input_file_paths([]) == []


class TestRemoveInputFiles:
    def test_removes_files_and_empty_directories(self, data_path):
        a = _write(data_path, "env/1/study/series/a.dcm")
        b = _write(data_path, "env/1/study/series/b.dcm")

        server._remove_input_files([a, b])

        assert not os.path.exists(a)
        assert not os.path.exists(b)
        # The whole branch is gone, but DATA_PATH itself survives for the next request.
        assert not os.path.exists(os.path.join(data_path, "env"))
        assert os.path.isdir(data_path)

    def test_keeps_directories_that_still_hold_files(self, data_path):
        a = _write(data_path, "env/1/study/series/a.dcm")
        keep = _write(data_path, "env/1/study/series/keep.dcm")

        server._remove_input_files([a])

        assert not os.path.exists(a)
        assert os.path.exists(keep)

    def test_missing_file_is_not_an_error(self, data_path):
        server._remove_input_files([os.path.join(data_path, "gone.dcm")])

    def test_does_not_climb_out_of_data_path(self, data_path):
        outside = os.path.dirname(data_path)
        a = _write(data_path, "env/a.dcm")

        server._remove_input_files([a])

        assert os.path.isdir(outside)
        assert os.path.isdir(data_path)


class TestClearDataPath:
    def test_empties_a_populated_directory(self, data_path):
        _write(data_path, "env/1/study/series/a.dcm")

        server._clear_data_path()

        assert os.path.isdir(data_path)
        assert os.listdir(data_path) == []

    def test_creates_the_directory_when_absent(self, tmp_path, monkeypatch):
        path = str(tmp_path / "absent")
        monkeypatch.setattr(server, "DATA_PATH", path)

        server._clear_data_path()

        assert os.path.isdir(path)


class TestResolveContentPath:
    def test_rejects_traversal(self, data_path):
        with pytest.raises(ValueError):
            server._resolve_content_path("../../etc/passwd")

    def test_resolves_within_data_path(self, data_path):
        assert server._resolve_content_path("env/1/a.dcm") == os.path.join(
            data_path, "env/1/a.dcm"
        )
