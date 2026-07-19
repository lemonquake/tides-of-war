"""Patch live hero-overhaul ability/unit objects during the map build.

The map deliberately keeps base_map.w3x immutable. The build extracts its
ability object file, applies these presentation-only changes, and injects the
result beside the custom JASS implementation. No new rawcodes are introduced.
"""

from __future__ import annotations

import argparse
import struct
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Modification:
    field_id: bytes
    value_type: int
    level: int
    data_pointer: int
    value: bytes
    end_token: bytes


@dataclass
class ObjectRecord:
    old_id: bytes
    new_id: bytes
    modifications: list[Modification]

    @property
    def rawcode(self) -> str:
        raw = self.new_id if self.new_id != b"\x00\x00\x00\x00" else self.old_id
        return raw.decode("latin-1")


@dataclass
class SimpleModification:
    field_id: bytes
    value_type: int
    value: bytes
    end_token: bytes


@dataclass
class SimpleObjectRecord:
    old_id: bytes
    new_id: bytes
    modifications: list[SimpleModification]

    @property
    def rawcode(self) -> str:
        raw = self.new_id if self.new_id != b"\x00\x00\x00\x00" else self.old_id
        return raw.decode("latin-1")


def read_i32(data: bytes, offset: int) -> tuple[int, int]:
    return struct.unpack_from("<i", data, offset)[0], offset + 4


def read_c_string(data: bytes, offset: int) -> tuple[bytes, int]:
    end = data.index(b"\x00", offset)
    return data[offset:end], end + 1


def read_object(data: bytes, offset: int) -> tuple[ObjectRecord, int]:
    old_id = data[offset : offset + 4]
    new_id = data[offset + 4 : offset + 8]
    offset += 8
    count, offset = read_i32(data, offset)
    modifications: list[Modification] = []
    for _ in range(count):
        field_id = data[offset : offset + 4]
        offset += 4
        value_type, offset = read_i32(data, offset)
        level, offset = read_i32(data, offset)
        data_pointer, offset = read_i32(data, offset)
        if value_type in (0, 1, 2):
            value = data[offset : offset + 4]
            offset += 4
        elif value_type == 3:
            value, offset = read_c_string(data, offset)
        else:
            raise ValueError(f"Unsupported object-data value type {value_type}")
        end_token = data[offset : offset + 4]
        offset += 4
        modifications.append(
            Modification(field_id, value_type, level, data_pointer, value, end_token)
        )
    return ObjectRecord(old_id, new_id, modifications), offset


def read_table(data: bytes, offset: int) -> tuple[list[ObjectRecord], int]:
    count, offset = read_i32(data, offset)
    records: list[ObjectRecord] = []
    for _ in range(count):
        record, offset = read_object(data, offset)
        records.append(record)
    return records, offset


def write_i32(value: int) -> bytes:
    return struct.pack("<i", value)


def write_object(record: ObjectRecord) -> bytes:
    out = bytearray(record.old_id + record.new_id + write_i32(len(record.modifications)))
    for mod in record.modifications:
        out += mod.field_id
        out += write_i32(mod.value_type)
        out += write_i32(mod.level)
        out += write_i32(mod.data_pointer)
        out += mod.value
        if mod.value_type == 3:
            out += b"\x00"
        out += mod.end_token
    return bytes(out)


def write_table(records: list[ObjectRecord]) -> bytes:
    return write_i32(len(records)) + b"".join(write_object(record) for record in records)


def read_simple_object(data: bytes, offset: int) -> tuple[SimpleObjectRecord, int]:
    old_id = data[offset : offset + 4]
    new_id = data[offset + 4 : offset + 8]
    offset += 8
    count, offset = read_i32(data, offset)
    modifications: list[SimpleModification] = []
    for _ in range(count):
        field_id = data[offset : offset + 4]
        offset += 4
        value_type, offset = read_i32(data, offset)
        if value_type in (0, 1, 2):
            value = data[offset : offset + 4]
            offset += 4
        elif value_type == 3:
            value, offset = read_c_string(data, offset)
        else:
            raise ValueError(f"Unsupported unit-data value type {value_type}")
        end_token = data[offset : offset + 4]
        offset += 4
        modifications.append(SimpleModification(field_id, value_type, value, end_token))
    return SimpleObjectRecord(old_id, new_id, modifications), offset


def read_simple_table(data: bytes, offset: int) -> tuple[list[SimpleObjectRecord], int]:
    count, offset = read_i32(data, offset)
    records: list[SimpleObjectRecord] = []
    for _ in range(count):
        record, offset = read_simple_object(data, offset)
        records.append(record)
    return records, offset


def write_simple_object(record: SimpleObjectRecord) -> bytes:
    out = bytearray(record.old_id + record.new_id + write_i32(len(record.modifications)))
    for mod in record.modifications:
        out += mod.field_id
        out += write_i32(mod.value_type)
        out += mod.value
        if mod.value_type == 3:
            out += b"\x00"
        out += mod.end_token
    return bytes(out)


def write_simple_table(records: list[SimpleObjectRecord]) -> bytes:
    return write_i32(len(records)) + b"".join(
        write_simple_object(record) for record in records
    )


