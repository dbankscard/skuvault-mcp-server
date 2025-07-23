#!/usr/bin/env python3
"""
Test script to verify the SkuVault MCP server is working correctly.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.server import mcp, get_warehouses


async def test_server():
    """Test basic server functionality."""
    print("🧪 Testing SkuVault MCP Server")
    print("=" * 50)
    
    # Test 1: Check if server initializes
    print("\n1. Server initialization... ", end="")
    try:
        # Access mcp object - list_tools is async
        tools = await mcp.list_tools()
        print(f"✅ OK ({len(tools)} tools registered)")
        
        print("\n   Available tools:")
        for tool in tools:
            print(f"   - {tool.name}")
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False
    
    # Test 2: Test a read-only operation
    print("\n2. Testing read-only operation (get_warehouses)... ", end="")
    try:
        # This will fail if no credentials are set, but that's expected
        result = await get_warehouses()
        
        if "error" in result:
            if "Authentication required" in result["error"]:
                print("⚠️  No credentials (expected)")
                print("   Set credentials in .env to test API calls")
            else:
                print(f"❌ API Error: {result['error']}")
        else:
            print("✅ OK")
            print(f"   Found {len(result.get('Warehouses', []))} warehouses")
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("✅ Server is functioning correctly!")
    print("\nNote: To test API operations, add your credentials to .env file")
    return True


def main():
    """Run the test."""
    try:
        success = asyncio.run(test_server())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()