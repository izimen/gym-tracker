"""
Tests for the eFitness 'Na terenie klubu' scraper parsing and the /api/occupancy fetch throttle.
Run: python -m pytest tests/ -v
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import app as app_module
from app import parse_entries_count

REAL_FETCH = app_module.fetch_entries_data


PAGE_WITH_WIDGET = """
<html><body>
<header><nav>Aktualności Grafik zajęć Kup karnet</nav></header>
<div id="innercontainer" class="clearfix">
  <div class="club-occupancy">
    <h2>Aktualnie w klubie</h2>
    <span class="value">
        142
    </span> / <span class="max">400</span>
  </div>
</div>
<footer>Trakt Lwowski 158A 08-400 Garwolin</footer>
</body></html>
"""

# What the portal returned on 2026-10-29 00:26 (club closed): logged in, but empty content container.
PAGE_EMPTY = """
<html><body>
<header><h1>Na terenie klubu</h1><nav>Aktualności Grafik zajęć</nav></header>
<div id="widecontainer"><div id="innercontainer" class="clearfix">

</div></div>
<footer>Cube Fitness Garwolin Trakt Lwowski 158A 08-400 Garwolin +48 730 930 030</footer>
</body></html>
"""


class TestParseEntriesCount:
    def test_parses_widget_split_across_tags_and_lines(self):
        count, text = parse_entries_count(PAGE_WITH_WIDGET)
        assert count == 142
        assert '\n' not in text

    def test_inline_text(self):
        count, _ = parse_entries_count('<p>Aktualnie w klubie 7/350</p>')
        assert count == 7

    def test_fallback_ratio_with_large_capacity(self):
        count, _ = parse_entries_count('<p>Osób: 55 / 300</p>')
        assert count == 55

    def test_fallback_ignores_small_ratios(self):
        count, _ = parse_entries_count('<p>Zajęcia 3/12</p>')
        assert count is None

    def test_empty_content_returns_none(self):
        count, text = parse_entries_count(PAGE_EMPTY)
        assert count is None
        assert 'Na terenie klubu' in text


class TestOccupancyThrottle:
    @pytest.fixture
    def client(self, monkeypatch):
        calls = []

        def fake_fetch():
            calls.append(1)
            app_module.last_fetch_attempt = app_module.time.time()
            app_module.entries_cache = {'entries_today': 0, 'last_updated': None,
                                        'status': 'error', 'error': 'Nie znaleziono danych o wejściach'}

        monkeypatch.setattr(app_module, 'fetch_entries_data', fake_fetch)
        monkeypatch.setattr(app_module, 'last_fetch_attempt', 0.0)
        monkeypatch.setattr(app_module, 'entries_cache',
                            {'entries_today': 0, 'last_updated': None, 'status': 'initializing', 'error': None})
        app_module.extensions.limiter.enabled = False
        yield app_module.app.test_client(), calls
        app_module.extensions.limiter.enabled = True

    def test_failing_source_is_not_scraped_on_every_request(self, client):
        c, calls = client
        for _ in range(5):
            r = c.get('/api/occupancy')
            assert r.status_code == 200
        assert len(calls) == 1
        assert r.get_json()['status'] == 'error'

    def test_scrapes_again_after_cooldown(self, client):
        c, calls = client
        c.get('/api/occupancy')
        app_module.last_fetch_attempt -= app_module.REFRESH_COOLDOWN + 1
        c.get('/api/occupancy')
        assert len(calls) == 2

    def test_error_message_is_generic(self, client, monkeypatch):
        c, _ = client
        monkeypatch.setattr(app_module, 'GYM_URL', 'https://example.invalid')
        monkeypatch.setattr(app_module, 'DATA_URL', 'https://example.invalid/na-terenie-klubu')

        def boom(force_new=False):
            raise RuntimeError('secret internal detail')

        monkeypatch.setattr(app_module, 'get_gym_session', boom)
        REAL_FETCH()
        assert app_module.entries_cache['status'] == 'error'
        assert 'secret' not in app_module.entries_cache['error']