ABILITY_TEXT = {
    "A03H": {
        b"anam": "Dimensional Anchors",
        b"atp1": "Dimensional Anchors [|cffffcc00Q|r]",
        b"aub1": (
            "Places a rotating spatial anchor for 25 seconds. Move Pointer keeps "
            "the two newest anchors; Fold links them into a real paired portal."
        ),
        b"aret": "Learn Dimensional Anchors [|cffffcc00Q|r]",
        b"arut": "Establishes persistent geometry for Fold and spatial control.",
        b"ahky": "Q",
        b"arhk": "Q",
    },
    "A03U": {
        b"anam": "Fold",
        b"atp1": "Fold [|cffffcc00W|r]",
        b"aub1": (
            "Links the two newest Dimensional Anchors for 8 seconds. Living units "
            "entering either gate emerge from the other with their facing "
            "preserved. TIDES ENGINE projectiles also cross the Fold without "
            "losing velocity. Without two anchors, creates a temporary pair "
            "between Move Pointer and the target."
        ),
        b"aret": "Learn Fold [|cffffcc00W|r]",
        b"arut": "A genuine two-way portal for units and custom missiles.",
        b"ahky": "W",
        b"arhk": "W",
    },
    "A03Y": {
        b"anam": "Unstable Coordinates",
        b"atp1": "Unstable Coordinates [|cffffcc00E|r]",
        b"aub1": (
            "Corrupts a 550-radius area for 7 seconds. Enemy movement accumulates "
            "Coordinate Error. At 460 traveled distance, the enemy swaps with its "
            "stored afterimage and takes 60 + 0.65x Agility + 2.5% maximum life "
            "as Pure damage."
        ),
        b"aret": "Learn Unstable Coordinates [|cffffcc00E|r]",
        b"arut": "Movement itself becomes a spatial liability.",
        b"ahky": "E",
        b"arhk": "E",
    },
    "A03W": {
        b"anam": "Move Point",
        b"atp1": "Move Point [|cffffcc00R|r]",
        b"aub1": (
            "Grabs every non-structure unit around Move Pointer inside a "
            "350 + 50 per level spatial disc. The disc travels along a visible "
            "curved spline for 1.25 seconds and drops all captured units at the "
            "target while preserving their relative positions."
        ),
        b"aret": "Learn Move Point [|cffffcc00R|r]",
        b"arut": "Selects, drags, and relocates an entire piece of battlefield space.",
        b"ahky": "R",
        b"arhk": "R",
    },
    "A033": {
        b"anam": "Shellguard Muster",
        b"atp1": "Shellguard Muster [|cffffcc00Q|r]",
        b"aub1": (
            "Deploys seven Shellguards for 15 seconds in a moving wedge ahead of "
            "the Turtler. The formation rotates and travels with its commander, "
            "powers Carapace Relay, and reinforces Testudo Doctrine."
        ),
        b"aret": "Learn Shellguard Muster [|cffffcc00Q|r]",
        b"arut": "Creates a disciplined mobile formation instead of scattered summons.",
        b"ahky": "Q",
        b"arhk": "Q",
    },
    "A032": {
        b"anam": "Carapace Relay",
        b"atp1": "Carapace Relay [|cffffcc00W|r]",
        b"aub1": (
            "Fires an energy strike through every Shellguard in wedge order "
            "before converging on the target. Deals 90 + 0.7x Strength + 15 per "
            "shell + 2% target maximum life as Pure damage."
        ),
        b"aret": "Learn Carapace Relay [|cffffcc00W|r]",
        b"arut": "Each allied shell visibly adds force to the final strike.",
        b"ahky": "W",
        b"arhk": "W",
    },
    "A034": {
        b"anam": "Testudo Doctrine",
        b"atp1": "Testudo Doctrine [|cffffcc00E|r]",
        b"aub1": (
            "Nearby Shellguards interlock whenever the Turtler takes damage. Each "
            "shell restores 8% of the incoming hit, up to 60%, and reflects 0.4% "
            "of the attacker's maximum life as Pure damage."
        ),
        b"aret": "Learn Testudo Doctrine [|cffffcc00E|r]",
        b"arut": "Converts formation density directly into defense and ricochet offense.",
        b"ahky": "E",
        b"arhk": "E",
    },
    "A035": {
        b"anam": "World Turtle",
        b"atp1": "World Turtle [|cffffcc00R|r]",
        b"aub1": (
            "The Shellguard formation combines beneath the Turtler, creating a "
            "mobile fortress. Nearby allies are carried with its movement. Every "
            "0.75 seconds it crushes enemies in 310 radius for 35 + 0.45x "
            "Strength + 1.25% maximum life as Pure damage and shoves them away."
        ),
        b"aret": "Learn World Turtle [|cffffcc00R|r]",
        b"arut": "Transforms the entire phalanx into one moving allied transport fortress.",
        b"ahky": "R",
        b"arhk": "R",
    },
    "A019": {
        b"anam": "Meteor Seed",
        b"atp1": "Meteor Seed [|cffffcc00Q|r]",
        b"aub1": (
            "Hurls a massive boulder in a visible arc. Impact deals 55 + 0.65x "
            "Strength + 2.5% maximum life as Pure damage in 245 radius, with "
            "extra maximum-life damage to heroes, then leaves a Meteor Seed "
            "embedded in the battlefield for 30 seconds."
        ),
        b"aret": "Learn Meteor Seed [|cffffcc00Q|r]",
        b"arut": (
            "Creates persistent boulders that Continental Roll and Tectonic "
            "Assembly can weaponize."
        ),
        b"ahky": "Q",
        b"arhk": "Q",
    },
    "A016": {
        b"anam": "Continental Roll",
        b"atp1": "Continental Roll [|cffffcc00W|r]",
        b"aub1": (
            "Launches a colossal rolling boulder for up to 1450 range and kicks "
            "up to 6 nearby Meteor Seeds into additional rollers. Boulders deal "
            "70 + 0.8x Strength + 2.5% maximum life as Pure damage, shove enemies, "
            "ricochet from terrain and other seeds, and re-embed when they stop."
        ),
        b"aret": "Learn Continental Roll [|cffffcc00W|r]",
        b"arut": (
            "Turns the seeded battlefield into a chaotic pinball engine of stone."
        ),
        b"ahky": "W",
        b"arhk": "W",
    },
    "A01B": {
        b"anam": "Lithic Heart",
        b"atp1": "Lithic Heart [|cffffcc00E|r]",
        b"aub1": (
            "Taking damage builds Strata. Every fifth hit restores 50% of that "
            "hit and releases a 375-radius counterwave dealing Strength and "
            "maximum-life Pure damage while blasting enemies away."
        ),
        b"aret": "Learn Lithic Heart [|cffffcc00E|r]",
        b"arut": "A reactive stone armor that answers sustained focus with a counterquake.",
        b"ahky": "E",
        b"arhk": "E",
    },
    "A01A": {
        b"anam": "Tectonic Assembly",
        b"atp1": "Tectonic Assembly [|cffffcc00R|r]",
        b"aub1": (
            "Raises every owned Meteor Seed into a monolith, links each one to "
            "its nearest neighbor with erupting fault lines, and detonates the "
            "entire network. Enemies struck take 140 + 25 per seed + 4.5% maximum "
            "life as Pure damage and are stunned. Creates an 8-monolith ring if "
            "no seeds exist."
        ),
        b"aret": "Learn Tectonic Assembly [|cffffcc00R|r]",
        b"arut": "Builds a temporary polygon of stone, then ruptures every edge at once.",
        b"ahky": "R",
        b"arhk": "R",
    },
    "A05R": {
        b"anam": "Judgment Hammer",
        b"atp1": "Judgment Hammer [|cffffcc00Q|r]",
        b"aub1": (
            "Drives a spectral warhammer into a unit or the ground for 25 seconds. "
            "A unit hit takes 70 + 0.8x Strength + 2% maximum life as Magic damage. "
            "Embedded hammers follow their victims and become relay points for "
            "Master of the Anvil."
        ),
        b"aret": "Learn Judgment Hammer [|cffffcc00Q|r]",
        b"arut": "Leaves a real hammer in the battlefield instead of a disposable projectile.",
        b"ahky": "Q",
        b"arhk": "Q",
    },
    "A05V": {
        b"anam": "Overforge",
        b"atp1": "Overforge [|cffffcc00W|r]",
        b"aub1": (
            "Superheats every embedded hammer for 6 seconds. Each hammer erupts "
            "every 0.75 seconds, dealing 20 + 1.25% maximum life as Pure damage "
            "nearby. Master of the Anvil also deals an additional 2.5% maximum "
            "life through a hot hammer."
        ),
        b"aret": "Learn Overforge [|cffffcc00W|r]",
        b"arut": "Turns the entire hammer network into a distributed burning foundry.",
        b"ahky": "W",
        b"arhk": "W",
    },
    "A05S": {
        b"anam": "Master of the Anvil",
        b"atp1": "Master of the Anvil [|cffffcc00E|r]",
        b"aub1": (
            "Whenever the God of Hammers damages an enemy, the nearest embedded "
            "hammer within 1200 range strikes that victim through a lightning "
            "relay for 35 + 0.55x Strength as Magic damage. Hot hammers add "
            "2.5% maximum-life Pure damage."
        ),
        b"aret": "Learn Master of the Anvil [|cffffcc00E|r]",
        b"arut": "Every placed hammer becomes a second attack origin.",
        b"ahky": "E",
        b"arhk": "E",
    },
    "A05U": {
        b"anam": "Heavenfall Foundry",
        b"atp1": "Heavenfall Foundry [|cffffcc00R|r]",
        b"aub1": (
            "Recalls and fuses all embedded hammers into a colossal spinning "
            "superhammer that falls from 1350 height. Impact deals 250 + 1.5x "
            "Strength plus 4% maximum life, gaining another 1.2% maximum life "
            "and 18 radius per consumed hammer, up to 18%, then stuns all enemies."
        ),
        b"aret": "Learn Heavenfall Foundry [|cffffcc00R|r]",
        b"arut": "Consumes the hammer network to forge one map-shaking divine impact.",
        b"ahky": "R",
        b"arhk": "R",
    },
    "A07I": {
        b"anam": "Citadel of War",
        b"atp1": "Citadel of War [|cffffcc00Q|r]",
        b"aub1": (
            "Raises an 800-radius electrified fortress for 7 seconds. Enemies "
            "outside cannot enter. Enemies caught inside cannot escape: crossing "
            "the wall deals 75 + 4% of maximum life as Pure damage and hurls "
            "them back into the arena.|n|n[|cff4EA6DACooldown|r: 15 seconds.]"
        ),
        b"ahky": "Q",
    },
    "A039": {
        b"anam": "Siegebreaker Pulse",
        b"atp1": "Siegebreaker Pulse [|cffffcc00W|r]",
        b"aub1": (
            "Detonates a 700-radius tectonic pulse, dealing 50 + 1.25x Strength "
            "+ 6% of each enemy's maximum life as Pure damage and blasting them "
            "outward. The original suppression field also cripples enemy damage "
            "for 10 seconds.|n|n[|cff4EA6DACooldown|r: 17 seconds.]"
        ),
        b"aret": "Learn Siegebreaker |cffffcc00P|rulse",
        b"arut": (
            "A tank-breaking shockwave whose damage scales with the maximum life "
            "of every enemy it hits."
        ),
        b"ahky": "W",
        b"arhk": "W",
    },
    "A038": {
        b"anam": "Reactive Plating",
        b"atp1": "Reactive Plating [|cffffcc00E|r]",
        b"aub1": (
            "Overloads the Tiles of War's armor for 6 seconds. Reactive Plating "
            "restores 75% of every incoming hit, reflects 2% of the attacker's "
            "maximum life as Pure damage, and repels nearby attackers."
            "|n|n[|cff4EA6DACooldown|r: 15 seconds.]"
        ),
        b"aret": "Learn Reactive Plat|cffffcc00i|rng",
        b"arut": (
            "A siege-tank defense that converts enemy durability into retaliatory "
            "damage."
        ),
        b"ahky": "E",
        b"arhk": "E",
    },
    "A037": {
        b"anam": "Worldbreaker Protocol",
        b"atp1": "Worldbreaker Protocol [|cffffcc00R|r]",
        b"aut1": "End Worldbreaker Protocol [|cffffcc00R|r]",
        b"aub1": (
            "Enters a fortified burrow form. Every 0.75 seconds, seismic pulses "
            "deal 25 + 2.5% of enemy maximum life as Pure damage, drag enemies "
            "inward, and repair the Tiles of War. Emerging detonates the ground "
            "for 150 + 8% maximum life damage and throws enemies away."
        ),
        b"auu1": "Emerge and trigger the Worldbreaker eruption.",
        b"aret": "Learn |cffffcc00W|rorldbreaker Protocol",
        b"arut": (
            "Transform into a living siege engine. Remaining burrowed sustains "
            "anti-tank tremors; emerging triggers a massive eruption."
        ),
        b"ahky": "R",
        b"auhk": "R",
        b"arhk": "R",
    },
    "A05Q": {
        b"anam": "Faultline",
        b"atp1": "Faultline [|cffffcc00Q|r]",
        b"aub1": (
            "Raises 15 physical rock segments across 1230 range for 5.25 "
            "seconds. The faultline deals 90 + 1.1x Strength as Magic damage "
            "and stuns every enemy it catches once. Each segment is a Resonance "
            "Node that empowers World Echo."
        ),
        b"aret": "Learn Faultline [|cffffcc00Q|r]",
        b"arut": (
            "Creates a temporary physical wall and a chain of Resonance Nodes."
        ),
        b"ahky": "Q",
        b"arhk": "Q",
    },
    "AEET": {
        b"anam": "Totemic Vault",
        b"atp1": "Totemic Vault [|cffffcc00W|r]",
        b"aub1": (
            "Vaults 280 distance in the EarthShaker's facing direction, plants "
            "a Resonance Node at the landing point, and triggers Aftershock. "
            "The enchanted totem still empowers the next attack."
        ),
        b"aret": "Learn Totemic Vault [|cffffcc00W|r]",
        b"arut": (
            "A short terrain-safe combat vault that seeds the battlefield for "
            "World Echo."
        ),
        b"ahky": "W",
        b"arhk": "W",
    },
    "A0as": {
        b"anam": "Aftershock Matrix",
        b"atp1": "Aftershock Matrix [|cffffcc00E|r]",
        b"aub1": (
            "Every EarthShaker spell releases a 325-radius resonance burst for "
            "45 + 0.65x Strength as Magic damage and stuns nearby enemies."
        ),
        b"aret": "Learn Aftershock Matrix [|cffffcc00E|r]",
        b"arut": (
            "Passively turns every spell into a close-range resonance burst."
        ),
        b"ahky": "E",
        b"arhk": "E",
    },
    "A100": {
        b"anam": "World Echo",
        b"atp1": "World Echo [|cffffcc00R|r]",
        b"aub1": (
            "Detonates the EarthShaker and all of his Resonance Nodes. Enemies "
            "within 1700 take 120 + 4% maximum life as Pure damage, plus 45 "
            "damage for every node within 350 of them. Multiple nearby nodes "
            "also stun. Consumes all owned nodes."
        ),
        b"aret": "Learn World Echo [|cffffcc00R|r]",
        b"arut": (
            "Routes a battlefield-wide slam through every planted faultline "
            "segment and totem node."
        ),
        b"ahky": "R",
        b"arhk": "R",
    },
    "A00N": {
        b"anam": "Drowned Garden",
        b"atp1": "Drowned Garden [|cffffcc00W|r]",
        b"aub1": (
            "Sinks terrain in a 600 radius for 6 seconds, blocking ground pathing "
            "around the outer edge and summoning 2 Abyssal Tentacles dealing "
            "35% of Lone Hydra's total stats as damage."
        ),
        b"aret": "Learn Drowned Garden [|cffffcc00W|r]",
        b"arut": "Floods a battle area and summons tentacles.",
        b"ahky": "W",
        b"arhk": "W",
    },
    "A02Z": {
        b"anam": "Abyssal Hold",
        b"atp1": "Abyssal Hold [|cffffcc00R|r]",
        b"aub1": (
            "Roots all enemy units in a 1000 radius for 5 seconds, granting "
            "Lone Hydra magic immunity and dealing 200/400/600 + 30% Intelligence "
            "pure damage over duration."
        ),
        b"aret": "Learn Abyssal Hold [|cffffcc00R|r]",
        b"arut": "Traps all surrounding enemies in crushing oceanic pressure.",
        b"ahky": "R",
        b"arhk": "R",
    },
    "A05L": {
        b"anam": "Smite",
        b"atp1": "Smite [|cffffcc00Q|r]",
        b"aub1": (
            "Strikes an enemy unit, dealing heavy damage scaling with Strength."
        ),
        b"aret": "Learn Smite [|cffffcc00Q|r]",
        b"arut": "Heavy crushing strike.",
        b"ahky": "Q",
        b"arhk": "Q",
    },
}


