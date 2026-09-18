from django.test import TestCase

from helium.common.utils.searchutils import matches_search_terms, normalize_search_text, tokenize_search_query


class TestCaseNormalizeSearchText(TestCase):
    def test_lowercases_and_folds_decomposable_diacritics(self):
        self.assertEqual(normalize_search_text('Café Naïve Über'), 'cafe naive uber')

    def test_folds_letters_that_expand_to_several(self):
        self.assertEqual(normalize_search_text('Ærø Łódź Œuvre Þing'), 'aero lodz oeuvre thing')

    def test_single_unit_folding_wins_over_multi_unit_as_in_the_package(self):
        self.assertEqual(normalize_search_text('Straße'), 'strase')

    def test_drops_combining_marks_and_keeps_unmapped_characters(self):
        self.assertEqual(normalize_search_text('e\u0301 日本 🎓'), 'e 日本 🎓')


class TestCaseTokenizeSearchQuery(TestCase):
    def test_splits_on_whitespace_runs_and_normalizes(self):
        self.assertEqual(tokenize_search_query('  Krebs   CYCLE\tcafé '), ['krebs', 'cycle', 'cafe'])

    def test_strips_edge_punctuation_but_keeps_internal(self):
        self.assertEqual(tokenize_search_query('weekend. p.42-50 c++'), ['weekend', 'p.42-50', 'c'])

    def test_double_quoted_span_is_one_phrase_term(self):
        self.assertEqual(tokenize_search_query('"Lab  Report" due'), ['lab report', 'due'])

    def test_phrase_edge_punctuation_is_stripped_and_unmatched_quote_is_punctuation(self):
        self.assertEqual(tokenize_search_query('"weekend plan." draft"'), ['weekend plan', 'draft'])

    def test_single_quotes_are_ordinary_characters(self):
        self.assertEqual(tokenize_search_query("don't 'forget'"), ["don't", 'forget'])

    def test_blank_and_punctuation_only_queries_yield_no_terms(self):
        for query in ('', '   ', '...', '"" ,'):
            self.assertEqual(tokenize_search_query(query), [], msg=repr(query))


class TestCaseMatchesSearchTerms(TestCase):
    def test_every_term_must_appear_in_some_haystack(self):
        # GIVEN
        haystacks = ('Meeting', 'Project Alpha')

        # WHEN
        both_found = matches_search_terms(haystacks, ['alpha', 'meeting'])
        one_missing = matches_search_terms(haystacks, ['alpha', 'beta'])

        # THEN
        self.assertTrue(both_found)
        self.assertFalse(one_missing)

    def test_haystacks_are_normalized_and_empty_ones_skipped(self):
        self.assertTrue(matches_search_terms(('', None, 'Café Notes'), ['cafe']))

    def test_no_terms_matches_everything(self):
        self.assertTrue(matches_search_terms(('anything',), []))
