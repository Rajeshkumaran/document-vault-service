import os
import logging
from typing import Tuple, Optional

logger = logging.getLogger("app.filename_utils")


def process_filename_with_folder(
    original_filename: str, 
    folder_name: Optional[str] = None
) -> Tuple[str, dict]:
    metadata = {
        "original_filename": original_filename,
        "folder_name": folder_name,
        "cleaned_filename": original_filename
    }
    
   
        # If no folder name provided, check if filename contains "/"
    if "/" in original_filename:
        # Split at the first "/" - first part is folder name, rest is filename
        parts = original_filename.split("/", 1)
        extracted_folder_name = parts[0]
        cleaned_filename = parts[1]
        metadata.update({
            "folder_name": extracted_folder_name,
            "original_filename": cleaned_filename,
            "cleaned_filename": cleaned_filename,
        })
        logger.info("Extracted folder name '%s' from filename. Original: '%s', Cleaned: '%s'", 
                   extracted_folder_name, original_filename, cleaned_filename)
    else:
        cleaned_filename = original_filename
        metadata.update({
            "folder_name": folder_name if folder_name else "",
        })
        logger.info("No folder name provided and no '/' found in filename, using original filename '%s'", 
                   original_filename)

    metadata["cleaned_filename"] = cleaned_filename
    return cleaned_filename, metadata


def extract_filename_parts(filename: str) -> dict:
    """
    Extract various parts from a filename.
    
    Args:
        filename: The filename to process
        
    Returns:
        Dictionary containing filename parts
    """
    name, extension = os.path.splitext(filename)
    
    return {
        "full_filename": filename,
        "name_without_extension": name,
        "extension": extension.lower(),
        "has_extension": bool(extension)
    }


def sanitize_filename(filename: str, replacement_char: str = "_") -> str:
    """
    Sanitize a filename by replacing invalid characters.
    
    Args:
        filename: The filename to sanitize
        replacement_char: Character to replace invalid chars with
        
    Returns:
        Sanitized filename
    """
    # Characters not allowed in filenames
    invalid_chars = '<>:"/\\|?*'
    
    sanitized = filename
    for char in invalid_chars:
        sanitized = sanitized.replace(char, replacement_char)
    
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip('. ')
    
    return sanitized
