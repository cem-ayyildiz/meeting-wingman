import io
import unittest

import _path  # noqa: F401
from gate import Gate, classify


class Classify(unittest.TestCase):
    def hits(self, text, mode="both", **kw):
        return classify(text, kw.pop("names", ()), mode, **kw)

    def test_questions(self):
        for t in ["What happens when the site goes offline?", "When will the pilot end",
                  "Can you share the slides", "Bunu kim yapacak?", "Peki bu ne zaman biter",
                  "Fiyat arttı mı", "Yarın gelebilir misiniz", "Warum ist das so?"]:
            self.assertIn("question", self.hits(t, "coach"), t)

    def test_statements_are_not_questions(self):
        for t in ["When the link comes back it uploads everything.", "How we built it is in the doc.",
                  "Bugün hava güzel.", "We start with the pilot results."]:
            self.assertNotIn("question", self.hits(t, "coach"), t)

    def test_team_triggers(self):
        self.assertEqual(self.hits("Maria, can you fix the export by Thursday?", "team"), ["action", "date"])
        self.assertIn("action", self.hits("Bunu cumaya kadar hallederim.", "team"))
        self.assertIn("date", self.hits("Bunu cumaya kadar hallederim.", "team"))
        self.assertIn("blocker", self.hits("SSO hâlâ bloklu, IT'yi bekliyoruz.", "team"))
        self.assertIn("decision", self.hits("OK, let's go with option B.", "team"))
        self.assertIn("decision", self.hits("Tamam o zaman, B seçeneğinde anlaştık.", "team"))

    def test_numbers_and_names(self):
        self.assertIn("number", self.hits("Fiyat yüzde 15 arttı.", "coach"))
        self.assertIn("number", self.hits("We saved 30% on energy.", "coach"))
        self.assertIn("name", self.hits("Cem, what do you think?", "coach", names=["cem"]))
        self.assertNotIn("name", self.hits("Cemal came late.", "coach", names=["cem"]))

    def test_mode_limits(self):
        self.assertEqual(self.hits("Can you send it by Friday?", "coach"), ["question"])
        self.assertNotIn("question", self.hits("Can you send it by Friday?", "team"))

    def test_self_questions_do_not_wake(self):
        self.assertEqual(classify("What happens offline?", (), "coach", "You", True), [])
        self.assertEqual(classify("We saved 30% on energy.", (), "coach", "You", True), ["number"])


class GateStream(unittest.TestCase):
    def run_gate(self, lines, **kw):
        now = [0.0]
        out = io.StringIO()
        g = Gate(out, clock=lambda: now[0], **kw)
        for line in lines:
            g.feed(line)
            now[0] += 1
        g.settle()
        g.flush_digest()
        return out.getvalue()

    def test_trigger_with_context_and_digest(self):
        out = self.run_gate(["[10:00:01] Good morning.", "[10:00:02] Can you hear me?",
                             "[10:00:03] Nice weather.", "[10:00:04] Indeed."], mode="coach")
        self.assertIn("▶ question · 10:00:02", out)
        self.assertIn("… [10:00:01] Good morning.", out)
        self.assertIn("◇ digest 10:00:03–10:00:04 · 2 lines", out)
        self.assertEqual(out.count("Good morning."), 1)   # never sent twice

    def test_translation_stays_with_its_line(self):
        out = self.run_gate(["[10:00:02] Was passiert offline?", "[10:00:02] ↳ en: What happens offline?"], mode="coach")
        block = out.split("▶")[1]
        self.assertIn("↳ en: What happens offline?", block)

    def test_speakers(self):
        out = self.run_gate(["[10:00:01] You: What happens offline?", "[10:00:02] Ana: Can you repeat that?"],
                            mode="coach", speakers=True)
        self.assertNotIn("▶ question · 10:00:01", out)
        self.assertIn("▶ question · 10:00:02", out)


if __name__ == "__main__":
    unittest.main()
