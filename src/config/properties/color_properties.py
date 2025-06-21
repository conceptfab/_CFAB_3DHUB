"""
ColorProperties - właściwości kolorów i tagów kolorów.
Wydzielone z config_properties.py dla lepszej separacji odpowiedzialności.
ETAP 3.1: Podział na kategorie właściwości.
"""

import logging
import re
from collections import OrderedDict
from typing import Any, Dict

from src.config.config_defaults import ConfigDefaults
from src.config.config_validator import ConfigValidator


class ColorProperties:
    """
    Klasa odpowiedzialna za zarządzanie kolorami i tagami kolorów.
    Wydzielona z ConfigProperties dla lepszej separacji odpowiedzialności.
    """

    def __init__(self, config: Dict[str, Any], config_io):
        """
        Inicjalizuje ColorProperties.

        Args:
            config: Referencja do słownika konfiguracji
            config_io: Instancja ConfigIO do zapisywania
        """
        self.logger = logging.getLogger(__name__)
        self._config = config
        self._config_io = config_io
        self._hex_color_pattern = re.compile(r"^#[0-9A-Fa-f]{6}$")

    def _save_config(self) -> None:
        """
        Wspólna metoda dla zapisywania konfiguracji.
        Eliminuje duplikację kodu w setterach.
        """
        self._config_io.schedule_async_save(self._config)

    def _validate_hex_color(self, color: str) -> str:
        """
        Waliduje format koloru hex.

        Args:
            color: Kolor do walidacji

        Returns:
            Zwalidowany kolor w formacie hex

        Raises:
            ValueError: Gdy kolor ma nieprawidłowy format
        """
        if not isinstance(color, str):
            raise ValueError(f"Kolor musi być stringiem: {color}")

        # Normalizuj kolor
        normalized_color = color.strip().upper()
        if not normalized_color.startswith("#"):
            normalized_color = f"#{normalized_color}"

        if not self._hex_color_pattern.match(normalized_color):
            raise ValueError(f"Nieprawidłowy format koloru hex: {color}")

        return normalized_color

    def _validate_color_name(self, name: str) -> str:
        """
        Waliduje nazwę koloru.

        Args:
            name: Nazwa koloru do walidacji

        Returns:
            Zwalidowana nazwa koloru

        Raises:
            ValueError: Gdy nazwa jest nieprawidłowa
        """
        if not isinstance(name, str):
            raise ValueError(f"Nazwa koloru musi być stringiem: {name}")

        name = name.strip()
        if not name:
            raise ValueError("Nazwa koloru nie może być pusta")

        if len(name) > 50:
            raise ValueError(f"Nazwa koloru jest za długa (max 50 znaków): {name}")

        return name

    def get_predefined_colors(self) -> Dict[str, str]:
        """
        Pobiera słownik predefiniowanych kolorów.

        Returns:
            Słownik kolorów {nazwa: kod_hex}
        """
        colors = self._config.get(
            "predefined_colors",
            ConfigDefaults.get_default_value("predefined_colors", {}),
        )

        if not isinstance(colors, dict):
            self.logger.warning(
                f"Nieprawidłowy typ kolorów: {type(colors)}, używam domyślnych"
            )
            return ConfigDefaults.get_default_value("predefined_colors", {})

        return colors

    def set_predefined_colors(self, colors: Dict[str, str]) -> bool:
        """
        Ustawia słownik predefiniowanych kolorów z walidacją każdego koloru.

        Args:
            colors: Słownik kolorów {nazwa: kod_hex}

        Returns:
            True jeśli kolory zostały ustawione
        """
        try:
            # Walidacja podstawowa słownika
            validated_colors = ConfigValidator.validate_dict(colors, "Kolory")

            # Walidacja każdego koloru osobno
            final_colors = {}
            for name, color in validated_colors.items():
                validated_name = self._validate_color_name(name)
                validated_color = self._validate_hex_color(color)
                final_colors[validated_name] = validated_color

            # Sprawdź czy kolory się zmieniły
            current_colors = self.get_predefined_colors()
            if current_colors == final_colors:
                self.logger.debug("Kolory nie uległy zmianie")
                return True

            self._config["predefined_colors"] = final_colors
            self._save_config()

            self.logger.info(
                f"Predefiniowane kolory zaktualizowane: {len(final_colors)} kolorów"
            )
            return True

        except ValueError as e:
            self.logger.error(f"Błąd ustawiania kolorów: {e}")
            return False

    def add_color(self, name: str, color: str) -> bool:
        """
        Dodaje pojedynczy kolor do listy predefiniowanych.

        Args:
            name: Nazwa koloru
            color: Kod koloru hex

        Returns:
            True jeśli kolor został dodany
        """
        try:
            validated_name = self._validate_color_name(name)
            validated_color = self._validate_hex_color(color)

            current_colors = self.get_predefined_colors()

            if validated_name in current_colors:
                if current_colors[validated_name] == validated_color:
                    self.logger.debug(f"Kolor już istnieje: {validated_name}")
                    return True
                else:
                    self.logger.info(
                        f"Aktualizacja koloru {validated_name}: "
                        f"{current_colors[validated_name]} -> {validated_color}"
                    )

            new_colors = current_colors.copy()
            new_colors[validated_name] = validated_color

            return self.set_predefined_colors(new_colors)

        except Exception as e:
            self.logger.error(f"Błąd dodawania koloru {name}: {e}")
            return False

    def remove_color(self, name: str) -> bool:
        """
        Usuwa kolor z listy predefiniowanych.

        Args:
            name: Nazwa koloru do usunięcia

        Returns:
            True jeśli kolor został usunięty
        """
        try:
            current_colors = self.get_predefined_colors()

            if name not in current_colors:
                self.logger.debug(f"Kolor nie istnieje: {name}")
                return True

            new_colors = {k: v for k, v in current_colors.items() if k != name}
            result = self.set_predefined_colors(new_colors)

            if result:
                self.logger.info(f"Usunięto kolor: {name}")

            return result

        except Exception as e:
            self.logger.error(f"Błąd usuwania koloru {name}: {e}")
            return False

    def get_color_by_name(self, name: str) -> str:
        """
        Pobiera kod koloru po nazwie.

        Args:
            name: Nazwa koloru

        Returns:
            Kod koloru hex lub pusty string jeśli nie znaleziono
        """
        colors = self.get_predefined_colors()
        return colors.get(name, "")

    def color_exists(self, name: str) -> bool:
        """
        Sprawdza czy kolor o podanej nazwie istnieje.

        Args:
            name: Nazwa koloru

        Returns:
            True jeśli kolor istnieje
        """
        colors = self.get_predefined_colors()
        return name in colors

    @property
    def predefined_colors_filter(self) -> OrderedDict:
        """
        Pobiera kolory jako OrderedDict dla filtrów z zachowaniem kolejności.

        Returns:
            OrderedDict kolorów dla komponentów UI
        """
        colors = self.get_predefined_colors()

        # Specjalne sortowanie - "Wszystkie kolory" zawsze na początku
        sorted_colors = OrderedDict()

        if "Wszystkie kolory" in colors:
            sorted_colors["Wszystkie kolory"] = colors["Wszystkie kolory"]

        # Pozostałe kolory alfabetycznie
        remaining_colors = {k: v for k, v in colors.items() if k != "Wszystkie kolory"}
        for name in sorted(remaining_colors.keys()):
            sorted_colors[name] = remaining_colors[name]

        return sorted_colors

    def reset_to_defaults(self) -> bool:
        """
        Resetuje kolory do wartości domyślnych.

        Returns:
            True jeśli reset się powiódł
        """
        try:
            default_colors = ConfigDefaults.get_default_value("predefined_colors", {})
            self._config["predefined_colors"] = default_colors
            self._save_config()

            self.logger.info("Kolory zresetowane do domyślnych")
            return True

        except Exception as e:
            self.logger.error(f"Błąd resetowania kolorów: {e}")
            return False

    def validate_all_colors(self) -> bool:
        """
        Waliduje wszystkie obecne kolory.

        Returns:
            True jeśli wszystkie kolory są prawidłowe
        """
        try:
            colors = self.get_predefined_colors()

            for name, color in colors.items():
                try:
                    self._validate_color_name(name)
                    self._validate_hex_color(color)
                except ValueError as e:
                    self.logger.warning(f"Nieprawidłowy kolor {name}: {e}")
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Błąd walidacji kolorów: {e}")
            return False

    def get_colors_count(self) -> int:
        """
        Pobiera liczbę zdefiniowanych kolorów.

        Returns:
            Liczba kolorów
        """
        colors = self.get_predefined_colors()
        return len(colors)

    def cleanup_invalid_colors(self) -> bool:
        """
        Usuwa nieprawidłowe kolory z konfiguracji.

        Returns:
            True jeśli operacja się powiodła
        """
        try:
            colors = self.get_predefined_colors()
            valid_colors = {}
            removed_count = 0

            for name, color in colors.items():
                try:
                    validated_name = self._validate_color_name(name)
                    validated_color = self._validate_hex_color(color)
                    valid_colors[validated_name] = validated_color
                except ValueError as e:
                    self.logger.warning(f"Usuwam nieprawidłowy kolor {name}: {e}")
                    removed_count += 1

            if removed_count > 0:
                self._config["predefined_colors"] = valid_colors
                self._save_config()
                self.logger.info(f"Usunięto {removed_count} nieprawidłowych kolorów")

            return True

        except Exception as e:
            self.logger.error(f"Błąd czyszczenia kolorów: {e}")
            return False