# =========================================================================
# Fast-paced arena rebalance (goal batch 24)
# =========================================================================
# Every hero-carried active ability gets its cooldown pulled down for arena
# pace. The user's hard rule: ultimates never dip below 10 seconds, basic
# abilities never below 4 seconds. Abilities the batch redesigns get explicit
# cooldowns instead of the formula.

HERO_IDS = [
    "H006", "H00D", "H003", "H00A", "H004", "H00N", "H002", "H007", "H001",
    "EEES", "H00H", "H00J", "N005", "H00S", "H00O", "H00T", "H00W", "H00X",
    "H013", "H015", "H017", "H019", "H01C", "H01E", "H01J", "H01K", "H01N",
    "H01P",
]

# Non-ability entries that can appear in a hero's ability list.
NON_SPELL_ABILITIES = {"AInv"}

EXPLICIT_COOLDOWNS = {
    "A008": 6.0,   # Grudge Bolt
    "A02D": 9.0,   # Wave of Terror
    "A00B": 12.0,  # Nether Swap (ultimate, >= 10)
    "A03J": 12.0,  # Slaughterhouse (ultimate, >= 10)
}

ULT_SCALE, ULT_FLOOR, ULT_CAP = 0.5, 10.0, 45.0
BASIC_SCALE, BASIC_FLOOR, BASIC_CAP = 0.6, 4.0, 18.0


