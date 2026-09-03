import importlib.util
from pathlib import Path

from django.test import SimpleTestCase

_SCRIPT = Path(__file__).resolve().parents[3] / "bin" / "refresh-timezones.py"
_spec = importlib.util.spec_from_file_location("refresh_timezones", _SCRIPT)
refresh_timezones = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(refresh_timezones)


class TestCaseResolveAliases(SimpleTestCase):
    """Covers alias resolution only; the IANA fetch is exercised by running the script."""

    def test_alias_resolves_to_its_link_target(self):
        # GIVEN
        links = {'Asia/Calcutta': 'Asia/Kolkata'}
        selectable = {'Asia/Kolkata'}

        # WHEN
        resolved = refresh_timezones._resolve_aliases(links, selectable)

        # THEN
        self.assertEqual(resolved, {'Asia/Calcutta': 'Asia/Kolkata'})

    def test_chain_stops_at_the_first_selectable_zone(self):
        """IANA has consolidated zones into regional ones, so following a chain to
        its end can walk past the zone a user would recognize."""
        # GIVEN
        links = {'America/Buenos_Aires': 'America/Argentina/Buenos_Aires',
                 'America/Argentina/Buenos_Aires': 'America/Argentina/Cordoba'}
        selectable = {'America/Argentina/Buenos_Aires', 'America/Argentina/Cordoba'}

        # WHEN
        resolved = refresh_timezones._resolve_aliases(links, selectable)

        # THEN
        self.assertEqual(
            resolved['America/Buenos_Aires'], 'America/Argentina/Buenos_Aires')

    def test_selectable_identifiers_are_not_remapped(self):
        # GIVEN a zone that is both a link and directly selectable
        links = {'Africa/Asmara': 'Africa/Nairobi'}
        selectable = {'Africa/Asmara', 'Africa/Nairobi'}

        # WHEN
        resolved = refresh_timezones._resolve_aliases(links, selectable)

        # THEN
        self.assertNotIn('Africa/Asmara', resolved)

    def test_alias_with_no_selectable_target_is_dropped(self):
        # GIVEN
        links = {'Old/Zone': 'Also/Missing'}
        selectable = {'Europe/London'}

        # WHEN
        resolved = refresh_timezones._resolve_aliases(links, selectable)

        # THEN
        self.assertEqual(resolved, {})

    def test_a_link_cycle_terminates(self):
        # GIVEN
        links = {'A/One': 'B/Two', 'B/Two': 'A/One'}
        selectable = {'Europe/London'}

        # WHEN
        resolved = refresh_timezones._resolve_aliases(links, selectable)

        # THEN
        self.assertEqual(resolved, {})
