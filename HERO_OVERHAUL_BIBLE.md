# Tides of War — Hero Overhaul Bible

Status: active implementation design, 2026-07-19  
Roster audited: 27 selectable heroes, 105 visible ability slots  
North star: every hero should create a recognizable combat “scene,” not merely
play four unrelated Warcraft III abilities.

## Global design language

- Every kit owns one unmistakable fantasy, one combat rhythm, one visual color
  language, and one piece of battlefield geometry.
- Percentage damage is deliberate, typed, and readable: current-life damage
  opens a fight, maximum-life damage breaks tanks, and missing-life damage
  executes. Flat damage still matters against low-health targets.
- Hard control always has visible anticipation and a clear boundary. Large
  effects get counterplay through wind-up, facing, breakable anchors, leaving a
  zone, interrupting a channel, or spending mobility.
- Custom motion is a first-class mechanic: wall collisions, rebounds, dragging,
  orbiting, tunneling, afterimages, curved missiles, and linked unit formations
  all run through reusable engine channels.
- Effects are layered in three beats: telegraph, impact, aftermath. A major
  spell should change the silhouette of the battlefield for several seconds.
- Repeated casts recycle instances, groups, dummies, effects, and lightning.
  No kit is allowed to trade stability for spectacle.

## Shared effect and mechanic primitives

1. `ArenaCore`: circular/arc barriers, directional crossing rules, inside/outside
   membership, boundary punishment, destructible nodes, and lightning walls.
2. `ZoneCore`: persistent circles, lines, cones, moving storms, terrain decals,
   re-entry effects, and owner/team filters.
3. `MotionCore`: dash, charge, knockback, pull, orbit, tether, leap, wall impact,
   ricochet, terrain-safe placement, and interruption.
4. `SequenceCore`: spell timelines with telegraph, volleys, delayed impacts,
   animation changes, and cleanup callbacks.
5. `StatusCore`: stun, root, silence, slow, disarm, armor fracture, shields,
   stacks, dispels, and consistent status visuals.
6. `ThreatCore`: current/max/missing-life damage helpers, per-target cooldowns,
   boss/creep caps where desired, damage flags, and combat text.
7. `SFXCore`: pooled anchors, persistent effect ownership, beams, rings,
   afterimages, local camera shake, impact sound layers, and effect budgets.

## Roster redesign

### 1. Lone Hydra (`H006`) — The Three-Headed Abyss

Combat rhythm: mark three targets, weave water and tentacles between them, then
collapse the triangle.

- `A05L` **Brine Lance**: a pressurized spear pierces enemies, applies a Head
  Mark, and bursts for current-life damage on the first hero struck.
- `A00N` **Drowned Garden**: tentacles erupt along a drawn curve. Marked enemies
  are linked by additional tentacles and briefly rooted.
- `A031` **Triune Benediction**: each head chooses a mode—guard, hunt, or mend.
  Recasting rotates the formation and changes the next spell’s rider effect.
- `A02Z` **Leviathan Convergence**: the three marks become whirlpools that drag
  enemies toward their centroid before a colossal spectral maw breaches.
- Signature effects: deep-blue water ribbons, three rotating head sigils,
  curved tentacle chains, and a screen-filling breach shadow.

### 2. Rifleman (`H00D`) — Ballistics Savant

Combat rhythm: establish firing geometry, ricochet through cover, then cash out
distance with a rail shot.

- `A00O` **Breach Round**: a physical shell punches through the first target,
  leaving a shrapnel cone behind it.
- `A07F` **Suppressive Grid**: fires a staggered lattice of micro-shells; crossing
  lines applies stacking suppression and reveals invisible units.
- `A02E` **Deadeye Calibration**: immobile aiming stance with a visible range
  reticle. Movement cancels it, while patience grants armor penetration.
- `A02B` **Horizon Railgun**: long wind-up beam through the entire battlefield;
  damage scales with travel distance and missing life.
- Signature effects: tracer lines, muzzle shock cones, ground pockmarks,
  shell-casing bursts, and a white-hot beam afterimage.

### 3. Vengeful Spirit (`H003`) — The Unfinished Death

Combat rhythm: haunt enemies with echoes, weaponize displacement, and punish
anyone who attacks the wrong body.

- `A008` **Grudge Bolt**: a homing spirit splits into echoes when the target uses
  movement; each echo attacks from the target’s previous position.
- `A02D` **Dreadwake**: a widening spectral wave steals outgoing damage and
  paints an escape trail visible through fog.
