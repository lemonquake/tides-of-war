# AGENT HANDOFF — Tides of War Engine Refactor
### Read this first, then read [TIDES_OF_WAR_MASTER_PLAN.md](TIDES_OF_WAR_MASTER_PLAN.md) — the plan is the contract; this file is where we are inside it.

> Status date: 2026-07-19. Latest verified wave is
> `dist/Tides_of_War_Wave3_Pending.w3x`. Warcraft III currently has
> `dist/Tides_of_War_Compiled.w3x` open, so the normal build correctly aborts
> instead of overwriting the live archive. After Warcraft exits, rerun
> `build.bat nopause` to promote the same source to the canonical filename.
> Git history is batch-committed; `git log --oneline` tells the story.

### Hero-overhaul campaign (active)

- `HERO_OVERHAUL_BIBLE.md` now audits and redesigns all 27 selectable heroes,
  grouped into four implementation waves.
- Tiles of War (`H00O`) is the first full live overhaul:
  - A07I **Citadel of War**: added to the authoritative map object data at build
    time; 800-radius, 16-pylon lightning arena with directional inside/outside
    crossing rules, escape damage, and forced boundary correction.
  - A039 **Siegebreaker Pulse**: 6% enemy max-life pure damage plus Strength,
    radial displacement, quake ring, and the inherited suppression debuff.
  - A038 **Reactive Plating**: 75% post-damage restoration, 2% attacker max-life
    reflection, recursion guard, and close-attacker repulsion.
  - A037 **Worldbreaker Protocol**: E001 burrow form emits 0.75-second max-life
    seismic pulses, pulls enemies, self-repairs, and erupts on emerging.
- `scripts/patch_tiles_object_data.py` patches `war3map.w3a` and `war3map.w3u`
  from the immutable base map during every build, including names, tooltips,
  Q/W/E/R hotkeys, A07I creation, and adding A07I to H00O.
- The formerly lightweight-only build now runs the installed `pjass` against
  `common.j` and `Blizzard.j`. A compile-repair pass fixed 36 pre-existing
  errors (malformed item creation calls, missing `call` statements, a force
  condition parenthesis, and a nonexistent group-count helper). Current source
  passes both leak validation and pjass.
- The offensive legacy item-trigger identifier was renamed to
  `Trig_Ninjaruels_Staff`.
- EarthShaker (`EEES`) is the second full live overhaul:
  - A05Q **Faultline** now raises 15 pooled h00C rock segments across 1230 range.
    Each segment is a five-second physical blocker and Resonance Node; the line
    damages/stuns each caught enemy once without locations or dummy spam.
  - AEET **Totemic Vault** performs a terrain-safe 280-distance vault, plants a
    node, preserves the native empowered attack, and triggers Aftershock.
  - A0as **Aftershock Matrix** emits a 325-radius Strength-scaling burst on each
    EarthShaker spell through pooled stun casters.
  - A100 **World Echo** ripples across 1700 range for 4% max-life pure damage,
    adds damage for each nearby owned node, stuns at node intersections, and
    consumes the full owned node field.
  - Build-time ability/unit presentation patches include the new Q/W/E/R names,
    tooltips, hotkeys, and resonance-controller hero theme.
- Ancient Wanderer (`H00A`) is the third full live overhaul:
  - A019 **Meteor Seed** throws a visible parabolic boulder, deals Strength plus
    percentage maximum-life pure damage, and embeds a persistent 30-second rock.
  - A016 **Continental Roll** launches a 1450-range roller and kicks up to six
    nearby seeds into extra boulders. They damage and push each enemy once,
    ricochet from blocked terrain and other seeds, then re-embed.
  - A01B **Lithic Heart** counts damage events per hero. Every fifth hit restores
    half the triggering damage and emits a recursion-safe counterquake.
  - A01A **Tectonic Assembly** raises every seed into a monolith, connects each
    to its nearest neighbor with fault-line segments, applies max-life pure
    damage and stun once per enemy, and detonates the network. It creates an
    eight-monolith fallback ring when cast without setup.
  - The old single-instance Drag and Bounce timers are no longer registered.
