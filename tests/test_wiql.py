import unittest
from unittest.mock import MagicMock

from azure_devops.export_ids import (
    compare_export_modes,
    diff_id_sets,
    fetch_work_item_ids,
    format_compare_report,
)
from azure_devops.wiql import (
    DEFAULT_EXPORT_MODE,
    MODE_SAVED_QUERY,
    MODE_WIQL_ENV,
    extract_changed_date_bounds,
    normalize_export_mode,
    rewrite_changed_date_bounds,
    to_ado_changed_date_literal,
)


LIVE_WIQL = (
    "select [System.Id], [System.WorkItemType], [System.Title], [System.AssignedTo], "
    "[System.State], [System.Tags], [System.ChangedDate] "
    "from WorkItems "
    "where [System.WorkItemType] <> 'User Story' "
    "and [System.ChangedDate] >= '2026-07-16T00:00:00.0000000' "
    "and [System.ChangedDate] <= '2026-08-15T00:00:00.0000000' "
    "and not [System.AssignedTo] contains 'Emily'"
)

WIQL_WITH_OTHER_DATES = (
    "select [System.Id], [System.CreatedDate], [System.ChangedDate] from WorkItems where "
    "[System.CreatedDate] >= '2020-01-01T00:00:00.0000000' "
    "and [System.ChangedDate] >= '2026-07-16T00:00:00.0000000' "
    "and [System.ChangedDate] <= '2026-08-15T00:00:00.0000000' "
    "and [Microsoft.VSTS.Common.ClosedDate] <= '2026-08-15T00:00:00.0000000'"
)


class ToAdoChangedDateLiteralTests(unittest.TestCase):
    def test_appends_midnight_for_date_only(self):
        self.assertEqual(
            to_ado_changed_date_literal("2026-07-16"),
            "2026-07-16T00:00:00.0000000",
        )

    def test_leaves_full_timestamp_unchanged(self):
        value = "2026-07-16T00:00:00.0000000"
        self.assertEqual(to_ado_changed_date_literal(value), value)

    def test_rejects_empty(self):
        with self.assertRaises(ValueError):
            to_ado_changed_date_literal("  ")


class RewriteChangedDateBoundsTests(unittest.TestCase):
    def test_live_wiql_same_dates_is_noop(self):
        rewritten = rewrite_changed_date_bounds(LIVE_WIQL, "2026-07-16", "2026-08-15")
        self.assertEqual(rewritten, LIVE_WIQL)

    def test_replaces_only_changed_date_bounds(self):
        rewritten = rewrite_changed_date_bounds(WIQL_WITH_OTHER_DATES, "2026-09-01", "2026-09-30")
        self.assertIn("[System.ChangedDate] >= '2026-09-01T00:00:00.0000000'", rewritten)
        self.assertIn("[System.ChangedDate] <= '2026-09-30T00:00:00.0000000'", rewritten)
        self.assertIn("[System.CreatedDate] >= '2020-01-01T00:00:00.0000000'", rewritten)
        self.assertIn("[Microsoft.VSTS.Common.ClosedDate] <= '2026-08-15T00:00:00.0000000'", rewritten)

    def test_keeps_non_date_filters_from_saved_query(self):
        rewritten = rewrite_changed_date_bounds(LIVE_WIQL, "2026-01-16", "2026-02-15")
        self.assertIn("[System.WorkItemType] <> 'User Story'", rewritten)
        self.assertIn("not [System.AssignedTo] contains 'Emily'", rewritten)
        self.assertIn("[System.ChangedDate] >= '2026-01-16T00:00:00.0000000'", rewritten)
        self.assertIn("[System.ChangedDate] <= '2026-02-15T00:00:00.0000000'", rewritten)
        self.assertNotIn("2026-07-16", rewritten)
        self.assertNotIn("2026-08-15", rewritten)

    def test_supports_whitespace_and_double_quotes(self):
        wiql = (
            "select [System.Id] from WorkItems where "
            "[ System.ChangedDate ]  >=  \"2026-07-16T00:00:00.0000000\" "
            "and [System.ChangedDate]<=\"2026-08-15T00:00:00.0000000\""
        )
        rewritten = rewrite_changed_date_bounds(wiql, "2026-07-20", "2026-08-01")
        self.assertIn(">=  \"2026-07-20T00:00:00.0000000\"", rewritten)
        self.assertIn("<=\"2026-08-01T00:00:00.0000000\"", rewritten)

    def test_requires_both_clauses(self):
        only_ge = "where [System.ChangedDate] >= '2026-07-16T00:00:00.0000000'"
        only_le = "where [System.ChangedDate] <= '2026-08-15T00:00:00.0000000'"
        with self.assertRaises(ValueError):
            rewrite_changed_date_bounds(only_ge, "2026-07-16", "2026-08-15")
        with self.assertRaises(ValueError):
            rewrite_changed_date_bounds(only_le, "2026-07-16", "2026-08-15")
        with self.assertRaises(ValueError):
            rewrite_changed_date_bounds("", "2026-07-16", "2026-08-15")

    def test_extract_bounds(self):
        date_from, date_to = extract_changed_date_bounds(LIVE_WIQL)
        self.assertEqual(date_from, "2026-07-16T00:00:00.0000000")
        self.assertEqual(date_to, "2026-08-15T00:00:00.0000000")