def collect_hero_ability_tiers(
    unit_records: "list[SimpleObjectRecord]",
) -> tuple[set[str], set[str]]:
    """Return (basics, ultimates) drawn from every hero's ability list.

    The map's GUI convention lists the ultimate as the last real ability of
    `uabi`; everything before it is a basic slot.
    """
    basics: set[str] = set()
    ults: set[str] = set()
    for record in unit_records:
        if record.rawcode not in HERO_IDS:
            continue
        for mod in record.modifications:
            if mod.field_id == b"uabi" and mod.value_type == 3:
                spells = [
                    code
                    for code in mod.value.decode("utf-8").split(",")
                    if code and code not in NON_SPELL_ABILITIES
                ]
                if spells:
                    ults.add(spells[-1])
                    basics.update(spells[:-1])
    # A hero pairing (H004/H00N) shares abilities; ultimate wins ties.
    basics -= ults
    return basics, ults


def rebalance_cooldowns(
    records: list[ObjectRecord], basics: set[str], ults: set[str]
) -> int:
    changes = 0
    for record in records:
        code = record.rawcode
        if code in EXPLICIT_COOLDOWNS or (code not in basics and code not in ults):
            continue
        is_ult = code in ults
        for mod in record.modifications:
            if mod.field_id != b"acdn" or mod.value_type not in (1, 2):
                continue
            old = struct.unpack("<f", mod.value)[0]
            if old <= 0.0:
                continue
            if is_ult:
                new = max(ULT_FLOOR, min(ULT_CAP, old * ULT_SCALE))
            else:
                new = max(BASIC_FLOOR, min(BASIC_CAP, old * BASIC_SCALE))
            new = round(new * 2.0) / 2.0
            if abs(new - old) > 0.01:
                mod.value = struct.pack("<f", new)
                changes += 1
    return changes


def string_mod(field_id: bytes, value: str, level: int = 0) -> Modification:
    return Modification(
        field_id, 3, level, 0, value.encode("utf-8"), b"\x00\x00\x00\x00"
    )


def int_mod(field_id: bytes, value: int, level: int = 0) -> Modification:
    return Modification(
        field_id, 0, level, 0, struct.pack("<i", value), b"\x00\x00\x00\x00"
    )


def real_mod(field_id: bytes, value: float, level: int = 1) -> Modification:
    return Modification(
        field_id, 1, level, 0, struct.pack("<f", value), b"\x00\x00\x00\x00"
    )


def encode_value(value_type: int, value) -> bytes:
    if value_type == 3:
        return str(value).encode("utf-8")
    if value_type == 0:
        return struct.pack("<i", int(value))
    return struct.pack("<f", float(value))


def upsert_field(
    record: ObjectRecord, field_id: bytes, value_type: int, level: int, value
) -> int:
    encoded = encode_value(value_type, value)
    for mod in record.modifications:
        if mod.field_id == field_id and mod.level == level:
            if mod.value_type == value_type and mod.value == encoded:
                return 0
            mod.value_type = value_type
            mod.value = encoded
            return 1
    record.modifications.append(
        Modification(field_id, value_type, level, 0, encoded, b"\x00\x00\x00\x00")
    )
    return 1


