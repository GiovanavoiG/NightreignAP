//! Turning received AP items into game state.
use super::flags;
use super::rva::{self, off};
use super::singletons::{equip_game_data_ptr, player_game_data_ptr};
use crate::ap::BASE_ID;
use crate::state::{push_log, Shared};

pub enum GrantError { NotNow, Unknown(String) }

/// Item offsets - must match apworld/nightreign/items.py.
mod off {
    pub const NIGHTFARER: std::ops::Range<i64> = 1..11;
    pub const EXPEDITION: std::ops::Range<i64> = 20..30;
    pub const SHIFTING_EARTH: std::ops::Range<i64> = 40..45;
    pub const REMEMBRANCE: std::ops::Range<i64> = 50..60;
    pub const REMEMBRANCE_KEY: std::ops::Range<i64> = 60..70;
    pub const GOBLET: std::ops::Range<i64> = 70..80;
    pub const GRAIL: std::ops::Range<i64> = 85..88;
    pub const DEEP_OF_NIGHT: i64 = 90;
    pub const MURK_500: i64 = 100;
    pub const MURK_1500: i64 = 101;
    pub const FLATSTONE: i64 = 102;
    pub const GRAND_FLATSTONE: i64 = 103;
    pub const RELIC_POLISHED: std::ops::Range<i64> = 110..114;
    pub const RELIC_GRAND: std::ops::Range<i64> = 120..124;
    pub const TRAPS: std::ops::Range<i64> = 140..144;
}

/// Item ids (regulation 1.03.5 + Smithbox names). Goods use category 0x40000000; relics, Murk and
/// flatstones are EquipParamAntique entries (GaItem category 0xC0000000).
mod goods {
    pub const CAT_GOODS: u32 = 0x4000_0000;
    pub const CAT_ANTIQUE: u32 = 0xC000_0000;
    pub const ANTIQUE_MURK: u32 = 10;
    pub const SCENIC_FLATSTONE: u32 = 20;          // antique
    pub const GRAND_SCENIC_FLATSTONE: u32 = 30;    // antique ("Large Scenic Flatstone")
    /// Goblet goods per hero (Wylder..Undertaker) - AntiqueStandParam row N001.
    pub const GOBLETS: [u32; 10] = [9601, 9604, 9607, 9610, 9613, 9616, 9619, 9622, 9901, 9911];
    /// Grails in apworld order: Spirit Shelter, Giant's Cradle, Sacred Erdtree.
    pub const GRAILS: [u32; 3] = [9651, 9652, 9650];
    /// Polished / Grand relic scenes per colour (Burning, Tranquil, Luminous, Drizzly) - antique ids.
    /// Relic *effects* roll from AttachEffectTableParam when the item is created.
    pub const RELIC_POLISHED: [u32; 4] = [101, 128, 119, 110];
    pub const RELIC_GRAND: [u32; 4] = [102, 129, 120, 111];
}

pub fn apply(item_id: i64) -> Result<(), GrantError> {
    let o = item_id - BASE_ID;
    if !super::singletons::in_game() { return Err(GrantError::NotNow); }

    if off::NIGHTFARER.contains(&o) {
        let idx = (o - off::NIGHTFARER.start) as usize;
        set_flag_or_note(flags::catalogue::NIGHTFARER_UNLOCKED[idx], "nightfarer unlock");
        super::locks::mark_nightfarer(idx);
        Ok(())
    } else if off::EXPEDITION.contains(&o) {
        super::locks::mark_expedition((o - off::EXPEDITION.start) as usize);
        Ok(())
    } else if off::SHIFTING_EARTH.contains(&o) {
        let idx = (o - off::SHIFTING_EARTH.start) as usize;
        set_flag_or_note(flags::catalogue::SHIFTING_EARTH_AVAILABLE[idx], "shifting earth");
        super::locks::mark_shifting_earth(idx);
        Ok(())
    } else if off::REMEMBRANCE.contains(&o) {
        super::locks::advance_remembrance((o - off::REMEMBRANCE.start) as usize);
        Ok(())
    } else if off::REMEMBRANCE_KEY.contains(&o) {
        super::locks::unlock_all_remembrance((o - off::REMEMBRANCE_KEY.start) as usize);
        Ok(())
    } else if off::GOBLET.contains(&o) {
        let idx = (o - off::GOBLET.start) as usize;
        flags::set(flags::catalogue::vessel_flags(idx as u32 + 1)[0], true);   // unlock at the Relic Rites too
        give_item(goods::CAT_GOODS | goods::GOBLETS[idx], 1)
    } else if off::GRAIL.contains(&o) {
        let idx = (o - off::GRAIL.start) as usize;
        flags::set(flags::catalogue::GRAIL_FLAGS[idx], true);
        give_item(goods::CAT_GOODS | goods::GRAILS[idx], 1)
    } else if o == off::DEEP_OF_NIGHT {
        set_flag_or_note(flags::catalogue::DEEP_OF_NIGHT_UNLOCKED, "deep of night");
        Ok(())
    } else if o == off::MURK_500 { add_murk(500) }
    else if o == off::MURK_1500 { add_murk(1500) }
    else if o == off::FLATSTONE { give_item(goods::CAT_ANTIQUE | goods::SCENIC_FLATSTONE, 1) }
    else if o == off::GRAND_FLATSTONE { give_item(goods::CAT_ANTIQUE | goods::GRAND_SCENIC_FLATSTONE, 1) }
    else if off::RELIC_POLISHED.contains(&o) { give_item(goods::CAT_ANTIQUE | goods::RELIC_POLISHED[(o - off::RELIC_POLISHED.start) as usize], 1) }
    else if off::RELIC_GRAND.contains(&o) { give_item(goods::CAT_ANTIQUE | goods::RELIC_GRAND[(o - off::RELIC_GRAND.start) as usize], 1) }
    else if off::TRAPS.contains(&o) { trap((o - off::TRAPS.start) as usize) }
    else { Err(GrantError::Unknown(format!("offset {o}"))) }
}

