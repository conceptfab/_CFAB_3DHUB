"""
ThumbnailProperties - właściwości miniaturek.
Wydzielone z config_properties.py dla lepszej separacji odpowiedzialności.
ETAP 3.1: Podział na kategorie właściwości.
"""

import logging
from typing import Any, Dict, Tuple

from src.config.config_defaults import ConfigDefaults
from src.config.config_validator import ConfigValidator


class ThumbnailProperties:
    """
    Klasa odpowiedzialna za właściwości miniaturek - rozmiar, pozycja suwaka, zakres.
    Wydzielona z ConfigProperties dla lepszej separacji odpowiedzialności.
    """

    def __init__(self, config: Dict[str, Any], config_io):
        """
        Inicjalizuje ThumbnailProperties.

        Args:
            config: Referencja do słownika konfiguracji
            config_io: Instancja ConfigIO do zapisywania
        """
        self.logger = logging.getLogger(__name__)
        self._config = config
        self._config_io = config_io
        self._thumbnail_size = (250, 250)  # Cache rozmiaru miniaturek
        self._calculate_thumbnail_size()

    def _calculate_thumbnail_size(self) -> None:
        """
        Oblicza rozmiar miniaturek na podstawie pozycji suwaka i zakresu.
        Optymalizacja - cache wyniku w _thumbnail_size.
        """
        # PRIORYTET: default_thumbnail_size z configu użytkownika
        default_size = self._config.get("default_thumbnail_size")
        if default_size is not None:
            try:
                validated = int(default_size)
                if validated < 20 or validated > 2000:
                    raise ValueError("default_thumbnail_size poza zakresem 20-2000")
                self._thumbnail_size = (validated, validated)
                self.logger.info(f"[THUMBNAIL] Użyto default_thumbnail_size z configu: {validated}px")
                return
            except Exception as e:
                self.logger.error(f"Błędna wartość default_thumbnail_size: {default_size} ({e}) – używam suwaka/min/max")
        slider_pos = self._config.get("thumbnail_slider_position", 50)
        min_size = self._config.get(
            "min_thumbnail_size", ConfigDefaults.get_default_value("min_thumbnail_size")
        )
        max_size = self._config.get(
            "max_thumbnail_size", ConfigDefaults.get_default_value("max_thumbnail_size")
        )

        if min_size >= max_size:
            self.logger.warning(
                f"Nieprawidłowy zakres miniaturek: {min_size}-{max_size}"
            )
            # Użyj domyślnych wartości
            min_size = ConfigDefaults.get_default_value("min_thumbnail_size")
            max_size = ConfigDefaults.get_default_value("max_thumbnail_size")

        size_range = max_size - min_size
        width = min_size + int((size_range * slider_pos) / 100)
        self._thumbnail_size = (width, width)

        self.logger.debug(
            f"Obliczony rozmiar miniaturek: {width}px (slider: {slider_pos}%)"
        )

    def _save_and_recalculate(self) -> None:
        """
        Wspólna metoda dla zapisywania konfiguracji i przeliczania rozmiaru.
        Eliminuje duplikację kodu w setterach.
        """
        self._config_io.schedule_async_save(self._config)
        self._calculate_thumbnail_size()

    def get_thumbnail_slider_position(self) -> int:
        """
        Pobiera pozycję suwaka miniaturek.

        Returns:
            Pozycja suwaka (0-100)
        """
        return self._config.get("thumbnail_slider_position", 50)

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
                position, 0, 100, "Pozycja suwaka miniaturek"
            )

            old_position = self._config.get("thumbnail_slider_position", 50)
            if old_position == validated_position:
                self.logger.debug("Pozycja suwaka nie uległa zmianie")
                return True

            self._config["thumbnail_slider_position"] = validated_position
            self._save_and_recalculate()

            self.logger.info(f"Pozycja suwaka miniaturek: {validated_position}%")
            return True

        except ValueError as e:
            self.logger.error(f"Błąd ustawiania pozycji suwaka: {e}")
            return False

    def get_thumbnail_size_range(self) -> Tuple[int, int]:
        """
        Pobiera zakres rozmiarów miniaturek.

        Returns:
            Tuple (min_size, max_size)
        """
        min_size = self._config.get(
            "min_thumbnail_size", ConfigDefaults.get_default_value("min_thumbnail_size")
        )
        max_size = self._config.get(
            "max_thumbnail_size", ConfigDefaults.get_default_value("max_thumbnail_size")
        )
        return (min_size, max_size)

    def set_thumbnail_size_range(self, min_size: int, max_size: int) -> bool:
        """
        Ustawia zakres rozmiarów miniaturek z walidacją cross-property.

        Args:
            min_size: Minimalny rozmiar miniaturek
            max_size: Maksymalny rozmiar miniaturek

        Returns:
            True jeśli zakres został ustawiony
        """
        try:
            # Walidacja podstawowa
            validated_min = ConfigValidator.validate_int(
                min_size, 50, 1000, "Minimalny rozmiar miniaturek"
            )
            validated_max = ConfigValidator.validate_int(
                max_size, 100, 2000, "Maksymalny rozmiar miniaturek"
            )

            # Cross-property validation - nowa funkcjonalność
            if validated_min >= validated_max:
                raise ValueError(
                    f"Minimalny rozmiar ({validated_min}) musi być mniejszy "
                    f"od maksymalnego ({validated_max})"
                )

            # Sprawdź czy wartości się zmieniły
            current_min, current_max = self.get_thumbnail_size_range()
            if current_min == validated_min and current_max == validated_max:
                self.logger.debug("Zakres miniaturek nie uległ zmianie")
                return True

            # Atomowa zmiana obu wartości
            self._config["min_thumbnail_size"] = validated_min
            self._config["max_thumbnail_size"] = validated_max
            self._save_and_recalculate()

            self.logger.info(
                f"Zakres rozmiarów miniaturek: {validated_min}-{validated_max}px"
            )
            return True

        except ValueError as e:
            self.logger.error(f"Błąd ustawiania zakresu miniaturek: {e}")
            return False

    @property
    def thumbnail_size(self) -> Tuple[int, int]:
        """
        Pobiera aktualny rozmiar miniaturek jako tuple (width, height).

        Returns:
            Tuple z rozmiarem miniaturek (width, height)
        """
        # PRIORYTET: default_thumbnail_size z configu użytkownika
        default_size = self._config.get("default_thumbnail_size")
        if default_size is not None:
            try:
                validated = int(default_size)
                if validated < 20 or validated > 2000:
                    raise ValueError("default_thumbnail_size poza zakresem 20-2000")
                return (validated, validated)
            except Exception as e:
                self.logger.error(f"Błędna wartość default_thumbnail_size: {default_size} ({e}) – używam suwaka/min/max")
        return self._thumbnail_size

    def get_current_thumbnail_width(self) -> int:
        """
        Pobiera aktualną szerokość miniaturek.

        Returns:
            Szerokość miniaturek w pikselach
        """
        # PRIORYTET: default_thumbnail_size z configu użytkownika
        default_size = self._config.get("default_thumbnail_size")
        if default_size is not None:
            try:
                validated = int(default_size)
                if validated < 20 or validated > 2000:
                    raise ValueError("default_thumbnail_size poza zakresem 20-2000")
                return validated
            except Exception as e:
                self.logger.error(f"Błędna wartość default_thumbnail_size: {default_size} ({e}) – używam suwaka/min/max")
        return self._thumbnail_size[0]

    def reset_to_defaults(self) -> bool:
        """
        Resetuje wszystkie właściwości miniaturek do wartości domyślnych.

        Returns:
            True jeśli reset się powiódł
        """
        try:
            default_position = 50
            default_min = ConfigDefaults.get_default_value("min_thumbnail_size")
            default_max = ConfigDefaults.get_default_value("max_thumbnail_size")

            self._config["thumbnail_slider_position"] = default_position
            self._config["min_thumbnail_size"] = default_min
            self._config["max_thumbnail_size"] = default_max

            self._save_and_recalculate()

            self.logger.info("Właściwości miniaturek zresetowane do domyślnych")
            return True

        except Exception as e:
            self.logger.error(f"Błąd resetowania właściwości miniaturek: {e}")
            return False

    def validate_current_settings(self) -> bool:
        """
        Waliduje obecne ustawienia miniaturek.

        Returns:
            True jeśli wszystkie ustawienia są prawidłowe
        """
        try:
            position = self.get_thumbnail_slider_position()
            min_size, max_size = self.get_thumbnail_size_range()

            # Walidacja pozycji suwaka
            if not (0 <= position <= 100):
                self.logger.warning(f"Nieprawidłowa pozycja suwaka: {position}")
                return False

            # Walidacja zakresu
            if min_size >= max_size:
                self.logger.warning(f"Nieprawidłowy zakres: {min_size}-{max_size}")
                return False

            # Walidacja granic
            if not (50 <= min_size <= 1000) or not (100 <= max_size <= 2000):
                self.logger.warning(
                    f"Zakres poza dozwolonymi granicami: {min_size}-{max_size}"
                )
                return False

            return True

        except Exception as e:
            self.logger.error(f"Błąd walidacji ustawień miniaturek: {e}")
            return False