# (field, value_type, level, value) applied on top of the existing records.
# value_type: 0=int, 1=real, 3=string. Level 0 = static field.
BTN = "ReplaceableTextures\\CommandButtons\\"

VENGE_PUDGE_FIELD_PATCHES = {
    # --- Vengeful Spirit ---------------------------------------------------
    "A008": [
        (b"anam", 3, 0, "Grudge Bolt"),
        (b"aart", 3, 0, BTN + "BTNSpiritOfVengeance.blp"),
        (b"arar", 3, 0, BTN + "BTNSpiritOfVengeance.blp"),
        (b"amat", 3, 0, ""),
        (b"amsp", 0, 0, 10000),
        (b"ahky", 3, 0, "Q"),
        (b"arhk", 3, 0, "Q"),
        (b"abpx", 0, 0, 0),
        (b"abpy", 0, 0, 2),
        (b"aani", 3, 0, "attack"),
    ]
    + [(b"Htb1", 1, lv, 0.0) for lv in (1, 2, 3, 4)]
    + [(b"adur", 1, lv, 0.01) for lv in (1, 2, 3, 4)]
    + [(b"ahdu", 1, lv, 0.01) for lv in (1, 2, 3, 4)]
    + [(b"acdn", 1, lv, EXPLICIT_COOLDOWNS["A008"]) for lv in (1, 2, 3, 4)]
    + [(b"aran", 1, lv, 750.0) for lv in (1, 2, 3, 4)]
    + [(b"atp1", 3, lv, "Grudge Bolt [|cffffcc00Q|r]") for lv in (1, 2, 3, 4)]
    + [
        (
            b"aub1",
            3,
            lv,
            "Hurls a vengeful spirit that hunts its target for |cffffcc00100 + "
            "260% Agility|r magic damage and stuns on impact. The grudge "
            "lingers: an echo wisp remains at the wound and strikes the victim "
            "again a moment later for half damage.",
        )
        for lv in (1, 2, 3, 4)
    ],
    "A00C": [
        (b"anam", 3, 0, "Unpaid Blood"),
        (b"ahky", 3, 0, "E"),
        (b"arhk", 3, 0, "E"),
        (b"abpx", 0, 0, 2),
        (b"abpy", 0, 0, 2),
    ]
    + [
        (
            b"atar",
            3,
            lv,
            "air,allies,friend,ground,invulnerable,self,vulnerable",
        )
        for lv in (1, 2, 3, 4)
    ]
    + [(b"Uau1", 1, lv, 0.08) for lv in (1, 2, 3, 4)]
    + [(b"Uau2", 1, lv, 0.0) for lv in (1, 2, 3, 4)]
    + [(b"atp1", 3, lv, "Unpaid Blood [|cffffcc00E|r] - |cff9456e7Aura|r") for lv in (1, 2, 3, 4)]
    + [
        (
            b"aub1",
            3,
            lv,
            "Vengeance never forgets. Nearby allied heroes move |cffffcc008%|r "
            "faster, and |cffffcc0025%|r of every point of damage they suffer "
            "is stored as Vengeance (up to 200 + 12x Agility). Venge's next "
            "strike detonates every stored point as bonus pure damage.",
        )
        for lv in (1, 2, 3, 4)
    ],
    # --- Butcher -----------------------------------------------------------
    "A03B": [
        (b"ahky", 3, 0, "Q"),
        (b"arhk", 3, 0, "Q"),
        (b"abpx", 0, 0, 0),
        (b"arpx", 0, 0, 0),
        (b"abpy", 0, 0, 2),
    ],
    "A03L": [
        (b"anam", 3, 0, "Rot"),
        (b"ahky", 3, 0, "W"),
        (b"auhk", 3, 0, "W"),
        (b"arhk", 3, 0, "W"),
        (b"abpx", 0, 0, 1),
        (b"arpx", 0, 0, 1),
        (b"abpy", 0, 0, 2),
    ]
    + [(b"Eim1", 1, lv, 0.0) for lv in (1, 2, 3, 4)]
    + [(b"aare", 1, lv, 250.0) for lv in (1, 2, 3, 4)]
    + [(b"atp1", 3, lv, "Rot [|cffffcc00W|r] - |cff9456e7Toggle|r") for lv in (1, 2, 3, 4)]
    + [(b"aut1", 3, lv, "Stop Rotting [|cffffcc00W|r]") for lv in (1, 2, 3, 4)]
    + [
        (
            b"aub1",
            3,
            lv,
            "Pudge's putrid flesh boils off in a noxious cloud, dealing "
            "|cffffcc0090 + 35% of his Strength|r per second to enemies within "
            "250 and slowing them. Enemies rotting for more than |cffffcc005 "
            "seconds|r begin to fester, taking |cffff5050 10% increased damage "
            "from every source|r while the wounds remain open.",
        )
        for lv in (1, 2, 3, 4)
    ],
    "A03J": [
        (b"anam", 3, 0, "Slaughterhouse"),
        (b"ahky", 3, 0, "R"),
        (b"arhk", 3, 0, "R"),
        (b"abpx", 0, 0, 3),
        (b"arpx", 0, 0, 3),
        (b"abpy", 0, 0, 2),
    ]
    + [(b"Htb1", 1, lv, 0.0) for lv in (1, 2, 3)]
    + [(b"adur", 1, lv, 1.0) for lv in (1, 2, 3)]
    + [(b"ahdu", 1, lv, 1.0) for lv in (1, 2, 3)]
    + [(b"acdn", 1, lv, EXPLICIT_COOLDOWNS["A03J"]) for lv in (1, 2, 3)]
    + [(b"aran", 1, lv, 450.0) for lv in (1, 2, 3)]
    + [(b"atp1", 3, lv, "Slaughterhouse [|cffffcc00R|r]") for lv in (1, 2, 3)]
    + [
        (
            b"aub1",
            3,
            lv,
            "Pudge impales his victim on a great chain, drags it onto the "
            "slaughter block at his side and butchers it alive: |cffffcc008 "
            "strikes|r over 3.2 seconds, each rending |cffffcc0065 + 50% "
            "Strength + 2.5% of maximum life|r as pure damage and feeding "
            "Pudge the same amount of life. The victim festers, taking 10% "
            "increased damage. If it dies on the block, Pudge gains "
            "|cffff50505 permanent Strength|r and the corpse detonates in "
            "gore.",
        )
        for lv in (1, 2, 3)
    ],
    # Rot's companion slow aura follows the new 250 radius.
    "A03D": [(b"aare", 1, 1, 250.0)],
    # --- Demon Witch: Finger of Death v2 --------------------------------
    "A014": [
        (
            b"aub1",
            3,
            lv,
            "Lion condemns a 600-radius field around the victim: every enemy "
            "inside is lashed by its own death-finger arc for "
            "|cffffcc00700 + 3x Intelligence + 50% of Lion's total stats|r as "
            "|cffff5050pure damage|r and slowed by 25% for 2 seconds.",
        )
        for lv in (1, 2, 3)
    ],
    # --- Lone Hydra: Abyssal Hold + sinking Drowned Garden --------------
    "A02Z": [
        (b"anam", 3, 0, "Abyssal Hold"),
        (
            b"aub1",
            3,
            1,
            "The Hydra roots itself and seizes every enemy soul within "
            "|cffffcc001000|r range: victims take |cffffcc00200 + 30% "
            "Intelligence|r pure damage and are held frozen for 5 seconds - "
            "chained to the Hydra by crackling drain-arcs, iced over, and "
            "sapped of 15 mana per second while frost pulses hammer them.",
        ),
    ],
    "A00N": [
        (
            b"aub1",
            3,
            lv,
            "The ground itself drowns: a 600-radius pit sinks beneath the "
            "battlefield while tentacles erupt from the deep. For 6 seconds "
            "no enemy inside can escape past the churning rim.",
        )
        for lv in (1, 2, 3, 4)
    ],
    # --- Naga Thunderlord: Lightning Grip storm dressing ----------------
    "A04J": [
        (
            b"aub1",
            3,
            lv,
            "Tears open a 5-second gravity storm: a massive ball of lightning "
            "anchors the well while three arcs race around its 500-radius "
            "rim. Caught enemies are gripped by drain-tethers, dragged toward "
            "the core, shocked for |cffffcc00100 pure damage|r per second and "
            "slowed until the storm collapses.",
        )
        for lv in (1, 2)
    ],
}


