from pathlib import Path
from typing import Optional

def check_bom(data: bytes) -> Optional[str]:
    """
    Checks the byte order mark (BOM) at the start of the byte sequence.
    Returns the corresponding encoding if BOM is found, otherwise None.
    """
    if data.startswith(b'\xEF\xBB\xBF'):  # UTF-8 BOM
        return 'utf-8-sig'
    if data.startswith(b'\xFF\xFE'):      # UTF-16 LE BOM
        return 'utf-16'
    if data.startswith(b'\xFE\xFF'):      # UTF-16 BE BOM
        return 'utf-16'
    return None

def detect_encoding(path: Path | str, sample_size: int = 65536) -> str:
    """
    Detects the encoding of a file by reading up to sample_size bytes.
    Checks BOM first, then uses chardet library for detection.
    Falls back to 'utf-8' if confidence is low or detection fails.
    
    Raises ImportError if chardet is not installed.
    """
    path = Path(path)
    try:
        import chardet
        
        with path.open('rb') as f:
            raw_data = f.read(sample_size)
            
        # Check for BOM first
        if bom_encoding := check_bom(raw_data):
            return bom_encoding
        
        # Detect encoding using chardet
        result = chardet.detect(raw_data)
        
        # Use utf-8 if confidence is below threshold
        if result['confidence'] < 0.7:
            return 'utf-8'
            
        return result['encoding'] or 'utf-8'
    except ImportError:
        raise ImportError("For automatic encoding detection, please install chardet")

def determine_minimal_encoding(content: str) -> str:
    """
    Determines the minimal encoding that can represent the given string content.
    Tries ASCII, then Windows-1251 (Cyrillic), then defaults to UTF-8.
    """
    try:
        content.encode('ascii')
        return 'ascii'
    except UnicodeEncodeError:
        pass
    
    try:
        content.encode('cp1251')
        return 'cp1251'
    except UnicodeEncodeError:
        pass
    
    return 'utf-8'
