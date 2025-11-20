#!/usr/bin/env python3
"""Verify API endpoint compliance with OpenAPI specification.

This script compares implemented endpoints in fm-knowledge-service
against the authoritative OpenAPI spec from FaultMaven-Mono.
"""

import re
import yaml
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Paths
SPEC_PATH = Path("reference/openapi.locked.yaml")
ROUTES_PATHS = [
    ("documents", Path("src/knowledge_service/api/routes/documents.py"), "/api/v1/knowledge/documents"),
    ("search", Path("src/knowledge_service/api/routes/search.py"), "/api/v1/search"),
]


def extract_spec_endpoints(spec_path: Path) -> Dict[str, Dict]:
    """Extract knowledge endpoints from OpenAPI spec.

    Returns:
        Dict mapping "METHOD /path" to endpoint details
    """
    with open(spec_path) as f:
        spec = yaml.safe_load(f)

    endpoints = {}
    for path, methods in spec['paths'].items():
        if path.startswith('/api/v1/knowledge'):
            for method, details in methods.items():
                if method in ['get', 'post', 'put', 'delete', 'patch']:
                    key = f"{method.upper()} {path}"
                    endpoints[key] = {
                        'method': method.upper(),
                        'path': path,
                        'operation_id': details.get('operationId', ''),
                        'summary': details.get('summary', ''),
                    }

    return endpoints


def extract_implemented_endpoints(routes_paths: List[Tuple[str, Path, str]]) -> Set[str]:
    """Extract implemented endpoints from route files.

    Returns:
        Set of "METHOD /path" strings
    """
    endpoints = set()

    for name, path, prefix in routes_paths:
        if not path.exists():
            continue

        with open(path) as f:
            content = f.read()

        # Pattern to match FastAPI route decorators
        pattern = r'@router\.(get|post|put|delete|patch)\(\s*["\']([^"\']*)["\']'

        for match in re.finditer(pattern, content):
            method = match.group(1).upper()
            route_path = match.group(2) if len(match.groups()) >= 2 else ""

            # Convert to full path
            if route_path.startswith('/api/v1'):
                full_path = route_path
            else:
                # Apply router prefix
                if route_path == "":
                    full_path = prefix
                else:
                    full_path = f"{prefix}{route_path}" if route_path.startswith('/') else f"{prefix}/{route_path}"

            key = f"{method} {full_path}"
            endpoints.add(key)

    return endpoints


def main():
    """Compare spec vs implementation."""
    print("=" * 80)
    print("FM-KNOWLEDGE-SERVICE OPENAPI COMPLIANCE CHECK")
    print("=" * 80)
    print()

    # Extract endpoints
    spec_endpoints = extract_spec_endpoints(SPEC_PATH)
    impl_endpoints = extract_implemented_endpoints(ROUTES_PATHS)

    # Convert to sets for comparison
    spec_keys = set(spec_endpoints.keys())

    # Calculate status
    missing = spec_keys - impl_endpoints
    extra = impl_endpoints - spec_keys
    implemented = spec_keys & impl_endpoints

    # Summary
    total_spec = len(spec_keys)
    total_impl = len(implemented)
    pct = (total_impl / total_spec * 100) if total_spec > 0 else 0

    print(f"SPEC ENDPOINTS:        {total_spec}")
    print(f"IMPLEMENTED:           {total_impl}")
    print(f"MISSING:               {len(missing)}")
    print(f"EXTRA (not in spec):   {len(extra)}")
    print(f"COVERAGE:              {pct:.1f}%")
    print()

    # Detailed results
    if implemented:
        print("✅ IMPLEMENTED ENDPOINTS:")
        print("-" * 80)
        for key in sorted(implemented):
            endpoint = spec_endpoints[key]
            print(f"  {endpoint['method']:6} {endpoint['path']}")
            print(f"         {endpoint['summary']}")
        print()

    if missing:
        print("❌ MISSING ENDPOINTS:")
        print("-" * 80)
        for key in sorted(missing):
            endpoint = spec_endpoints[key]
            print(f"  {endpoint['method']:6} {endpoint['path']}")
            print(f"         {endpoint['summary']}")
            print(f"         Operation ID: {endpoint['operation_id']}")
        print()

    if extra:
        print("⚠️  EXTRA ENDPOINTS (not in OpenAPI spec):")
        print("-" * 80)
        for key in sorted(extra):
            print(f"  {key}")
        print()

    # Final verdict
    print("=" * 80)
    if len(missing) == 0 and len(extra) == 0:
        print("✅ PERFECT COMPLIANCE - All spec endpoints implemented, no extras")
    elif len(missing) == 0:
        print("✅ COMPLETE - All spec endpoints implemented (some extra endpoints present)")
    else:
        print(f"⚠️  INCOMPLETE - {len(missing)} endpoints need to be ported")
    print("=" * 80)


if __name__ == "__main__":
    main()
