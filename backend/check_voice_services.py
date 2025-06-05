#!/usr/bin/env python3
"""
Voice Services Reference Checker

This script helps verify which voice service references are used in your codebase
and identifies any outdated patterns that need updating in tests.
"""

import os
import re
from pathlib import Path
from collections import defaultdict


def find_service_references(directory):
    """Find all voice service references in Python files."""
    results = defaultdict(list)
    
    for root, dirs, files in os.walk(directory):
        # Skip common directories that don't need checking
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', '.pytest_cache', 'node_modules']]
        
        for file in files:
            if file.endswith('.py'):
                file_path = Path(root) / file
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Search for various service import patterns
                    patterns = {
                        'deepgram_service_current': r'from app\.services\.voice import.*deepgram_service|from app\.services\.voice\.deepgram_service import',
                        'deepgram_stt_service_old': r'deepgram_stt_service|DeepgramSTTService',
                        'elevenlabs_service_current': r'from app\.services\.voice import.*elevenlabs_service|from app\.services\.voice\.elevenlabs_service import',
                        'voice_import_patterns': r'from app\.services\.voice import',
                        'websocket_endpoints': r'/ws/voice/|/api/ws/voice/',
                        'voice_api_endpoints': r'/voice/stt/|/voice/tts/',
                    }
                    
                    for pattern_name, pattern in patterns.items():
                        matches = re.finditer(pattern, content, re.MULTILINE)
                        for match in matches:
                            line_num = content[:match.start()].count('\n') + 1
                            results[pattern_name].append({
                                'file': str(file_path),
                                'line': line_num,
                                'match': match.group()
                            })
                            
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
    
    return results


def analyze_test_files(test_directory):
    """Specifically analyze test files for outdated patterns."""
    test_issues = []
    
    if not os.path.exists(test_directory):
        return ["Test directory not found"]
    
    for file_path in Path(test_directory).glob("test_voice*.py"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            issues = []
            
            # Check for outdated service references
            if 'deepgram_stt_service' in content:
                issues.append("❌ Uses outdated 'deepgram_stt_service' (should be 'deepgram_service')")
            
            if 'DeepgramSTTService' in content:
                issues.append("❌ Uses outdated 'DeepgramSTTService' class (should be 'DeepgramService')")
            
            # Check for correct imports
            if 'from app.services.voice import deepgram_service' in content:
                issues.append("✅ Uses correct deepgram_service import")
            
            if 'from app.services.voice import elevenlabs_service' in content:
                issues.append("✅ Uses correct elevenlabs_service import")
            
            # Check WebSocket patterns
            if '/api/ws/voice/' in content and '/ws/voice/' in content:
                issues.append("⚠️ Mixed WebSocket endpoint patterns")
            elif '/api/ws/voice/' in content:
                issues.append("⚠️ Uses '/api/ws/voice/' pattern (check if current)")
            elif '/ws/voice/' in content:
                issues.append("✅ Uses '/ws/voice/' pattern")
            
            if issues:
                test_issues.append({
                    'file': str(file_path),
                    'issues': issues
                })
                
        except Exception as e:
            test_issues.append({
                'file': str(file_path),
                'issues': [f"Error reading file: {e}"]
            })
    
    return test_issues


def main():
    """Main function to check service references."""
    print("🔍 Voice Services Reference Checker")
    print("=" * 50)
    
    # Check current directory
    current_dir = os.getcwd()
    print(f"Checking directory: {current_dir}")
    
    # Find all service references
    print("\n📂 Scanning for voice service references...")
    results = find_service_references(current_dir)
    
    # Report current service usage
    print("\n✅ CURRENT SERVICE REFERENCES:")
    if results['deepgram_service_current']:
        print(f"  deepgram_service found in {len(results['deepgram_service_current'])} locations:")
        for ref in results['deepgram_service_current'][:5]:  # Show first 5
            print(f"    📄 {ref['file']}:{ref['line']}")
        if len(results['deepgram_service_current']) > 5:
            print(f"    ... and {len(results['deepgram_service_current']) - 5} more")
    else:
        print("  ⚠️ No current deepgram_service references found")
    
    if results['elevenlabs_service_current']:
        print(f"  elevenlabs_service found in {len(results['elevenlabs_service_current'])} locations:")
        for ref in results['elevenlabs_service_current'][:3]:  # Show first 3
            print(f"    📄 {ref['file']}:{ref['line']}")
        if len(results['elevenlabs_service_current']) > 3:
            print(f"    ... and {len(results['elevenlabs_service_current']) - 3} more")
    else:
        print("  ⚠️ No current elevenlabs_service references found")
    
    # Report outdated references
    print("\n❌ OUTDATED REFERENCES:")
    if results['deepgram_stt_service_old']:
        print(f"  deepgram_stt_service found in {len(results['deepgram_stt_service_old'])} locations:")
        for ref in results['deepgram_stt_service_old']:
            print(f"    📄 {ref['file']}:{ref['line']} - {ref['match']}")
    else:
        print("  ✅ No outdated deepgram_stt_service references found")
    
    # Report API endpoints
    print("\n🌐 API ENDPOINTS:")
    if results['voice_api_endpoints']:
        print(f"  Voice API endpoints found in {len(results['voice_api_endpoints'])} locations:")
        for ref in results['voice_api_endpoints'][:3]:
            print(f"    📄 {ref['file']}:{ref['line']}")
    
    if results['websocket_endpoints']:
        print(f"  WebSocket endpoints found in {len(results['websocket_endpoints'])} locations:")
        for ref in results['websocket_endpoints'][:3]:
            print(f"    📄 {ref['file']}:{ref['line']} - {ref['match']}")
    
    # Analyze test files specifically
    print("\n🧪 TEST FILE ANALYSIS:")
    test_issues = analyze_test_files(os.path.join(current_dir, 'tests'))
    
    if not test_issues:
        print("  ✅ No test files found or no issues detected")
    else:
        for test_file in test_issues:
            print(f"\n  📄 {test_file['file']}:")
            for issue in test_file['issues']:
                print(f"    {issue}")
    
    # Recommendations
    print("\n💡 RECOMMENDATIONS:")
    
    if results['deepgram_stt_service_old']:
        print("  🔧 Update outdated deepgram_stt_service references:")
        print("     - Replace 'deepgram_stt_service' with 'deepgram_service'")
        print("     - Replace 'DeepgramSTTService' with 'DeepgramService'")
        print("     - Update import: 'from app.services.voice import deepgram_service'")
    
    if not results['deepgram_service_current'] and not results['elevenlabs_service_current']:
        print("  ⚠️ No current service references found - this might indicate:")
        print("     - Services are not being imported correctly")
        print("     - Code might be using different import patterns")
        print("     - Services might be defined differently than expected")
    
    total_outdated = len(results['deepgram_stt_service_old'])
    total_current = len(results['deepgram_service_current']) + len(results['elevenlabs_service_current'])
    
    if total_outdated > 0:
        print(f"\n⚠️ MIGRATION NEEDED: {total_outdated} outdated references found")
        print("   Consider using the consolidated test file to replace outdated tests")
    elif total_current > 0:
        print(f"\n✅ GOOD: {total_current} current service references found")
        print("   Your codebase appears to be using current service patterns")
    else:
        print("\n❓ UNCLEAR: No clear service patterns detected")
        print("   Manual verification of service usage may be needed")


if __name__ == "__main__":
    main()
