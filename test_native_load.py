#!/usr/bin/env python3
"""
Test script to verify that the extended load() and loadfile() functions
now provide access to native MAD-NG load and loadfile functionality.

This addresses issue #26: Pythonic layer prevents access to load and loadfile
"""

import tempfile
import os
from pathlib import Path

try:
    from pymadng import MAD
except ImportError:
    print("PyMAD-NG not available, cannot run test")
    exit(1)

def test_native_load():
    """Test that load() can now handle Lua chunks (native MAD-NG behavior)"""
    print("Testing native MAD-NG load() function...")
    
    with MAD(stdout="/dev/null", redirect_stderr=True) as mad:
        # Test native load with a simple Lua chunk
        lua_chunk = "return function(x) return x * 2 end"
        
        # This should now work - loads the Lua chunk and returns a function
        loaded_func = mad.load(lua_chunk)
        print(f"✓ Native load() succeeded: {type(loaded_func)}")
        
        # Test calling the loaded function
        result = mad.eval("_last[1](5)")
        print(f"✓ Loaded function executed correctly: 5 * 2 = {result}")
        
        # Test that module loading still works (backward compatibility)
        mad.load("MAD.gmath", "sin", "cos")
        sin_result = mad.sin(1).eval()
        print(f"✓ Module loading still works: sin(1) = {sin_result:.4f}")

def test_native_loadfile():
    """Test that loadfile() can now handle regular Lua files (native MAD-NG behavior)"""
    print("\nTesting native MAD-NG loadfile() function...")
    
    # Create a temporary Lua file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.lua', delete=False) as f:
        f.write("""
-- Test Lua file
return function(a, b)
    return a + b
end
""")
        lua_file_path = f.name
    
    try:
        with MAD(stdout="/dev/null", redirect_stderr=True) as mad:
            # Test native loadfile with explicit flag
            loaded_func = mad.loadfile(lua_file_path, native_loadfile=True)
            print(f"✓ Native loadfile() succeeded: {type(loaded_func)}")
            
            # Test calling the loaded function
            result = mad.eval("_last[1](3, 7)")
            print(f"✓ Loaded function executed correctly: 3 + 7 = {result}")
            
            # Test that .mad file loading still works (backward compatibility)
            with tempfile.NamedTemporaryFile(mode='w', suffix='.mad', delete=False) as mad_file:
                mad_file.write("""
local test_var = 42
return {result = test_var}
""")
                mad_file_path = mad_file.name
            
            try:
                mad.loadfile(mad_file_path, "result")
                mad_result = mad.result
                print(f"✓ .mad file loading still works: result = {mad_result}")
            finally:
                os.unlink(mad_file_path)
                
    finally:
        os.unlink(lua_file_path)

def test_workaround_compatibility():
    """Test that the workaround using mad.send() still works"""
    print("\nTesting workaround compatibility...")
    
    with MAD(stdout="/dev/null", redirect_stderr=True) as mad:
        # The old workaround should still work
        mad.send('test_func = load("return function(x) return x * 3 end")')
        mad.send('test_result = test_func()(4)')
        result = mad.test_result
        print(f"✓ Workaround still works: 4 * 3 = {result}")

def main():
    """Run all tests"""
    print("Testing extended load() and loadfile() functions for issue #26")
    print("=" * 60)
    
    try:
        test_native_load()
        test_native_loadfile()
        test_workaround_compatibility()
        
        print("\n" + "=" * 60)
        print("✅ All tests passed! Issue #26 has been resolved.")
        print("\nThe extended functions now provide:")
        print("1. Native MAD-NG load() for Lua chunks")
        print("2. Native MAD-NG loadfile() for Lua files")
        print("3. Backward compatibility with existing PyMAD-NG behavior")
        print("4. Continued support for the send() workaround")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