- `A00C` **Unpaid Blood**: allies store a portion of damage received as Vengeance.
  The Spirit’s next hit detonates stored Vengeance around the attacker.
- `A00B` **Nether Exchange**: swaps two units, leaves attackable afterimages at
  both endpoints, and permits one timed recast to return.
- Signature effects: violet silhouettes, backward-traveling particles, tethered
  soul wisps, and shattered mirror portals.

### 4. Ancient Wanderer (`H00A`) — The Walking Mountain

Combat rhythm: seed boulders, roll them through enemies, then awaken the entire
stone field.

- `A019` **Meteor Seed**: throws a boulder that embeds in terrain and damages by
  maximum life on direct hero impact.
- `A016` **Continental Roll**: kicks every nearby seeded boulder forward; stones
  ricochet from arena walls and each other.
- `A01B` **Lithic Heart**: damage taken builds Strata. At full Strata, the next
  displacement is ignored and releases a stone counterwave.
- `A01A` **Tectonic Assembly**: every boulder rises into a monolith, draws fault
  lines to adjacent monoliths, and detonates the enclosed polygons.
- Signature effects: physical stone anchors, fracture decals, dust wakes,
  bouncing impact rings, and rising monolith silhouettes.

### 5. Turtler (`H004`) — Commander of the Shell Phalanx

Combat rhythm: build a moving formation, redirect attacks through it, and turn
defense into ricochet offense.

- `A033` **Shellguard Muster**: summons turtles into a controllable wedge rather
  than scattered ordinary summons.
- `A032` **Carapace Relay**: attacks bounce between allied shells, gaining force
  before striking the marked enemy.
- `A034` **Testudo Doctrine**: nearby turtles interlock. Projectiles hitting the
  front are reduced and reflected at a visible angle.
- `A035` **World Turtle**: the formation combines beneath the hero, becoming a
  mobile fortress that can carry allies and crush structures.
- Signature effects: connected shell beams, formation arrows, projectile
  reflections, dust tracks, and a giant composite shell.

### 6. Slithereen Guard (`H002`) — Abyssal Pursuer

Combat rhythm: mark prey with a trident, ride undertows through them, and break
armor through repeated close-range collisions.

- `A003` **Undertow Sprint**: leaves a current that allies can ride; passing
  through marked enemies turns the current into a damaging rip.
- `A004` **Abyssal Crush**: expanding water-pressure rings stun at the center and
  drag at the edge.
- `A005` **Trident Harpoon**: three prongs fan out and converge behind the target,
  pinning it if two or more connect.
- `A006` **Expose the Deep**: armor fracture becomes a visible shell that cracks
  in stages; breaking the last stage deals maximum-life physical damage.
- Signature effects: caustic-green currents, trident trails, pressure bubbles,
  armor shards, and fin-shaped dash wakes.

### 7. Demon Witch (`H007`) — Soul Puppeteer

Combat rhythm: suspend one victim, redirect its suffering, and sever the soul at
the moment it tries to flee.

- `A011` **Soul Spire**: impales the target’s spirit above its body; damaging the
  spirit repeats a percentage onto the body.
- `A012` **Marionette Hex**: transforms and tethers a victim to a cursed point.
  Moving too far snaps it back.
- `A013` **Usurer’s Drain**: channels a branching drain that steals mana first,
  then life, then cooldown time.
- `A014` **Finger of Unmaking**: draws a thin execution line, pauses for one
  heartbeat, then deals missing-life pure damage and erupts stored soul damage.
- Signature effects: black strings, suspended soul doubles, hand-shaped shadow
  telegraphs, and an abrupt color-drain execution frame.

### 8. Reefwalker (`H001`) — Sovereign of Moving Tides

Combat rhythm: surf continuously, leave water routes, and steer orbiting weapons
through enemies.

- `A06O` **Reefwalk**: freeform surf dash that paints a temporary water path.
  Allies gain speed on it; enemies slip toward its center.
- `A02K` **Torpedo Bloom**: a steerable torpedo splits after its first impact
  into reef-seeking shards.
- `A071` **Riptide Brand**: attacks alternate cold and pressure marks. Combining
  both freezes water beneath the victim and exposes it to current-life damage.
- `A02U` **Crown of Tides**: tidal orbs orbit at different radii; recast reverses
  them, flinging struck enemies toward the center.
- Signature effects: persistent water ribbons, coral eruptions, orbital wakes,
  foam rings, and refracted blue projectile trails.

