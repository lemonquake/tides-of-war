# TIDES OF WAR — Master Engineering Plan
### The definitive roadmap for refactoring every GUI-converted trigger into a unified, leak-free, data-driven pure-JASS engine — with custom Ability, Buff, Timer, Projectile, Damage, and AI systems

> **Document status:** Living design document. Version 1.0 — 2026-07-18
> **Scope:** `src/war3map.j` (~24,000 lines), built into `dist/Tides_of_War_Compiled.w3x` via `build.bat` + MPQEditor.
> **Governing skill:** `.agents/skills/warcraft3-jass-optimization` — every rule in that skill (native XY coords, null-all-locals, group/force hygiene, div-by-zero guards) is mandatory law for all code written under this plan.

---

## Table of Contents

1. [Current-State Audit (what we actually have)](#1-current-state-audit)
2. [Target Architecture Overview](#2-target-architecture-overview)
3. [Layer 0 — Toolchain & Build Pipeline](#3-layer-0--toolchain--build-pipeline)
4. [Layer 1 — Core Foundation Modules](#4-layer-1--core-foundation-modules)
5. [Layer 2 — The Timer System (TimerCore)](#5-layer-2--the-timer-system)
6. [Layer 3 — The Damage Engine](#6-layer-3--the-damage-engine)
7. [Layer 4 — The Buff System (BuffCore)](#7-layer-4--the-buff-system)
8. [Layer 5 — The Projectile System (MissileCore)](#8-layer-5--the-projectile-system)
9. [Layer 6 — The Ability System (SpellCore)](#9-layer-6--the-ability-system)
10. [Layer 7 — Movement & Physics (Knockback, Jump, Dash)](#10-layer-7--movement--physics)
11. [Layer 8 — The AI Brain (WarMind)](#11-layer-8--the-ai-brain-warmind)
12. [Data-Driven Pipeline (xlsx → JASS)](#12-data-driven-pipeline)
13. [Migration Plan — Spell-by-Spell](#13-migration-plan--spell-by-spell)
14. [Case Study — Torpedo, Before and After](#14-case-study--torpedo)
15. [Leak Elimination Campaign](#15-leak-elimination-campaign)
16. [Performance Budget & Coding Standards](#16-performance-budget--coding-standards)
17. [Testing & QA Protocol](#17-testing--qa-protocol)
18. [Milestones & Delivery Order](#18-milestones--delivery-order)
19. [Risk Register](#19-risk-register)

---

## 1. Current-State Audit

Measured directly from `src/war3map.j` on 2026-07-18:

| Metric | Value | Verdict |
|---|---|---|
| Total lines | ~23,985 | — |
| GUI-converted triggers (`Trig_*_Actions`) | ~300 | Nearly all must be rewritten |
| `udg_` global variables | **896** | Collapse into system-owned storage |
| `CreateTrigger` calls | 308 | Target: < 60 after refactor |
| `PolarProjectionBJ` calls | **86** | All replaced with native `Cos`/`Sin` math |
| `GetUnitsInRange*/GetUnitsInRect*` BJ enums | 122 | Replace with reused global group + native enum |
| `CreateNUnitsAtLoc` (dummy spam) | **98** | Replace with recycled dummy pool |
| Potential location leaks (analyzer) | **86 functions** | Zero tolerance — all eliminated |
| Un-nulled local handles | 0 | Keep at 0 |

### What exists today (and its problems)

- **Spells** are per-hero GUI conversions (`Trig_Torpedo_*`, `Trig_Echo_Slam_*`, `Trig_Fissure_*`, `Trig_Starfall_*`, `Trig_Hook_*`, `Trig_Soul_Strike_*`, …). Each spell owns its own parallel `udg_` arrays (`udg_WB_Hero[]`, `udg_WB_Distance[]`, …), its own periodic loop trigger, and its own incrementing counter (`udg_Times3`) that **never recycles indices** — a guaranteed array overflow in long games.
- **Stuns** are done by spawning `'h005'` dummies that cast `thunderbolt` (`'A00V'`) — 98 dummy spawns across the map, each a full unit allocation with pathing, collision, and a timed-life decay.
- **"Systems"** exist in embryonic form: `Trig_Unit_Indexer`, `Trig_GUI_SpellEvent`, `Trig_Knockback_2D`, `Trig_JUMP_LOOP`, `Trig_Combat_*`, `Trig_Take_Damage` — these are GUI community systems, half-integrated, each with its own event plumbing. They will be superseded by the layers below.
- **AI** is 27 separate triggers (`Trig_Player_2..10`, `Trig_P*_Att`, `Trig_P*_Skill`) plus `Trig_Wander`, `Trig_Behavior1..3`, `Trig_KS`, `Trig_Retreat` — hardcoded per-player copies of the same logic. No item purchasing intelligence, no ability scoring, no threat evaluation.
- **Items** (`Trig_The_Triforce`, `Trig_Dragon_Slayer`, `Trig_Blink_Dagger_*`, …) are one trigger per item with duplicated combat-state checks.
- **Game flow** (modes, duels, multiboard, respawn, kill streaks, bomb game-mode) is functional and mostly fine — lowest refactor priority.
- **Databases** exist as Excel files (`database/UnitData.xlsx`, `ItemData.xlsx`, `SkilData.xlsx`, `EfctData.xlsx`, …) but are not wired into codegen. This is a huge untapped asset — see [§12](#12-data-driven-pipeline).

### Why plain JASS (and not vJASS) — a decision, made explicit

The build pipeline injects `src/war3map.j` **directly** into the MPQ. There is no JassHelper/vJASS compile step. Two options:

- **Option A (chosen): Pure JASS 1.24+** using hashtables + parallel arrays + index recycling ("struct emulation by hand"). Zero new toolchain dependencies; what you write is what ships. All code sketches in this document are pure JASS.
- **Option B (optional upgrade later):** Add JassHelper to `build.bat` to get structs/libraries/textmacros. The architecture below is deliberately designed so that every module maps 1:1 onto a vJASS struct if we ever adopt Option B — nothing would need redesign, only re-syntaxing.

Either way, **pjass** (the syntax checker) gets added to the build immediately — see Layer 0.

---

## 2. Target Architecture Overview

Everything is rebuilt as a layered engine. Higher layers may only call downward. No spell ever touches a timer, group, or dummy unit directly — it goes through the engine API.

```
┌────────────────────────────────────────────────────────────┐
│  GAME LAYER: modes, duels, multiboard, respawn, streaks    │
├────────────────────────────────────────────────────────────┤
│  Layer 8  WarMind AI      (hero brains, item builds)       │
├────────────────────────────────────────────────────────────┤
│  Layer 6  SpellCore       (ability definitions/instances)  │
│  Layer 7  MotionCore      (knockback / jump / dash)        │
├────────────────────────────────────────────────────────────┤
│  Layer 5  MissileCore     (projectiles: homing/arc/aoe)    │
│  Layer 4  BuffCore        (buffs/debuffs/stacks/dispels)   │
├────────────────────────────────────────────────────────────┤
│  Layer 3  DamageCore      (unified damage pipeline)        │
├────────────────────────────────────────────────────────────┤
│  Layer 2  TimerCore       (one master clock, N channels)   │
├────────────────────────────────────────────────────────────┤
│  Layer 1  Foundation: UnitDex · Alloc · Table · DummyPool  │
│           GroupUtils · EventBus · MathUtils · SFX          │
└────────────────────────────────────────────────────────────┘
```

**File organization inside `war3map.j`:** the single file is kept, but reorganized into clearly banner-commented sections in dependency order (Foundation first, Game layer last), so any future split into multiple files (Option B) is mechanical.

---

## 3. Layer 0 — Toolchain & Build Pipeline

Before writing engine code, harden the pipeline:

1. **Add `pjass.exe`** to the repo and to `build.bat` — the build must *fail* if the script doesn't parse against `common.j`/`Blizzard.j`. Today a typo ships a silently broken map.
2. **Write the missing `validate_jass_syntax.py`.** The skill's workflow (step 3) references `scripts/validate_jass_syntax.py`, but only `analyze_jass_leaks.py` exists. Implement it: block-balance checking (`function/endfunction`, `loop/endloop`, `if/endif`, `globals/endglobals`), plus a zero-leak-warnings gate that runs `analyze_jass_leaks.py` and fails on regressions.
3. **`git init`** the project. A 24k-line hand-edited file with no VCS is a catastrophe waiting to happen. Commit before/after every migration batch.
4. **Upgraded `build.bat`:**
   ```bat
   python .agents\skills\warcraft3-jass-optimization\scripts\analyze_jass_leaks.py src\war3map.j || exit /b 1
   python .agents\skills\warcraft3-jass-optimization\scripts\validate_jass_syntax.py src\war3map.j || exit /b 1
   pjass common.j Blizzard.j src\war3map.j || exit /b 1
   copy /Y "base_map.w3x" "dist\Tides_of_War_Compiled.w3x"
   MPQEditor.exe add "dist\Tides_of_War_Compiled.w3x" "src\war3map.j" "war3map.j"
   ```
5. **Extract `common.j` / `Blizzard.j`** from the game (or `base_map.w3x`) into a `vendor/` folder for pjass.

---

## 4. Layer 1 — Core Foundation Modules

### 4.1 UnitDex — unit indexing (replaces `Trig_Unit_Indexer`)

Every unit gets a stable integer id in `[1, 8190]`, assigned on enter-map, recycled on a deferred schedule after death/removal. All per-unit data in every system is `array[GetUnitId(u)]` — O(1), no hashtable lookups in hot loops.

```jass
globals
    integer array UDex_Recycle      // free-list of ids
    integer       UDex_Count = 0
    integer       UDex_RecycleCount = 0
    unit array    UDex_Unit         // id -> unit
endglobals
function GetUnitId takes unit u returns integer
    return GetUnitUserData(u)       // stored via SetUnitUserData on index
endfunction
```

- Fires `EventBus` events `EVENT_UNIT_INDEXED` / `EVENT_UNIT_DEINDEXED` so BuffCore/AI/etc. can attach and clean per-unit state.
- **Rule:** nothing else in the map may call `SetUnitUserData`.

### 4.2 Alloc — instance allocator (the "struct emulator")

One tiny pattern reused by every system (timers, buffs, missiles, spell instances): a free-list allocator over parallel arrays. This is what fixes the `udg_Times3`-style ever-growing counters.

```jass
// Per-system: replace X with system prefix
globals
    integer array X_Next   // free list / active linked list
    integer       X_Alloc = 0
    integer       X_Free  = 0
endglobals
function X_Allocate takes nothing returns integer
    local integer i
    if X_Free != 0 then
        set i = X_Free
        set X_Free = X_Next[i]
    else
        set X_Alloc = X_Alloc + 1
        set i = X_Alloc
    endif
    return i
endfunction
function X_Deallocate takes integer i returns nothing
    set X_Next[i] = X_Free
    set X_Free = i
endfunction
```

### 4.3 Table — one shared hashtable

A single `hashtable` (`InitHashtable()`) wrapped with typed getters/setters, used for sparse data (handle→instance mapping, e.g. timer handle → timer data id). Warcraft III caps hashtables at 256 — we use **one**, forever.

### 4.4 DummyPool — recycled caster/effect dummies (kills the 98 `CreateNUnitsAtLoc`)

One dummy unit type (`'h005'` reused, but: locust, no shadow, no collision, `Amov` removed, flying) pooled per player:

- `Dummy_Get(player, x, y, facing)` → recycled unit or new if pool empty.
- `Dummy_Recycle(u)` / `Dummy_RecycleTimed(u, delay)`.
- `Dummy_CastTarget(player, abilId, level, order, target)` and `Dummy_CastPoint(...)` — the one-line replacement for every "spawn dummy, add ability, timed life, issue order" block in the map.
- Pool pre-warmed at init (e.g. 8 dummies/player) to avoid in-combat allocation spikes.

### 4.5 GroupUtils, MathUtils, SFX

- **GroupUtils:** one global scratch `group ENUM_GROUP` + `ForUnitsInRange(x, y, radius, filterFunc, actionFunc)`-style wrappers using `GroupEnumUnitsInRange` + `FirstOfGroup` loops (no `boolexpr` allocation, no group leaks — filter is a plain function call inside the loop). This retires all 122 BJ enum calls.
- **MathUtils:** `Angle(x1,y1,x2,y2)`, `DistSq(x1,y1,x2,y2)` (compare squared distances — no `SquareRoot` in hot paths), `ProjectX/Y(x, dist, angleRad)`. This retires all 86 `PolarProjectionBJ` calls. All engine angles are **radians**; degrees exist only at GUI boundaries.
- **SFX:** `AddSfx(model, x, y)` / `AddSfxTarget(model, unit, attach)` that create-destroy-null in one call for one-shot effects (destroying an effect immediately still plays its birth animation — standard trick), plus handle-returning variants for persistent effects owned by buffs.

### 4.6 EventBus — typed custom events

A tiny registry: systems register handler triggers per event id; firing sets shared "event args" globals and evaluates the handlers. Events: unit indexed/deindexed, damage dealt (pre/post), buff applied/removed/expired, missile launched/hit, spell cast start/effect/finish, hero killed, item purchased. **This is the seam that makes everything composable** — e.g. the kill-streak system and the AI both just subscribe to the same death event instead of owning duplicate triggers.

---

## 5. Layer 2 — The Timer System

**Problem today:** ~53 scattered `TimerStart`/periodic-trigger usages; each spell runs its own 0.02–0.04s loop trigger even when zero instances are active.

**Design — one master clock, many logical timers:**

- `TICK = 0.03125` (32 fps — divides evenly into WC3's engine cadence; smooth for projectiles and knockback).
- One periodic native timer runs the **master tick**. Systems register *channels* (Missile update, Buff periodic, Motion update, AI micro) that iterate their own active-instance linked lists. When a channel has zero instances, it's skipped (cheap integer check). When *all* channels are empty the master timer pauses.
- **TimerCore one-shot API** for delayed callbacks without handle churn:
  ```jass
  function Timer_After takes real delay, integer callbackId, integer data returns integer
  function Timer_Every takes real period, integer callbackId, integer data returns integer  // repeating
  function Timer_Cancel takes integer timerInstance returns nothing
  ```
  Implemented on the master tick with expiry timestamps (no per-call `CreateTimer`). Callback dispatch via a `trigger array` indexed by `callbackId` (registered at init) — pure JASS's answer to function pointers, using `TriggerEvaluate` on triggers holding `condition` functions (conditions are ~2× faster than actions and don't queue).
- **Long-tick channel** (0.25s) for cheap periodic work: regen effects, AI macro decisions, combat-state timeouts (`Trig_Combat_*` logic moves here).

This retires every `Trig_*_Loop` trigger in the map (`Trig_Smite_Loop`, `Trig_Soul_Strike_Loop`, `Trig_MS_Loop`, `Trig_TLoop`, `Trig_Hook_Loop`, `Trig_JUMP_LOOP`, …).

---

## 6. Layer 3 — The Damage Engine

**Problem today:** `Trig_On_Damage`, `Trig_On_Damage2`, `Trig_Take_Damage`, `Trig_Amplify_Damage`, item procs, and lifesteal all hook damage independently and can't see each other. Spell damage is raw `UnitDamageTarget` with no shared pipeline.

**Design — every point of damage flows through one function:**

```jass
function Damage_Deal takes unit source, unit target, real amount, integer dmgType, integer flags returns real
```

- `dmgType`: `DMG_PHYSICAL | DMG_MAGICAL | DMG_PURE`. `flags`: bitmask (`DF_NO_REFLECT`, `DF_DOT`, `DF_SPELL`, `DF_ATTACK`, …) using integer addition/`ModuloInteger` bit tricks (pure JASS has no bitwise ops — we use a small `HasFlag(flags, f)` helper).
- **Pipeline stages**, each an EventBus event with mutable shared globals (`Damage_Amount`, `Damage_Source`, `Damage_Target`, `Damage_Type`):
  1. `PRE_MITIGATION` — amplifiers (Amplify Damage curse), crits, spell amp.
  2. `MITIGATION` — armor/resist handled by engine or buffs (Improved Resistance, Valor, shields absorb here and can zero the damage).
  3. `POST_DAMAGE` — lifesteal, on-hit procs (Denki's Shock Tazer, Derping Axe cleave), Bash, kill-credit, combat-state tagging, AI threat table updates.
- Native `EVENT_UNIT_DAMAGED` (registered per-unit on index) feeds *attack* damage into the same pipeline with `DF_ATTACK`, with a recursion guard so proc damage doesn't re-trigger procs infinitely.
- Returns the damage actually dealt (post-mitigation) so spells/AI can react.

Every migrated spell **must** deal damage via `Damage_Deal`. Direct `UnitDamageTarget`/`UnitDamageTargetBJ` calls become lint errors in the analyzer (we extend `analyze_jass_leaks.py` to flag them).

---

## 7. Layer 4 — The Buff System (BuffCore)

**Problem today:** stuns are `thunderbolt` dummies; slows/DoTs are ad-hoc groups like `udg_Freezed[]`; `Trig_Get_DOT`/`Trig_Deal_DOT` is a bespoke DoT loop; there is no unified concept of "this unit has buff X at level Y for Z seconds."

**Design — a buff is an allocated instance attached to a unit:**

Per-instance data (parallel arrays via Alloc): `Buff_TypeId`, `Buff_Target`, `Buff_Source`, `Buff_Level`, `Buff_Stacks`, `Buff_Remaining`, `Buff_TickAccum`, `Buff_Sfx`, plus per-unit intrusive linked list (`Buff_NextOnUnit`) rooted at `BuffHead[unitId]`.

Per-**type** data (registered at init, one row per buff type): name, category (`BUFF_STUN`, `BUFF_SLOW`, `BUFF_DOT`, `BUFF_SILENCE`, `BUFF_ROOT`, `BUFF_SHIELD`, `BUFF_STAT`, `BUFF_CUSTOM`), positive/negative, dispellable flag, max stacks, **stacking policy** (`REFRESH | STACK_INTENSITY | STACK_INDEPENDENT | IGNORE`), tick period, attach SFX model + attach point, and four callback ids (`onApply`, `onTick`, `onRemove`, `onExpire`) dispatched through TimerCore's trigger-array mechanism.

**API:**

```jass
function Buff_Apply   takes unit target, unit source, integer buffTypeId, integer level, real duration returns integer
function Buff_Remove  takes integer buffInstance returns nothing
function Buff_Dispel  takes unit target, boolean positive, integer maxCount returns integer
function Buff_Has     takes unit target, integer buffTypeId returns boolean
function Buff_GetLevel/GetStacks/GetRemaining/Refresh/AddStacks ...
```

**Engine-owned status effects** (so no spell ever spawns a stun dummy again):

- `BUFF_STUN` / `BUFF_ROOT` / `BUFF_SILENCE` are implemented **once** inside BuffCore using a hidden aura/`Abun`-style dummy ability or DummyPool cast — the implementation detail lives in exactly one place. Spells just call `Buff_Apply(target, caster, BUFF_STUN_ID, 1, 2.0)`.
- `BUFF_SLOW`/`BUFF_STAT` variants manipulate movement speed / bonuses through a small bonus-manager (ability-based `'AId1'..` item-armor/damage/speed abilities added-removed by level), so effects **stack correctly and always revert exactly** — the root cause of most "my hero is permanently slow" bugs in GUI maps.
- Ticking (DoTs, heals-over-time, Burning Will, Rot, Curse of the Sea) runs on the TimerCore buff channel; `onTick` deals damage through `Damage_Deal` with `DF_DOT`.
- On `EVENT_UNIT_DEINDEXED` or death, all buffs on the unit are force-removed — automatic cleanup, zero leaks.

This single layer absorbs and retires: `Trig_Get_DOT`/`Trig_Deal_DOT`, `udg_Freezed[]` groups, `Trig_Rot`, `Trig_Burning_Will*`, `Trig_Amplify_Damage` (becomes a buff with a PRE_MITIGATION hook), `Trig_Power_Stance*`, `Trig_Take_Aim`, all `thunderbolt` dummy stuns, and every hand-rolled slow.

---

## 8. Layer 5 — The Projectile System (MissileCore)

**The crown jewel — every skillshot, orb, hook, arrow, and thrown rock in the map becomes a tracked missile instance.** This is what makes "custom effects during, after, or before" trivially possible for every projectile of every skill.

**Per-instance state** (Alloc + parallel arrays): owner unit, owner player, missile dummy unit (from DummyPool, model attached via `AddSpecialEffectTarget`), `x, y, z`, `vx, vy` (precomputed velocity per tick), speed, max range / traveled, target unit (for homing) or target point, collision radius, arc height (parabolic z via `SetUnitFlyHeight`), pierce count, spell instance backref, hit-group (units already struck, so piercing missiles hit each target once), and five callback ids:

- `onLaunch` — fired once at creation.
- `onPeriod` — every tick (trail effects, cone checks, growing radius — e.g. Arrow Shower).
- `onHitUnit` — enemy entered collision radius; callback returns whether the missile dies, pierces, or bounces (Bounce/Toss Rock logic).
- `onHitGround`/`onExpire` — reached destination or max range (AoE detonation — Torpedo freeze field, Hell Blast).
- `onDestroy` — guaranteed final cleanup hook.

**API:**

```jass
function Missile_LaunchPoint  takes unit owner, real x, real y, real tx, real ty, integer missileTypeId returns integer
function Missile_LaunchTarget takes unit owner, unit target, integer missileTypeId returns integer  // homing
function Missile_Get*/Set* ...   // speed, angle (redirect mid-flight!), callbacks, userData
```

**Missile types** are registered at init (model path, speed, radius, arc, homing flag, default callbacks) — data rows, not code. Adding a new projectile to a spell is ~5 lines.

**Update loop** (TimerCore missile channel): advance position, update dummy, parabola z, per-tick enemy scan via GroupUtils reusable enum at (x,y) with collision radius, dispatch callbacks. Budget: 100 simultaneous missiles at 32 fps with zero allocations per tick (all groups/dummies recycled).

**Special modes** built in from day one because the map already needs them:
- **Homing** (Soul Strike, Thunder Ball) — recompute heading each tick; target-death fallback to last known point.
- **Pull/tether** (Hook, Lightning Grip, Drag, Leash) — missile that, on hit, reverses and drags the struck unit via MotionCore.
- **Boomerang/return** (Cutting Glide) — invert velocity at apex, `onHitUnit` active both ways.
- **Wave/multi-missile** (Arrow Shower, Starfall, Tidal Orbs) — N missiles from one spell instance sharing `userData`.

---

## 9. Layer 6 — The Ability System (SpellCore)

The layer that ties it all together. **A spell = a registered definition + short callback functions. All plumbing (events, instances, per-cast data, cleanup) is engine-owned.**

### 9.1 Spell registration (replaces 100+ `InitTrig_*` + condition functions)

```jass
call Spell_Register('A01X', SPELL_TARGET_POINT, onCastId, onEffectId, onEndId)
call Spell_SetPeriodic('A01X', 0.03125, onPeriodId)   // optional per-instance periodic
```

**One** trigger for `EVENT_PLAYER_UNIT_SPELL_EFFECT` (plus one each for `_CAST`, `_CHANNEL`, `_ENDCAST`, `_FINISH`) dispatches by `GetSpellAbilityId()` through the Table — replacing ~100 separate spell triggers. This also retires `Trig_GUI_SpellEvent` and `Trig_Loop_Spell`.

### 9.2 Spell instances — true multi-unit, multi-player instancing

On cast, SpellCore allocates an instance: caster, caster id, owner, level, target unit/x/y, per-instance user slots (`Spell_Int1..4`, `Spell_Real1..4`, `Spell_Unit1..2`, `Spell_Group`) and inserts it into the periodic channel if registered. **Ten Blazikens can all cast the same spell simultaneously** — every tick each instance runs with its own data; when an instance finishes it deallocates and recycles its group/dummies. The `udg_Times3`-style shared counters die here.

### 9.3 Spell data — levels as data, not if-chains

Per-spell, per-level tuning tables filled at init (from the xlsx pipeline, §12): `Spell_Damage[spellIndex * 4 + level]`, cooldown, range, radius, duration, missile type, buff type. The `Trig_Hell_Blast_250/450/750` triplet (three triggers for three levels of one spell!) collapses into one definition reading its level table.

### 9.4 Composition — the payoff

A typical migrated spell is now ~30 lines: an `onEffect` that launches missiles, an `onMissileHit` that applies a buff and damage. Example shape:

```jass
// ---- Freezing Blast: point-target missile, AoE freeze on arrival ----
function FreezingBlast_OnHit takes nothing returns boolean
    call Damage_Deal(Missile_Owner[EV_MISSILE], EV_UNIT, FB_Damage[EV_LEVEL], DMG_MAGICAL, DF_SPELL)
    call Buff_Apply(EV_UNIT, Missile_Owner[EV_MISSILE], BUFF_FROZEN, EV_LEVEL, FB_FreezeTime[EV_LEVEL])
    return true  // missile dies
endfunction
function FreezingBlast_OnCast takes nothing returns boolean
    call Missile_LaunchPoint(Spell_Caster[EV_SPELL], Spell_CasterX, Spell_CasterY, Spell_TargetX, Spell_TargetY, MISSILE_FROSTBOLT)
    return false
endfunction
```

No locations. No leaks. No dummies to remember to kill. No loop trigger. No globals except system-owned arrays.

---

## 10. Layer 7 — Movement & Physics

Consolidates `Trig_Knockback_2D`, `Trig_Knockback_Effects`, `Trig_Knockback_Collider`, `Trig_Collide`, `Trig_JUMP_*`, `Trig_Jump/Jump2`, `Trig_Leap*`, `Trig_EA_Movement`, `Trig_Hook_Loop` drag, `Trig_Drag`, `Trig_Toss_Rock*` into **one** MotionCore channel:

- `Motion_Knockback(u, angle, distance, duration, flags)` — eased displacement with optional tree-destruction (`Trig_trees` logic folds in), wall-collision stop, and collision damage.
- `Motion_Jump(u, tx, ty, duration, arcHeight, onLandCallbackId)` — parabolic `SetUnitFlyHeight` arcs (Leap, Jump, Toss).
- `Motion_Pull(u, towardUnit, speed)` — for Hook/Lightning Grip/Leash tethers.
- Per-unit exclusivity rules (a new knockback overrides an existing one; jumps are uninterruptible), pathability checks each tick (`IsTerrainWalkable` via item-visibility trick or `PATHING_TYPE_WALKABILITY`), and `SetUnitPropWindow`/pause policy centralized so stunned+knocked-back units never end in a broken state.

---

## 11. Layer 8 — The AI Brain (WarMind)

**Goal:** replace the 30+ hardcoded per-player triggers with one data-driven brain instanced per AI-controlled hero — an AI that *knows its abilities, knows the map, knows enemies and allies, and shops intelligently.*

### 11.1 Architecture — utility-scored behavior, two clocks

- **Macro tick (0.25s, long channel):** state selection. States: `FIGHT`, `CHASE`, `RETREAT`, `FARM`, `PUSH`, `SHOP`, `HEAL`, `DUEL`, `WANDER`. Each state has a utility scorer reading the blackboard; highest score wins with hysteresis (switching cost) to prevent oscillation.
- **Micro tick (0.10s, only while in combat):** targeting, ability usage, kiting, item actives.

### 11.2 The blackboard (per AI hero, updated incrementally by engine events)

- **Self:** HP%, MP%, cooldown states (tracked by SpellCore — the AI *asks the engine* `Spell_Ready(hero, abilIndex)` instead of guessing), buff states (am I stunned/silenced — from BuffCore), gold, items, level.
- **Threat table:** per-enemy accumulated threat from the DamageCore `POST_DAMAGE` event (who hurt me/allies recently, decayed over time). Focus-fire target = highest `threat × killability`.
- **Killability:** enemy effective HP vs. our burst estimate — computed from SpellCore damage tables of *ready* abilities. The AI literally knows its combo damage.
- **Map knowledge:** precomputed waypoint graph (fountain, shops, rune/mine spots, arena center, lanes, escape routes) generated once from region data; danger field = recent enemy sightings + tower zones. `Trig_Wander`, `Trig_Retreat`, `Trig_KS`, `Trig_Behavior1..3` all fold into states reading this graph.

### 11.3 Ability intelligence — the killer feature

Every registered spell carries **AI metadata** (in the same registration row, from `SkilData.xlsx`): tactical class (`NUKE_TARGET`, `NUKE_POINT_AOE`, `SKILLSHOT_LINE`, `STUN_TARGET`, `ESCAPE_BLINK`, `SELF_BUFF`, `SUMMON`, `HEAL_ALLY`, `ULT_COMBO_OPENER`), cast range, radius, projectile speed, mana cost, score weight.

The micro tick scores each ready ability against the current situation:
- **Skillshots** (`SKILLSHOT_LINE` — Torpedo, Piercing Shot, Hook): fire at *predicted* position — target's current order point/velocity extrapolated by projectile travel time (the engine knows missile speed!). This makes AI skillshots feel scary-good, tunable per difficulty by adding aim error.
- **AoE nukes**: cast at the centroid of ≥N enemies within radius (cheap clustering via the reusable enum).
- **Stuns**: held for kill-confirm or interrupting enemy channels (SpellCore broadcasts enemy `EVENT_SPELL_CHANNEL` — the AI can *reactively interrupt*, difficulty-gated by reaction delay 0.2–0.8s).
- **Escapes** (Blink Dagger, Warp, Reef Walk): reserved while `RETREAT` scorer is low; triggered by lethal-burst detection (incoming damage in last 1.5s vs remaining HP).
- **Combo sequencing:** per-hero optional combo scripts ("Fissure → walk in → Echo Slam") expressed as ordered ability lists with conditions; fall back to utility scoring when the combo isn't available.

### 11.4 Item intelligence

- **Build orders** from `ItemData.xlsx`: per-hero prioritized shopping list with situational branches (enemy team heavy-magic → Cloak of Magi earlier; getting bursted → Armor of Terror). `SHOP` state paths to the shop waypoint when gold ≥ next item cost and threat is low, buys, returns.
- **Item actives** (Blink Dagger, Denki's Tazer) registered with the same AI metadata as spells — the micro tick uses them like abilities.
- Consumables/healing valued by missing HP.

### 11.5 Humanization & difficulty

Difficulty knobs, all data: reaction delay, aim error (radians of skillshot spread), combo completeness %, threat-table memory length, gold handicap. Insane AI = 0.2s reactions + perfect prediction; Easy = 0.8s + 30% aim error.

---

## 12. Data-Driven Pipeline

The `database/*.xlsx` files become the **single source of truth**, compiled into JASS at build time:

1. Python script `scripts/compile_data.py` (openpyxl) reads `SkilData.xlsx` (spell ids, per-level damage/range/radius/cooldowns, missile type, buff type, AI class), `ItemData.xlsx` (costs, build orders, actives), `UnitData.xlsx` (hero base stats, AI archetype), `EfctData.xlsx` (SFX model paths, attach points).
2. Emits `src/generated_data.j` — a single `TidesData_Init` function full of array assignments.
3. Build step injects it into `war3map.j` between `//! BEGIN GENERATED DATA` / `//! END GENERATED DATA` markers (script-managed region).
4. **Result:** balance patches = edit a spreadsheet, run `build.bat`. No code edits, no risk.

---

## 13. Migration Plan — Spell-by-Spell

Ordered so each batch exercises the newest engine layer, hardest risk first. **Never migrate a spell until its required layers are done and soak-tested.** Old GUI trigger stays in place (disabled) until its replacement passes the QA protocol, then is deleted.

| Batch | Spells / triggers | Exercises |
|---|---|---|
| B1 — Simple nukes & self-buffs | Smite, Divine Light, Blessing, Cold Touch, Wind Strike, Tidal Strike, Overload, Valor, Improved Resistance | SpellCore basics, DamageCore, BuffCore stat buffs |
| B2 — DoTs & auras | Rot, Curse of the Sea, Burning Will, Melting Strike, Poison Fumes, Vileplume, Amplify Damage, Power Stance, Take Aim, After Shock | BuffCore ticking + damage-event hooks |
| B3 — Line/point missiles | Torpedo (case study below), Piercing Shot, Freezing Blast, Soul Strike, Thunder Ball, Explosive Impulse, Gentle Wind, Hell Blast (unify 250/450/750) | MissileCore point/homing |
| B4 — AoE/multi-missile & channels | Starfall, Arrow Shower, Tentacles, Glacial Freeze, Fissure, Impale, Echo Slam, Tremor, Inferno, Lightning Ward, Repelling Ward, Tidal Orbs | Multi-missile, wards via DummyPool, channel events |
| B5 — Movement spells | Leap, Jump, Warp, Reef Walk, Unstable Motion, Hell Step, Cutting Glide, Ancient Hide, Water Clone, Enchant Totem | MotionCore + SpellCore |
| B6 — Tethers & compound ults | Hook, Drag, Lightning Grip, Leash, Toss Rock + Bounce, Chomp, Assassinate/Hitman, Destiny Bond, Soul Strike chains, Butterfree, Blaziken | Everything at once |
| B7 — Items | Triforce, Divine Impaler, Dragon Slayer, Cloak of Magi, Rubber Boots, Tazer, Grand Bracer, Staff of Wuulgarath, Armor of Terror, Derping Axe, Blink Dagger (+Combat variants), Mortar Fire, AoT | Item procs on DamageCore, item actives |
| B8 — AI cutover | All `Trig_Player_*`, `P*_Att`, `P*_Skill`, Wander, Behavior1–3, KS, Retreat, Cast_KB, Pickup_Lines | WarMind replaces all of it |
| B9 — Game systems polish | Combat/PS/Revive/Duel/Multiboard/Bomb mode leak-scrub & EventBus adoption | Cleanup |

One item in B7 needs a content note: the item trigger named `Trig_Ninjaruels_Niggastick` contains a racial slur. **Rename the item and trigger during migration** — it has no place in the map.

---

## 14. Case Study — Torpedo

**Today** (`Trig_Torpedo_*`, ~120 lines + shares `udg_WB_*` arrays and `udg_Times3` with other water spells): creates 2 locations per cast (one *leaked* — `udg_WB_X` is assigned `GetUnitLoc` then removed one line later, but `udg_WB_Point[1/2]` pattern relies on manual cleanup), an ever-growing index (`udg_Times3 = udg_Times3 + 1` — **never decremented: after ~8190 casts across WB spells the map breaks**), a 7-deep nest of generated `Func001Func005002003002001` condition functions, per-cast `'h005'` thunderbolt dummies for the freeze, and `udg_Freezed[]` groups that persist per index forever.

**After migration** (~35 lines):

- `Spell_Register('A0XX', SPELL_TARGET_POINT, TORPEDO_CAST, 0, 0)` — onCast launches `MISSILE_TORPEDO` (registered: model, speed 960/s [= old 30/tick], range 2000, radius from data table).
- `onHitUnit` → `Damage_Deal(..., DMG_MAGICAL, DF_SPELL)` + `Buff_Apply(target, caster, BUFF_FROZEN, level, duration)` → return `false` (pierces, like the original wave).
- `onExpire` → nothing (or a splash SFX via `AddSfx`).
- Freeze visual/behavior lives in `BUFF_FROZEN` (shared by Freezing Blast, Glacial Freeze, Cold Touch — **one** implementation).
- Zero locations, zero dummies at cast site, index recycled on expiry, unlimited concurrent torpedoes from any number of players.

---

## 15. Leak Elimination Campaign

Target: analyzer reports **0 potential location leaks** (from 86) and stays there.

1. Every migrated spell inherently removes its leaks (engine APIs take x/y only).
2. For the 86 flagged functions, triage into: (a) fixed by migration batch (most), (b) game-layer functions needing manual XY conversion (respawn, duels, camera, revive — fix in B9), (c) false positives (document them in the analyzer's allowlist).
3. Extend `analyze_jass_leaks.py` with new lint rules as systems land: forbid `CreateNUnitsAtLoc`, `PolarProjectionBJ`, raw `UnitDamageTarget`, raw `TimerStart` outside TimerCore, `CreateGroup` outside GroupUtils, `SetUnitUserData` outside UnitDex.
4. Handle-count watermarking in QA (§17) proves it at runtime, not just statically.

---

## 16. Performance Budget & Coding Standards

**Budgets (worst case: 10 heroes mid-teamfight):** ≤ 100 active missiles, ≤ 120 active buffs, ≤ 40 motion instances, master tick total ≤ 1.5 ms; steady-state handle count flat over a 60-minute soak (± dummy pool).

**Standards (additive to the optimization skill's six rules):**
- Natives over BJs everywhere (`SetUnitState` vs `SetUnitLifeBJ`, `IsUnitType(u, UNIT_TYPE_DEAD)`+`GetUnitTypeId(u) != 0` vs `IsUnitAliveBJ`).
- No string comparisons in hot paths; orders by order-id integer (`OrderId("thunderbolt")` cached at init).
- `TriggerEvaluate`/conditions for dispatch, never `TriggerExecute` in per-tick code (actions run in a new thread — slow; conditions don't).
- All system globals prefixed by module (`Msl_`, `Buff_`, `Spl_`, `Tmr_`, `AI_`) — greppable ownership; `udg_` reserved for the legacy game layer until B9 retires most of them.
- Every module has a banner header documenting its API and invariants.
- Squared-distance comparisons; radians internally; `RMaxBJ(x, 0.01)` guards on every division by a variable (skill Rule 5).

---

## 17. Testing & QA Protocol

1. **Static gate** (every build): pjass + syntax validator + leak analyzer, all must pass (§3).
2. **In-map debug suite** (chat commands, single-player only): `-hc` prints handle count delta since mark (via the `H2I`-style handle-id trick or `bj_lastCreated` probing); `-spam <spellId> <n>` casts a spell n times at random points via a dummy hero to soak instancing; `-buffs`, `-missiles`, `-motion` print live instance counts; `-aidbg <player>` prints the AI blackboard (state, target, next item, top ability score). The existing debug triggers (`Trig_BM_Debug*`, `Trig_BOMB_Debug*`, `Trig_debug*`) are replaced by this suite.
3. **Per-batch acceptance:** each migrated spell tested for (a) correctness vs old behavior, (b) 3 simultaneous casters, (c) caster dies mid-flight/mid-channel, (d) target dies mid-flight, (e) handle count returns to watermark within 10s.
4. **Soak test:** 60-minute AI-vs-AI match (WarMind makes this possible!) with `-hc` sampled every 5 minutes — flat line required.
5. **Version control:** git tag per completed batch; any regression bisectable.

---

## 18. Milestones & Delivery Order

| # | Milestone | Contents | Exit criterion |
|---|---|---|---|
| M0 | Pipeline hardening | §3: pjass, validator script, git, build gates | Build fails on bad JASS |
| M1 | Foundation | UnitDex, Alloc, Table, DummyPool, GroupUtils, MathUtils, SFX, EventBus | Debug suite shows indexing + pooling working |
| M2 | TimerCore + DamageCore | §5, §6; combat/DoT triggers rewired | All damage flows through pipeline |
| M3 | BuffCore | §7 + engine stun/slow/silence | Thunderbolt dummies gone from migrated paths |
| M4 | MissileCore + MotionCore | §8, §10 | 100-missile stress test at 32fps |
| M5 | SpellCore + Batches B1–B3 | §9 | First 25 spells migrated, leak count < 40 |
| M6 | Batches B4–B6 | All hero spells migrated | Leak count < 15; `udg_Times3`-class counters deleted |
| M7 | Batch B7 + data pipeline | Items + xlsx codegen (§12) | Balance patch via spreadsheet demo |
| M8 | WarMind | §11, Batch B8 | 10-AI soak match completes; old AI triggers deleted |
| M9 | Polish | B9, leak count 0, final soak, difficulty tuning | Analyzer: 0 warnings; 60-min flat handle count |

Each milestone ends with: run analyzer → run validator → build → in-game soak → git commit + tag.

---

## 19. Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| Hand-editing one 24k-line file causes merge-with-self chaos | High | Git from M0; banner-sectioned layout; batch-scoped edits only |
| Pure-JASS verbosity slows development | Medium | Alloc/dispatch patterns are boilerplate-once; optionally adopt JassHelper at any milestone (architecture is 1:1 compatible) |
| Behavior drift vs. beloved old spell feel | Medium | Old trigger kept disabled until side-by-side acceptance passes; speed/damage constants carried over exactly, then moved to data |
| Op limit (JASS thread instruction cap) in big teamfight ticks | Medium | Channel iteration bounded; heavy callbacks dispatched via `TriggerEvaluate` (fresh op budget per evaluation) |
| Hashtable/array limits (8192 array indices) | Low | UnitDex caps at 8190 with recycling; allocators recycle aggressively; watermarks in debug suite |
| AI pathing cost | Medium | Waypoint graph precomputed; macro tick at 0.25s; micro tick only in combat |
| MPQEditor build corrupting map | Low | `base_map.w3x` is immutable source shell; dist is always regenerated |

---

## Appendix A — Trigger Disposition Index (summary)

- **Rewritten as engine (deleted as triggers):** all `Trig_*_Loop`, `Trig_Unit_Indexer`, `Trig_GUI_SpellEvent`, `Trig_Knockback_*`, `Trig_Collide`, `Trig_JUMP_*`, `Trig_On_Damage*`, `Trig_Take_Damage`, `Trig_Get_DOT`/`Trig_Deal_DOT`, `Trig_Is_Unit_Moving`, `Trig_On_Move/Stop`, `Trig_Combat*`, `Trig_Clear_Group`.
- **Migrated to SpellCore definitions:** every hero spell trigger listed in §13 B1–B6.
- **Migrated to item definitions:** §13 B7 set.
- **Replaced by WarMind:** `Trig_Player_2..10`, `P*_Att`, `P*_Skill*`, `Wander`, `Behavior1..3`, `KS`, `Retreat`, `Cast_KB`, `KB`.
- **Kept (leak-scrubbed, EventBus-adopted):** game modes, duel system, multiboard, respawn/revive, kill streaks, bomb mode, camera, initialization, preload.
- **Deleted outright:** debug leftovers (`Trig_lalala`, `Trig_lol*`, `Trig_lal*`, `Trig_debug*`) after debug suite lands.

## Appendix B — Event Reference (EventBus ids)

`EV_UNIT_INDEXED, EV_UNIT_DEINDEXED, EV_DAMAGE_PRE, EV_DAMAGE_MIT, EV_DAMAGE_POST, EV_BUFF_APPLIED, EV_BUFF_REMOVED, EV_BUFF_EXPIRED, EV_MISSILE_LAUNCH, EV_MISSILE_HIT, EV_MISSILE_EXPIRE, EV_SPELL_CAST, EV_SPELL_EFFECT, EV_SPELL_CHANNEL, EV_SPELL_FINISH, EV_SPELL_END, EV_HERO_KILLED, EV_HERO_REVIVED, EV_ITEM_BOUGHT, EV_COMBAT_ENTER, EV_COMBAT_EXIT, EV_DUEL_START, EV_DUEL_END`

---

*This plan is the contract. Every future edit to `war3map.j` cites the layer it belongs to, follows the optimization skill's six rules, passes the build gates, and moves one row of §13 from "GUI" to "engine."*