- God of Hammers (`H01J`) is the fourth full live overhaul:
  - A05R **Judgment Hammer** embeds persistent Storm Hammer anchors in a unit or
    terrain; unit-bound hammers follow their victim.
  - A05V **Overforge** heats every owned hammer for six seconds and pulses
    percentage maximum-life pure damage every 0.75 seconds.
  - A05S **Master of the Anvil** relays damage through the nearest embedded
    hammer within 1200, adding Strength damage and hot-hammer max-life damage.
  - A05U **Heavenfall Foundry** consumes the network and fuses it into a scaled
    superhammer falling from 1350 height, with growing radius, capped max-life
    pure damage, terrain deformation, layered effects, and stun.
  - The legacy Mastery/Overload GDD registrations are retired to prevent double
    damage. New names, Q/W/E/R hotkeys, tooltips, and hero themes are packed.
- Move Pointer (`H00X`) is the fifth full live overhaul:
  - A03H **Dimensional Anchors** keeps the two newest 25-second spatial nodes.
  - A03U **Fold** creates an eight-second two-way portal between those nodes.
    Living units preserve facing, while every active MissileCore projectile
    crosses the portal with its velocity unchanged.
  - A03Y **Unstable Coordinates** tracks movement inside a 550-radius corruption
    zone. At 460 accumulated distance, an enemy swaps to its stored afterimage
    and takes Agility plus maximum-life pure damage.
  - A03W **Move Point** captures a radius around the caster, stores every unit's
    relative offset, pauses/pathing-disables the group, carries the entire disc
    along a quadratic spline, then restores all units safely at the destination.
  - The old single-instance Warp loop and direct duplicate Move Point event are
    retired.
- Turtler (`H004`/`H00N`) is the sixth full live overhaul:
  - A033 **Shellguard Muster** creates seven pooled h00M shells in a deterministic
    moving wedge; the native scattered Locust summons are intercepted.
  - A032 **Carapace Relay** draws a visible ordered strike through every wedge
    slot, gaining damage per shell before converging on the target.
  - A034 **Testudo Doctrine** restores 8% of incoming damage per nearby shell,
    capped at 60%, and reflects attacker maximum-life damage with recursion
    protection.
  - A035 **World Turtle** hides/combines the formation beneath H00N, carries
    nearby allies by the fortress's exact movement delta, and emits repeated
    Strength/max-life crush pulses with displacement.
  - Both hero forms receive the new names, tooltips, hotkeys, and phalanx theme.

---

## 1. The workflow you MUST follow (non-negotiable)

1. Load the project skill `.agents/skills/warcraft3-jass-optimization/SKILL.md` — its six rules are law (native XY coords, null all locals, group/force hygiene, div-by-zero guards).
2. After **every** edit to `src/war3map.j`:
   `python .agents/skills/warcraft3-jass-optimization/scripts/validate_jass_syntax.py src/war3map.j`
   It checks block balance, declared-before-use, duplicate functions, and **fails on any leak regression** vs `scripts/leak_baseline.txt` (current baseline: all categories 0). It caught a real un-nulled local of mine — trust it.
3. Build: copy `base_map.w3x` → `dist/Tides_of_War_Compiled.w3x`, then `MPQEditor.exe add "dist\Tides_of_War_Compiled.w3x" "src\war3map.j" "war3map.j"` (or run `build.bat nopause`, which gates on the validator).
4. Commit per batch with a message naming what migrated and the leak delta. Author identity used so far: `-c user.name="Lemon" -c user.email="lemonquake@gmail.com"`, co-author trailer for Claude.
5. **Update the leak baseline** (`scripts/leak_baseline.txt`) only downward, when you've genuinely removed leaks.

**Hard constraint:** pure JASS 1.24+ only — the build injects `war3map.j` directly, there is no JassHelper/vJASS step. Object data (abilities/units/buffs) lives inside `base_map.w3x`; you can only use **existing rawcodes** unless the user edits objects in World Editor.

---

## 2. What is DONE (do not redo)

### The TIDES ENGINE (pure JASS), located in `src/war3map.j` immediately after the single `globals` block (search banner `TIDES ENGINE`). Engine globals are inside the globals block (search `TIDES ENGINE - core globals`).

