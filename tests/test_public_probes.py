import socket
import gzip
import sys
import unittest
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dispatch_bridge_radar.contract import ContentCandidate, Platform
from dispatch_bridge_radar.evidence import SignalName, StatementKind
from dispatch_bridge_radar.live_baseline import build_live_evidence, default_task, overall_status
from dispatch_bridge_radar.public_probes import (
    BILIBILI_HOSTS,
    LiveContentCandidate,
    ProbeDiagnostics,
    SafePublicHttpClient,
    _SafeRedirectHandler,
    _decode_body,
    discover_bilibili_urls,
    discover_youtube_urls,
    parse_public_video_page,
)
from dispatch_bridge_radar.scoring import rank_platforms, score_platform


FIXTURE = (ROOT / "tests/fixtures/public-video-minimal.html").read_text()


class TimeoutOpener:
    def __init__(self):
        self.calls = 0

    def open(self, request, timeout):
        self.calls += 1
        raise urllib.error.URLError(socket.timeout())


def live_candidate(candidate_id="ok", source_kind="live_public", title="handmade doll making"):
    return LiveContentCandidate(
        candidate_id=candidate_id,
        platform=Platform.YOUTUBE,
        title=title,
        description="cloth doll sewing process",
        creator="Small Maker",
        url="https://www.youtube.com/watch?v=abc123DEF45",
        source_kind=source_kind,
        creator_id="smallmaker",
        creator_name="Small Maker",
        source_url="https://www.youtube.com/watch?v=abc123DEF45",
        fetched_at="2026-07-17T00:00:00Z",
    )


class PublicProbeTests(unittest.TestCase):
    def test_https_allowlist_and_outside_redirect_are_rejected(self):
        client = SafePublicHttpClient(BILIBILI_HOSTS)
        client.validate_url("https://www.bilibili.com/video/BV1234567890")
        with self.assertRaisesRegex(ValueError, "https"):
            client.validate_url("http://www.bilibili.com/video/BV1234567890")
        handler = _SafeRedirectHandler(client.validate_url)
        with self.assertRaisesRegex(ValueError, "allowlisted"):
            handler.redirect_request(None, None, 302, "", {}, "https://example.com/tracker")

    def test_timeout_has_finite_retry_count(self):
        opener = TimeoutOpener()
        client = SafePublicHttpClient(BILIBILI_HOSTS, retries=1, opener=opener, sleeper=lambda _: None)
        with self.assertRaisesRegex(Exception, "timeout"):
            client.fetch_text("https://www.bilibili.com/video/BV1234567890")
        self.assertEqual(opener.calls, 2)

    def test_gzip_public_html_is_decoded_with_size_guard(self):
        encoded = gzip.compress(FIXTURE.encode("utf-8"))
        self.assertEqual(_decode_body(encoded, "gzip", 100_000).decode("utf-8"), FIXTURE)
        with self.assertRaisesRegex(Exception, "response_too_large"):
            _decode_body(encoded, "gzip", 10)

    def test_json_ld_and_open_graph_minimal_fixture(self):
        item = parse_public_video_page(FIXTURE, platform=Platform.YOUTUBE, candidate_id="abc123DEF45", fetched_at="2026-07-17T00:00:00Z", page_url="https://www.youtube.com/watch?v=abc123DEF45")
        self.assertEqual(item.creator_name, "Small Maker")
        self.assertEqual(item.metrics["views"], 1200)
        self.assertEqual(item.metrics["likes"], 86)
        self.assertNotIn("comments", item.metrics)
        self.assertIn("comments", item.missing_fields)

    def test_missing_fields_are_not_zero(self):
        item = parse_public_video_page('<meta property="og:title" content="art doll">', platform=Platform.YOUTUBE, candidate_id="abc123DEF45", fetched_at="2026-07-17T00:00:00Z", page_url="https://www.youtube.com/watch?v=abc123DEF45")
        self.assertEqual(item.public_metrics, ())
        self.assertIn("views", item.missing_fields)

    def test_page_instruction_text_cannot_change_safety_policy(self):
        item = parse_public_video_page(FIXTURE, platform=Platform.YOUTUBE, candidate_id="abc123DEF45", fetched_at="2026-07-17T00:00:00Z", page_url="https://www.youtube.com/watch?v=abc123DEF45")
        self.assertTrue(default_task().safety.read_only)
        self.assertEqual(item.source_kind, "live_public")

    def test_discovery_extracts_only_canonical_video_ids(self):
        bili = discover_bilibili_urls('"bvid":"BV1abcdefghi" https://www.bilibili.com/video/BV1abcdefghi')
        youtube = discover_youtube_urls('"videoId":"abc123DEF45"')
        self.assertEqual(bili, ("https://www.bilibili.com/video/BV1abcdefghi",))
        self.assertEqual(youtube, ("https://www.youtube.com/watch?v=abc123DEF45",))

    def test_rejected_candidate_does_not_enter_live_evidence(self):
        accepted = live_candidate("accepted")
        rejected = live_candidate("rejected", title="beauty tutorial")
        evidence = build_live_evidence(Platform.YOUTUBE, [accepted, rejected], {"accepted"})
        self.assertTrue(all(item.candidate_id == "accepted" for item in evidence))

    def test_replay_and_live_are_not_mixed(self):
        replay = live_candidate("replay", source_kind="replay")
        evidence = build_live_evidence(Platform.YOUTUBE, [replay], {"replay"})
        self.assertEqual(evidence, ())

    def test_first_window_cannot_produce_main_or_experiment(self):
        item = live_candidate()
        evidence = build_live_evidence(Platform.YOUTUBE, [item], {item.candidate_id})
        result = rank_platforms([score_platform(Platform.YOUTUBE, evidence)])[0]
        self.assertEqual(result.tier, "insufficient_evidence")
        self.assertTrue(result.needs_confirmation)
        growth = next(entry for entry in evidence if entry.signal == SignalName.SMALL_ACCOUNT_RELATIVE_GROWTH)
        self.assertEqual(growth.statement_kind, StatementKind.MISSING)

    def test_missing_live_source_routes_to_needs_confirmation(self):
        diagnostics = ProbeDiagnostics(Platform.YOUTUBE, 1, 0, 0, 0, ("search:http_403",))
        score = score_platform(Platform.YOUTUBE, ())
        from dispatch_bridge_radar.live_baseline import PlatformRun
        run = PlatformRun(Platform.YOUTUBE, ("handmade doll",), (), (), (), (), diagnostics, score)
        self.assertEqual(overall_status([run]), "needs_confirmation")


if __name__ == "__main__":
    unittest.main()
