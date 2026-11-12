import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "etl"))

import scheduler


class SchedulerTests(unittest.TestCase):
    def test_failed_source_does_not_publish_partial_data(self):
        broken = Mock(side_effect=ValueError("bad response"))
        healthy = Mock()
        with (
            patch.dict(scheduler.INGESTIONS, {"careerviet": broken, "arbeitnow": healthy}),
            patch.object(scheduler, "create_engine"),
            patch.object(scheduler, "record_source_run") as history,
            patch.object(scheduler, "run_pipeline") as publish,
            self.assertLogs("scheduler", level="ERROR"),
        ):
            with self.assertRaisesRegex(RuntimeError, "careerviet"):
                scheduler.run_job(["careerviet", "arbeitnow"])
            healthy.assert_called_once_with()
            self.assertEqual([call.args[4] for call in history.call_args_list], [False, True])
            publish.assert_not_called()

    def test_publishes_once_after_selected_sources_succeed(self):
        with (
            patch.dict(os.environ, {"INGEST_SOURCES": "TopDev, arbeitnow, topdev"}),
            patch.dict(scheduler.INGESTIONS, {"topdev": Mock(), "arbeitnow": Mock()}),
            patch.object(scheduler, "create_engine"),
            patch.object(scheduler, "record_source_run"),
            patch.object(scheduler, "run_pipeline") as publish,
        ):
            scheduler.run_job(scheduler.selected_sources())
            scheduler.INGESTIONS["topdev"].assert_called_once_with()
            scheduler.INGESTIONS["arbeitnow"].assert_called_once_with()
            publish.assert_called_once_with()