| Module | API | Notes |
|---|---|---|
| Dummy pool (DummyCore v2) | `Dummy_Get(p, typeId, x, y, faceDeg)` / `Dummy_Recycle(u)` / `Dummy_AttachFx(u, model)` / `Dummy_ClearFx(u)` | Facing-bucketed per unit-type in `Eng_HT` (parent=typeId, child `9000000+b`=count of 30-degree bucket b, child `(b+1)*100000+n`=unit) — checkout probes the nearest non-empty bucket so reused dummies already face the right way (SetUnitFacing needs ~0.7s for 180 degrees). Every created dummy is crow-form enabled ('Amrf' add/remove) for SetUnitFlyHeight. Effects attached via `Dummy_AttachFx` are auto-destroyed on recycle; recycle also resets fly height and scale. Engine_Init preloads one 'h00R' chain link per bucket + four 'h005' casters + one 'h00Q' head. Never CreateUnit a dummy directly. |
| Timed recycler | `Dummy_RecycleTimed(u, delay, removeAbilOr0)` / `Dummy_RemoveTimed(u, delay)` | Recycles ordinary dummies and strips temp abilities; the remove variant permanently removes self-decaying visuals that are unsafe to pool. |
| Dummy casting | `Dummy_CastTarget(p, abil, orderId, target)` / `Dummy_CastTargetLevel(..., lvl, ...)` / `Stun_Bolt(p, target)` | Order ids precomputed: `Eng_OrdThunderbolt/Acidbomb/Bloodlust/MagicLeash/ChainLightning`. Stun = 'h005'+'A00V'. |
| Damage | `Damage_Phys / Damage_Magic / Damage_Pure (s, t, amt)` | Pure = CHAOS/FIRE (matches old map convention). |
| SFX | `SFX_Point(model, x, y)` / `SFX_Unit(model, u, attach)` | One-shot, zero-leak. |
| Trees | `Eng_KillTreesAt(x, y, radius)` | Kills 'ZTtw'/'ZTtc' only, circle-exact, no locations. |
| Target filter | `Eng_ValidTarget(u, castOwner)` + `Eng_IsDummyType(t)` | The dummy list now includes Ancient Wanderer rollers 'h008' and 'h00B'. Extend it whenever a new visual unit joins the engine. |
| **MissileCore** | `Missile_LaunchXY(owner,x,y,tx,ty,speed,maxDist,radius,dummyType,model,onHitTrig,onEndTrig) -> i`, `Missile_SetHoming(i,target)`, `Missile_SetOnTick(i,trig)` | Callbacks are triggers holding `Condition(function F)`; dispatch via `TriggerEvaluate`. Context globals: `EV_MISSILE`, `EV_UNIT`. onHit returning `true` kills the missile; `false` = pierce. Per-instance scratch: `Msl_Data`, `Msl_DataR`, `Msl_DataX/Y`; `Msl_RecycleDelay` keeps a finished missile visible before pooling. **World-bounds clamped** — `SetUnitX/Y` outside world bounds hard-crashes WC3; bounds are `Eng_MinX/MaxX/MinY/MaxY` (playable area ±64). |
| **HookCore** | `Hook_Launch(caster, tx, ty)` | Pudge Hook v2 per user spec: never pauses caster, chain re-laid each tick caster→head (moving launch/retract), 3000 range, multi-instance, links pooled in `Eng_HT` parent `1000000+i`. **Now visible:** the build patches h00Q's model to MeatwagonMissile and h00R's to WardenMissile (h00R previously pointed at the nonexistent import `war3mapImported\ChainElement.mdl` — the whole chain rendered invisible). The head also faces its travel direction on retract. |
| **JumpCore** | `Jump_Launch(u, tx, ty, height, speed, trees, anim, animSpeed, trailModel, onLandTrig) -> i` | Pure-JASS port of Paladon's Jump n' Dash: sine arc on the master tick, crow-form enable, pathing off during flight, animation+time-scale restored on landing or death, optional tree kill along the path, throttled trail SFX, onLand via TriggerEvaluate with `EV_UNIT`/`EV_JUMP`. Callback triggers live in Engine_Init (`Lea_OnLand`, `Esv_OnLand`). |
| Shard channel | `FreezingBlast_Launch(caster)` | 0.2s cadence on master tick. |
| Dash channel | `CuttingGlide_Launch(caster, tx, ty)` | MotionCore's first resident; restores invuln/tint/pathing even on death. |
| Glacial Freeze | `GlacialFreeze_Launch(caster)` | Native 750-range enumeration; one pooled `hsor` + 3-second A030 channel per valid enemy. The self-decaying `h00L` visual is permanently removed after four seconds. |
| Arrow Shower | `ArrowShower_Launch(caster, tx, ty)` | 55 staggered vertical MissileCore instances; pooled rise/fall arrows, isolated 100-radius impacts, and one-second ground linger. |
| Thunder Ball | `ThunderBall_Launch(caster, target)` | Invisible speed-2000 homing proxy synchronized with A04M's native ZapMissile; 30% current-life damage occurs on impact, with last-known-point cleanup. |
| Chain Shock | `ChainShock_Launch(caster, tx, ty)` | MissileCore steering preserves the radial flight, blocked-terrain deflection, 1600 range, and 0.90-second A04G pulse cadence without the legacy CS/BL globals. |
| Water Clone guard | GDD handler + `Wcl_HT` | Each A06P/B01Q clone independently absorbs its first damage event at full life and dies on its second regardless of source or amount; death/expiry flushes its counter. |
| Lightning Grip | `LightningGrip_Launch(caster, tx, ty)` / `LightningGrip_StopCaster(caster)` | Per-cast gravity well: pooled h01A beacon, A06N slow aura, terrain-safe 166.67/sec pull in 500, explicit 100 pure DPS in 375, and re-entry-safe channel-end cleanup. |
| Melting Strike | `MeltingStrike_Launch(caster, target)` | Five 0.10-second, 2×Strength melee/normal strikes: selected target first, then random living ground enemies within 600; isolated groups and complete camera/tint/time-scale cleanup. |
| Tremor channel | `Tremor_Launch(caster, tx, ty)` | Per-cast crater group; `Trm_Tick` expires all 17 pooled craters together and destroys the group. |
| Heartbeat | `Eng_MasterTick` (0.025s) owns engine channels plus Tiles arenas/forms, EarthShaker nodes, Ancient Wanderer boulders, and God of Hammers anchors/superhammers. | `Engine_Init()` is called from `main` after `InitGlobals`. Add new channels to both places. |

