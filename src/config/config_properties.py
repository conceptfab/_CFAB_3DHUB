"""
ConfigProperties - fasada dla wszystkich właściwości konfiguracji.
🚀 ETAP 3: Refaktoryzacja - delegacja do specjalistycznych klas właściwości.
ETAP 3.1: Podział na kategorie właściwości - ZAIMPLEMENTOWANE.
"""

import logging
from collections import OrderedDict
from typing import Any, Dict, List, Tuple

from .properties import (
    ColorProperties,
    ExtensionProperties,
    FormatProperties,
    ThumbnailProperties,
)

logger = logging.getLogger(__name__)


class ConfigProperties:
    """
    Fasada dla wszystkich właściwości konfiguracji.
    Deleguje odpowiedzialności do specjalistycznych klas właściwości.

    REFAKTORYZACJA ETAP 3.1:
    - ThumbnailProperties: rozmiar, pozycja suwaka, zakres miniaturek
    - ExtensionProperties: obsługiwane rozszerzenia plików
    - ColorProperties: kolory i tagi kolorów
    - FormatProperties: formaty i jakość miniaturek

    Zachowuje pełną backward compatibility.
    """

    def __init__(self, config: Dict[str, Any], config_io):
        """
        Inicjalizuje ConfigProperties z delegacją do specjalistycznych klas.

        Args:
            config: Słownik konfiguracji
            config_io: Instancja ConfigIO do zapisywania
        """
        self._config = config
        self._config_io = config_io

        # Inicjalizacja specjalistycznych klas właściwości
        self._thumbnail_props = ThumbnailProperties(config, config_io)
        self._extension_props = ExtensionProperties(config, config_io)
        self._color_props = ColorProperties(config, config_io)
        self._format_props = FormatProperties(config, config_io)

        logger.debug(
            "ConfigProperties zainicjalizowane z delegacją do specjalistycznych klas"
        )

    # --- Generic methods (zachowane) ---

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
            logger.debug(f"Konfiguracja zaktualizowana: {key} = {value}")
            return True
        except Exception as e:
            logger.error(f"Błąd ustawiania konfiguracji {key}: {e}")
            return False

    # --- Thumbnail properties delegation ---

    def set_thumbnail_slider_position(self, position: int) -> bool:
        """Delegacja do ThumbnailProperties."""
        return self._thumbnail_props.set_thumbnail_slider_position(position)

    def get_thumbnail_slider_position(self) -> int:
        """Delegacja do ThumbnailProperties."""
        return self._thumbnail_props.get_thumbnail_slider_position()

    def set_thumbnail_size_range(self, min_size: int, max_size: int) -> bool:
        """Delegacja do ThumbnailProperties."""
        return self._thumbnail_props.set_thumbnail_size_range(min_size, max_size)

    def get_thumbnail_size_range(self) -> Tuple[int, int]:
        """Delegacja do ThumbnailProperties."""
        return self._thumbnail_props.get_thumbnail_size_range()

    @property
    def thumbnail_size(self) -> Tuple[int, int]:
        """Delegacja do ThumbnailProperties."""
        return self._thumbnail_props.thumbnail_size

    # --- Extension properties delegation ---

    def get_supported_extensions(self, extension_type: str) -> List[str]:
        """Delegacja do ExtensionProperties."""
        return self._extension_props.get_supported_extensions(extension_type)

    def set_supported_extensions(
        self, extension_type: str, extensions: List[str]
    ) -> bool:
        """Delegacja do ExtensionProperties."""
        return self._extension_props.set_supported_extensions(
            extension_type, extensions
        )

    @property
    def special_folders(self) -> List[str]:
        """Delegacja do ExtensionProperties."""
        return self._extension_props.special_folders

    # --- Color properties delegation ---

    def get_predefined_colors(self) -> Dict[str, str]:
        """Delegacja do ColorProperties."""
        return self._color_props.get_predefined_colors()

    def set_predefined_colors(self, colors: Dict[str, str]) -> bool:
        """Delegacja do ColorProperties."""
        return self._color_props.set_predefined_colors(colors)

    @property
    def predefined_colors_filter(self) -> OrderedDict:
        """Delegacja do ColorProperties."""
        return self._color_props.predefined_colors_filter

    # --- Format properties delegation ---

    def get_thumbnail_format(self) -> str:
        """Delegacja do FormatProperties."""
        return self._format_props.get_thumbnail_format()

    def set_thumbnail_format(self, format_name: str) -> bool:
        """Delegacja do FormatProperties."""
        return self._format_props.set_thumbnail_format(format_name)

    def get_thumbnail_quality(self) -> int:
        """Delegacja do FormatProperties."""
        return self._format_props.get_thumbnail_quality()

    def set_thumbnail_quality(self, quality: int) -> bool:
        """Delegacja do FormatProperties."""
        return self._format_props.set_thumbnail_quality(quality)

    def get_thumbnail_webp_method(self) -> int:
        """Delegacja do FormatProperties."""
        return self._format_props.get_thumbnail_webp_method()

    def set_thumbnail_webp_method(self, method: int) -> bool:
        """Delegacja do FormatProperties."""
        return self._format_props.set_thumbnail_webp_method(method)

    def get_thumbnail_preserve_transparency(self) -> bool:
        """Delegacja do FormatProperties."""
        return self._format_props.get_thumbnail_preserve_transparency()

    def set_thumbnail_preserve_transparency(self, preserve: bool) -> bool:
        """Delegacja do FormatProperties."""
        return self._format_props.set_thumbnail_preserve_transparency(preserve)

    # --- Advanced methods (nowe funkcjonalności) ---

    def reset_all_to_defaults(self) -> bool:
        """
        Resetuje wszystkie właściwości do wartości domyślnych.

        Returns:
            True jeśli reset się powiódł
        """
        try:
            success = True
            success &= self._thumbnail_props.reset_to_defaults()
            success &= self._extension_props.reset_to_defaults()
            success &= self._color_props.reset_to_defaults()
            success &= self._format_props.reset_format_settings()

            if success:
                logger.info("Wszystkie właściwości zresetowane do domyślnych")
            else:
                logger.warning("Niektóre właściwości nie zostały zresetowane")

            return success

        except Exception as e:
            logger.error(f"Błąd resetowania wszystkich właściwości: {e}")
            return False

    def validate_all_settings(self) -> bool:
        """
        Waliduje wszystkie ustawienia konfiguracji.

        Returns:
            True jeśli wszystkie ustawienia są prawidłowe
        """
        try:
            thumbnail_valid = self._thumbnail_props.validate_current_settings()
            extension_valid = self._extension_props.validate_extension_lists()
            color_valid = self._color_props.validate_all_colors()
            format_valid = self._format_props.validate_format_settings()

            all_valid = (
                thumbnail_valid and extension_valid and color_valid and format_valid
            )

            if all_valid:
                logger.info("Wszystkie ustawienia konfiguracji są prawidłowe")
            else:
                logger.warning("Wykryto nieprawidłowe ustawienia konfiguracji")

            return all_valid

        except Exception as e:
            logger.error(f"Błąd walidacji ustawień: {e}")
            return False

    def get_properties_summary(self) -> Dict[str, Any]:
        """
        Pobiera podsumowanie wszystkich właściwości.

        Returns:
            Słownik z podsumowaniem właściwości
        """
        try:
            return {
                "thumbnail": {
                    "size": self._thumbnail_props.thumbnail_size,
                    "slider_position": self._thumbnail_props.get_thumbnail_slider_position(),
                    "size_range": self._thumbnail_props.get_thumbnail_size_range(),
                },
                "extensions": {
                    "archive": self._extension_props.get_supported_extensions(
                        "archive"
                    ),
                    "preview": self._extension_props.get_supported_extensions(
                        "preview"
                    ),
                    "special_folders": self._extension_props.special_folders,
                },
                "colors": {
                    "count": self._color_props.get_colors_count(),
                    "colors": self._color_props.get_predefined_colors(),
                },
                "format": self._format_props.get_format_info(),
            }

        except Exception as e:
            logger.error(f"Błąd pobierania podsumowania właściwości: {e}")
            return {}

    def cleanup_invalid_settings(self) -> bool:
        """
        Czyści wszystkie nieprawidłowe ustawienia.

        Returns:
            True jeśli operacja się powiodła
        """
        try:
            success = True
            success &= self._color_props.cleanup_invalid_colors()

            if success:
                logger.info("Wyczyszczono nieprawidłowe ustawienia")
            else:
                logger.warning(
                    "Nie udało się wyczyścić wszystkich nieprawidłowych ustawień"
                )

            return success

        except Exception as e:
            logger.error(f"Błąd czyszczenia ustawień: {e}")
            return False

    # --- Direct access to specialized classes (dla zaawansowanych użytkowników) ---

    @property
    def thumbnail_properties(self) -> ThumbnailProperties:
        """Bezpośredni dostęp do ThumbnailProperties."""
        return self._thumbnail_props

    @property
    def extension_properties(self) -> ExtensionProperties:
        """Bezpośredni dostęp do ExtensionProperties."""
        return self._extension_props

    @property
    def color_properties(self) -> ColorProperties:
        """Bezpośredni dostęp do ColorProperties."""
        return self._color_props

    @property
    def format_properties(self) -> FormatProperties:
        """Bezpośredni dostęp do FormatProperties."""
        return self._format_props