def build_wave_of_terror() -> ObjectRecord:
    """A02D rebuilt from Channel: a point-target spectral wave (JASS does the
    work). The old record was a Howl of Terror variant on a mind-control-free
    base; a clean Channel base gives a proper point cast."""
    tooltip = (
        "Venge screams a spectral shockwave that tears |cffffcc001300|r units "
        "forward, dealing |cffffcc0075 + 220% Agility|r magic damage to every "
        "enemy in its path, shredding armor and slowing them for 3 seconds."
    )
    return ObjectRecord(
        b"ANcl",
        b"A02D",
        [
            string_mod(b"anam", "Wave of Terror"),
            int_mod(b"aher", 0),
            int_mod(b"alev", 1),
            int_mod(b"abpx", 1),
            int_mod(b"abpy", 2),
            string_mod(b"aart", BTN + "BTNHowlOfTerror.blp"),
            string_mod(b"arar", BTN + "BTNHowlOfTerror.blp"),
            string_mod(b"ahky", "W"),
            string_mod(b"arhk", "W"),
            string_mod(b"aani", "spell"),
            string_mod(b"atp1", "Wave of Terror [|cffffcc00W|r]", 1),
            string_mod(b"aub1", tooltip, 1),
            real_mod(b"Ncl1", 0.0, 1),
            int_mod(b"Ncl2", 2, 1),
            int_mod(b"Ncl3", 1, 1),
            real_mod(b"Ncl4", 0.0, 1),
            int_mod(b"Ncl5", 0, 1),
            string_mod(b"Ncl6", "shockwave", 1),
            real_mod(b"acdn", EXPLICIT_COOLDOWNS["A02D"], 1),
            int_mod(b"amcs", 90, 1),
            real_mod(b"aran", 1300.0, 1),
        ],
    )


def build_nether_swap() -> ObjectRecord:
    """A00B rebuilt from Storm Bolt: an instant, unit-target soul swap that can
    grab allies and enemies alike; all mechanics live in JASS."""
    tooltip = (
        "Rips two souls through the nether, instantly trading places with any "
        "hero - friend or foe. A swapped enemy takes |cffffcc00100 + 300% "
        "Agility|r pure damage and is soul-tethered for 3.5 seconds: straying "
        "beyond |cffffcc00650|r range drags it screaming back to Venge."
    )
    mods = [
        string_mod(b"anam", "Nether Swap"),
        int_mod(b"aher", 0),
        int_mod(b"alev", 1),
        int_mod(b"abpx", 3),
        int_mod(b"abpy", 2),
        string_mod(b"aart", BTN + "BTNSpiritWalkerAdeptTraining.blp"),
        string_mod(b"arar", BTN + "BTNSpiritWalkerAdeptTraining.blp"),
        string_mod(b"ahky", "R"),
        string_mod(b"arhk", "R"),
        string_mod(b"aani", "spell"),
        string_mod(b"amat", ""),
        int_mod(b"amsp", 10000),
        string_mod(b"atp1", "Nether Swap [|cffffcc00R|r]", 1),
        string_mod(b"aub1", tooltip, 1),
        real_mod(b"Htb1", 0.0, 1),
        real_mod(b"adur", 0.01, 1),
        real_mod(b"ahdu", 0.01, 1),
        real_mod(b"acdn", EXPLICIT_COOLDOWNS["A00B"], 1),
        int_mod(b"amcs", 100, 1),
        real_mod(b"aran", 1100.0, 1),
        string_mod(
            b"atar",
            "air,allies,enemies,friend,ground,hero,mechanical,neutral,organic",
            1,
        ),
    ]
    return ObjectRecord(b"AHtb", b"A00B", mods)


def build_nether_chill() -> ObjectRecord:
    """A07J: hidden dummy-cast slow (25% move / 10% attack for 2 seconds)
    used by Finger of Death v2. Cast through Dummy_CastTarget with the
    'slow' order."""
    return ObjectRecord(
        b"Aslo",
        b"A07J",
        [
            string_mod(b"anam", "Nether Chill (engine)"),
            int_mod(b"aher", 0),
            int_mod(b"alev", 1),
            real_mod(b"Slo1", 0.25, 1),
            real_mod(b"Slo2", 0.10, 1),
            real_mod(b"adur", 2.0, 1),
            real_mod(b"ahdu", 2.0, 1),
            real_mod(b"acdn", 0.0, 1),
            int_mod(b"amcs", 0, 1),
            real_mod(b"aran", 900.0, 1),
            string_mod(
                b"atar",
                "air,enemies,ground,mechanical,neutral,organic",
                1,
            ),
        ],
    )


REBUILT_ABILITIES = {
    "A02D": build_wave_of_terror,
    "A00B": build_nether_swap,
    "A07J": build_nether_chill,
}


def rebuild_hero_abilities(
    original: list[ObjectRecord], custom: list[ObjectRecord]
) -> int:
    changes = 0
    for rawcode, builder in REBUILT_ABILITIES.items():
        for table in (original, custom):
            before = len(table)
            table[:] = [rec for rec in table if rec.rawcode != rawcode]
            changes += before - len(table)
        custom.append(builder())
        changes += 1
    return changes


