#!/usr/bin/env python
"""Replace all 8765 with 7000 in project files"""

import os
import re
from pathlib import Path

def update_files():
    count = 0
    for root, dirs, files in os.walk('c:/07code/mem_server'):
        # Skip data and .git directories
        dirs[:] = [d for d in dirs if d not in ['data', '.git', '__pycache__', '.idea', '.gradle']]
        
        for file in files:
            if file.endswith(('.md', '.py', '.txt')):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    new_content = content.replace('127.0.0.1:7000', '127.0.0.1:7000')
                    new_content = new_content.replace('http://127.0.0.1:7000', 'http://127.0.0.1:7000')
                    
                    if new_content != content:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        print(f'Updated: {filepath}')
                        count += 1
                except Exception as e:
                    print(f'Error processing {filepath}: {e}')
    
    print(f'\nTotal files updated: {count}')

if __name__ == '__main__':
    update_files()
