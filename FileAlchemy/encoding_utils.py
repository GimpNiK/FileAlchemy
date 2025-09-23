from pathlib import Path
from typing import Optional
def check_bom(data: bytes) -> Optional[str]:
    if data.startswith(b'\xEF\xBB\xBF'):  # UTF-8 BOM
        return 'utf-8-sig'
    if data.startswith(b'\xFF\xFE'):      # UTF-16 LE
        return 'utf-16'
    if data.startswith(b'\xFE\xFF'):      # UTF-16 BE
        return 'utf-16'
    return None
def detect_encoding(path: Path|str, sample_size: int = 65536) -> str:
    path = Path(path)
    try:
        import chardet
        
        with path.open('rb') as f:
            raw_data = f.read(sample_size)
            
        # Проверяем BOM в первую очередь
        if bom_encoding := check_bom(raw_data):
            return bom_encoding
        
        # Определение через chardet
        result = chardet.detect(raw_data)
        
        if result['confidence'] < 0.7:
            return 'utf-8'
            
        return result['encoding'] or 'utf-8'
    except ImportError:
        raise ImportError("Для автоматического определения кодировки установите chardet")


# Глобальная функция для определения минимальной кодировки
def determine_minimal_encoding(content: str) -> str:
    """Определяет минимальную кодировку, поддерживающую содержимое"""
    # Пробуем ASCII (1 байт на символ)
    try:
        content.encode('ascii')
        return 'ascii'
    except UnicodeEncodeError:
        pass
    
    # Пробуем Windows-1251 (кириллица, 1 байт на символ)
    try:
        content.encode('cp1251')
        return 'cp1251'
    except UnicodeEncodeError:
        pass
    
    # По умолчанию UTF-8 (поддерживает все символы, 1-4 байта на символ)
    return 'utf-8'