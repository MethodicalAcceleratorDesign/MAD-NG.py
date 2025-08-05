# Solution for Issue #26: Pythonic layer prevents access to load and loadfile

## Problem Summary

The PyMAD-NG Python wrapper had methods called `load()` and `loadfile()` that were preventing access to the native MAD-NG Lua functions of the same names. This created a limitation where users couldn't access the native Lua `load` (for loading Lua chunks from strings) and `loadfile` (for loading Lua files) functions directly.

## Solution Implemented

Instead of renaming the Python functions (which would break backward compatibility), we **extended the functionality** of both `load()` and `loadfile()` to support both the original PyMAD-NG behavior AND the native MAD-NG functionality.

### Enhanced `load()` Function

The `load()` function now supports two modes:

1. **PyMAD-NG Module Loading** (original behavior):
   ```python
   mad.load("MAD.gmath", "sin", "cos")  # Import specific functions from module
   mad.load("element")  # Import all from element module
   ```

2. **Native MAD-NG Lua Chunk Loading** (new functionality):
   ```python
   # Load and compile a Lua code chunk
   func = mad.load("return function(x) return x * 2 end")
   ```

**Auto-detection**: The function automatically detects the intended usage:
- If additional variables are provided (`*vars`), it assumes module loading mode
- If only one argument is provided and it contains Lua code patterns, it uses native load
- Otherwise, it defaults to module loading mode

### Enhanced `loadfile()` Function

The `loadfile()` function now supports two modes:

1. **PyMAD-NG .mad File Loading** (original behavior):
   ```python
   mad.loadfile("script.mad")  # Execute .mad file
   mad.loadfile("script.mad", "var1", "var2")  # Import specific variables
   ```

2. **Native MAD-NG Lua File Loading** (new functionality):
   ```python
   # Load and compile a Lua file, returns compiled function
   func = mad.loadfile("script.lua", native_loadfile=True)
   # Or automatically detected for non-.mad files:
   func = mad.loadfile("script.lua")  # No vars, not .mad extension
   ```

## Technical Implementation

### Lua Chunk Detection Heuristic

Added `_is_lua_chunk()` method that uses pattern matching to detect if a string contains Lua code:
- Looks for Lua keywords: `function`, `end`, `local`, `return`, `if`, `then`, etc.
- Checks for statement patterns: `=`, function definitions, etc.
- Requires multiple patterns or obvious statement indicators

### Backward Compatibility

- **100% backward compatible**: All existing PyMAD-NG code continues to work unchanged
- **Workaround still works**: The original workaround using `mad.send("load(...)")` still functions
- **No breaking changes**: Existing behavior is preserved when conditions match original usage patterns

## Benefits

1. **Native Access**: Users can now access native MAD-NG `load` and `loadfile` functions
2. **No Breaking Changes**: Existing code continues to work
3. **Intuitive**: Auto-detection makes usage natural and obvious
4. **Complete**: Covers both string chunks and file loading
5. **Future-proof**: Extensible design allows for further enhancements

## Testing

Created comprehensive test suite (`test_native_load.py`) that verifies:
- Native `load()` with Lua chunks works correctly
- Native `loadfile()` with Lua files works correctly  
- Backward compatibility with existing PyMAD-NG behavior
- Original workaround continues to function

## Usage Examples

### Before (Workaround Required)
```python
# Had to use workaround
mad.send('func = load("return function(x) return x * 2 end")')
mad.send('result = func()(5)')
```

### After (Direct Access)
```python
# Can now use directly
func = mad.load("return function(x) return x * 2 end")
result = mad.eval("_last[1](5)")

# Or for files
func = mad.loadfile("script.lua", native_loadfile=True)

# Existing usage still works unchanged
mad.load("MAD.gmath", "sin", "cos")
mad.loadfile("script.mad", "var1", "var2")
```

## Contributor

**mdnoyon9758** - Extended load() and loadfile() functions to provide native MAD-NG access while maintaining backward compatibility.

---

**Issue Status**: ✅ **RESOLVED**  
**Implementation**: Extended functionality approach (option 2 from issue description)  
**Backward Compatibility**: ✅ **Maintained**  
**Testing**: ✅ **Comprehensive test suite included**