### 9. EarthShaker (`EEES`) — Resonance Engine

Combat rhythm: create walls and echoes, then route one final slam through every
piece of affected terrain.

- `A05Q` **Faultline**: fissure becomes a segmented physical wall whose sections
  can be destroyed or detonated.
- `AEET` **Totemic Vault**: charges the totem, leaps a short distance, and makes
  the landing attack echo from nearby fissure sections.
- `A0as` **Aftershock Matrix**: every cast leaves a resonance node. Repeated
  effects in the same area increase frequency instead of merely stunning again.
- `A100` **World Echo**: releases concentric waves from the hero and every node;
  intersecting waves amplify one another and launch stone shards upward.
- Signature effects: visible seismic wavefronts, pulsing cracks, resonance
  pillars, upward rock shards, and bass-heavy staggered impacts.

### 10. Arch Seraphim (`H00H`) — Commander of the Last Host

Combat rhythm: position angels as a formation, redirect harm through sacred
links, and fire through the formation.

- `A02L` **Muster the Host**: summons fewer but meaningful angels in a chosen
  line, wedge, or circle.
- `A02M` **Judgment Ray**: Divine Light becomes a piercing ally-heal/enemy-burn
  beam that refracts through angels.
- `A02N` **Covenant of Wings**: links allies; lethal damage instead shatters one
  angel and grants a brief sanctuary.
- `A06J` **Soul Spear Ascension**: throws a rising spear, carries the first enemy
  soul skyward, then crashes it through the angel formation.
- Signature effects: gold-white formation lines, feather vortices, refracted
  rays, cathedral rings, and descending spear shadows.

### 11. Priestess of the Moon (`H00J`) — Lunar Huntress

Combat rhythm: hunt through darkness, predict movement, and turn arrows into
constellations.

- `A02Q` **Constellation Fall**: stars land in a player-drawn pattern and connect
  into damaging lunar lines.
- `A02P` **Elune’s Arrow**: keeps distance scaling but leaves a moon gate at max
  range; allied arrows passing through gain speed and split.
- `A058` **Moonstep**: a leap with a silver afterimage that repeats the Priestess’
  next attack from the departure point.
- New inherent **Hunt by Moonlight**: moving unseen charges Lunar Sight; the next
  hero hit briefly reveals future movement as a ghost trajectory.
- Signature effects: star-map lines, crescent afterimages, moon gates, silver
  shadows, and soft eclipse lighting.

### 12. Firelord (`N005`) — The Three Temperatures

Combat rhythm: cycle Ember, Furnace, and White Heat; each Hell Blast changes
form, and the ultimate consumes temperature.

- `A015` **Ember Jet**: fast cone, stacking embers, excellent ignition setup.
- `A01C` **Furnace Column**: delayed vertical blast that lifts and melts armor.
- `A01D` **White-Heat Lance**: narrow beam that deals current-life damage and
  leaves glassed ground.
- `A029` **Caldera Heart**: creates a volcano whose behavior reflects the last
  temperature used; consuming all three triggers a map-shaking super-eruption.
- Signature effects: visible temperature color progression, soot accumulation,
  molten glass ground, heat distortion, and rising ash columns.

### 13. Butcher (`H00S`) — The Chain-and-Flesh Juggernaut

Combat rhythm: hook prey, create a toxic fighting pocket, and convert body mass
into brutal sustain.

- `A03B` **Living Chain**: the existing moving-caster, 3000-range custom hook
  remains the kit’s centerpiece; wall scraping creates sparks and brief drag.
- `A03L` **Rot Reactor**: damage aura now leaves meat-fog zones that grow where
  heroes take damage.
- `A03J` **Devour Whole**: Chomp stores a percentage of damage as Meat. Recast
  spits bone shrapnel based on stored Meat.
- New inherent **Mass Is Power**: max life increases hook-head size and Rot
  radius slightly; healing beyond full becomes a decaying flesh shield.
- Signature effects: articulated chain, toxin clouds, bloodless bone shrapnel,
  swelling flesh shield, and heavy camera recoil on catches.

### 14. Tiles of War (`H00O`) — Living Siege Citadel

Implemented first. This hero no longer behaves like a generic defensive aura
carrier; every skill either breaks a tank or creates battlefield geometry.

- `A039` **Siegebreaker Pulse**: 700-radius blast for 50 + 1.25x Strength + 6% of
  each enemy’s maximum life as pure damage, plus outward displacement.
