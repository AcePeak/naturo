#!/usr/bin/env python3
"""
Test to verify README.md correctly mentions Linux/macOS as "coming soon"
"""
import re
import sys

def check_readme():
    with open('README.md', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for Linux coming soon
    linux_pattern = r'Linux.*[Cc]oming [Ss]oon'
    if not re.search(linux_pattern, content):
        print("ERROR: README should mention Linux as 'coming soon'")
        return False
    
    # Check for macOS coming soon
    macos_pattern = r'macOS.*[Cc]oming [Ss]oon'
    if not re.search(macos_pattern, content):
        print("ERROR: README should mention macOS as 'coming soon'")
        return False
    
    # Check the platform support table
    # Look for the table rows
    table_section = re.search(r'## Platform Support.*?##', content, re.DOTALL)
    if table_section:
        table_text = table_section.group(0)
        # Check each platform row
        if 'macOS' in table_text and '🚧 Coming soon' not in table_text:
            # Look for the emoji and status
            macos_row = re.search(r'macOS.*\n', table_text)
            if macos_row:
                row = macos_row.group(0)
                if '🚧' not in row and 'Coming soon' not in row:
                    print("ERROR: macOS row in platform table should show '🚧 Coming soon'")
                    return False
    else:
        print("WARNING: Could not find Platform Support section")
    
    print("SUCCESS: README correctly clarifies Linux/macOS status as 'coming soon'")
    return True

if __name__ == '__main__':
    success = check_readme()
    sys.exit(0 if success else 1)
