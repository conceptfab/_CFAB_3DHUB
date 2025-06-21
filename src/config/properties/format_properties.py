"""
FormatProperties - właściwości formatów i jakości miniaturek.
Wydzielone z config_properties.py dla lepszej separacji odpowiedzialności.
ETAP 3.1: Podział na kategorie właściwości.
"""

import logging
from typing import Any, Dict, List

from src.config.config_defaults import ConfigDefaults
from src.config.config_validator import ConfigValidator


class FormatProperties:
    """
    Klasa odpowiedzialna za zarządzanie formatami i jakością miniaturek.
    Wydzielona z ConfigProperties dla lepszej separacji odpowiedzialności.
    """

    def __init__(self, config: Dict[str, Any], config_io):
        """
        Inicjalizuje FormatProperties.

        Args:
            config: Referencja do słownika konfiguracji
            config_io: Instancja ConfigIO do zapisywania
        """
        self.logger = logging.getLogger(__name__)
        self._config = config
        self._config_io = config_io
        self._supported_formats = {"WEBP", "JPEG", "PNG"}

    def _save_config(self) -> None:
        """
        Wspólna metoda dla zapisywania konfiguracji.
        Eliminuje duplikację kodu w setterach.
        """
        self._config_io.schedule_async_save(self._config)

    def _validate_format(self, format_name: str) -> str:
        """
        Waliduje format miniaturek.

        Args:
            format_name: Nazwa formatu do walidacji

        Returns:
            Zwalidowany format (wielkimi literami)

        Raises:
            ValueError: Gdy format jest nieobsługiwany
        """
        if not isinstance(format_name, str):
            raise ValueError(f"Format musi być stringiem: {format_name}")

        normalized_format = format_name.strip().upper()

        if normalized_format not in self._supported_formats:
            supported_list = ", ".join(sorted(self._supported_formats))
            raise ValueError(
                f"Nieobsługiwany format miniaturek: {format_name}. "
                f"Obsługiwane: {supported_list}"
            )

        return normalized_format

    def get_thumbnail_format(self) -> str:
        """
        Pobiera format miniaturek.

        Returns:
            Format miniaturek (WEBP, JPEG, PNG)
        """
        return self._config.get("thumbnail_format", "WEBP")

    def set_thumbnail_format(self, format_name: str) -> bool:
        """
        Ustawia format miniaturek z walidacją dostępności.

        Args:
            format_name: Nazwa formatu (WEBP, JPEG, PNG)

        Returns:
            True jeśli format został ustawiony
        """
        try:
            validated_format = ConfigValidator.validate_str(
                format_name, "Format miniaturek"
            )
            validated_format = self._validate_format(validated_format)

            # Sprawdź czy format się zmienił
            current_format = self.get_thumbnail_format()
            if current_format == validated_format:
                self.logger.debug("Format miniaturek nie uległ zmianie")
                return True

            self._config["thumbnail_format"] = validated_format
            self._save_config()

            self.logger.info(f"Format miniaturek zmieniony na: {validated_format}")
            return True

        except ValueError as e:
            self.logger.error(f"Błąd ustawiania formatu miniaturek: {e}")
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
        Ustawia jakość kompresji miniaturek z walidacją zakresu.

        Args:
            quality: Jakość kompresji (1-100)

        Returns:
            True jeśli jakość została ustawiona
        """
        try:
            validated_quality = ConfigValidator.validate_int(
                quality, 1, 100, "Jakość miniaturek"
            )

            # Sprawdź czy jakość się zmieniła
            current_quality = self.get_thumbnail_quality()
            if current_quality == validated_quality:
                self.logger.debug("Jakość miniaturek nie uległa zmianie")
                return True

            self._config["thumbnail_quality"] = validated_quality
            self._save_config()

            self.logger.info(f"Jakość miniaturek zmieniona na: {validated_quality}")
            return True

        except ValueError as e:
            self.logger.error(f"Błąd ustawiania jakości miniaturek: {e}")
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
        Ustawia metodę kompresji WebP z walidacją zakresu.

        Args:
            method: Metoda kompresji (0-6, wyższa = lepsza kompresja)

        Returns:
            True jeśli metoda została ustawiona
        """
        try:
            validated_method = ConfigValidator.validate_int(method, 0, 6, "Metoda WebP")

            # Sprawdź czy metoda się zmieniła
            current_method = self.get_thumbnail_webp_method()
            if current_method == validated_method:
                self.logger.debug("Metoda WebP nie uległa zmianie")
                return True

            self._config["thumbnail_webp_method"] = validated_method
            self._save_config()

            self.logger.info(f"Metoda WebP zmieniona na: {validated_method}")
            return True

        except ValueError as e:
            self.logger.error(f"Błąd ustawiania metody WebP: {e}")
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
        try:
            # Sprawdź czy ustawienie się zmieniło
            current_preserve = self.get_thumbnail_preserve_transparency()
            if current_preserve == preserve:
                self.logger.debug("Ustawienie przezroczystości nie uległo zmianie")
                return True

            self._config["thumbnail_preserve_transparency"] = preserve
            self._save_config()

            self.logger.info(f"Zachowywanie przezroczystości: {preserve}")
            return True

        except Exception as e:
            self.logger.error(f"Błąd ustawiania przezroczystości: {e}")
            return False

    def get_supported_formats(self) -> List[str]:
        """
        Pobiera listę obsługiwanych formatów.

        Returns:
            Lista obsługiwanych formatów miniaturek
        """
        return sorted(list(self._supported_formats))

    def is_format_supported(self, format_name: str) -> bool:
        """
        Sprawdza czy format jest obsługiwany.

        Args:
            format_name: Nazwa formatu do sprawdzenia

        Returns:
            True jeśli format jest obsługiwany
        """
        try:
            self._validate_format(format_name)
            return True
        except ValueError:
            return False

    def reset_format_settings(self) -> bool:
        """
        Resetuje wszystkie ustawienia formatów do domyślnych.

        Returns:
            True jeśli reset się powiódł
        """
        try:
            self._config["thumbnail_format"] = "WEBP"
            self._config["thumbnail_quality"] = 80
            self._config["thumbnail_webp_method"] = 6
            self._config["thumbnail_preserve_transparency"] = True

            self._save_config()

            self.logger.info("Ustawienia formatów zresetowane do domyślnych")
            return True

        except Exception as e:
            self.logger.error(f"Błąd resetowania formatów: {e}")
            return False

    def get_format_info(self) -> Dict[str, Any]:
        """
        Pobiera pełne informacje o ustawieniach formatów.

        Returns:
            Słownik z wszystkimi ustawieniami formatów
        """
        return {
            "format": self.get_thumbnail_format(),
            "quality": self.get_thumbnail_quality(),
            "webp_method": self.get_thumbnail_webp_method(),
            "preserve_transparency": self.get_thumbnail_preserve_transparency(),
            "supported_formats": self.get_supported_formats(),
        }

    def validate_format_settings(self) -> bool:
        """
        Waliduje wszystkie obecne ustawienia formatów.

        Returns:
            True jeśli wszystkie ustawienia są prawidłowe
        """
        try:
            # Walidacja formatu
            current_format = self.get_thumbnail_format()
            if not self.is_format_supported(current_format):
                self.logger.warning(f"Nieobsługiwany format: {current_format}")
                return False

            # Walidacja jakości
            quality = self.get_thumbnail_quality()
            if not (1 <= quality <= 100):
                self.logger.warning(f"Nieprawidłowa jakość: {quality}")
                return False

            # Walidacja metody WebP
            webp_method = self.get_thumbnail_webp_method()
            if not (0 <= webp_method <= 6):
                self.logger.warning(f"Nieprawidłowa metoda WebP: {webp_method}")
                return False

            # Walidacja przezroczystości
            preserve_transparency = self.get_thumbnail_preserve_transparency()
            if not isinstance(preserve_transparency, bool):
                self.logger.warning(
                    f"Nieprawidłowy typ przezroczystości: {type(preserve_transparency)}"
                )
                return False

            return True

        except Exception as e:
            self.logger.error(f"Błąd walidacji formatów: {e}")
            return False

    def optimize_for_format(self, format_name: str) -> bool:
        """
        Optymalizuje ustawienia dla konkretnego formatu.

        Args:
            format_name: Format do optymalizacji

        Returns:
            True jeśli optymalizacja się powiodła
        """
        try:
            validated_format = self._validate_format(format_name)

            # Optymalne ustawienia dla różnych formatów
            if validated_format == "WEBP":
                self.set_thumbnail_format("WEBP")
                self.set_thumbnail_quality(80)
                self.set_thumbnail_webp_method(6)
                self.set_thumbnail_preserve_transparency(True)
            elif validated_format == "JPEG":
                self.set_thumbnail_format("JPEG")
                self.set_thumbnail_quality(85)
                self.set_thumbnail_preserve_transparency(False)
            elif validated_format == "PNG":
                self.set_thumbnail_format("PNG")
                self.set_thumbnail_quality(100)  # PNG jest bezstratny
                self.set_thumbnail_preserve_transparency(True)

            self.logger.info(f"Optymalizacja dla formatu {validated_format} zakończona")
            return True

        except Exception as e:
            self.logger.error(f"Błąd optymalizacji dla {format_name}: {e}")
            return False
