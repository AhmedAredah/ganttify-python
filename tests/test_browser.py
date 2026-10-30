"""Browser delivery must outlive asynchronous launch and close on failure."""

import os
import subprocess
import sys
import time
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import pytest

import ganttify
from ganttify import _browser


def test_browser_can_read_html_synchronously(monkeypatch):
    received = []

    def launch(url):
        with urlopen(url, timeout=2) as response:
            received.append((response.read().decode(), response.headers["Cache-Control"]))
        return True

    monkeypatch.setattr(_browser.webbrowser, "open", launch)
    _browser.open_html_in_browser("<p>Schedule 🚢</p>", timeout=2)
    assert received == [("<p>Schedule 🚢</p>", "no-store")]


def test_delayed_browser_receives_page_before_display_returns(monkeypatch):
    received = []
    readers = []

    def launch(url):
        def read_later():
            time.sleep(0.1)
            with urlopen(url, timeout=2) as response:
                received.append(response.read())

        readers.append(Thread(target=read_later))
        readers[-1].start()
        return True

    monkeypatch.setattr(_browser.webbrowser, "open", launch)
    _browser.open_html_in_browser("<p>Delayed</p>", timeout=2)
    for reader in readers:
        reader.join(timeout=2)
    assert received == [b"<p>Delayed</p>"]


@pytest.mark.parametrize("raises", [False, True])
def test_failed_launch_closes_preview_and_reports_error(monkeypatch, raises):
    opened = []

    def launch(url):
        opened.append(url)
        if raises:
            raise _browser.webbrowser.Error("No browser")
        return False

    monkeypatch.setattr(_browser.webbrowser, "open", launch)
    with pytest.raises(RuntimeError, match="write_html"):
        _browser.open_html_in_browser("<p>Preview</p>")
    with pytest.raises(URLError):
        urlopen(opened[0], timeout=0.5)


def test_browser_request_timeout_closes_preview(monkeypatch):
    opened = []
    monkeypatch.setattr(_browser.webbrowser, "open", lambda url: opened.append(url) or True)
    with pytest.raises(TimeoutError, match="did not load"):
        _browser.open_html_in_browser("<p>Preview</p>", timeout=0.05)
    with pytest.raises(URLError):
        urlopen(opened[0], timeout=0.5)


def test_preview_serves_only_its_generated_route(monkeypatch):
    def launch(url):
        with pytest.raises(HTTPError) as error:
            urlopen(url + "/unrelated", timeout=2)
        assert error.value.code == 404
        with urlopen(url, timeout=2) as response:
            assert response.read() == b"Preview"
        return True

    monkeypatch.setattr(_browser.webbrowser, "open", launch)
    _browser.open_html_in_browser("Preview", timeout=2)


def test_short_lived_script_waits_for_background_browser(tmp_path):
    result = tmp_path / "received.html"
    script = """
import subprocess, sys
from ganttify import _browser
readers = []
client = '''
import pathlib, sys, time, urllib.request
time.sleep(0.15)
with urllib.request.urlopen(sys.argv[1], timeout=3) as response:
    pathlib.Path(sys.argv[2]).write_bytes(response.read())
'''
def launch(url):
    readers.append(subprocess.Popen([sys.executable, '-c', client, url, sys.argv[1]]))
    return True
_browser.webbrowser.open = launch
_browser.open_html_in_browser('<p>Still available after launch</p>', timeout=3)
for reader in readers:
    assert reader.wait(timeout=3) == 0
"""
    environment = dict(os.environ, PYTHONPATH=str(Path(ganttify.__file__).parent.parent))
    subprocess.run(
        [sys.executable, "-c", script, str(result)],
        check=True,
        timeout=10,
        env=environment,
        capture_output=True,
    )
    assert result.read_text() == "<p>Still available after launch</p>"