- `A07I` **Citadel of War**: requested 800-radius wall. Sixteen stone pylons and
  lightning spans define a true boundary for seven seconds. Outsiders are
  rejected; caught enemies that cross outward take 75 + 4% max-life pure damage
  and are slammed back inside.
- `A038` **Reactive Plating**: restores 75% of each incoming hit, reflects 2% of
  the attacker’s maximum life as pure damage, and repels nearby attackers.
- `A037` **Worldbreaker Protocol**: burrow pulses every 0.75 seconds for 25 +
  2.5% enemy max life, drags victims inward, and self-repairs. Emerging erupts
  for 150 + 8% max life and throws enemies outward.
- Signature effects: resurrection-stone pylons, live lightning walls, radial
  impales, layered war-stomps, quake decals, and volcano eruption bursts.

### 15. Bow Master (`H00T`) — Kinetic Geometry Archer

Combat rhythm: place arrows as geometry, change stance, and detonate every
crossing line.

- `A03F` **Bore Shot**: piercing projectile leaves suspended arrowheads in every
  target passed through.
- `A00M` **Galeforce Cut**: wind blade bends toward suspended arrowheads and
  ricochets between them.
- `A067` **Kinetic Stance**: toggle between mobile curve shots and rooted
  high-velocity shots; stance changes alter all projectile steering.
- `A00P` **Skyloom**: Arrow Shower becomes a woven canopy. Recast drops every
  suspended arrow at once, with intersections dealing bonus max-life damage.
- Signature effects: visible ballistic arcs, air ribbons, suspended arrows,
  crossing-line flashes, and a dense vertical arrow curtain.

### 16. Hell Walker (`H00W`) — Momentum Demon

Combat rhythm: never stop moving; every dash heats the hero, and every melee
impact spends heat in a different way.

- `A00R` **Infernal Velocity**: Fury builds from distance traveled, not idle
  attack speed.
- `A04N` **Hellstep**: target-point dash leaves delayed demonic footprints that
  erupt in order.
- `A00S` **Burning Will**: incoming control is stored as Rage; recast burns Rage
  to shorten future disables and ignite attackers.
- `A03I` **Melting Sequence**: the existing five-hit cinematic slash now targets
  heated enemies first and leaves molten cuts that explode together.
- Signature effects: ember afterimages, delayed footprints, red time-slice
  frames, molten cut lines, and heat shimmer around the hero.

### 17. Move Pointer (`H00X`) — Spatial Editor

Combat rhythm: place objects and control points, then rewrite where movement
ends. This should be the map’s most mechanically alien hero.

- `A03H` **Dimensional Anchors**: places draggable spatial nodes rather than
  decorative objects.
- `A03U` **Fold**: creates paired curved gates; missiles, dashes, and units can
  enter one gate and leave the other with preserved momentum.
- `A03Y` **Unstable Coordinates**: enemies accumulate coordinate error while
  moving; at full error their current position and afterimage swap.
- `A03W` **Move Point**: grabs an area of space as a translucent disc, drags it
  along a spline, and drops every unit and missile at the destination.
- Signature effects: wireframe circles, cubic interpolation trails, portal
  refraction, coordinate glyphs, and displaced terrain afterimages.

### 18. Elementalist (`H013`) — Four-State Spell Composer

Combat rhythm: select two elements; the ordered pair changes the next cast.
Water→Lightning is not the same spell as Lightning→Water.

- `A079` **Element Wheel**: cycles Fire, Water, Wind, and Earth and displays the
  queued pair as orbiting runes.
- `A046` **Conduit Ward**: ward form depends on the first element and modifies
  projectiles that pass through it.
- `A073` **Elemental Impulse**: burst form depends on the second element and the
  order of the pair.
- `A07A` **Grand Synthesis**: consumes both elements for one of twelve hybrid
  ultimates—steam veil, glass storm, mud prison, plasma chain, and more.
- Signature effects: two orbiting color runes, ward prisms, hybrid particles,
  element-colored terrain, and combinational cast banners.

### 19. Sea King (`H015`) — Royal Tide Duelist

Combat rhythm: create royal clones, trade positions with them, and make every
clone repeat a weaker version of the King’s attack.

- `A049` **Royal Breaker**: Tidal Strike marks a line; clones strike the same
  line from their own facing one beat later.
- `A06P` **Court of Reflections**: water clones retain the custom two-hit rule,
  but spawn in formation and can be position-swapped by recast.
