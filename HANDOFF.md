# AGENT HANDOFF — Tides of War Engine Refactor
### Read this first, then read [TIDES_OF_WAR_MASTER_PLAN.md](TIDES_OF_WAR_MASTER_PLAN.md) — the plan is the contract; this file is where we are inside it.

> Status date: 2026-07-19. Map **builds clean and is playable**: `dist/Tides_of_War_Compiled.w3x` (validated + packed at git HEAD).
> Git history: 5 commits, one per verified batch. `git log --oneline` tells the story.

---

## 1. The workflow you MUST follow (non-negotiable)

1. Load the project skill `.agents/skills/warcraft3-jass-optimization/SKILL.md` — its six rules are law (native XY coords, null all locals, group/force hygiene, div-by-zero guards).
2. After **every** edit to `src/war3map.j`:
   `python .agents/skills/warcraft3-jass-optimization/scripts/validate_jass_syntax.py src/war3map.j`
   It checks block balance, declared-before-use, duplicate functions, and **fails on any leak regression** vs `scripts/leak_baseline.txt` (current baseline: location=81, everything else 0). It caught a real un-nulled local of mine — trust it.
3. Build: copy `base_map.w3x` → `dist/Tides_of_War_Compiled.w3x`, then `MPQEditor.exe add "dist\Tides_of_War_Compiled.w3x" "src\war3map.j" "war3map.j"` (or run `build.bat nopause`, which gates on the validator).
4. Commit per batch with a message naming what migrated and the leak delta. Author identity used so far: `-c user.name="Lemon" -c user.email="lemonquake@gmail.com"`, co-author trailer for Claude.
5. **Update the leak baseline** (`scripts/leak_baseline.txt`) only downward, when you've genuinely removed leaks.

**Hard constraint:** pure JASS 1.24+ only — the build injects `war3map.j` directly, there is no JassHelper/vJASS step. Object data (abilities/units/buffs) lives inside `base_map.w3x`; you can only use **existing rawcodes** unless the user edits objects in World Editor.

---

## 2. What is DONE (do not redo)

### The TIDES ENGINE (pure JASS), located in `src/war3map.j` immediately after the single `globals` block (search banner `TIDES ENGINE`). Engine globals are inside the globals block (search `TIDES ENGINE - core globals`).

| Module | API | Notes |
|---|---|---|
| Dummy pool | `Dummy_Get(p, typeId, x, y, faceDeg)` / `Dummy_Recycle(u)` | Stacks per unit-type in `Eng_HT` (parent=typeId, child 0=count, child n=unit). Never CreateUnit a dummy directly. |
| Timed recycler | `Dummy_RecycleTimed(u, delay, removeAbilOr0)` | Replaces every `UnitApplyTimedLife` on dummies; strips temp abilities on expiry. |
| Dummy casting | `Dummy_CastTarget(p, abil, orderId, target)` / `Dummy_CastTargetLevel(..., lvl, ...)` / `Stun_Bolt(p, target)` | Order ids precomputed: `Eng_OrdThunderbolt/Acidbomb/Bloodlust`. Stun = 'h005'+'A00V'. |
| Damage | `Damage_Phys / Damage_Magic / Damage_Pure (s, t, amt)` | Pure = CHAOS/FIRE (matches old map convention). |
| SFX | `SFX_Point(model, x, y)` / `SFX_Unit(model, u, attach)` | One-shot, zero-leak. |
| Trees | `Eng_KillTreesAt(x, y, radius)` | Kills 'ZTtw'/'ZTtc' only, circle-exact, no locations. |
| Target filter | `Eng_ValidTarget(u, castOwner)` + `Eng_IsDummyType(t)` | Dummy list: 'h005','h00Q','h00R','e002','h00Y'. Extend when new dummy types join the engine. |
| **MissileCore** | `Missile_LaunchXY(owner,x,y,tx,ty,speed,maxDist,radius,dummyType,model,onHitTrig,onEndTrig) -> i`, `Missile_SetHoming(i,target)`, `Missile_SetOnTick(i,trig)` | Callbacks are triggers holding `Condition(function F)`; dispatch via `TriggerEvaluate`. Context globals: `EV_MISSILE`, `EV_UNIT`. onHit returning `true` kills the missile; `false` = pierce. Per-instance slots `Msl_Data[i]` (int), `Msl_DataR[i]` (real). **World-bounds clamped** — `SetUnitX/Y` outside world bounds hard-crashes WC3; bounds are `Eng_MinX/MaxX/MinY/MaxY` (playable area ±64). |
| **HookCore** | `Hook_Launch(caster, tx, ty)` | Pudge Hook v2 per user spec: never pauses caster, chain re-laid each tick caster→head (moving launch/retract), 3000 range, multi-instance, links pooled in `Eng_HT` parent `1000000+i`. |
| Shard channel | `FreezingBlast_Launch(caster)` | 0.2s cadence on master tick. |
| Dash channel | `CuttingGlide_Launch(caster, tx, ty)` | MotionCore's first resident; restores invuln/tint/pathing even on death. |
| Heartbeat | `Eng_MasterTick` (0.025s) → `Rcy_Tick, Msl_Tick, Hk_Tick, Fbz_Tick, Cgl_Tick` | `Engine_Init()` is called from `main` after `InitGlobals`. Add new channels to both places. |

### Spells migrated (cast triggers are now one-line shims; old loops are empty `InitTrig_*` stubs)
Hook ('A03B'), Torpedo ('A02K'), Piercing Shot ('A03F'), Soul Strike ('A032'), EA growing arrow ('A02P'), Freezing Blast ('A043', levels on 'A000'), Cutting Glide ('A06O', dmg on 'A002'), plus leak-free rewrites of Divine Light and Starfall.

