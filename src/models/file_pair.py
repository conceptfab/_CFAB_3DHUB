import os 
import logging 
from PIL import Image, UnidentifiedImageError 
from src.utils.image_utils import create_placeholder_pixmap, pillow_image_to_qpixmap 
 
 
class FilePair: 
    def __init__(self, archive_path, preview_path): 
        self.archive_path = archive_path 
        self.preview_path = preview_path 
        self.preview_thumbnail = None 
        self.archive_size_bytes = None 
        logging.debug(f"Utworzono nowy obiekt FilePair: {self.get_base_name()}") 
 
    def get_base_name(self): 
        return os.path.splitext(os.path.basename(self.archive_path))[0] 
 
    def get_archive_path(self): 
        return self.archive_path 
 
    def get_preview_path(self):
        return self.preview_path

    def load_preview_thumbnail(self, target_size_wh):
        """
        Wczytuje plik podglądu i tworzy z niego miniaturę o zadanym rozmiarze.
        
        Args:
            target_size_wh (tuple): Docelowy rozmiar miniatury (szerokość, wysokość) w pikselach
            
        Returns:
            QPixmap: Utworzona miniatura jako obiekt QPixmap
        """
        width, height = target_size_wh
        try:
            # Wczytanie obrazu przy użyciu Pillow
            with Image.open(self.preview_path) as img:
                # Utworzenie kopii obrazu do skalowania (thumbnail modyfikuje oryginalny obraz)
                thumbnail = img.copy()
                # Skalowanie z zachowaniem proporcji
                thumbnail.thumbnail(target_size_wh, Image.LANCZOS)
                
                # Konwersja na QPixmap
                self.preview_thumbnail = pillow_image_to_qpixmap(thumbnail)
                
                if self.preview_thumbnail.isNull():
                    raise ValueError("Konwersja do QPixmap dała pusty wynik")
                    
                return self.preview_thumbnail
                
        except FileNotFoundError:
            logging.error(f"Nie znaleziono pliku podglądu: {self.preview_path}")
            self.preview_thumbnail = create_placeholder_pixmap(width, height, text="Brak pliku")
        except UnidentifiedImageError:
            logging.error(f"Nieprawidłowy format pliku: {self.preview_path}")
            self.preview_thumbnail = create_placeholder_pixmap(width, height, text="Błąd formatu")
        except Exception as e:
            logging.error(f"Błąd wczytywania podglądu {self.preview_path}: {e}")
            self.preview_thumbnail = create_placeholder_pixmap(width, height, text="Błąd")
            
        return self.preview_thumbnail
    
    def get_archive_size(self):
        """
        Pobiera rozmiar pliku archiwum w bajtach.
        
        Returns:
            int: Rozmiar pliku archiwum w bajtach lub 0 w przypadku błędu
        """
        try:
            self.archive_size_bytes = os.path.getsize(self.archive_path)
            return self.archive_size_bytes
        except FileNotFoundError:
            logging.error(f"Nie znaleziono pliku archiwum: {self.archive_path}")
            self.archive_size_bytes = 0
        except Exception as e:
            logging.error(f"Błąd pobierania rozmiaru archiwum {self.archive_path}: {e}")
            self.archive_size_bytes = 0
            
        return self.archive_size_bytes
    
    def get_formatted_archive_size(self):
        """
        Zwraca sformatowany rozmiar pliku archiwum w czytelnej postaci (B, KB, MB, GB).
        
        Jeśli rozmiar nie został jeszcze pobrany, wywołuje get_archive_size().
        
        Returns:
            str: Sformatowany rozmiar pliku z jednostką
        """
        if self.archive_size_bytes is None:
            self.get_archive_size()
            
        # Obsługa przypadku, gdy rozmiar nadal jest None lub 0
        if self.archive_size_bytes is None or self.archive_size_bytes == 0:
            return "0 B"
            
        # Konwersja na czytelny format z odpowiednią jednostką
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(self.archive_size_bytes)
        unit_index = 0
        
        while size >= 1024.0 and unit_index < len(units) - 1:
            size /= 1024.0
            unit_index += 1
            
        # Formatowanie liczby: do 2 miejsc po przecinku, usunięcie końcowych zer
        if size.is_integer():
            formatted_size = str(int(size))
        else:
            formatted_size = f"{size:.2f}".rstrip('0').rstrip('.') if '.' in f"{size:.2f}" else f"{int(size)}"
            
        return f"{formatted_size} {units[unit_index]}" 