def apply_field_patches(records: list[ObjectRecord]) -> int:
    changes = 0
    for record in records:
        patches = VENGE_PUDGE_FIELD_PATCHES.get(record.rawcode)
        if not patches:
            continue
        for field_id, value_type, level, value in patches:
            changes += upsert_field(record, field_id, value_type, level, value)
    return changes


def ensure_citadel_ability(records: list[ObjectRecord]) -> bool:
    if any(record.rawcode == "A07I" for record in records):
        return False
    text = ABILITY_TEXT["A07I"]
    records.append(
        ObjectRecord(
            b"Arsw",
            b"A07I",
            [
                string_mod(b"anam", text[b"anam"]),
                int_mod(b"aher", 0),
                int_mod(b"abpx", 0),
                int_mod(b"abpy", 2),
                string_mod(
                    b"aart", "ReplaceableTextures\\CommandButtons\\BTNStoneForm.blp"
                ),
                string_mod(
                    b"arar", "ReplaceableTextures\\CommandButtons\\BTNStoneForm.blp"
                ),
                string_mod(b"atp1", text[b"atp1"], 1),
                string_mod(b"aub1", text[b"aub1"], 1),
                string_mod(b"ahky", text[b"ahky"]),
                int_mod(b"alev", 1),
                real_mod(b"adur", 7.00),
                real_mod(b"ahdu", 7.00),
                real_mod(b"acdn", 15.00),
                real_mod(b"aran", 0.00),
                int_mod(b"amcs", 0, 1),
                string_mod(b"Hwe1", "esen", 1),
            ],
        )
    )
    return True


def patch_records(records: list[ObjectRecord]) -> int:
    changes = 0
    for record in records:
        replacements = ABILITY_TEXT.get(record.rawcode)
        if replacements is None:
            continue
        for mod in record.modifications:
            if mod.value_type == 3 and mod.field_id in replacements:
                replacement = replacements[mod.field_id].encode("utf-8")
                if mod.value != replacement:
                    mod.value = replacement
                    changes += 1
    return changes


# HookCore chain dummies shipped with broken visuals: h00R pointed at the
# import "war3mapImported\ChainElement.mdl" which does not exist inside
# base_map.w3x (an invisible chain), and h00Q used the near-invisible
# BloodElfSpellThief wisp as the hook head. Swap both to guaranteed
# built-in models so Meat Hook renders a visible head and chain links.
DUMMY_UNIT_VISUALS = {
    "h00Q": {
        b"umdl": "Abilities\\Weapons\\MeatwagonMissile\\MeatwagonMissile.mdl",
    },
    "h00R": {
        b"umdl": "Abilities\\Weapons\\WardenMissile\\WardenMissile.mdl",
    },
}


# Unit-level surgery for the goal batch: Venge becomes a real Agility hero
# and both overhauled heroes present their new kits.
UNIT_FIELD_PATCHES = {
    "H003": [
        (b"upra", 3, "AGI"),
        (b"uagi", 0, 26),
        (b"uagp", 1, 2.9),
        (b"ustr", 0, 18),
        (b"ustp", 1, 2.1),
        (b"uint", 0, 15),
        (b"uinp", 1, 1.7),
        (
            b"utub",
            3,
            "The Unfinished Death. A spirit of pure grudge who trades places "
            "with the living and repays every drop of allied blood with "
            "interest.|n|n|cffF79E46Skills|r: Grudge Bolt, Wave of Terror, "
            "Unpaid Blood, and |cff9456E7Nether Swap|r.|n"
            "|cffF2754ARange|r: 400",
        ),
    ],
    "H00S": [
        (
            b"utub",
            3,
            "A butcher of the arena. Hooks his prey across the map, rots it "
            "alive, and drags it onto the slaughter block.|n|n"
            "|cffF79E46Skills|r: Meat Hook, Rot, and "
            "|cff9456E7Slaughterhouse|r.|n"
            "|cffF2754ARange|r: 128 (Melee)",
        ),
    ],
}


def upsert_simple_field(
    record: SimpleObjectRecord, field_id: bytes, value_type: int, value
) -> int:
    encoded = encode_value(value_type, value)
    for mod in record.modifications:
        if mod.field_id == field_id and mod.value_type == value_type:
            if mod.value == encoded:
                return 0
            mod.value = encoded
            return 1
    record.modifications.append(
        SimpleModification(field_id, value_type, encoded, b"\x00\x00\x00\x00")
    )
    return 1


