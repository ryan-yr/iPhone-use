import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import urllib.parse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))
import wda_apps


class FakeSetup:
    config = {}


class AppTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.setup = FakeSetup()
        self.setup.config = {}
        self.catalog = wda_apps.AppCatalog(Path(self.temp.name), self.setup)

    def test_catalog_exact_alias_and_case_preserving_bundle(self):
        with patch.object(wda_apps.subprocess, "run", side_effect=AssertionError("must stay offline")):
            result = self.catalog.lookup("cmb", source="catalog", limit=1)
        self.assertTrue(result["ok"])
        self.assertEqual(result["candidates"][0]["bundle_id"], "com.cmbchina.MPBBank")
        self.assertFalse(result["candidates"][0]["installed_verified"])
        self.assertFalse(result["candidates"][0]["installation_checked"])

    def test_catalog_limits_deduplicates_and_never_guesses(self):
        rows = self.catalog.lookup("银行", source="catalog", limit=2)
        self.assertEqual(len(rows["candidates"]), 2)
        self.assertGreater(rows["total_matches"], 2)
        self.assertEqual(self.catalog.lookup("unknown app 999", source="catalog")["candidates"], [])

    def test_catalog_has_evidence_for_every_reviewed_app(self):
        doc = json.loads(wda_apps.CATALOG_PATH.read_text())
        bundles = [row["bundleId"] for row in doc["apps"]]
        self.assertEqual(len(bundles), len(set(bundles)))
        self.assertGreaterEqual(len(bundles), 25)
        for row in doc["apps"]:
            self.assertTrue(wda_apps._valid_bundle(row["bundleId"]))
            self.assertEqual(urllib.parse.urlsplit(row["sourceUrl"]).hostname, "itunes.apple.com")
            self.assertTrue(row["verifiedAt"])
            self.assertTrue(row["publisher"])
            self.assertTrue(row["aliases"])

    def test_parse_device_formats_and_invalid_entries(self):
        rows = wda_apps.AppCatalog.parse_installed({"result": {"apps": [
            {"name": "招商银行", "bundleIdentifier": "com.cmbchina.MPBBank"},
            {"displayName": "掌上生活", "bundleId": "com.cmbchina.cmblife"},
            {"name": "duplicate", "bundleID": "com.cmbchina.MPBBank"},
            {"name": "malformed", "bundleIdentifier": "../not-a-bundle"}, None]}})
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row["installed_verified"] for row in rows))
        self.assertEqual(wda_apps.AppCatalog.parse_installed({"result": {"installedApps": {
            "com.example.app": {"displayName": "Example"}}}})[0]["bundle_id"], "com.example.app")
        self.assertEqual(wda_apps.AppCatalog.parse_installed({}), [])

    def _run_device(self, argv, **kwargs):
        self.assertIsInstance(argv, list)
        self.assertIn("--include-all-apps", argv)
        self.assertNotIn("shell", kwargs)
        path = Path(argv[argv.index("--json-output") + 1])
        path.write_text(json.dumps({"result": {"apps": [
            {"name": "招商银行", "bundleIdentifier": "com.cmbchina.MPBBank"},
            {"name": "Private unrelated app", "bundleIdentifier": "com.private.secret"}]}}))
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    def test_installed_probe_accepts_supported_inventory_formats(self):
        self.setup.config = {"udid": "00008150-ABCDEF0123456789"}
        for key in ("apps", "installedApps"):
            for apps in ([{"name": "Example", "bundleIdentifier": "com.example.app"}],
                         {"com.example.app": {"displayName": "Example"}}, []):
                with self.subTest(key=key, apps=apps):
                    cache = Path(self.temp.name) / "apps-installed-cache.json"
                    cache.unlink(missing_ok=True)
                    def run(argv, **kwargs):
                        Path(argv[argv.index("--json-output") + 1]).write_text(
                            json.dumps({"result": {key: apps}}))
                        return subprocess.CompletedProcess(argv, 0)
                    with patch.object(wda_apps.subprocess, "run", side_effect=run):
                        result = self.catalog.lookup("Example", source="installed")
                        again = self.catalog.lookup("Example", source="installed")
                    self.assertTrue(result["ok"])
                    self.assertEqual(result["candidates"], again["candidates"])
                    self.assertFalse(result["warnings"])
                    self.assertEqual(len(result["candidates"]), 1 if apps else 0)
                    if apps:
                        self.assertTrue(result["candidates"][0]["installed_verified"])

    def test_malformed_installed_response_returns_warning_and_catalog_fallback(self):
        self.setup.config = {"udid": "00008150-ABCDEF0123456789"}
        for document in (None, [], {"result": None}, {"result": []},
                         {"result": {}}, {"result": {"apps": None}}):
            with self.subTest(document=document):
                def run(argv, **kwargs):
                    Path(argv[argv.index("--json-output") + 1]).write_text(json.dumps(document))
                    return subprocess.CompletedProcess(argv, 0)
                with patch.object(wda_apps.subprocess, "run", side_effect=run):
                    explicit = self.catalog.lookup("招商银行", source="installed")
                    fallback = self.catalog.lookup("招商银行", source="auto")
                self.assertFalse(explicit["ok"])
                self.assertEqual(explicit["error"]["code"], "app_lookup_unavailable")
                self.assertTrue(fallback["ok"])
                self.assertTrue(fallback["warnings"])
                self.assertFalse(fallback["candidates"][0]["installation_checked"])
                self.assertFalse(fallback["candidates"][0]["installed_verified"])
                self.assertFalse((Path(self.temp.name) / "apps-installed-cache.json").exists())
                self.assertEqual(list(Path(self.temp.name).glob("apps-device-*")), [])

    def test_auto_prioritises_installed_and_caches_privately(self):
        self.setup.config = {"udid": "00008150-ABCDEF0123456789"}
        with patch.object(wda_apps.subprocess, "run", side_effect=self._run_device) as run:
            result = self.catalog.lookup("CMB")
            again = self.catalog.lookup("招行")
        self.assertEqual(run.call_count, 1)
        candidate = result["candidates"][0]
        self.assertEqual(candidate["origin"], "installed")
        self.assertTrue(candidate["installed_verified"])
        self.assertEqual(candidate["track_id"], 392899425)
        self.assertEqual(candidate["publisher"], "招商银行")
        self.assertEqual(len(result["candidates"]), 1)
        self.assertNotIn("com.private.secret", json.dumps(result))
        self.assertEqual(again["candidates"][0]["bundle_id"], candidate["bundle_id"])
        self.assertEqual(os.stat(Path(self.temp.name) / "apps-installed-cache.json").st_mode & 0o777, 0o600)

    def test_cache_expiry_and_device_change_refresh_inventory(self):
        self.setup.config = {"udid": "00008150-ABCDEF0123456789"}
        with patch.object(wda_apps.subprocess, "run", side_effect=self._run_device) as run:
            self.catalog.lookup("招商银行", source="installed")
            cache_path = Path(self.temp.name) / "apps-installed-cache.json"
            cache = json.loads(cache_path.read_text())
            cache["fetched_at"] = time.time() - 301
            cache_path.write_text(json.dumps(cache))
            self.catalog.lookup("招商银行", source="installed")
            self.setup.config = {"udid": "00008150-ABCDEF9876543210"}
            self.catalog.lookup("招商银行", source="installed")
        self.assertEqual(run.call_count, 3)

    def test_missing_device_and_invalid_udid_are_actionable_without_commands(self):
        with patch.object(wda_apps.subprocess, "run", side_effect=AssertionError("must not run")):
            result = self.catalog.lookup("招商银行", source="installed")
            self.setup.config = {"udid": "$(touch /tmp/unsafe)"}
            invalid = self.catalog.lookup("招商银行", source="installed")
        self.assertFalse(result["ok"])
        self.assertIn("pua_setup", result["warnings"][0])
        self.assertFalse(invalid["ok"])

    def test_failed_installed_probe_does_not_claim_catalog_app_installed(self):
        self.setup.config = {"udid": "00008150-ABCDEF0123456789"}
        with patch.object(wda_apps.subprocess, "run", side_effect=OSError("missing xcrun")):
            result = self.catalog.lookup("招商银行")
        self.assertTrue(result["ok"])
        self.assertFalse(result["candidates"][0]["installation_checked"])
        self.assertFalse(result["candidates"][0]["installed_verified"])
        self.assertTrue(result["warnings"])

    def test_auto_misses_and_explicit_apple_requests_remain_local(self):
        from iphone_use import result_content
        with patch("socket.getaddrinfo", side_effect=AssertionError("unexpected DNS")), \
                patch("socket.socket.connect", side_effect=AssertionError("unexpected network")):
            empty = self.catalog.lookup("Internal Project Canary")
            self.assertTrue(empty["ok"])
            self.assertEqual(empty["searched_sources"], ["installed", "catalog"])
            self.assertEqual(empty["candidates"], [])
            self.assertFalse(result_content(empty)["isError"])
            rejected = self.catalog.lookup("Internal Project Canary", source="apple")
            self.assertTrue(result_content(rejected)["isError"])
            self.assertEqual(rejected["error"]["code"], "invalid_argument")
            missing = self.catalog.lookup("Internal Project Canary", source="installed")
            self.assertEqual(missing["error"]["code"], "app_lookup_unavailable")
            self.assertTrue(result_content(missing)["isError"])

    def test_input_bounds(self):
        for kwargs in ({"query": ""}, {"query": "x" * 101}, {"query": "x", "country": "china"},
                       {"query": "x", "source": "shell"}, {"query": "x", "limit": True}, {"query": "x", "limit": 31}):
            self.assertFalse(self.catalog.lookup(**kwargs)["ok"])

    def test_state_inside_git_rejected(self):
        root = Path(self.temp.name) / "repo"
        root.mkdir()
        (root / ".git").mkdir()
        with self.assertRaises(ValueError):
            wda_apps.AppCatalog(root / "state", self.setup)


if __name__ == "__main__":
    unittest.main()
