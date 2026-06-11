"""Lightweight spell tolerance via bounded Levenshtein distance.

Visitors mistype venue and city names ("stadiom", "halaal"). This corrects tokens against
a domain vocabulary when within an edit-distance budget, improving recall without a
heavyweight spellchecker. The vocabulary is injected so it can track the live index.
"""
from __future__ import annotations


def levenshtein(a: str, b: str, max_distance: int | None = None) -> int:
    """Compute edit distance, short-circuiting once it exceeds ``max_distance``."""
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if abs(la - lb) > (max_distance if max_distance is not None else max(la, lb)):
        return (max_distance or max(la, lb)) + 1
    previous = list(range(lb + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        best = i
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            val = min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost)
            current.append(val)
            best = min(best, val)
        if max_distance is not None and best > max_distance:
            return max_distance + 1
        previous = current
    return previous[lb]


class SpellCorrector:
    """Corrects tokens against a domain vocabulary within an edit budget."""

    def __init__(self, vocabulary: set[str], *, max_distance: int = 2) -> None:
        self._vocab = {w.lower() for w in vocabulary}
        self.max_distance = max_distance

    def correct_token(self, token: str) -> str:
        """Return the closest vocabulary word, or the token unchanged."""
        low = token.lower()
        if low in self._vocab or len(low) < 4:
            return token
        best_word = token
        best_dist = self.max_distance + 1
        for word in self._vocab:
            if abs(len(word) - len(low)) > self.max_distance:
                continue
            dist = levenshtein(low, word, self.max_distance)
            if dist < best_dist:
                best_dist = dist
                best_word = word
        return best_word if best_dist <= self.max_distance else token

    def correct(self, text: str) -> str:
        """Correct each token in a phrase."""
        return " ".join(self.correct_token(t) for t in text.split())

    @classmethod
    def from_events(cls, events, **kwargs) -> "SpellCorrector":
        """Build a corrector from the vocabulary present in a set of events."""
        vocab: set[str] = set()
        for ev in events:
            vocab.update(ev.text_blob().split())
            vocab.add(ev.city.lower())
        return cls(vocab, **kwargs)