### Spells migrated (cast triggers are now one-line shims; old loops are empty stubs or deleted)
Hook ('A03B'), Torpedo ('A02K'), Piercing Shot ('A03F'), Soul Strike ('A032'), EA growing arrow ('A02P'), Freezing Blast ('A043', levels on 'A000'), Cutting Glide ('A06O', dmg on 'A002'), Tremor ('A01A'), Glacial Freeze ('A02Z'), Arrow Shower ('A00P'), Thunder Ball ('A04M'), Chain Shock ('A05O', compatibility entry 'A05P'), Lightning Grip ('A04J'), Melting Strike ('A03I'), plus leak-free rewrites of Divine Light, Starfall, and Inferno.

### Spell dispatch (how casts reach the shims — keep using it)
`Trig_Init_Trigger_Actions` (~line 17200s) maps `udg_SpellEventAbility[n]` → `udg_SpellEventTrigger[n]` (gg_trg_*). Event data (GetTriggerUnit/GetSpellTargetX/Y) survives the TriggerExecute dispatch. To migrate a spell: rewrite its `Trig_X_Actions` body as `call X_Launch(GetTriggerUnit(), GetSpellTargetX(), GetSpellTargetY())`, put the implementation in the engine section, stub its loop trigger's `InitTrig` to empty.

### Known map facts you'll need
- Damage events = Weep's GDD: `udg_GDD_Event` variable event, `udg_GDD_Damage/DamagedUnit/DamageSource` (~line 20800).
- 'A00A' = spell-immunity marker checked by Hook/EA/Soul Strike.
- Hook stats: `udg_AHA_COUNTER[pid]` per cast, `udg_AHA[1..10]` per landed hook (multiboard reads these).
- The `\ Trigger:` lines you may see in Read output are a display artifact — the file really has `// Trigger:`.
- Shared-global hazards found so far: `udg_MUI_1` was shared by Melting Strike AND Cutting Glide (CG side fixed); `udg_TempLoc/udg_Points/udg_Real` are shared scratch across many GUI spells — never assume a `udg_` var belongs to one spell; grep before deleting.
- The legacy item trigger with an offensive name was renamed to `Trig_Ninjaruels_Staff` during the compile-repair pass.