def patch_units(input_path: Path, output_path: Path) -> int:
    data = input_path.read_bytes()
    version, offset = read_i32(data, 0)
    original, offset = read_simple_table(data, offset)
    custom, offset = read_simple_table(data, offset)
    if offset != len(data):
        raise ValueError(f"Unit parser stopped at {offset}, file has {len(data)} bytes")

    changes = 0
    for record in original + custom:
        unit_patches = UNIT_FIELD_PATCHES.get(record.rawcode)
        if unit_patches:
            for field_id, value_type, value in unit_patches:
                changes += upsert_simple_field(record, field_id, value_type, value)
    for record in original + custom:
        visuals = DUMMY_UNIT_VISUALS.get(record.rawcode)
        if visuals is not None:
            for field_id, text in visuals.items():
                encoded = text.encode("utf-8")
                existing = next(
                    (
                        mod
                        for mod in record.modifications
                        if mod.field_id == field_id and mod.value_type == 3
                    ),
                    None,
                )
                if existing is None:
                    record.modifications.append(
                        SimpleModification(field_id, 3, encoded, b"\x00\x00\x00\x00")
                    )
                    changes += 1
                elif existing.value != encoded:
                    existing.value = encoded
                    changes += 1
        if record.rawcode not in (
            "H00O",
            "EEES",
            "H00A",
            "H01J",
            "H00X",
            "H004",
            "H00N",
            "H006",
        ):
            continue
        for mod in record.modifications:
            if mod.value_type != 3:
                continue
            if record.rawcode == "H00O" and mod.field_id == b"uabi":
                abilities = mod.value.decode("utf-8")
                if "A07I" not in abilities.split(","):
                    if abilities.startswith("A06Q,"):
                        abilities = abilities.replace("A06Q,", "A06Q,A07I,", 1)
                    else:
                        abilities = "A07I," + abilities
                    mod.value = abilities.encode("utf-8")
                    changes += 1
            elif record.rawcode == "H00O" and mod.field_id == b"utub":
                tooltip = (
                    "A living siege citadel built to break enemy tanks and control "
                    "entire battlefields.|n|n|cffF79E46Skills|r: Citadel of War, "
                    "Siegebreaker Pulse, Reactive Plating, and "
                    "|cff9456E7Worldbreaker Protocol|r.|n"
                    "|cffF2754ARange|r: 128 (Melee)"
                ).encode("utf-8")
                if mod.value != tooltip:
                    mod.value = tooltip
                    changes += 1
            elif record.rawcode == "EEES" and mod.field_id == b"utub":
                tooltip = (
                    "A battlefield resonance controller who raises physical "
                    "faultlines and detonates their nodes.|n|n"
                    "|cffF79E46Skills|r: Faultline, Totemic Vault, Aftershock "
                    "Matrix, and |cff9456E7World Echo|r.|n"
                    "|cffF2754ARange|r: 128 (Melee)"
                ).encode("utf-8")
                if mod.value != tooltip:
                    mod.value = tooltip
                    changes += 1
            elif record.rawcode == "H00A" and mod.field_id == b"utub":
                tooltip = (
                    "A tectonic architect who plants persistent boulders, kicks "
                    "them into ricocheting weapons, and assembles them into "
                    "detonating fault polygons.|n|n|cffF79E46Skills|r: Meteor "
                    "Seed, Continental Roll, Lithic Heart, and "
                    "|cff9456E7Tectonic Assembly|r.|n"
                    "|cffF2754ARange|r: 128 (Melee)"
                ).encode("utf-8")
                if mod.value != tooltip:
                    mod.value = tooltip
                    changes += 1
            elif record.rawcode == "H01J" and mod.field_id == b"utub":
                tooltip = (
                    "A divine foundry master whose thrown hammers remain embedded "
                    "in units and terrain, relay attacks, overheat, and fuse into "
                    "a superweapon.|n|n|cffF79E46Skills|r: Judgment Hammer, "
                    "Overforge, Master of the Anvil, and "
                    "|cff9456E7Heavenfall Foundry|r.|n"
                    "|cffF2754ARange|r: 128 (Melee)"
                ).encode("utf-8")
                if mod.value != tooltip:
                    mod.value = tooltip
                    changes += 1
            elif record.rawcode == "H00X" and mod.field_id == b"utub":
                tooltip = (
                    "A spatial editor who places anchors, opens two-way portals "
                    "for units and projectiles, corrupts movement coordinates, "
                    "and drags entire areas along curved paths.|n|n"
                    "|cffF79E46Skills|r: Dimensional Anchors, Fold, Unstable "
                    "Coordinates, and |cff9456E7Move Point|r.|n"
                    "|cffF2754ARange|r: 600"
                ).encode("utf-8")
                if mod.value != tooltip:
                    mod.value = tooltip
                    changes += 1
            elif record.rawcode in ("H004", "H00N") and mod.field_id == b"utub":
                tooltip = (
                    "Commander of a moving shell phalanx who routes attacks "
                    "through formation geometry and merges the wedge into an "
                    "ally-carrying mobile fortress.|n|n|cffF79E46Skills|r: "
                    "Shellguard Muster, Carapace Relay, Testudo Doctrine, and "
                    "|cff9456E7World Turtle|r.|n"
                    "|cffF2754ARange|r: 128 (Melee)"
                ).encode("utf-8")
                if mod.value != tooltip:
                    mod.value = tooltip
                    changes += 1
            elif record.rawcode == "H006" and mod.field_id == b"utub":
                tooltip = (
                    "A terrifying aquatic beast that floods battlefield terrain, "
                    "summons abyssal tentacles, and holds all surrounding enemies.|n|n"
                    "|cffF79E46Skills|r: Smite, Drowned Garden, Hydra Carapace, and "
                    "|cff9456E7Abyssal Hold|r.|n"
                    "|cffF2754ARange|r: 128 (Melee)"
                ).encode("utf-8")
                if mod.value != tooltip:
                    mod.value = tooltip
                    changes += 1
        if record.rawcode == "H01J" and not any(
            mod.field_id == b"utub" for mod in record.modifications
        ):
            tooltip = (
                "A divine foundry master whose thrown hammers remain embedded "
                "in units and terrain, relay attacks, overheat, and fuse into "
                "a superweapon.|n|n|cffF79E46Skills|r: Judgment Hammer, "
                "Overforge, Master of the Anvil, and "
                "|cff9456E7Heavenfall Foundry|r.|n"
                "|cffF2754ARange|r: 128 (Melee)"
            ).encode("utf-8")
            record.modifications.append(
                SimpleModification(b"utub", 3, tooltip, b"\x00\x00\x00\x00")
            )
            changes += 1

    output = write_i32(version) + write_simple_table(original) + write_simple_table(custom)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(output)
    return changes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--unit-input", type=Path)
    parser.add_argument("--unit-output", type=Path)
    args = parser.parse_args()

    data = args.input.read_bytes()
    version, offset = read_i32(data, 0)
    original, offset = read_table(data, offset)
    custom, offset = read_table(data, offset)
    if offset != len(data):
        raise ValueError(f"Parser stopped at {offset}, file has {len(data)} bytes")

    added_citadel = ensure_citadel_ability(custom)
    changes = patch_records(original) + patch_records(custom)

    rebuilt = rebuild_hero_abilities(original, custom)
    field_changes = apply_field_patches(original) + apply_field_patches(custom)

    rebalanced = 0
    if args.unit_input is not None:
        unit_data = args.unit_input.read_bytes()
        unit_version, unit_offset = read_i32(unit_data, 0)
        unit_original, unit_offset = read_simple_table(unit_data, unit_offset)
        unit_custom, unit_offset = read_simple_table(unit_data, unit_offset)
        basics, ults = collect_hero_ability_tiers(unit_original + unit_custom)
        # The rebuilt kit abilities keep their explicit cooldowns.
        rebalanced = rebalance_cooldowns(original, basics, ults)
        rebalanced += rebalance_cooldowns(custom, basics, ults)

    if changes == 0 and not added_citadel and rebuilt == 0 and field_changes == 0:
        raise ValueError("No hero-overhaul ability fields were patched")

    output = write_i32(version) + write_table(original) + write_table(custom)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(output)
    print(
        f"Patched {changes} hero-overhaul ability text fields"
        f"{' and added A07I Citadel of War' if added_citadel else ''}, "
        f"rebuilt {rebuilt} kit records, applied {field_changes} kit fields, "
        f"rebalanced {rebalanced} cooldown entries "
        f"({len(data)} -> {len(output)} bytes)"
    )
    if (args.unit_input is None) != (args.unit_output is None):
        raise ValueError("--unit-input and --unit-output must be provided together")
    if args.unit_input is not None and args.unit_output is not None:
        unit_changes = patch_units(args.unit_input, args.unit_output)
        if unit_changes == 0:
            raise ValueError("No hero-overhaul unit fields were patched")
        print(f"Patched {unit_changes} hero-overhaul unit fields")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
