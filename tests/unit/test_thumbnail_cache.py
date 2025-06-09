"""
Test dla klasy ThumbnailCache.
"""
import os
import pytest
import time
from unittest.mock import Mock, patch

from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QPixmap

from src.ui.widgets.thumbnail_cache import ThumbnailCache


@pytest.fixture
def thumbnail_cache():
    """Fixture tworzący instancję ThumbnailCache ze zresetowanym stanem."""
    # Reset singletonu przed każdym testem
    ThumbnailCache._instance = None
    
    # Utwórz tymczasową konfigurację dla testów
    with patch('src.ui.widgets.thumbnail_cache.config') as mock_config:
        mock_config.thumbnail_cache_max_entries = 10
        mock_config.thumbnail_cache_max_memory_mb = 10
        mock_config.thumbnail_cache_cleanup_threshold = 0.8
        cache = ThumbnailCache.get_instance()
        yield cache
        # Cleanup po teście
        cache.clear_cache()


@pytest.fixture
def mock_pixmap():
    """Fixture tworzący symulowany QPixmap."""
    pixmap = Mock(spec=QPixmap)
    pixmap.isNull.return_value = False
    pixmap.width.return_value = 100
    pixmap.height.return_value = 100
    return pixmap


def test_singleton_instance():
    """Test czy ThumbnailCache działa jako singleton."""
    # Reset singletonu przed testem
    ThumbnailCache._instance = None
    
    # Pobierz dwie instancje
    instance1 = ThumbnailCache.get_instance()
    instance2 = ThumbnailCache.get_instance()
    
    # Sprawdź czy to ten sam obiekt
    assert instance1 is instance2


def test_add_and_get_thumbnail(thumbnail_cache, mock_pixmap):
    """Test dodawania i pobierania miniaturki z cache."""
    path = "test_image.jpg"
    width, height = 100, 100
    
    # Dodaj miniaturkę do cache
    thumbnail_cache.add_thumbnail(path, width, height, mock_pixmap)
    
    # Pobierz miniaturkę z cache
    result = thumbnail_cache.get_thumbnail(path, width, height)
    
    # Sprawdź czy to ta sama miniaturka
    assert result is mock_pixmap
    assert thumbnail_cache.get_cache_size() == 1


def test_schedule_cleanup(thumbnail_cache, mock_pixmap):
    """Test planowania asynchronicznego czyszczenia cache."""
    # Patch metody _schedule_cleanup do monitorowania wywołań
    with patch.object(thumbnail_cache, '_schedule_cleanup', wraps=thumbnail_cache._schedule_cleanup) as mock_schedule:
        # Dodaj miniaturkę do cache
        thumbnail_cache.add_thumbnail("test1.jpg", 100, 100, mock_pixmap)
        
        # Sprawdź czy _schedule_cleanup było wywołane
        assert mock_schedule.call_count == 1


def test_timer_cleanup_scheduling(thumbnail_cache, mock_pixmap):
    """Test czy timer cleanup jest uruchamiany prawidłowo."""
    # Patch metody timera start do monitorowania wywołań
    with patch.object(thumbnail_cache._cleanup_timer, 'start') as mock_timer_start:
        # Symuluj przekroczenie progu
        # Ustawiamy czyszczenie na 80% z 10 elementów = 8
        for i in range(9):  # Dodajemy 9 elementów (> 8)
            thumbnail_cache.add_thumbnail(f"test{i}.jpg", 100, 100, mock_pixmap)
        
        # Sprawdź czy timer został uruchomiony
        mock_timer_start.assert_called_once()


def test_critical_cleanup(thumbnail_cache, mock_pixmap):
    """Test natychmiastowego cleanupa przy krytycznym poziomie."""
    # Patch metody _perform_cleanup do monitorowania wywołań
    with patch.object(thumbnail_cache, '_perform_cleanup') as mock_cleanup:
        # Ustaw bardzo duży rozmiar pixmapa aby przekroczyć krytyczny próg
        big_pixmap = Mock(spec=QPixmap)
        big_pixmap.isNull.return_value = False
        big_pixmap.width.return_value = 5000
        big_pixmap.height.return_value = 5000  # To powinno przekroczyć 95% limitu
        
        # Dodaj dużą miniaturkę
        thumbnail_cache.add_thumbnail("big_image.jpg", 5000, 5000, big_pixmap)
        
        # Sprawdź czy _perform_cleanup było wywołane natychmiast
        mock_cleanup.assert_called_once()


