"""
ConfigProperties - właściwości i gettery/settery konfiguracji.
🚀 ETAP 2: Refaktoryzacja AppConfig - komponent właściwości
"""

import logging
from collections import OrderedDict
from typing import Any, Dict, List, Tuple

from .config_defaults import ConfigDefaults
from .config_validator import ConfigValidator

logger = logging.getLogger(__name__)


class ConfigProperties:
    """
    Właściwości i gettery/settery dla konfiguracji.
    
    Odpowiedzialności:
    - Gettery i settery dla wszystkich właściwości konfiguracji
    - Walidacja wartości przy ustawianiu
    - Obliczanie wartości pochodnych
    - Property accessors dla backward compatibility
    """

    def __init__(self, config: Dict[str, Any], config_io):
        """
        Inicjalizuje ConfigProperties.
        
        Args:
            config: Słownik konfiguracji
            config_io: Instancja ConfigIO do zapisywania
        """
        self._config = config
        self._config_io = config_io
        self._thumbnail_size = (250, 250)  # Domyślny rozmiar
        self._update_derived_values()

    def _update_derived_values(self) -> None:
        """Aktualizuje wartości pochodne na podstawie konfiguracji."""
        slider_pos = self._config.get("thumbnail_slider_position", 50)
        min_size = self._config.get(
            "min_thumbnail_size", ConfigDefaults.get_default_value("min_thumbnail_size")
        )
        max_size = self._config.get(
            "max_thumbnail_size", ConfigDefaults.get_default_value("max_thumbnail_size")
        )

        size_range = max_size - min_size
        width = min_size + int((size_range * slider_pos) / 100)
        self._thumbnail_size = (width, width)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Pobiera wartość konfiguracji.

        Args:
            key: Klucz konfiguracji
            default: Wartość domyślna jeśli klucz nie istnieje

        Returns:
            Wartość konfiguracji lub default
        """
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """
        Ustawia wartość konfiguracji.

        Args:
            key: Klucz konfiguracji
            value: Nowa wartość

        Returns:
            True jeśli wartość została ustawiona
        """
        try:
            self._config[key] = value
            self._config_io.schedule_async_save(self._config)
            self._update_derived_values()
            logger.debug(f"Konfiguracja zaktualizowana: {key} = {value}")
            return True
        except Exception as e:
            logger.error(f"Błąd ustawiania konfiguracji {key}: {e}")
            return False

    # --- Thumbnail properties ---

    def set_thumbnail_slider_position(self, position: int) -> bool:
        """
        Ustawia pozycję suwaka miniaturek.

        Args:
            position: Pozycja suwaka (0-100)

        Returns:
            True jeśli pozycja została ustawiona
        """
        try:
            validated_position = ConfigValidator.validate_int(
                position, 0, 100, "Pozycja suwaka"
            )
            self._config["thumbnail_slider_position"] = validated_position
            self._update_derived_values()
            self._config_io.schedule_async_save(self._config)
            logger.debug(f"Pozycja suwaka miniaturek: {validated_position}%")
            return True
        except ValueError as e:
            logger.error(f"Błąd ustawiania pozycji suwaka: {e}")
            return False

    def get_thumbnail_slider_position(self) -> int:
        """
        Pobiera pozycję suwaka miniaturek.

        Returns:
            Pozycja suwaka (0-100)
        """
        return self._config.get("thumbnail_slider_position", 50)

    def set_thumbnail_size_range(self, min_size: int, max_size: int) -> bool:
        """
        Ustawia zakres rozmiarów miniaturek.

        Args:
            min_size: Minimalny rozmiar miniaturek
            max_size: Maksymalny rozmiar miniaturek

        Returns:
            True jeśli zakres został ustawiony
        """
        try:
            validated_min = ConfigValidator.validate_int(
                min_size, 50, 1000, "Minimalny rozmiar miniaturek"
            )
            validated_max = ConfigValidator.validate_int(
                max_size, 100, 2000, "Maksymalny rozmiar miniaturek"
            )

            if validated_min >= validated_max:
                raise ValueError(
                    f"Minimalny rozmiar ({validated_min}) musi być mniejszy od maksymalnego ({validated_max})"
                )

            self._config["min_thumbnail_size"] = validated_min
            self._config["max_thumbnail_size"] = validated_max
            self._update_derived_values()
            self._config_io.schedule_async_save(self._config)
            logger.info(
                f"Zakres rozmiarów miniaturek: {validated_min}-{validated_max}px"
            )
            return True
        except ValueError as e:
            logger.error(f"Błąd ustawiania zakresu miniaturek: {e}")
            return False

    @property
    def thumbnail_size(self) -> Tuple[int, int]:
        """Pobiera aktualny rozmiar miniaturek jako tuple (width, height)."""
        return self._thumbnail_size

    # --- Extensions properties ---

    def get_supported_extensions(self, extension_type: str) -> List[str]:
        """
        Pobiera listę obsługiwanych rozszerzeń.

        Args:
            extension_type: Typ rozszerzeń ('archive' lub 'preview')

        Returns:
            Lista obsługiwanych rozszerzeń
        """
        if extension_type == "archive":
            return self._config.get(
                "supported_archive_extensions",
                ConfigDefaults.get_default_value("supported_archive_extensions", [])
            )
        elif extension_type == "preview":
            return self._config.get(
                "supported_preview_extensions",
                ConfigDefaults.get_default_value("supported_preview_extensions", [])
            )
        else:
            logger.warning(f"Nieznany typ rozszerzeń: {extension_type}")
            return []

    def set_supported_extensions(
        self, extension_type: str, extensions: List[str]
    ) -> bool:
        """
        Ustawia listę obsługiwanych rozszerzeń.

        Args:
            extension_type: Typ rozszerzeń ('archive' lub 'preview')
            extensions: Lista rozszerzeń

        Returns:
            True jeśli lista została ustawiona
        """
        try:
            validated_extensions = ConfigValidator.validate_list(
                extensions, str, f"Rozszerzenia {extension_type}"
            )

            # Walidacja formatów rozszerzeń
            for ext in validated_extensions:
                if not ext.startswith("."):
                    raise ValueError(f"Rozszerzenie musi zaczynać się od '.': {ext}")

            if extension_type == "archive":
                self._config["supported_archive_extensions"] = validated_extensions
            elif extension_type == "preview":
                self._config["supported_preview_extensions"] = validated_extensions
            else:
                raise ValueError(f"Nieznany typ rozszerzeń: {extension_type}")

            self._config_io.schedule_async_save(self._config)
            logger.info(f"Rozszerzenia {extension_type} zaktualizowane: {validated_extensions}")
            return True
        except ValueError as e:
            logger.error(f"Błąd ustawiania rozszerzeń {extension_type}: {e}")
            return False

    # --- Colors properties ---

    def get_predefined_colors(self) -> Dict[str, str]:
        """
        Pobiera słownik predefiniowanych kolorów.

        Returns:
            Słownik kolorów {nazwa: kod_hex}
        """
        return self._config.get(
            "predefined_colors",
            ConfigDefaults.get_default_value("predefined_colors", {})
        )

    def set_predefined_colors(self, colors: Dict[str, str]) -> bool:
        """
        Ustawia słownik predefiniowanych kolorów.

        Args:
            colors: Słownik kolorów {nazwa: kod_hex}

        Returns:
            True jeśli kolory zostały ustawione
        """
        try:
            validated_colors = ConfigValidator.validate_dict(colors, "Kolory")
            self._config["predefined_colors"] = validated_colors
            self._config_io.schedule_async_save(self._config)
            logger.info(f"Predefiniowane kolory zaktualizowane: {len(validated_colors)} kolorów")
            return True
        except ValueError as e:
            logger.error(f"Błąd ustawiania kolorów: {e}")
            return False

    @property
    def predefined_colors_filter(self) -> OrderedDict:
        """Pobiera kolory jako OrderedDict dla filtrów."""
        colors = self.get_predefined_colors()
        return OrderedDict(colors)

    # --- Thumbnail format properties ---

    def get_thumbnail_format(self) -> str:
        """
        Pobiera format miniaturek.

        Returns:
            Format miniaturek (WEBP, JPEG, PNG)
        """
        return self._config.get("thumbnail_format", "WEBP")

    def set_thumbnail_format(self, format_name: str) -> bool:
        """
        Ustawia format miniaturek.

        Args:
            format_name: Nazwa formatu (WEBP, JPEG, PNG)

        Returns:
            True jeśli format został ustawiony
        """
        try:
            validated_format = ConfigValidator.validate_str(format_name, "Format miniaturek")
            
            if validated_format.upper() not in ["WEBP", "JPEG", "PNG"]:
                raise ValueError(f"Nieobsługiwany format miniaturek: {validated_format}")
            
            self._config["thumbnail_format"] = validated_format.upper()
            self._config_io.schedule_async_save(self._config)
            logger.info(f"Format miniaturek zmieniony na: {validated_format.upper()}")
            return True
        except ValueError as e:
            logger.error(f"Błąd ustawiania formatu miniaturek: {e}")
            return False

    def get_thumbnail_quality(self) -> int:
        """
        Pobiera jakość kompresji miniaturek.

        Returns:
            Jakość kompresji (1-100)
        """
        return self._config.get("thumbnail_quality", 80)

    def set_thumbnail_quality(self, quality: int) -> bool:
        """
        Ustawia jakość kompresji miniaturek.

        Args:
            quality: Jakość kompresji (1-100)

        Returns:
            True jeśli jakość została ustawiona
        """
        try:
            validated_quality = ConfigValidator.validate_int(quality, 1, 100, "Jakość miniaturek")
            self._config["thumbnail_quality"] = validated_quality
            self._config_io.schedule_async_save(self._config)
            logger.info(f"Jakość miniaturek zmieniona na: {validated_quality}")
            return True
        except ValueError as e:
            logger.error(f"Błąd ustawiania jakości miniaturek: {e}")
            return False

    def get_thumbnail_webp_method(self) -> int:
        """
        Pobiera metodę kompresji WebP.

        Returns:
            Metoda kompresji WebP (0-6)
        """
        return self._config.get("thumbnail_webp_method", 6)

    def set_thumbnail_webp_method(self, method: int) -> bool:
        """
        Ustawia metodę kompresji WebP.

        Args:
            method: Metoda kompresji (0-6, wyższa = lepsza kompresja)

        Returns:
            True jeśli metoda została ustawiona
        """
        try:
            validated_method = ConfigValidator.validate_int(method, 0, 6, "Metoda WebP")
            self._config["thumbnail_webp_method"] = validated_method
            self._config_io.schedule_async_save(self._config)
            logger.info(f"Metoda WebP zmieniona na: {validated_method}")
            return True
        except ValueError as e:
            logger.error(f"Błąd ustawiania metody WebP: {e}")
            return False

    def get_thumbnail_preserve_transparency(self) -> bool:
        """
        Sprawdza czy zachowywać przezroczystość w miniaturkach.

        Returns:
            True jeśli zachowywać przezroczystość
        """
        return self._config.get("thumbnail_preserve_transparency", True)

    def set_thumbnail_preserve_transparency(self, preserve: bool) -> bool:
        """
        Ustawia czy zachowywać przezroczystość w miniaturkach.

        Args:
            preserve: Czy zachowywać przezroczystość

        Returns:
            True jeśli ustawienie zostało zmienione
        """
        self._config["thumbnail_preserve_transparency"] = preserve
        self._config_io.schedule_async_save(self._config)
        logger.info(f"Zachowywanie przezroczystości: {preserve}")
        return True 