fn set_flag_or_note(flag: u32, what: &str) {
    if flag == 0 { push_log(format!("TODO(RE): no flag id for {what}; unlock is tracked mod-side only")); }
    else { flags::set(flag, true); }
}

fn add_murk(amount: u32) -> Result<(), GrantError> {
    // Murk is EquipParamAntique id 10 (a GaItem, not a plain counter). Give it as an item so the
    // game's own bookkeeping (and the save) stay consistent.
    give_item(goods::CAT_ANTIQUE | goods::ANTIQUE_MURK, amount)
}

/// Item entry as consumed by CS::EquipGameData::AddInventoryEquip. TODO(live): confirm the layout with a
/// breakpoint at the function during a world pickup (ER: {id, qty, ...}; NR's 0x57a0f0 reads the id at +0).
#[repr(C)]
#[derive(Default, Clone, Copy)]
pub struct ItemEntry { pub id: u32, pub quantity: u32, pub relic_seed: i32, pub unk: i32 }

type AddInventoryEquipFn = unsafe extern "C" fn(*mut u8, *const ItemEntry, u32, bool, bool, bool) -> u64;

/// Gives one item to the player through the game's inventory-add routine (signature-verified).
fn give_item(full_id: u32, qty: u32) -> Result<(), GrantError> {
    let Some(r) = rva::current() else { return Err(GrantError::Unknown("unsupported exe version".into())) };
    if !rva::sig_ok(r.add_inventory_equip, rva::SIG_ADD_INVENTORY_EQUIP) {
        return Err(GrantError::Unknown("AddInventoryEquip signature mismatch".into()));
    }
    let egd = equip_game_data_ptr().ok_or(GrantError::NotNow)?;
    let entry = ItemEntry { id: full_id, quantity: qty, relic_seed: -1, unk: 0 };
    unsafe {
        let f: AddInventoryEquipFn = std::mem::transmute(rva::va(r.add_inventory_equip));
        f(egd, &entry, qty, true, false, false);
        let result = *(egd.add(off::EGD_LAST_ADD_ITEM_RESULT) as *const u32);
        match result {
            0 => Ok(()),
            2 => { push_log(format!("item {full_id:#x} already owned (unique)")); Ok(()) }
            4 => Err(GrantError::NotNow),   // inventory full: retry later
            other => Err(GrantError::Unknown(format!("AddInventoryEquip result {other}"))),
        }
    }
}

fn trap(idx: usize) -> Result<(), GrantError> {
    match idx {
        0 => push_log("trap: cursed relic (TODO: equip a negative-effect Depths relic)"),
        1 => push_log("trap: murk tax (TODO(live): needs the Murk removal path / negative quantity)"),
        2 => push_log("trap: Night's Cavalry ambush (TODO: spawn via ChrIns creation)"),
        3 => push_log("trap: circle collapse (TODO: write rain timer in expedition state)"),
        _ => {}
    }
    Ok(())
}

pub fn queue_death(s: &mut Shared) {
    // TODO(live): confirm PlayerGameData HP offset for Nightreign before writing it (ER: +0x10).
    let _ = player_game_data_ptr();
    s.log.push_back("DeathLink received (kill not applied until the HP offset is confirmed)".into());
}
