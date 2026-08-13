import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class LaypersonTextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html=(ROOT/"web"/"index.html").read_text(encoding="utf-8")
        cls.start=(ROOT/"start.sh").read_text(encoding="utf-8")
        cls.launcher=(ROOT/"tools"/"runtime_launcher.py").read_text(encoding="utf-8")
        cls.guide=(ROOT/"KLICKSTART_ANLEITUNG.md").read_text(encoding="utf-8")

    def test_simple_primary_terms_exist(self):
        for phrase in ("Dateien wiederfinden","Fundliste erstellen","Nachweisordner",
                       "Sicherheitsstatus","Was das Programm darf",
                       "Sicherheitsmodus: nur lesen","So benutzt du das Programm"):
            self.assertIn(phrase,self.html)

    def test_old_developer_headings_are_not_primary_text(self):
        for phrase in (">Recovery<","<h2>Candidate Index erzeugen</h2>",
                       "Fail-closed Status","<h2>System- und Release-Gates</h2>",
                       "<strong>Read-only aktiv</strong>"):
            self.assertNotIn(phrase,self.html)

    def test_plain_error_explanations_exist(self):
        self.assertIn("Der angegebene Ordner wurde nicht gefunden.",self.html)
        self.assertIn("Dieser Systemordner ist aus Sicherheitsgründen gesperrt.",self.html)
        self.assertIn("Der Nachweisordner ist noch nicht richtig vorbereitet.",self.html)
        self.assertIn("Die Aktion konnte nicht ausgeführt werden.",self.html)

    def test_start_messages_are_simple(self):
        self.assertIn("Start prüfen",self.start)
        self.assertIn("Sicherheit prüfen",self.start)
        self.assertIn("Programm öffnen",self.start)
        self.assertIn("Das Programm läuft bereits",self.launcher)

    def test_guide_explains_safety_plainly(self):
        self.assertIn("liest Dateien nur",self.guide)
        self.assertIn("löscht, verschiebt oder überschreibt keine",self.guide)

if __name__=="__main__":
    unittest.main()