---

## 3. What to do NEXT (in order)

### 3a. Location-leak baseline burn-down — COMPLETE
The validator baseline is zero in every category. Re-run the analyzer for a named hit-list if a regression appears:
```
python .agents/skills/warcraft3-jass-optimization/scripts/analyze_jass_leaks.py src/war3map.j
```

Completed in leak-scrub batch 6: Echo Slam, Smite, Impale, and all three Hell Blast rawcodes now use native XY enumeration and pooled dummies; Hell Blast shares one implementation. Location warnings: 81 → 71.

Completed in leak-scrub batch 7: Take Aim, Fury, Tidal Strike, Vileplume, Butterfree, Blaziken, Overload, Mortar Fire, and AoT Cast now use native XY APIs; eligible caster units are pooled and the three unique summons share one implementation. Location warnings: 71 → 62.

Completed in leak-scrub batch 8: Poison Fumes, Burning Will, Leash, Valor, and Improved Resistance now use native XY enumeration; Burning Will's caster is pooled and obsolete GUI filter/callback trees were removed. Location warnings: 62 → 56.

Completed in leak-scrub batch 9: the TEAM1, TEAM2, and free-for-all revive paths now roll native XY respawn coordinates, call `ReviveHero` directly, and pan cameras without temporary locations. Location warnings: 56 → 53.

Completed in leak-scrub batch 10: Behavior1/3 and the P2/P4/P6/P7/P8 area-count decisions now use native coordinates. One shared `Eng_CountUnitsAt` replaces five leaking GUI count expressions; Behavior3 uses pooled stun dummies. Location warnings: 53 → 46.

Completed in leak-scrub batch 11: initialization camera centering, mine detonation, base redirects, BM/BOMB debug spawners, and camera tracking now use native coordinates. Mine damage uses an isolated destroyed group because damage events may re-enter shared enumeration. Location warnings: 46 → 37.

Completed in leak-scrub batch 12: game intro/mode transmissions, initial camera setup, duel return, repick placement, and revival item recovery now use native coordinates. `Game_TransmissionInitial` owns and cleans the one location required by Blizzard's transmission API plus its temporary audience force. Location warnings: 37 → 27.

Completed in leak-scrub batch 13: bomb planting, pickup/drop tracking, diffuse respawn pings, and hero-pick camera return now use native coordinates and cleaned forces. The analyzer now matches exact allocation APIs, so `GetRectCenterX/Y` and start-location configuration are no longer false positives. Location warnings: 27 → 17.

Completed in leak-scrub batch 14: Preload and Observatory now use native coordinates; SC and Magic Missile use native enumeration and pooled casters; Nether Aura recycles its formerly immortal dummy; and the NS callback uses a pooled native-XY caster. Magic Missile retains an isolated destroyed group because damage events may re-enter shared enumeration. Location warnings: 17 → 9.

Completed in leak-scrub batch 15: Tremor and Inferno now use native isolated damage loops; Leap and Arrow Shower use pooled impact casters; Unstable Motion, Lightning Ward, and CS CAST use native XY APIs; and Explode caches the bomb position before removal, uses native deformation/item placement, and pings the newly spawned bomb instead of a stale global location. The analyzer now prints named findings and only declares clean when locations are also zero. Location warnings: 9 → 0.

Keep `leak_baseline.txt` at zero; every new finding is now a regression.

### 3b. Migrate remaining loop spells to engine channels (pattern is established — copy an existing one)
- **Toss Rock + Bounce**, **Repelling Ward**, **Lightning Ward** (pool 'h014').
- **Knockback_2D / Warp / Hell Step (HCS)** systems → fold into MotionCore next to `Cgl_*` (plan §10). Knockback_2D has five call sites (11258, 21128, 24534, 24545, 25871) with per-caller config globals — migrate as its own batch. JUMP and Leap are DONE (batch 23).

