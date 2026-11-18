import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))
from iphone_use import Runtime, tool_result
from test_controller import FakeWDA
from wda_setup import _NoStatusRedirect
import urllib.request


class NoExternalServicesTests(unittest.TestCase):
    def test_real_runtime_with_old_opt_in_and_local_account_overrides(self):
        old_env = {"IPHONE_USE_ANALYTICS": "1", "DO_NOT_TRACK": "0",
                   "IPHONE_USE_POSTHOG_PROJECT_TOKEN": "test", "IPHONE_USE_GA4_API_SECRET": "test",
                   "IPHONE_USE_GA4_MEASUREMENT_ID": "G-TEST"}
        attempts = []
        def forbidden(*args):
            attempts.append(True)
            raise AssertionError("Unexpected network access")

        with tempfile.TemporaryDirectory() as state, patch.dict(os.environ, old_env), \
                patch.object(socket, "getaddrinfo", forbidden), patch.object(socket.socket, "connect", forbidden):
            runtime = Runtime(state)
            runtime.client = runtime.phone.client = FakeWDA()
            runtime.client.close = lambda: None
            try:
                def call(name, **args):
                    return tool_result(runtime, {"name": name, "arguments": args})
                self.assertFalse(call("pua_launch_app", bundle_id="com.example.internal")["isError"])
                observed = call("pua_observe", mode="both")
                self.assertFalse(observed["isError"])
                self.assertTrue(json.loads(observed["content"][0]["text"])["nodes"])
                self.assertEqual(observed["content"][1]["type"], "image")
                empty = call("pua_apps", query="private-test-application")
                self.assertEqual(json.loads(empty["content"][0]["text"])["candidates"], [])
                self.assertTrue(call("pua_apps", query="private-test-application", source="apple")["isError"])
            finally:
                runtime.close()
            self.assertEqual(attempts, [])
            self.assertFalse((Path(state) / "analytics-id").exists())

    def test_local_status_probe_declines_redirects(self):
        request = urllib.request.Request("http://127.0.0.1:18100/status")
        self.assertIsNone(_NoStatusRedirect().redirect_request(request, None, 302, "", {}, "https://example.invalid/"))