- `A02R` **Drowning Decree**: a curse counts movement and spell casts; exceeding
  the limit causes a clone to emerge and execute a percentage strike.
- `A03C` **High Tide Tyrant**: Enrage raises a moving water level. Enemies below
  the crest are slowed and take increasing current-life damage.
- Signature effects: royal-blue clone ribbons, delayed mirrored attacks, water
  level rings, decree seals, and cresting wave silhouettes.

### 20. Bear Lord (`H017`) — Unstoppable Winter Beast

Combat rhythm: build momentum, collide with heroes, and become harder to stop
the longer the rampage survives.

- `A04B` **Avalanche Clap**: clap sends a snow shelf forward; enemies struck near
  terrain are buried rather than merely slowed.
- `A04C` **Dominance Roar**: fear direction is away from the Bear; feared units
  leave scent trails the Bear can charge along.
- `A04D` **Maul Through**: splash becomes a cleaving body collision that carries
  the primary target a short distance.
- `A04E` **Gerun Unchained**: rampage gains speed per collision, breaks ordinary
  control once, and ends in an avalanche proportional to distance traveled.
- Signature effects: snow shelves, scent paths, paw shockwaves, rolling debris,
  and an enlarging frost aura during rampage.

### 21. Naga Thunderlord (`H019`) — Living Storm Circuit

Combat rhythm: place charge in units and terrain, then choose whether lightning
chains, orbits, or collapses inward.

- `A05O` **Chain Vector**: keeps the custom radial MissileCore movement but
  deposits charge at every deflection point.
- `A04M` **Ball Lightning**: existing impact-timed current-life damage becomes a
  movable charge node after impact.
- `A04H` **Thunder Verdict**: calls lightning through every charged unit in
  nearest-neighbor order, with visible path prediction.
- `A04J` **Storm Singularity**: the existing gravity well pulls charged nodes
  inward; collapsing three or more creates a branching superbolt.
- Signature effects: persistent ground charge nodes, predicted lightning paths,
  orbit arcs, gravity-warped bolts, and a blinding convergence flash.

### 22. Goddess of the Wind (`H01C`) — Airborne Blade Dancer

Combat rhythm: remain in motion, carve air lanes, and revisit them at higher
speed.

- `A04S` **Feather Satellites**: feathers orbit and intercept one projectile
  each; spent feathers remain as map anchors.
- `A04V` **Tailwind Covenant**: moving wind lane accelerates allies and curves
  hostile missiles away.
- `A04W` **Vacuum Edge**: attacks cut pressure scars; crossing two scars creates
  a vacuum slash.
- `A002` **Lightning Glide**: existing custom dash can chain through spent
  feathers, gaining damage and changing direction at each anchor.
- Signature effects: white feather satellites, transparent wind tunnels,
  pressure-scar lines, sonic rings, and chained lightning afterimages.

### 23. Pokemans Master (`H01E`) — Creature Combo Trainer

Combat rhythm: creatures remain individually simple, but positioning two
creatures together creates combination attacks.

- `A04R` **Vileplume — Toxic Garden**: plants reactive pollen zones that other
  creature attacks can ignite, electrify, or scatter.
- `A053` **Butterfree — Dream Current**: wingbeats carry pollen, allies, and
  small projectiles along a controlled air stream.
- `A055` **Blaziken — Comet Kick**: target-point diving kick; ignited pollen
  becomes a chain of fire blooms.
- `A04Y` **Groudon — Continental Arrival**: enormous telegraphed footprint,
  terrain uplift, and a command window for one primal follow-up.
- Signature effects: creature command rings, combo-colored pollen, flight
  currents, footprint telegraphs, and terrain uplift.

### 24. God of Hammers (`H01J`) — Divine Forge Artillery

Combat rhythm: throw hammers, overheat them, recall them through enemies, and
assemble the field into one impossible weapon.

- `A05R` **Judgment Hammer**: thrown hammer embeds in units or terrain and
  continues to radiate threat.
- `A05V` **Overforge**: overheats every embedded hammer; heat changes recall
  damage into maximum-life damage.
- `A05S` **Master of the Anvil**: attacks strike the nearest embedded hammer,
  sending a shockline from hammer to victim.
- `A05U` **Heavenfall Foundry**: all hammers fly skyward, fuse, cast a giant
  shadow, and descend as one terrain-cracking superhammer.