Completed in systems-wave batch 23 (the three attached reference systems):
- **DummyCore v2**: facing-bucketed pooling (12 x 30-degree buckets per type), crow-form enable on creation, `Dummy_AttachFx`/`Dummy_ClearFx` effect registry keyed by handle id, fly-height/scale reset on recycle, and Engine_Init preload (12 chain links across all buckets + 4 casters + 1 hook head). The map's Bribe unit indexer (udg_UDex) already covers the unit-indexer reference.
- **JumpCore**: Paladon Jump n' Dash ported as an engine channel (`Jmp_*`, `Jump_Launch`). Migrated: **Leap** ('Aadm' and 'A058' → 830-range facing leap, 332 height, 1500 speed, 3x walk anim; the A058 empowered landing bloodlusts allies in 500 via `Leap_OnLand`), the two **rect jump pads** (gg_rct_Jump1/Jump2, 1000 range east/west), and **Totemic Vault** (AEET) which now performs a real 280-distance sine-arc vault and plants its Resonance Node on touchdown (`Esh_VaultLand`). The legacy Paladon JD system (Set_Leap/Leap_Ef), the udg_JUMP_* INSTALL/LOOP system, its INTIALIZATION timer registration, and the dead unregistered Trig_ET are deleted/stubbed.
- **Meat Hook visibility**: `scripts/patch_tiles_object_data.py` gained `DUMMY_UNIT_VISUALS`, which repoints h00Q (head) to MeatwagonMissile and h00R (chain link) to WardenMissile at build time. Root cause: h00R referenced the import `war3mapImported\ChainElement.mdl`, which does not exist in base_map.w3x, so every chain link rendered invisible; the head was the near-invisible BloodElfSpellThief wisp. The retracting head now also faces its travel direction.

Completed in engine-channel batch 16: Tremor now owns one crater group per cast on `Trm_Tick`. The old `Trig_TLoop` bookkeeping timer, `Trig_Tremor_D` global death listener, saved location/player/level state, and Tremor-only initialization globals are deleted. All 18 visual units are pooled; each crater applies the original overlapping delayed burst before recycling. Inferno was already reduced to a native one-shot implementation in batch 15.

Completed in engine-channel batch 17: Glacial Freeze now uses native coordinates and an isolated per-cast enumeration. Each valid enemy receives the original three-second A030 Magic Leash from a pooled `hsor`, then the caster is stripped and recycled; the four-second self-decaying `h00L` visual uses the timed permanent-removal path. The legacy location/global state and GUI filter/callback tree are deleted.

Completed in engine-channel batch 18: Arrow Shower is 55 vertical MissileCore instances with the original one-second wind-up, 0.03-second stagger, 150-radius spread, 100-radius/35-damage impacts, and one-second ground linger. `h00U`/`h00V` are pooled; damage enumeration is isolated for GDD re-entry. The old per-cast location, two groups, recycled-index registry, 0.03-second trigger, callback tree, and redundant direct spell-event registration are deleted.

Completed in engine-channel batch 19: Thunder Ball keeps A04M's native `ZapMissile.mdx` visual and mirrors it with an invisible speed-2000 MissileCore proxy. The original 30% current-life melee/enhanced hit now occurs when the proxy reaches the live target; target death/removal switches to the last known point and expires harmlessly. The cast trigger is a one-line dispatch shim.

Completed in engine-channel batch 20: Chain Shock now launches directly from A05O through MissileCore; A05P remains as a compatibility dispatch only. Its original 400-speed radial steering, +25-degree/333.33-speed blocked-terrain deflection, 1600 range, 0.90-second pulses, and caster teleport to the orb endpoint are preserved. Each pulse uses isolated enumeration and pooled A04G chain-lightning casters for every valid enemy in 600 range. The old h01I projectile, CS/BL globals, 0.03-second trigger, and callback tree are deleted. Water Clone was also overhauled into an amount/source-independent two-hit guard: the first GDD event restores the individual B01Q clone to full life, the second kills it, and a death listener clears stale per-handle state.

