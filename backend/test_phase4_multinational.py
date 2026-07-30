import unittest
import os
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from currency_engine import CurrencyNormalizationEngine, global_currency_engine
from multilingual_engine import MultilingualEngine, global_multilingual_engine
from global_metadata_engine import GlobalMetadataEngine, global_metadata_engine

class TestPhase4Multinational(unittest.TestCase):
    def test_currency_normalization(self):
        # 1. EUR Salary String
        parsed_eur = global_currency_engine.parse_salary_string("€75,000 - €90,000 / yr + Equity")
        self.assertEqual(parsed_eur["currency"], "EUR")
        self.assertGreater(parsed_eur["min_usd"], 70000.0)
        self.assertTrue(parsed_eur["has_equity"])

        # 2. INR LPA Salary String
        parsed_inr = global_currency_engine.parse_salary_string("₹15 - ₹20 LPA")
        self.assertEqual(parsed_inr["currency"], "INR")
        self.assertEqual(parsed_inr["normalized_lpa"], 17.5)

        # 3. GBP Salary String
        parsed_gbp = global_currency_engine.parse_salary_string("£60k - £70k")
        self.assertEqual(parsed_gbp["currency"], "GBP")
        self.assertGreater(parsed_gbp["min_usd"], 70000.0)

        print("✓ Currency normalization & FX conversion test passed")

    def test_multilingual_detection_and_scams(self):
        # German Job Description
        de_job = "Wir suchen einen erfahrenen Senior React Entwickler in Berlin. Anforderungen: 5 Jahre Erfahrung mit TypeScript."
        lang_de = global_multilingual_engine.detect_language(de_job)
        self.assertEqual(lang_de, "de")

        # German Scam Listing
        de_scam = "Kostenpflichtige Ausbildung zum Softwareentwickler. Schulungsgebühr vorab erforderlich."
        is_scam, reasons = global_multilingual_engine.analyze_multilingual_scams(de_scam)
        self.assertTrue(is_scam)

        print("✓ Multilingual language detection & international scam analysis test passed")

    def test_global_visa_and_timezone_metadata(self):
        job_text_1 = "Senior Engineer. Visa sponsorship offered (H-1B transfer supported). Work from anywhere (Global Remote)."
        meta1 = global_metadata_engine.extract_all_metadata(job_text_1)
        self.assertTrue(meta1["sponsorship_offered"])
        self.assertEqual(meta1["sponsorship_status"], "OFFERED")
        self.assertIn("GLOBAL_REMOTE", meta1["timezone_constraints"])

        job_text_2 = "Frontend Developer. No visa sponsorship provided. Must be legally authorized to work in the US."
        meta2 = global_metadata_engine.extract_all_metadata(job_text_2)
        self.assertFalse(meta2["sponsorship_offered"])
        self.assertEqual(meta2["sponsorship_status"], "NOT_OFFERED")

        print("✓ Global visa sponsorship & timezone metadata test passed")

if __name__ == "__main__":
    unittest.main()