- Signature effects: persistent hammer anchors, orange heat stages, recall
  streaks, anvil shocklines, and a massive descending shadow.

### 25. Kung Fu Panda (`H01K`) — Stance Combo Master

Combat rhythm: alternate soft and hard techniques; repeating the same stance is
safe, alternating creates spectacular finishers.

- `A05W` **Mountain Body**: body slam rebounds from units and terrain; timing a
  second cast at impact converts the rebound into a piledriver.
- `A07L` **Panda Forms**: toggle Flow and Iron stance. Flow redirects force;
  Iron stores it.
- `A07K` **Eight-Cup Sequence**: four-input martial combo whose result depends
  on stance alternation—sweep, launch, spin, counter, or palm burst.
- New inherent **Perfect Rhythm**: correctly alternating skills leaves yin-yang
  echoes; collecting both makes the next finisher cost no mana.
- Signature effects: ink-brush arcs, yin-yang footprints, impact freeze frames,
  circular combo prompts, and exaggerated rebound trails.

### 26. Cowmonger (`H01N`) — Bovine Siege Engineer

Combat rhythm: deploy absurd heavy hardware, create firing lanes, and reward
standing ground under pressure.

- `A065` **Peacemaker Battery**: deploys a cannon with a manually rotatable
  firing cone and visible recoil.
- `A06E/A06A` **Battle Hunger**: marks a target as the battery’s priority; each
  missed shot tightens accuracy and increases shell speed.
- `A06D` **Brutal Force**: converts nearby explosions into temporary armor and
  makes the next melee hit fire a point-blank shell.
- `A06S` **Shockwave Time**: the proton-cannon barrage becomes a sweepable beam
  sequence with eight timed aim adjustments.
- Signature effects: mechanical deployment arms, targeting cones, shell arcs,
  recoil dust, proton sweep lines, and comic bovine warning sirens.

### 27. Elite Soldier (`H01P`) — Adaptive Frontline Captain

Combat rhythm: read enemy damage types, establish a rally line, and turn defense
into coordinated counterfire.

- `A077` **Shield Bash Breach**: directional bash interrupts and paints the
  target for allied follow-up fire.
- `A06X` **Valor Line**: draws a rally line between the Soldier and a point;
  allies crossing it gain courage while enemies crossing it are challenged.
- `A06R` **Adaptive Resistance**: records recent physical, magical, and pure
  damage; the largest category gains resistance while the others empower the
  next attack.
- `A06U` **Destiny Bond**: links the Soldier to an ally or enemy. Ally mode
  shares protection; enemy mode mirrors a percentage of healing and movement.
- Signature effects: military line holograms, shield-angle telegraphs, damage
  type emblems, linked health pulses, and synchronized allied muzzle flashes.

## Implementation waves

### Wave 0 — Living Siege Citadel

Tiles of War full kit, `ArenaCore` prototype, percentage-damage helpers,
boundary visuals, rawcode presentation patching, static validation, and build.

### Wave 1 — Geometry heroes

Move Pointer, EarthShaker, Ancient Wanderer, God of Hammers, Bow Master, and
Turtler. These six justify `ArenaCore`, `ZoneCore`, richer `MotionCore`, and
SequenceCore, then every later hero becomes cheaper and safer.

### Wave 2 — Projectile and mobility heroes

Rifleman, Priestess, Reefwalker, Naga Thunderlord, Goddess of the Wind, Butcher,
and Hell Walker. This wave expands missile steering, gates, afterimages,
projectile interception, and collision effects.

### Wave 3 — Status and formation heroes

Vengeful Spirit, Demon Witch, Arch Seraphim, Sea King, Elite Soldier, Lone Hydra,
and Elementalist. This wave completes StatusCore, formation logic, tethering,
and multi-source combo ownership.

### Wave 4 — Transformation and spectacle heroes

Firelord, Bear Lord, Pokemans Master, Kung Fu Panda, Cowmonger, Slithereen Guard,
and remaining polish. This wave adds the most asset-heavy transformations and
finisher sequences after the reusable systems are battle-tested.

## Quality gate for every completed hero

- All visible names and tooltips match live behavior.
- Four abilities form a combo loop and share a coherent visual language.
- Every spell is multi-instance safe and cleans all owned handles.
- No direct location math, unbounded counters, dummy spam, or orphaned effects.
- Death, interruption, teleport, spell immunity, terrain edges, simultaneous
  casts, and recursive damage are tested.
- The packed map passes the JASS validator and an in-game combat/handle soak.
