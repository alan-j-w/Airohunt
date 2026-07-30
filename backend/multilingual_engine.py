import re
from typing import Dict, Any, List, Tuple

# Common stop words & language indicators
LANG_INDICATORS = {
    "en": [" requirements ", " looking for ", " experience ", " responsibilities ", " developer ", " engineer ", " salary "],
    "de": [" anforderungen ", " wir suchen ", " erfahrung ", " aufgaben ", " entwickler ", " ingenieur ", " gehalt "],
    "fr": [" exigences ", " nous recherchons ", " expérience ", " responsabilités ", " développeur ", " ingénieur ", " salaire "],
    "es": [" requisitos ", " buscamos ", " experiencia ", " responsabilidades ", " desarrollador ", " ingeniero ", " salario "],
    "nl": [" vereisten ", " wij zoeken ", " ervaring ", " verantwoordelijkheden ", " ontwikkelaar ", " salaris "]
}

# Multilingual scam & low-quality listing patterns
MULTILINGUAL_SCAM_PATTERNS = {
    "de": [
        r'schulungsgebühr', r'kostenpflichtige ausbildung', r'eigenkapital erforderlich',
        r'vorkasse', r'kein gehalt', r'provisionsbasis 100%'
    ],
    "fr": [
        r'formation payante', r'stage payant par le candidat', r'frais de dossier',
        r'investissement initial'
    ],
    "es": [
        r'curso de pago', r'inversión inicial', r'paga por trabajar', r'sin sueldo'
    ]
}

class MultilingualEngine:
    """
    Multilingual detection, scam analysis, and language metadata extraction engine.
    """
    def detect_language(self, text: str) -> str:
        t_lower = f" {text.lower()} "
        scores = {}
        for lang, indicators in LANG_INDICATORS.items():
            score = sum(1 for ind in indicators if ind in t_lower)
            scores[lang] = score

        best_lang = max(scores, key=scores.get)
        return best_lang if scores[best_lang] > 0 else "en"

    def analyze_multilingual_scams(self, text: str, lang: str = None) -> Tuple[bool, List[str]]:
        rejections = []
        t_lower = text.lower()

        for l_code, patterns in MULTILINGUAL_SCAM_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, t_lower):
                    rejections.append(f"Multilingual Scam Indicator ({l_code.upper()}): {pat}")

        return (len(rejections) > 0, rejections)

    def extract_language_metadata(self, text: str) -> Dict[str, Any]:
        lang = self.detect_language(text)
        is_scam, rejections = self.analyze_multilingual_scams(text, lang)
        return {
            "language": lang,
            "is_english": lang == "en",
            "is_multilingual_scam": is_scam,
            "scam_reasons": rejections
        }

global_multilingual_engine = MultilingualEngine()
