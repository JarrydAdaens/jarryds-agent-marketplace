"""Tests for the deterministic parsing and naming logic in youtube_context.py.

The subprocess-driven subcommands are validated by running the real tools, not
here; these tests cover the caption parsing and filename rules that would break
silently.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import youtube_context as yc


# --------------------------------------------------------------------------
# naming
# --------------------------------------------------------------------------

def test_slugify_strips_punctuation_and_collapses_separators():
    assert yc.slugify("Build a  WPF App: Part 2 (2026!)") == "build-a-wpf-app-part-2-2026"


def test_slugify_falls_back_when_nothing_survives():
    assert yc.slugify("!!!") == "video"


def test_slugify_respects_the_length_limit():
    assert len(yc.slugify("word " * 40, limit=20)) <= 20


def test_video_id_handles_every_youtube_url_shape():
    assert yc.video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert yc.video_id("https://youtu.be/dQw4w9WgXcQ?t=42") == "dQw4w9WgXcQ"
    assert yc.video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert yc.video_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert yc.video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert yc.video_id("https://example.com/video") is None


def test_stamp_drops_the_hour_only_when_it_is_zero():
    assert yc.stamp(5) == "00:05"
    assert yc.stamp(725) == "12:05"
    assert yc.stamp(3750) == "1:02:30"


def test_file_stamp_avoids_characters_windows_rejects():
    assert yc.file_stamp(3750) == "01h02m30s"
    assert ":" not in yc.file_stamp(725)


# --------------------------------------------------------------------------
# caption parsing
# --------------------------------------------------------------------------

def test_vtt_seconds_accepts_both_decimal_separators():
    assert yc.vtt_seconds("00:01:02.500") == 62.5
    assert yc.vtt_seconds("01:00:00,000") == 3600.0


MANUAL_VTT = """WEBVTT
Kind: captions
Language: en

1
00:00:01.000 --> 00:00:04.000
Welcome to the talk.

2
00:00:04.000 --> 00:00:08.000
Today we cover &amp; compare two designs.
"""


def test_parse_vtt_keeps_cue_text_and_drops_headers_and_cue_numbers():
    cues = yc.parse_vtt(MANUAL_VTT)
    assert cues == [(1.0, "Welcome to the talk."), (4.0, "Today we cover & compare two designs.")]


AUTO_VTT = """WEBVTT

00:00:00.800 --> 00:00:03.120 align:start position:0%
the first thing

00:00:03.120 --> 00:00:05.440 align:start position:0%
the first thing
you need to <00:00:04.000><c>install</c>

00:00:05.440 --> 00:00:07.900 align:start position:0%
you need to install
is the driver
"""


def test_parse_vtt_removes_rolling_auto_caption_repeats():
    assert [text for _, text in yc.parse_vtt(AUTO_VTT)] == [
        "the first thing",
        "you need to install",
        "is the driver",
    ]


def test_parse_vtt_strips_inline_timing_tags():
    assert all("<" not in text for _, text in yc.parse_vtt(AUTO_VTT))


def test_dedupe_keeps_a_phrase_that_genuinely_recurs_much_later():
    cues = [(0.0, "same line")] + [(float(i), "filler %d" % i) for i in range(1, 8)]
    cues.append((9.0, "same line"))
    assert yc.dedupe_cues(cues)[-1] == (9.0, "same line")


# --------------------------------------------------------------------------
# grouping
# --------------------------------------------------------------------------

def test_group_cues_opens_a_new_block_once_the_span_elapses():
    cues = [(0.0, "a"), (10.0, "b"), (31.0, "c"), (40.0, "d")]
    assert yc.group_cues(cues, span=30.0) == [(0.0, "a b"), (31.0, "c d")]


def test_group_cues_handles_an_empty_transcript():
    assert yc.group_cues([]) == []


def test_render_transcript_prefixes_every_block_with_its_timestamp():
    rendered = yc.render_transcript([(0.0, "intro"), (95.0, "detail")])
    assert rendered == "[00:00] intro\n\n[01:35] detail"


# --------------------------------------------------------------------------
# caption track selection
# --------------------------------------------------------------------------

SLUG = "some-talk-abcdefghijk"


def vtt_paths(*tags):
    return [Path("{0}.{1}.vtt".format(SLUG, tag)) for tag in tags]


def test_subtitle_tag_reads_the_language_out_of_the_filename():
    assert yc.subtitle_tag(Path(SLUG + ".en-US.vtt"), SLUG) == "en-US"


def test_pick_subtitle_prefers_the_plain_tag_over_a_regional_variant():
    chosen, discarded = yc.pick_subtitle(vtt_paths("en-US", "en"), SLUG)
    assert yc.subtitle_tag(chosen, SLUG) == "en"
    assert [yc.subtitle_tag(p, SLUG) for p in discarded] == ["en-US"]


def test_pick_subtitle_treats_the_orig_track_as_a_last_resort():
    chosen, _ = yc.pick_subtitle(vtt_paths("en-orig", "en"), SLUG)
    assert yc.subtitle_tag(chosen, SLUG) == "en"


def test_pick_subtitle_still_returns_the_orig_track_when_it_is_the_only_one():
    chosen, discarded = yc.pick_subtitle(vtt_paths("en-orig"), SLUG)
    assert yc.subtitle_tag(chosen, SLUG) == "en-orig"
    assert discarded == []


def test_pick_subtitle_is_deterministic_across_input_order():
    tags = ("en-orig", "en-GB", "en", "en-US")
    first, _ = yc.pick_subtitle(vtt_paths(*tags), SLUG)
    second, _ = yc.pick_subtitle(vtt_paths(*reversed(tags)), SLUG)
    assert first == second


def test_pick_subtitle_handles_no_captions_at_all():
    assert yc.pick_subtitle([], SLUG) == (None, [])


# --------------------------------------------------------------------------
# frame timestamps
# --------------------------------------------------------------------------

SCENE_LOG = """frame:0    pts:7007     pts_time:0.2336
lavfi.scene_score=0.512
frame:1    pts:300300   pts_time:10.01
lavfi.scene_score=0.418
"""


def test_parse_scene_log_reads_presentation_times_in_order():
    assert yc.parse_scene_log(SCENE_LOG) == [0.2336, 10.01]


def test_parse_scene_log_returns_nothing_for_an_empty_log():
    assert yc.parse_scene_log("") == []