Completed in engine-channel batch 21: Lightning Grip now owns one master-tick instance per A04J channel. The object-data audit confirmed a five-second/500-radius spell, h01A beacon, and A06N -55% slow aura; it also confirmed the legacy HDS path never registered its beacon, never saved its caster/timer, and multiplied damage by unrelated A000. The replacement pools h01A, removes its inherited nondeterministic A06M damage aura, pulls enemies at the old 166.67 units/sec with terrain/bounds checks, and applies the live tooltip's 100 pure DPS inside 375. Spell interruption, caster death, expiry, overlapping casts, and damage-event re-entry all cleanly destroy the instance group and recycle the beacon. The two old periodic triggers, HDS globals/groups/locations, callback tree, and stale hashtable payloads are deleted.

Completed in engine-channel batch 22: Melting Strike now owns one master-tick instance per A03I cast. It preserves the original five 0.10-second attacks, first hit on the selected unit, four random living ground targets within 600 of that unit, 2×Strength melee/normal damage, 50-radius victim offsets, camera lock, red tint, Phoenix weapon effect, and attack animation. Per-instance enum/valid groups make overlapping casts and recursive damage safe. Cleanup destroys both groups/effects, restores camera/color/animation, and now also restores the 100% time scale the old loop forgot. The shared `udg_MUI_1` registry, CL arrays, preallocated/leaked groups, location math, filter tree, and standalone 0.10-second trigger are deleted.

### 3c. Then the big layers, per plan milestones (§18)
M3 BuffCore (§7) → finish M4 MotionCore (§10) → M5-M7 SpellCore registration + remaining batches + items (§9, §13) → M8 **WarMind AI** replacing `Trig_Player_2..10`/`P*_Att`/`P*_Skill`/Wander/Behavior1-3/KS/Retreat (§11) → xlsx→JASS codegen (§12) → M9 leak-zero polish + 60-min soak test (§17).

### 3d. Testing reminders
No in-game test has been run yet (only static validation + successful MPQ pack). First priority for a session with the game available: load `dist/Tides_of_War_Compiled.w3x`, cast Hook while moving (spec: no pause, chain follows moving Pudge, 3000 range, multi-cast), Torpedo, Piercing Shot, Soul Strike, EA, Freezing Blast, Cutting Glide, simultaneous Tremors, Glacial Freeze against several targets, overlapping Arrow Showers, Thunder Ball against moving/dying targets, and overlapping Chain Shocks across blocked terrain. For Water Clone, test both H015/H01B forms and multiple damage sources: a massive first hit must leave the clone alive, then even a one-damage second hit must destroy it. For Lightning Grip, verify smooth pull/slow and 100 DPS, blocked-terrain refusal, simultaneous wells from different players, early channel interruption, and caster death during a damage pulse. For Melting Strike, verify exactly five hits, ground-only follow-up selection, empty-target early cleanup, simultaneous casters, caster death, and restoration of camera/tint/animation speed. For batch 23: cast Hook and confirm the meat head and every chain link are now VISIBLE during launch, latch, and retract; cast Leap ('Aadm'/'A058') and confirm the sine arc, triple-speed walk animation, restored pathing/time-scale on landing, and the A058 ally bloodlust on touchdown; walk into the Jump1/Jump2 pads; cast Totemic Vault and confirm the hero arcs 280 units and the node plants at the landing point (blocked terrain = node in place, no vault); verify reused engine projectiles no longer visibly rotate toward their launch angle (facing-bucket pool). Finish with the `-hc`-style handle soak per plan §17 (debug suite not built yet).

---

## 4. File map
- `TIDES_OF_WAR_MASTER_PLAN.md` — **the architecture contract.** §13 = migration order, §16 = coding standards, §17 = QA protocol.
- `src/war3map.j` — everything. Engine = after globals block. 25,448 lines.
- `.agents/skills/warcraft3-jass-optimization/` — skill + `analyze_jass_leaks.py` + `validate_jass_syntax.py` + `leak_baseline.txt`.
- `build.bat` — gated build. `base_map.w3x` — immutable shell (object data source). `dist/` — output.
- `database/*.xlsx` — future data pipeline source (plan §12), not yet wired.
- Persistent memory: `tides-engine-status.md` in the project memory dir mirrors this handoff in brief.