def test_cache_memory_usage(thumbnail_cache, mock_pixmap):
    """Test raportowania użycia pamięci cache."""
    # Dodaj miniaturkę do cache
    thumbnail_cache.add_thumbnail("test1.jpg", 100, 100, mock_pixmap)
    
    # Pobierz statystyki
    stats = thumbnail_cache.get_cache_memory_usage()
    
    # Sprawdź czy statystyki mają odpowiednie klucze
    assert "entries" in stats
    assert "memory_bytes" in stats
    assert "memory_mb" in stats
    assert stats["entries"] == 1
    
    # Sprawdź czy rozmiar w bajtach jest większy od zera
    assert stats["memory_bytes"] > 0


def test_remove_thumbnail(thumbnail_cache, mock_pixmap):
    """Test usuwania pojedynczej miniaturki z cache."""
    path = "test_image.jpg"
    width, height = 100, 100
    
    # Dodaj miniaturkę do cache
    thumbnail_cache.add_thumbnail(path, width, height, mock_pixmap)
    assert thumbnail_cache.get_cache_size() == 1
    
    # Usuń miniaturkę
    thumbnail_cache.remove_thumbnail(path, width, height)
    
    # Sprawdź czy cache jest pusty
    assert thumbnail_cache.get_cache_size() == 0
    assert thumbnail_cache.get_thumbnail(path, width, height) is None


def test_clear_cache(thumbnail_cache, mock_pixmap):
    """Test czyszczenia całego cache."""
    # Dodaj kilka miniaturek do cache
    for i in range(5):
        thumbnail_cache.add_thumbnail(f"test{i}.jpg", 100, 100, mock_pixmap)
    
    assert thumbnail_cache.get_cache_size() == 5
    
    # Wyczyść cache
    thumbnail_cache.clear_cache()
    
    # Sprawdź czy cache jest pusty
    assert thumbnail_cache.get_cache_size() == 0
    assert thumbnail_cache.get_cache_memory_usage()["memory_bytes"] == 0
    
    # Sprawdź czy timer został zatrzymany
    assert not thumbnail_cache._cleanup_timer.isActive()


def test_lru_behavior(thumbnail_cache):
    """Test zachowania LRU (Least Recently Used) w cache."""
    # Tworzymy mock piksmapy o różnych rozmiarach dla łatwiejszej identyfikacji
    pixmap1 = Mock(spec=QPixmap)
    pixmap1.isNull.return_value = False
    pixmap1.width.return_value = 100
    pixmap1.height.return_value = 100
    
    pixmap2 = Mock(spec=QPixmap)
    pixmap2.isNull.return_value = False
    pixmap2.width.return_value = 200
    pixmap2.height.return_value = 200
    
    # Dodaj miniaturki do cache
    thumbnail_cache.add_thumbnail("test1.jpg", 100, 100, pixmap1)
    thumbnail_cache.add_thumbnail("test2.jpg", 200, 200, pixmap2)
    
    # Dostęp do pierwszej miniaturki (aktualizuje LRU)
    thumbnail_cache.get_thumbnail("test1.jpg", 100, 100)
    
    # Testujemy wewnętrzny OrderedDict w cache
    # Ostatnio używanym powinien być test1.jpg
    cache_keys = list(thumbnail_cache._cache.keys())
    assert cache_keys[0] == thumbnail_cache._normalize_cache_key("test2.jpg", 200, 200)
    assert cache_keys[1] == thumbnail_cache._normalize_cache_key("test1.jpg", 100, 100)


def test_estimate_pixmap_size(thumbnail_cache, mock_pixmap):
    """Test ulepszonego szacowania rozmiaru pixmapy."""
    estimated_size = thumbnail_cache._estimate_pixmap_size(mock_pixmap)
    # Oczekiwana wartość: 100 * 100 * 4 * 0.5 = 20000 bajtów (z współczynnikiem kompresji)
    assert estimated_size == 20000


def test_perform_cleanup_logic(thumbnail_cache):
    """Test logiki czyszczenia cache."""
    # Tworzymy mock miniaturki
    pixmap = Mock(spec=QPixmap)
    pixmap.isNull.return_value = False
    pixmap.width.return_value = 100
    pixmap.height.return_value = 100
    
    # Dodaj więcej miniaturek niż limit czyszczenia (10 * 0.8 = 8)
    for i in range(9):
        thumbnail_cache.add_thumbnail(f"test{i}.jpg", 100, 100, pixmap)
    
    # Ręcznie wywołaj czyszczenie
    thumbnail_cache._perform_cleanup()
    
    # Po cleanup powinno zostać około 70% limitu (10 * 0.7 = 7)
    assert thumbnail_cache.get_cache_size() <= 7