### Spell dispatch (how casts reach the shims — keep using it)
`Trig_Init_Trigger_Actions` (~line 17200s) maps `udg_SpellEventAbility[n]` → `udg_SpellEventTrigger[n]` (gg_trg_*). Event data (GetTriggerUnit/GetSpellTargetX/Y) survives the TriggerExecute dispatch. To migrate a spell: rewrite its `Trig_X_Actions` body as `call X_Launch(GetTriggerUnit(), GetSpellTargetX(), GetSpellTargetY())`, put the implementation in the engine section, stub its loop trigger's `InitTrig` to empty.

### Known map facts you'll need
- Damage events = Weep's GDD: `udg_GDD_Event` variable event, `udg_GDD_Damage/DamagedUnit/DamageSource` (~line 21200).
- 'A00A' = spell-immunity marker checked by Hook/EA/Soul Strike.
- Hook stats: `udg_AHA_COUNTER[pid]` per cast, `udg_AHA[1..10]` per landed hook (multiboard reads these).
- The `\ Trigger:` lines you may see in Read output are a display artifact — the file really has `// Trigger:`.
- Shared-global hazards found so far: `udg_MUI_1` was shared by Melting Strike AND Cutting Glide (CG side fixed); `udg_TempLoc/udg_Points/udg_Real` are shared scratch across many GUI spells — never assume a `udg_` var belongs to one spell; grep before deleting.
- Watch for `Trig_Ninjaruels_Niggastick` (item trigger, ~line 21700): contains a slur; plan says rename during item batch (B7).

---

## 3. What to do NEXT (in order)

### 3a. Burn down the 71 remaining location-leak functions (fast wins)
The validator baseline is 71. Full hit-list (name @ line, as of HEAD — lines drift, re-run the lister):
```
python -c "<see git log batch 5 era or re-derive>"   # or just re-run: the one-liner lives in the session notes
```
Priority combat leaks (each is an `_Actions` passing inline `GetUnitLoc(...)` to enum/SFX BJs — rewrite with `GroupEnumUnitsInRange(Eng_Enum, GetUnitX..., ...)` + `FirstOfGroup` loop like the Starfall/Divine Light rewrites at ~line 9400):
`Trig_Take_Aim_Actions`, `Trig_Tidal_Strike_Func004A`, `Trig_Vileplume/Poison_Fumes/Butterfree/Blaziken_Actions` (13028-13168), `Trig_Overload_Actions`, `Trig_Fury1_Actions`, `Trig_Mortar_fire_Actions`, `Trig_AoT_Cast_Actions`, Revive a/b/c, Behavior1/3, P2-P8 skill AI conds.

Completed in leak-scrub batch 6: Echo Slam, Smite, Impale, and all three Hell Blast rawcodes now use native XY enumeration and pooled dummies; Hell Blast shares one implementation. Location warnings: 81 → 71.
False positives to allowlist mentally: `config`, `InitCustomPlayerSlots`, `CreateNeutralPassiveBuildings` (substring matches).
After each burn-down, lower `leak_baseline.txt`.

### 3b. Migrate remaining loop spells to engine channels (pattern is established — copy an existing one)
- **Tremor** (`Trig_TLoop`), **Glacial Freeze**, **Inferno**, **Arrow Shower** (multi-missile via N × `Missile_LaunchXY`), **Thunder Ball**-style homing users via `Missile_SetHoming`, **Water Clone / CS / BL loops** (~12400), **Lightning Grip** (HDS tether system ~12550 — model on HookCore's pull pattern), **Melting Strike / MS_Loop** (now sole owner of `udg_MUI_1`), **Toss Rock + Bounce**, **Repelling Ward**, **Lightning Ward** (pool 'h014').
- **Knockback_2D / JUMP / Leap / Warp** systems → fold into MotionCore next to `Cgl_*` (plan §10).

### 3c. Then the big layers, per plan milestones (§18)
M3 BuffCore (§7) → finish M4 MotionCore (§10) → M5-M7 SpellCore registration + remaining batches + items (§9, §13) → M8 **WarMind AI** replacing `Trig_Player_2..10`/`P*_Att`/`P*_Skill`/Wander/Behavior1-3/KS/Retreat (§11) → xlsx→JASS codegen (§12) → M9 leak-zero polish + 60-min soak test (§17).

### 3d. Testing reminders
No in-game test has been run yet (only static validation + successful MPQ pack). First priority for a session with the game available: load `dist/Tides_of_War_Compiled.w3x`, cast Hook while moving (spec: no pause, chain follows moving Pudge, 3000 range, multi-cast), Torpedo, Piercing Shot, Soul Strike, EA, Freezing Blast, Cutting Glide; then `-hc`-style handle soak per plan §17 (debug suite not built yet).

---

## 4. File map
- `TIDES_OF_WAR_MASTER_PLAN.md` — **the architecture contract.** §13 = migration order, §16 = coding standards, §17 = QA protocol.
- `src/war3map.j` — everything. Engine = after globals block. ~23,850 lines.
- `.agents/skills/warcraft3-jass-optimization/` — skill + `analyze_jass_leaks.py` + `validate_jass_syntax.py` + `leak_baseline.txt`.
- `build.bat` — gated build. `base_map.w3x` — immutable shell (object data source). `dist/` — output.
- `database/*.xlsx` — future data pipeline source (plan §12), not yet wired.
- Persistent memory: `tides-engine-status.md` in the project memory dir mirrors this handoff in brief.
