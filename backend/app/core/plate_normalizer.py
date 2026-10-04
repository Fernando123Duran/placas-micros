import re
from typing import Tuple, Optional


class PlateNormalizer:
    """Normalizador y validador sintáctico para placas vehiculares bolivianas."""

    # Palabras comunes en marcos de placas que deben ignorarse
    NOISE_WORDS = [
        "BOLIVIA", "TRANSPORTE", "PUBLICO", "PÚBLICO", "URBANO", "MICRO",
        "SANTA", "CRUZ", "LA PAZ", "COCHABAMBA", "BENI", "PANDO", "ORURO",
        "POTOSI", "TARIJA", "CHUQUISACA", "SCZ", "LPZ", "CBB"
    ]

    # Mapeo de corrección OCR: de letras a números (cuando se espera un dígito)
    CHAR_TO_DIGIT = {
        'O': '0', 'Q': '0', 'D': '0', 'U': '0',
        'I': '1', 'L': '1', 'T': '1', '|': '1', '/': '1',
        'Z': '2',
        'E': '3',
        'A': '4',
        'S': '5',
        'G': '6', 'b': '6',
        'B': '8',
    }

    # Mapeo de corrección OCR: de números a letras (cuando se espera una letra)
    DIGIT_TO_CHAR = {
        '0': 'O',
        '1': 'I',
        '2': 'Z',
        '3': 'E',
        '4': 'A',
        '5': 'S',
        '6': 'G',
        '8': 'B',
    }

    # Formato boliviano estándar: 3 o 4 dígitos seguidos de 3 letras
    # Ejemplos: 1234ABC, 345XYZ, 2048PTD
    BOLIVIAN_PLATE_REGEX = re.compile(r"^(\d{3,4})([A-Z]{3})$")

    @classmethod
    def clean_text(cls, raw_text: str) -> str:
        """Limpia el texto bruto eliminando palabras secundarias y caracteres especiales."""
        if not raw_text:
            return ""

        upper = raw_text.upper()

        # Eliminar palabras de ruido
        for word in cls.NOISE_WORDS:
            upper = upper.replace(word, " ")

        # Conservar solo caracteres alfanuméricos
        cleaned = re.sub(r"[^A-Z0-9]", "", upper)
        return cleaned

    @classmethod
    def disambiguate_bolivian_plate(cls, text: str) -> str:
        """Aplica corrección contextual de caracteres para placas bolivianas (3-4 números + 3 letras)."""
        length = len(text)
        if length not in (6, 7):
            return text

        # Si tiene 7 caracteres: 4 números + 3 letras
        # Si tiene 6 caracteres: 3 números + 3 letras
        num_digits = length - 3
        part_digits = list(text[:num_digits])
        part_letters = list(text[num_digits:])

        # Corregir parte numérica
        corrected_digits = [cls.CHAR_TO_DIGIT.get(c, c) for c in part_digits]

        # Corregir parte alfabética
        corrected_letters = [cls.DIGIT_TO_CHAR.get(c, c) for c in part_letters]

        return "".join(corrected_digits) + "".join(corrected_letters)

    @classmethod
    def normalize(cls, raw_text: str) -> Tuple[str, str, bool]:
        """Normaliza el texto OCR y valida si corresponde a una patente boliviana.
        
        Returns:
            (plate_raw, plate_normalized, is_valid)
        """
        cleaned = cls.clean_text(raw_text)
        if not cleaned:
            return (raw_text.strip(), "", False)

        # Si ya coincide exactamente con la regex
        if cls.BOLIVIAN_PLATE_REGEX.match(cleaned):
            return (raw_text.strip(), cleaned, True)

        # Intentar desambiguar si tiene longitud de 6 o 7 caracteres
        candidate = cls.disambiguate_bolivian_plate(cleaned)
        if cls.BOLIVIAN_PLATE_REGEX.match(candidate):
            return (raw_text.strip(), candidate, True)

        # Si hay más caracteres (por ejemplo ruido adicional al inicio o final),
        # buscar una subsecuencia de 6 o 7 caracteres que cumpla el patrón
        for i in range(len(cleaned) - 5):
            for length in (7, 6):
                sub = cleaned[i:i + length]
                if len(sub) == length:
                    sub_cand = cls.disambiguate_bolivian_plate(sub)
                    if cls.BOLIVIAN_PLATE_REGEX.match(sub_cand):
                        return (raw_text.strip(), sub_cand, True)

        # Si no cumple el formato boliviano estricto pero tiene al menos 4 caracteres alfanuméricos
        return (raw_text.strip(), cleaned, False)
