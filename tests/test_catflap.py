import importlib
import types
import sys
from unittest.mock import MagicMock
import os
import tempfile

import pytest


def load_module(monkeypatch):
    gpio = types.SimpleNamespace(
        BCM=1,
        IN=0,
        PUD_UP=0,
        BOTH=3,
        LOW=0,
        HIGH=1,
        setmode=lambda *a, **k: None,
        setup=lambda *a, **k: None,
        input=lambda *a, **k: gpio.HIGH,
        add_event_detect=lambda *a, **k: None,
    )
    rpi = types.ModuleType("RPi")
    rpi.GPIO = gpio
    monkeypatch.setitem(sys.modules, "RPi", rpi)
    monkeypatch.setitem(sys.modules, "RPi.GPIO", gpio)

    camera_instance = MagicMock()
    picamera = types.ModuleType("picamera")
    picamera.PiCamera = lambda: camera_instance
    monkeypatch.setitem(sys.modules, "picamera", picamera)

    twython_instance = MagicMock()
    Twython = MagicMock(return_value=twython_instance)
    twython_mod = types.ModuleType("twython")
    twython_mod.Twython = Twython
    monkeypatch.setitem(sys.modules, "twython", twython_mod)

    if "catflap3" in sys.modules:
        del sys.modules["catflap3"]
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root not in sys.path:
        sys.path.insert(0, root)
    module = importlib.import_module("catflap3")
    return module, twython_instance, camera_instance


def test_determine_state(monkeypatch):
    module, _, _ = load_module(monkeypatch)
    assert module.determine_state("inside", "inner_opening") == "exiting"
    assert module.determine_state("inside", "outer_opening") == "exiting"
    assert module.determine_state("exiting", "outer_opening") == "outside"
    assert module.determine_state("outside", "outer_opening") == "entering"
    assert module.determine_state("entering", "inner_opening") == "inside"


def test_tweet(monkeypatch, tmp_path):
    module, twython_instance, _ = load_module(monkeypatch)
    for k in ["apiKey", "apiSecret", "accessToken", "accessTokenSecret"]:
        monkeypatch.setenv(k, k)

    f = tmp_path / "img.jpg"
    f.write_bytes(b"data")

    module.tweet("hello", str(f))

    module.Twython.assert_called_once_with("apiKey", "apiSecret", "accessToken", "accessTokenSecret")
    assert twython_instance.upload_media.called
    assert twython_instance.update_status.called


def test_inner_callback_triggers_tweet(monkeypatch):
    module, twython_instance, camera = load_module(monkeypatch)
    module.cat_state = "entering"
    module.time_stamp_inner = 0

    for k in ["apiKey", "apiSecret", "accessToken", "accessTokenSecret"]:
        monkeypatch.setenv(k, k)

    monkeypatch.setattr(module.io, "input", lambda pin: module.io.HIGH)
    monkeypatch.setattr(module.time, "time", lambda: 3)
    monkeypatch.setattr(module.time, "strftime", lambda fmt, t=None: "19700101-000003")
    monkeypatch.setattr(module.time, "sleep", lambda s: None)
    monkeypatch.setattr(module, "tweet", MagicMock())

    module.catflap_callback_inner(module.Inner_door_pin)

    assert module.cat_state == "inside"
    camera.capture.assert_called_once_with("/srv/cats/19700101-000003.jpg")
    module.tweet.assert_called_once()


def test_outer_callback_triggers_tweet(monkeypatch):
    module, twython_instance, _ = load_module(monkeypatch)
    module.cat_state = "exiting"
    module.time_stamp_outer = 0
    module.final_path = "/srv/cats/19700101-000003.jpg"

    for k in ["apiKey", "apiSecret", "accessToken", "accessTokenSecret"]:
        monkeypatch.setenv(k, k)

    monkeypatch.setattr(module.io, "input", lambda pin: module.io.HIGH)
    monkeypatch.setattr(module.time, "time", lambda: 3)
    monkeypatch.setattr(module.time, "strftime", lambda fmt, t=None: "19700101-000003")
    monkeypatch.setattr(module.time, "sleep", lambda s: None)
    monkeypatch.setattr(module, "tweet", MagicMock())

    module.catflap_callback_outer(module.Outer_door_pin)

    assert module.cat_state == "outside"
    module.tweet.assert_called_once()
