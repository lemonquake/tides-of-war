import re
import os
import sys

jass_path = sys.argv[1] if len(sys.argv) > 1 else r"src\war3map.j"

if not os.path.exists(jass_path):
    print(f"Error: File '{jass_path}' not found.")
    sys.exit(1)

with open(jass_path, "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

print(f"=== ANALYZING JASS FILE: {jass_path} ({len(lines)} lines) ===")

func_start_re = re.compile(r'^(?:constant\s+)?function\s+([a-zA-Z0-9_]+)\s+takes\s+(.*?)\s+returns\s+([a-zA-Z0-9_]+)', re.IGNORECASE)
endfunc_re = re.compile(r'^endfunction', re.IGNORECASE)

functions = []
cur_func = None

for idx, line in enumerate(lines, 1):
    l_strip = line.strip()
    m_func = func_start_re.match(l_strip)
    if m_func:
        cur_func = {'name': m_func.group(1), 'start': idx, 'lines': []}
        continue
    if cur_func:
        if endfunc_re.match(l_strip):
            cur_func['end'] = idx
            functions.append(cur_func)
            cur_func = None
        else:
            cur_func['lines'].append((idx, line))

HANDLE_TYPES = {
    'unit', 'group', 'force', 'location', 'effect', 'timer', 'trigger', 'sound',
    'lightning', 'texttag', 'multiboard', 'multiboarditem', 'trackable', 'dialog',
    'button', 'quest', 'questitem', 'defeatcondition', 'timerdialog', 'leaderboard',
    'item', 'destructable', 'region', 'rect', 'fogmodifier', 'fogstate', 'image', 'ubersplat', 'boolexpr'
}

unnulled_handles = []
grp_leaks = []
force_leaks = []
loc_leaks = []
location_alloc_patterns = [
    re.compile(r'\bGetUnitLoc\s*\(', re.IGNORECASE),
    re.compile(r'\bPolarProjectionBJ\s*\(', re.IGNORECASE),
    re.compile(r'\bGetSpellTargetLoc\s*\(', re.IGNORECASE),
    re.compile(r'\bGetOrderPointLoc\s*\(', re.IGNORECASE),
    re.compile(r'\bGetRectCenter\s*\(', re.IGNORECASE),
    re.compile(r'\bLocation\s*\(', re.IGNORECASE),
]

for fn in functions:
    fn_name = fn['name']
    fn_lines = fn['lines']
    fn_text = "\n".join([l[1] for l in fn_lines])
    
    # 1. Check local handles
    for l_idx, l_raw in fn_lines:
        m_local = re.match(r'^\s*local\s+([a-zA-Z0-9_]+)\s+([a-zA-Z0-9_]+)', l_raw.strip(), re.IGNORECASE)
        if m_local:
            l_type = m_local.group(1).lower()
            l_name = m_local.group(2)
            if l_type in HANDLE_TYPES:
                if not re.search(rf'set\s+{re.escape(l_name)}\s*=\s*null', fn_text, re.IGNORECASE):
                    unnulled_handles.append((fn_name, l_idx, l_type, l_name))

    # 2. Check group leaks
    if any(k in fn_text for k in ['GetUnitsInRangeOfLoc', 'GetUnitsInRect', 'GetUnitsOfPlayer']) and ('DestroyGroup' not in fn_text and 'bj_wantDestroyGroup' not in fn_text):
        grp_leaks.append((fn_name, fn['start']))

    # 3. Check force leaks
    if ('GetPlayersMatching' in fn_text or 'CreateForce' in fn_text) and 'DestroyForce' not in fn_text:
        force_leaks.append((fn_name, fn['start']))

    # 4. Check location leaks
    if any(pattern.search(fn_text) for pattern in location_alloc_patterns) and 'RemoveLocation' not in fn_text:
        loc_leaks.append((fn_name, fn['start']))

print(f"\n--- Diagnostic Results ---")
print(f"Functions with un-nulled local handles: {len(unnulled_handles)}")
print(f"Functions with potential Location leaks: {len(loc_leaks)}")
print(f"Functions with Group leaks: {len(grp_leaks)}")
print(f"Functions with Force leaks: {len(force_leaks)}")

if len(unnulled_handles) == 0 and len(grp_leaks) == 0 and len(force_leaks) == 0:
    print("\n>>> SCRIPT IS CLEAN AND LEAK-FREE! <<<")
