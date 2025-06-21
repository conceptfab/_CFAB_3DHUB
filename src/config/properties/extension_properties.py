"""
ExtensionProperties - właściwości obsługiwanych rozszerzeń plików.
Wydzielone z config_properties.py dla lepszej separacji odpowiedzialności.
ETAP 3.1: Podział na kategorie właściwości.
"""

import logging
from typing import Any, Dict, List

from src.config.config_defaults import ConfigDefaults
from src.config.config_validator import ConfigValidator


class ExtensionProperties:
    """
    Klasa odpowiedzialna za zarządzanie obsługiwanymi rozszerzeniami plików.
    Wydzielona z ConfigProperties dla lepszej separacji odpowiedzialności.
    """

    def __init__(self, config: Dict[str, Any], config_io):
        """
        Inicjalizuje ExtensionProperties.

        Args:
            config: Referencja do słownika konfiguracji
            config_io: Instancja ConfigIO do zapisywania
        """
        self.logger = logging.getLogger(__name__)
        self._config = config
        self._config_io = config_io
        self._extension_types = {"archive", "preview"}

    def _save_config(self) -> None:
        """
        Wspólna metoda dla zapisywania konfiguracji.
        Eliminuje duplikację kodu w setterach.
        """
        self._config_io.schedule_async_save(self._config)

    def _validate_extension_type(self, extension_type: str) -> None:
        """
        Waliduje typ rozszerzeń.

        Args:
            extension_type: Typ rozszerzeń do walidacji

        Raises:
            ValueError: Gdy typ jest nieprawidłowy
        """
        if extension_type not in self._extension_types:
            raise ValueError(f"Nieznany typ rozszerzeń: {extension_type}")

    def _validate_extension_format(self, extensions: List[str]) -> List[str]:
        """
        Waliduje format rozszerzeń (muszą zaczynać się od '.').

        Args:
            extensions: Lista rozszerzeń do walidacji

        Returns:
            Lista zwalidowanych rozszerzeń

        Raises:
            ValueError: Gdy rozszerzenie ma nieprawidłowy format
        """
        validated = []
        for ext in extensions:
            if not isinstance(ext, str):
                raise ValueError(f"Rozszerzenie musi być stringiem: {ext}")
            if not ext.startswith("."):
                raise ValueError(f"Rozszerzenie musi zaczynać się od '.': {ext}")
            if len(ext) < 2:
                raise ValueError(f"Rozszerzenie jest za krótkie: {ext}")
            validated.append(ext.lower())  # Normalizacja do małych liter
        return validated

    def get_supported_extensions(self, extension_type: str) -> List[str]:
        """
        Pobiera listę obsługiwanych rozszerzeń.

        Args:
            extension_type: Typ rozszerzeń ('archive' lub 'preview')

        Returns:
            Lista obsługiwanych rozszerzeń
        """
        try:
            self._validate_extension_type(extension_type)

            config_key = f"supported_{extension_type}_extensions"
            default_key = f"supported_{extension_type}_extensions"

            extensions = self._config.get(
                config_key, ConfigDefaults.get_default_value(default_key, [])
            )

            if not isinstance(extensions, list):
                self.logger.warning(
                    f"Nieprawidłowy typ rozszerzeń {extension_type}: {type(extensions)}"
                )
                return ConfigDefaults.get_default_value(default_key, [])

            return extensions

        except ValueError as e:
            self.logger.warning(f"Błąd pobierania rozszerzeń: {e}")
            return []

    def set_supported_extensions(
        self, extension_type: str, extensions: List[str]
    ) -> bool:
        """
        Ustawia listę obsługiwanych rozszerzeń z pełną walidacją.

        Args:
            extension_type: Typ rozszerzeń ('archive' lub 'preview')
            extensions: Lista rozszerzeń

        Returns:
            True jeśli lista została ustawiona
        """
        try:
            # Walidacja typu rozszerzeń
            self._validate_extension_type(extension_type)

            # Walidacja podstawowa listy
            validated_extensions = ConfigValidator.validate_list(
                extensions, str, f"Rozszerzenia {extension_type}"
            )

            # Walidacja formatów rozszerzeń
            validated_extensions = self._validate_extension_format(validated_extensions)

            # Sprawdź czy lista się zmieniła
            current_extensions = self.get_supported_extensions(extension_type)
            if set(current_extensions) == set(validated_extensions):
                self.logger.debug(f"Rozszerzenia {extension_type} nie uległy zmianie")
                return True

            # Ustawienie konfiguracji
            config_key = f"supported_{extension_type}_extensions"
            self._config[config_key] = validated_extensions
            self._save_config()

            self.logger.info(
                f"Rozszerzenia {extension_type} zaktualizowane: "
                f"{len(validated_extensions)} rozszerzeń"
            )
            return True

        except ValueError as e:
            self.logger.error(f"Błąd ustawiania rozszerzeń {extension_type}: {e}")
            return False

    def add_extension(self, extension_type: str, extension: str) -> bool:
        """
        Dodaje pojedyncze rozszerzenie do listy.

        Args:
            extension_type: Typ rozszerzeń ('archive' lub 'preview')
            extension: Rozszerzenie do dodania

        Returns:
            True jeśli rozszerzenie zostało dodane
        """
        try:
            current_extensions = self.get_supported_extensions(extension_type)

            # Normalizuj rozszerzenie
            normalized_ext = extension.lower()
            if not normalized_ext.startswith("."):
                normalized_ext = f".{normalized_ext}"

            if normalized_ext in current_extensions:
                self.logger.debug(f"Rozszerzenie już istnieje: {normalized_ext}")
                return True

            new_extensions = current_extensions + [normalized_ext]
            return self.set_supported_extensions(extension_type, new_extensions)

        except Exception as e:
            self.logger.error(f"Błąd dodawania rozszerzenia {extension}: {e}")
            return False

    def remove_extension(self, extension_type: str, extension: str) -> bool:
        """
        Usuwa pojedyncze rozszerzenie z listy.

        Args:
            extension_type: Typ rozszerzeń ('archive' lub 'preview')
            extension: Rozszerzenie do usunięcia

        Returns:
            True jeśli rozszerzenie zostało usunięte
        """
        try:
            current_extensions = self.get_supported_extensions(extension_type)

            # Normalizuj rozszerzenie
            normalized_ext = extension.lower()
            if not normalized_ext.startswith("."):
                normalized_ext = f".{normalized_ext}"

            if normalized_ext not in current_extensions:
                self.logger.debug(f"Rozszerzenie nie istnieje: {normalized_ext}")
                return True

            new_extensions = [
                ext for ext in current_extensions if ext != normalized_ext
            ]
            return self.set_supported_extensions(extension_type, new_extensions)

        except Exception as e:
            self.logger.error(f"Błąd usuwania rozszerzenia {extension}: {e}")
            return False

    def get_all_supported_extensions(self) -> Dict[str, List[str]]:
        """
        Pobiera wszystkie obsługiwane rozszerzenia jako słownik.

        Returns:
            Słownik {typ: lista_rozszerzeń}
        """
        result = {}
        for ext_type in self._extension_types:
            result[ext_type] = self.get_supported_extensions(ext_type)
        return result

    def reset_to_defaults(self, extension_type: str = None) -> bool:
        """
        Resetuje rozszerzenia do wartości domyślnych.

        Args:
            extension_type: Typ do resetowania (None = wszystkie)

        Returns:
            True jeśli reset się powiódł
        """
        try:
            types_to_reset = (
                [extension_type] if extension_type else self._extension_types
            )

            for ext_type in types_to_reset:
                self._validate_extension_type(ext_type)

                default_key = f"supported_{ext_type}_extensions"
                default_extensions = ConfigDefaults.get_default_value(default_key, [])

                config_key = f"supported_{ext_type}_extensions"
                self._config[config_key] = default_extensions

            self._save_config()

            reset_types = ", ".join(types_to_reset)
            self.logger.info(f"Rozszerzenia {reset_types} zresetowane do domyślnych")
            return True

        except Exception as e:
            self.logger.error(f"Błąd resetowania rozszerzeń: {e}")
            return False

    def validate_extension_lists(self) -> bool:
        """
        Waliduje wszystkie listy rozszerzeń.

        Returns:
            True jeśli wszystkie listy są prawidłowe
        """
        try:
            for ext_type in self._extension_types:
                extensions = self.get_supported_extensions(ext_type)

                if not extensions:
                    self.logger.warning(f"Brak rozszerzeń {ext_type}")
                    continue

                # Walidacja każdego rozszerzenia
                for ext in extensions:
                    if not isinstance(ext, str) or not ext.startswith("."):
                        self.logger.warning(
                            f"Nieprawidłowe rozszerzenie {ext_type}: {ext}"
                        )
                        return False

            return True

        except Exception as e:
            self.logger.error(f"Błąd walidacji rozszerzeń: {e}")
            return False

    @property
    def special_folders(self) -> List[str]:
        """
        Pobiera listę nazw folderów specjalnych.

        Returns:
            Lista nazw folderów specjalnych
        """
        return self._config.get(
            "special_folders", ConfigDefaults.get_default_value("special_folders", [])
        )