class NormalizeExportModeTests(unittest.TestCase):
    def test_default_is_wiql_env(self):
        self.assertEqual(normalize_export_mode(None), MODE_WIQL_ENV)
        self.assertEqual(normalize_export_mode("  "), DEFAULT_EXPORT_MODE)
        self.assertEqual(normalize_export_mode("WIQL_ENV"), MODE_WIQL_ENV)

    def test_saved_query(self):
        self.assertEqual(normalize_export_mode("saved_query"), MODE_SAVED_QUERY)

    def test_rejects_unknown(self):
        with self.assertRaises(ValueError):
            normalize_export_mode("legacy")


class FetchWorkItemIdsModeTests(unittest.TestCase):
    def test_saved_query_uses_legacy_get_path_only(self):
        client = MagicMock()
        client.get_query_wiql_url.return_value = "https://example/wiql-link"
        client.execute_wiql.return_value = [10, 20]

        ids = fetch_work_item_ids(client, "saved_query", "query-id")

        self.assertEqual(ids, [10, 20])
        client.get_query_wiql_url.assert_called_once_with("query-id")
        client.execute_wiql.assert_called_once_with("https://example/wiql-link")
        client.get_query_wiql.assert_not_called()
        client.execute_wiql_query.assert_not_called()

    def test_wiql_env_rewrites_and_posts(self):
        client = MagicMock()
        client.get_query_wiql.return_value = LIVE_WIQL
        client.execute_wiql_query.return_value = [1, 2, 3]

        ids = fetch_work_item_ids(
            client,
            "wiql_env",
            "query-id",
            date_from="2026-07-16",
            date_to="2026-08-15",
        )

        self.assertEqual(ids, [1, 2, 3])
        client.get_query_wiql.assert_called_once_with("query-id")
        posted_wiql = client.execute_wiql_query.call_args[0][0]
        self.assertEqual(posted_wiql, LIVE_WIQL)
        client.get_query_wiql_url.assert_not_called()
        client.execute_wiql.assert_not_called()

    def test_wiql_env_posts_rewritten_dates(self):
        client = MagicMock()
        client.get_query_wiql.return_value = LIVE_WIQL
        client.execute_wiql_query.return_value = []

        fetch_work_item_ids(
            client,
            MODE_WIQL_ENV,
            "query-id",
            date_from="2026-09-01",
            date_to="2026-09-30",
        )
        posted_wiql = client.execute_wiql_query.call_args[0][0]
        self.assertIn("[System.ChangedDate] >= '2026-09-01T00:00:00.0000000'", posted_wiql)
        self.assertIn("[System.ChangedDate] <= '2026-09-30T00:00:00.0000000'", posted_wiql)
        self.assertIn("not [System.AssignedTo] contains 'Emily'", posted_wiql)

    def test_wiql_env_requires_env_dates(self):
        client = MagicMock()
        with self.assertRaises(ValueError):
            fetch_work_item_ids(client, MODE_WIQL_ENV, "query-id")
        client.get_query_wiql.assert_not_called()


class DiffIdSetsTests(unittest.TestCase):
    def test_equal_sets_ignore_order_and_duplicates(self):
        result = diff_id_sets([3, 1, 2, 1], [2, 3, 1])
        self.assertTrue(result["equal"])
        self.assertEqual(result["saved_query_count"], 3)
        self.assertEqual(result["wiql_env_count"], 3)
        self.assertEqual(result["saved_query_ids"], [1, 2, 3])
        self.assertEqual(result["only_in_saved_query"], [])
        self.assertEqual(result["only_in_wiql_env"], [])

    def test_reports_symmetric_difference(self):
        result = diff_id_sets([1, 2], [2, 3])
        self.assertFalse(result["equal"])
        self.assertEqual(result["only_in_saved_query"], [1])
        self.assertEqual(result["only_in_wiql_env"], [3])
        report = format_compare_report(result)
        self.assertIn("conjuntos iguales: NO", report)
        self.assertIn("solo en saved_query (1): [1]", report)


class CompareExportModesTests(unittest.TestCase):
    def test_runs_both_modes_and_records_original_bounds(self):
        client = MagicMock()
        client.get_query_wiql.return_value = LIVE_WIQL
        client.get_query_wiql_url.return_value = "https://example/wiql-link"
        client.execute_wiql.return_value = [10, 20, 30]
        client.execute_wiql_query.return_value = [30, 10, 20]

        result = compare_export_modes(
            client,
            query_id="query-id",
            date_from="2026-07-16",
            date_to="2026-08-15",
        )

        self.assertTrue(result["equal"])
        self.assertEqual(result["saved_query_count"], 3)
        self.assertEqual(result["wiql_env_count"], 3)
        self.assertEqual(result["saved_query_changed_date_from"], "2026-07-16T00:00:00.0000000")
        self.assertEqual(result["saved_query_changed_date_to"], "2026-08-15T00:00:00.0000000")
        self.assertEqual(result["rewritten_changed_date_from"], "2026-07-16T00:00:00.0000000")
        client.execute_wiql.assert_called_once()
        client.execute_wiql_query.assert_called_once()


if __name__ == "__main__":
    unittest.main()
