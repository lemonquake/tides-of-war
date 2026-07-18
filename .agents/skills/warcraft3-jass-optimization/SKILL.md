---
name: warcraft3-jass-optimization
description: Guidelines, best practices, memory leak prevention, performance optimization rules, and validation tools for Warcraft III JASS code and war3map.j. Use whenever creating, editing, refactoring, or auditing Warcraft 3 JASS scripts.
---

# Warcraft III JASS Optimization & Leak Prevention Guide

This skill provides a comprehensive, production-grade guide for writing, editing, refactoring, and maintaining Warcraft III JASS (`war3map.j`) code. Following these practices ensures zero memory leaks, high frame rates, stable handle counts, and crash-free execution.

---

## 1. Core Principles of JASS Memory Management

Warcraft III uses an internal handle table with reference counting. If handles are allocated and not properly destroyed, or if local variables pointing to handles are not set to `null` before a function returns, the handle indices remain locked in memory forever. Over time, this leads to memory bloat, frame drops, stuttering, and eventual game crashes.

### Key Handle Types Subject to Leaks
`unit`, `group`, `force`, `location`, `effect`, `timer`, `trigger`, `sound`, `lightning`, `texttag`, `multiboard`, `multiboarditem`, `dialog`, `button`, `quest`, `item`, `destructable`, `region`, `rect`, `boolexpr`.

---

## 2. Mandatory Coding Rules for Every Add/Edit

### Rule 1: Use Native (X, Y) Coordinates (NEVER create unnecessary Locations)
- **Do NOT use**: `GetUnitLoc(u)`, `GetSpellTargetLoc()`, `GetOrderPointLoc()`, `GetRectCenter(r)`, or `PolarProjectionBJ(...)`.
- **Do use**: `GetUnitX(u)`, `GetUnitY(u)`, `GetSpellTargetX()`, `GetSpellTargetY()`, `GetRectCenterX(r)`, `GetRectCenterY(r)`.
- **Polar offset math**:
  ```jass
  // PolarProjectionBJ replacement with native coordinates
  set targetX = x0 + distance * Cos(angleInDegrees * bj_DEGTORAD)
  set targetY = y0 + distance * Sin(angleInDegrees * bj_DEGTORAD)
  ```
- **Location cleanup**: If a Blizzard API strictly requires a `location` handle, always execute `call RemoveLocation(loc)` immediately after use and set `set loc = null`.

### Rule 2: Null ALL Local Handle Variables Before Exit
- Every local variable of a handle type must be set to `null` before `endfunction` or before any `return` statement in that function.
  ```jass
  function Example takes unit u returns nothing
      local unit target = u
      local group g = CreateGroup()
      
      // ... logic ...

      call DestroyGroup(g)
      set g = null
      set target = null
  endfunction
  ```

### Rule 3: Unit Group Leak Prevention
- **When using `ForGroupBJ`**: Place `set bj_wantDestroyGroup = true` on the line immediately preceding `call ForGroupBJ(...)`.
  ```jass
  set bj_wantDestroyGroup = true
  call ForGroupBJ( GetUnitsInRangeOfLocMatching(...), function Callback )
  ```
- **When using native `GroupEnumUnitsInRange`**: Reuse global unit groups (e.g. `bj_lastCreatedGroup`) instead of `CreateGroup()`.

### Rule 4: Player Group (Force) Optimization
- **All Players**: Replace `GetPlayersAll()` with the constant `bj_FORCE_ALL_PLAYERS`.
- **Filtered Player Groups**: Store `GetPlayersMatching(...)` in a temporary force, execute `ForForce`, call `DestroyForce`, and null the variable:
  ```jass
  local force tempForce = GetPlayersMatching(...)
  call ForForce(tempForce, function Callback)
  call DestroyForce(tempForce)
  set tempForce = null
  ```

### Rule 5: Division-by-Zero Protection
- Never divide by a variable or parameter that could evaluate to `0.0`.
- Wrap denominators with `RMaxBJ(val, minVal)`:
  ```jass
  set count = total / RMaxBJ(interval, 0.01)
  ```

### Rule 6: Global Variable Hygiene
- If global location or unit group variables (`udg_TempPoint`, `udg_KBA_StartingPosition`, etc.) are assigned temporary locations, always call `call RemoveLocation(...)` or `call GroupClear(...)` when finished.

---

## 3. Workflow for Editing `war3map.j`

When adding a feature, modifying a trigger, or refactoring code, follow this 4-step workflow:

1. **Pre-Edit Scan**:
   Run the analysis script to identify baseline handles and potential leaks:
   ```bash
   python .agents/skills/warcraft3-jass-optimization/scripts/analyze_jass_leaks.py src/war3map.j
   ```

2. **Apply Changes**:
   Write/edit the JASS code adhering to Rules 1 through 6.

3. **Post-Edit Automated Health Validation**:
   Run the validation script to verify 100% block balance and zero handle leaks:
   ```bash
   python .agents/skills/warcraft3-jass-optimization/scripts/validate_jass_syntax.py src/war3map.j
   ```

4. **Build & Pack Map**:
   Compile `src/war3map.j` into `dist/Tides_of_War_Compiled.w3x` using `build.bat` or MPQEditor:
   ```bash
   powershell -Command "Copy-Item -Force 'base_map.w3x' 'dist\Tides_of_War_Compiled.w3x'; .\MPQEditor.exe add 'dist\Tides_of_War_Compiled.w3x' 'src\war3map.j' 'war3map.j'"
   ```

---

## 4. Automation Helper Scripts

- `scripts/analyze_jass_leaks.py`: Scans JASS source files for location leaks, group leaks, force leaks, un-nulled local handles, and division-by-zero risks.
- `scripts/validate_jass_syntax.py`: Checks nesting balance for functions, loops, if-blocks, and verifies zero leak warnings.
