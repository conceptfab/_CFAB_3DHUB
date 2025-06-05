# tests/unit/test_app_config_performance.py
"""
Testy wydajnościowe dla modułu app_config.py.
"""

import os
import shutil
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.app_config import AppConfig


class TestAppConfigPerformance(unittest.TestCase):
    """Klasa testowa dla testów wydajnościowych app_config."""

    def setUp(self):
        """Przygotowanie środowiska przed każdym testem."""
        # Stwórz tymczasowy katalog na pliki konfiguracyjne
        self.test_config_dir = tempfile.mkdtemp()
        self.test_config_file = "test_config.json"

        # Instancja obiektu konfiguracji dla testów
        self.app_config = AppConfig(
            config_dir=self.test_config_dir, config_file=self.test_config_file
        )

    def tearDown(self):
        """Czyszczenie po każdym teście."""
        # Usuń tymczasowy katalog i wszystkie pliki
        shutil.rmtree(self.test_config_dir)

    def test_load_config_performance(self):
        """Test wydajności wczytywania konfiguracji."""
        iterations = 100
        start_time = time.time()

        for _ in range(iterations):
            config = AppConfig(
                config_dir=self.test_config_dir, config_file=self.test_config_file
            )

        total_time = time.time() - start_time
        avg_time = total_time / iterations

        print(
            f"\nCzas wczytywania konfiguracji (średnia z {iterations} iteracji): {avg_time:.6f} s"
        )
        # Cel wydajnościowy: poniżej 0.01s na wczytanie
        self.assertLess(
            avg_time, 0.01, f"Wczytywanie konfiguracji trwa zbyt długo: {avg_time:.6f}s"
        )

    def test_save_config_performance(self):
        """Test wydajności zapisywania konfiguracji."""
        iterations = 50
        start_time = time.time()

        for i in range(iterations):
            # Zmień wartość i zapisz
            self.app_config.set("test_value", i)

        total_time = time.time() - start_time
        avg_time = total_time / iterations

        print(
            f"\nCzas zapisywania konfiguracji (średnia z {iterations} iteracji): {avg_time:.6f} s"
        )
        # Cel wydajnościowy: poniżej 0.005s na zapis
        self.assertLess(
            avg_time,
            0.005,
            f"Zapisywanie konfiguracji trwa zbyt długo: {avg_time:.6f}s",
        )

    def test_frequent_config_changes(self):
        """Test wydajności przy częstych zmianach konfiguracji."""
        num_changes = 100
        start_time = time.time()

        # Symulacja intensywnego użycia konfiguracji
        for i in range(num_changes):
            position = i % 101  # 0-100
            self.app_config.set_thumbnail_slider_position(position)
            # Pobierz wartości po każdej zmianie
            _ = self.app_config.thumbnail_size

        total_time = time.time() - start_time

        print(f"\nCzas wykonania {num_changes} zmian konfiguracji: {total_time:.6f} s")
        print(f"Średni czas na operację: {total_time/num_changes:.6f} s")

        # Cel: poniżej 0.001s na operację zmiany i odczytu
        self.assertLess(
            total_time / num_changes,
            0.005,
            f"Operacje zmiany konfiguracji są zbyt wolne: {total_time/num_changes:.6f}s na operację",
        )


if __name__ == "__main__":
    unittest.main()
