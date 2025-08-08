#!/usr/bin/env python3
"""
Test script for filename utilities
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.utils import process_filename_with_folder, extract_filename_parts, sanitize_filename


def test_filename_processing():
    """Test the filename processing utilities"""
    
    print("=== Testing Filename Processing ===\n")
    
    # Test cases
    test_cases = [
        {
            "original": "Documents/report.pdf",
            "folder": "Documents",
            "description": "Remove folder from path"
        },
        {
            "original": "Photos/vacation.jpg", 
            "folder": "Images",
            "description": "Folder doesn't match - no change"
        },
        {
            "original": "simple_file.docx",
            "folder": "Documents", 
            "description": "Simple filename with folder specified"
        },
        {
            "original": "Projects/2024/budget.xlsx",
            "folder": "Projects",
            "description": "Deep path - remove first folder"
        },
        {
            "original": "contract.pdf",
            "folder": "",
            "description": "Empty folder name"
        },
        {
            "original": "contract.pdf",
            "folder": None,
            "description": "No folder name provided"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"Test {i}: {case['description']}")
        print(f"  Original: '{case['original']}'")
        print(f"  Folder: '{case['folder']}'")
        
        cleaned, metadata = process_filename_with_folder(
            case['original'], 
            case['folder']
        )
        
        print(f"  Result: '{cleaned}'")
        print(f"  Folder removed: {metadata['folder_removed']}")
        print()


def test_filename_parts():
    """Test filename parts extraction"""
    
    print("=== Testing Filename Parts Extraction ===\n")
    
    test_files = [
        "document.pdf",
        "report.docx", 
        "image.png",
        "file_without_extension",
        "archive.tar.gz"
    ]
    
    for filename in test_files:
        parts = extract_filename_parts(filename)
        print(f"File: '{filename}'")
        print(f"  Name: '{parts['name_without_extension']}'")
        print(f"  Extension: '{parts['extension']}'")
        print(f"  Has extension: {parts['has_extension']}")
        print()


def test_filename_sanitization():
    """Test filename sanitization"""
    
    print("=== Testing Filename Sanitization ===\n")
    
    test_names = [
        "valid_filename.pdf",
        "file with spaces.docx",
        'invalid<chars>in:name.txt',
        "file|with?bad*chars.pdf",
        "  leading_and_trailing_spaces  .doc",
        "...leading_dots.xlsx"
    ]
    
    for filename in test_names:
        sanitized = sanitize_filename(filename)
        print(f"Original:  '{filename}'")
        print(f"Sanitized: '{sanitized}'")
        print()


if __name__ == "__main__":
    test_filename_processing()
    test_filename_parts() 
    test_filename_sanitization()
