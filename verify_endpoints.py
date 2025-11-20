#!/usr/bin/env python3
"""
Verify that all required knowledge service endpoints are implemented.
"""

import ast
import sys
from pathlib import Path


def find_endpoints_in_file(file_path):
    """Extract endpoint definitions from a Python file."""
    with open(file_path, 'r') as f:
        content = f.read()

    endpoints = []
    lines = content.split('\n')

    for i, line in enumerate(lines, 1):
        # Look for @router.get, @router.post, etc.
        if '@router.' in line and '(' in line:
            for method in ['get', 'post', 'put', 'delete', 'patch']:
                if f'@router.{method}(' in line:
                    # Extract path from the decorator
                    if '("' in line:
                        start = line.find('("') + 2
                        end = line.find('")', start)
                        path = line[start:end] if end > 0 else ""
                    elif "('" in line:
                        start = line.find("('") + 2
                        end = line.find("')", start)
                        path = line[start:end] if end > 0 else ""
                    else:
                        path = ""

                    endpoints.append({
                        'method': method.upper(),
                        'path': path,
                        'line': i
                    })
                    break

    return endpoints


def main():
    """Main verification function."""
    print("=" * 80)
    print("FM Knowledge Service - Endpoint Verification")
    print("=" * 80)

    # Required endpoints
    required_endpoints = [
        ('POST', '/search', 'Unified search endpoint'),
        ('POST', '/documents/bulk-delete', 'Bulk delete documents'),
        ('GET', '/stats', 'Knowledge base statistics'),
        ('GET', '/analytics/search', 'Search analytics'),
        ('GET', '/jobs/{job_id}', 'Job status tracking'),
    ]

    # Find the knowledge_endpoints.py file
    knowledge_file = Path('src/knowledge_service/api/routes/knowledge_endpoints.py')

    if not knowledge_file.exists():
        print(f"\n❌ ERROR: {knowledge_file} not found!")
        return 1

    print(f"\n✓ Found: {knowledge_file}")

    # Extract endpoints
    endpoints = find_endpoints_in_file(knowledge_file)

    print(f"\nFound {len(endpoints)} endpoints in knowledge_endpoints.py:")
    for ep in endpoints:
        print(f"  {ep['method']:6s} {ep['path']:30s} (line {ep['line']})")

    # Check required endpoints
    print("\n" + "=" * 80)
    print("Checking Required Endpoints:")
    print("=" * 80)

    found_count = 0
    total_count = len(required_endpoints)

    for method, path, description in required_endpoints:
        # Normalize paths for comparison (remove leading slash if present)
        path_normalized = path.lstrip('/')

        found = False
        for ep in endpoints:
            ep_path_normalized = ep['path'].lstrip('/')
            if ep['method'] == method and ep_path_normalized == path_normalized:
                found = True
                found_count += 1
                print(f"✓ {method:6s} /api/v1/knowledge/{path_normalized:30s} - {description}")
                break

        if not found:
            print(f"✗ {method:6s} /api/v1/knowledge/{path_normalized:30s} - {description} [MISSING]")

    # Calculate completion percentage
    completion = (found_count / total_count) * 100

    print("\n" + "=" * 80)
    print(f"Completion: {found_count}/{total_count} ({completion:.1f}%)")
    print("=" * 80)

    if found_count == total_count:
        print("\n✓ SUCCESS: All required endpoints are implemented!")
        return 0
    else:
        print(f"\n✗ INCOMPLETE: {total_count - found_count} endpoint(s) missing.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
