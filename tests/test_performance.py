#!/usr/bin/env python3
#
# Copyright (c) 2024-2026, Ryan Galloway (ryan@rsgalloway.com)
#

"""Coarse performance regression tests for envstack."""

import os
import shutil
import time
import unittest

from helpers import create_fixture_env_root

from envstack import util
from envstack.encrypt import AESGCMEncryptor, FernetEncryptor
from envstack.env import encrypt_environ, load_environ, resolve_environ


class PerformanceTests(unittest.TestCase):
    """Coarse-grained performance guardrails for envstack hotspots."""

    def setUp(self):
        self.root = create_fixture_env_root()
        self.old_env = os.environ.copy()
        self.old_cache_timeout = util.CACHE_TIMEOUT

        os.environ["ROOT"] = self.root
        os.environ["ENVPATH"] = os.pathsep.join(
            [
                os.path.join(self.root, "prod", "env"),
                os.path.join(self.root, "dev", "env"),
            ]
        )
        os.environ[AESGCMEncryptor.KEY_VAR_NAME] = "jHLNsFrhs9JsjuPkNhYX5ubwLpId2ZSxcFXAkHyMjOU="
        os.environ[FernetEncryptor.KEY_VAR_NAME] = "v4-Ry7uKSOBEXMDv9x_crBBpi0eo2WCYNAIlSB1t4VE="

        # Keep memoized paths warm and stable across the repeated calls below.
        util.CACHE_TIMEOUT = 60

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.old_env)
        util.CACHE_TIMEOUT = self.old_cache_timeout
        shutil.rmtree(self.root)

    def test_load_environ_repeated_dev_stack_stays_fast(self):
        """Repeated stack loading should remain comfortably below startup-budget scale."""
        start = time.perf_counter()
        last = None
        for _ in range(200):
            last = load_environ("dev", scope=self.root)
        elapsed = time.perf_counter() - start

        self.assertIsNotNone(last)
        self.assertEqual(last["ENV"], "dev")
        self.assertEqual(last["STACK"], "dev")
        self.assertLess(elapsed, 1.0)

    def test_resolve_environ_large_modifier_graph_stays_fast(self):
        """Large chained substitutions should not regress catastrophically."""
        env = {"ROOT": self.root, "PATH": "/usr/bin", "ENVPATH": os.environ["ENVPATH"]}
        for i in range(500):
            env[f"VAR_{i}"] = "${ROOT}/show/pkg/%d:${PATH}" % i

        start = time.perf_counter()
        resolved = resolve_environ(env)
        elapsed = time.perf_counter() - start

        self.assertTrue(resolved["VAR_499"].startswith(self.root))
        self.assertIn("/pkg/499", resolved["VAR_499"])
        self.assertLess(elapsed, 1.0)

    def test_encrypted_stack_load_and_resolve_stays_fast(self):
        """Encrypted stack resolution should stay well within a coarse CI budget."""
        start = time.perf_counter()
        last = None
        for _ in range(100):
            last = resolve_environ(load_environ("secrets", scope=self.root, encrypt=True))
        elapsed = time.perf_counter() - start

        self.assertIsNotNone(last)
        self.assertEqual(last["KEY"], "This is encrypted")
        self.assertEqual(last["SECRET"], "my_super_secret_password")
        self.assertLess(elapsed, 1.5)

    def test_encrypt_environ_medium_payload_stays_fast(self):
        """Bulk encryption of a moderate environment should remain snappy."""
        env = load_environ("dev", scope=self.root)
        for i in range(200):
            env[f"EXTRA_{i}"] = "${DEPLOY_ROOT}/lib/%d:${PATH}" % i

        start = time.perf_counter()
        encrypted = encrypt_environ(env)
        elapsed = time.perf_counter() - start

        self.assertEqual(encrypted["ENV"].resolve(env=os.environ), "dev")
        self.assertLess(elapsed, 1.0)


if __name__ == "__main__":
    unittest.main()
