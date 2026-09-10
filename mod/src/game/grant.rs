//! Turning received AP items into game state.
use super::flags;
use super::singletons::game_data_man;
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

/// EquipParamGoods ids for things we hand out directly. TODO(RE): fill from Smithbox.
mod goods {
    pub const SCENIC_FLATSTONE: u32 = 0;
    pub const GRAND_SCENIC_FLATSTONE: u32 = 0;
    pub const GOBLETS: [u32; 10] = [0; 10];
    pub const GRAILS: [u32; 3] = [0; 3];
    /// Polished / Grand relics per colour (Burning/Tranquil/Luminous/Drizzly). Relic *effects* roll
    /// from AttachEffectTableParam when the goods item is created, so giving the goods id is enough.
    pub const RELIC_POLISHED: [u32; 4] = [0; 4];
    pub const RELIC_GRAND: [u32; 4] = [0; 4];
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
        give_goods(goods::GOBLETS[(o - off::GOBLET.start) as usize], 1)
    } else if off::GRAIL.contains(&o) {
        give_goods(goods::GRAILS[(o - off::GRAIL.start) as usize], 1)
    } else if o == off::DEEP_OF_NIGHT {
        set_flag_or_note(flags::catalogue::DEEP_OF_NIGHT_UNLOCKED, "deep of night");
        Ok(())
    } else if o == off::MURK_500 { add_murk(500) }
    else if o == off::MURK_1500 { add_murk(1500) }
    else if o == off::FLATSTONE { give_goods(goods::SCENIC_FLATSTONE, 1) }
    else if o == off::GRAND_FLATSTONE { give_goods(goods::GRAND_SCENIC_FLATSTONE, 1) }
    else if off::RELIC_POLISHED.contains(&o) { give_goods(goods::RELIC_POLISHED[(o - off::RELIC_POLISHED.start) as usize], 1) }
    else if off::RELIC_GRAND.contains(&o) { give_goods(goods::RELIC_GRAND[(o - off::RELIC_GRAND.start) as usize], 1) }
    else if off::TRAPS.contains(&o) { trap((o - off::TRAPS.start) as usize) }
    else { Err(GrantError::Unknown(format!("offset {o}"))) }
}

fn set_flag_or_note(flag: u32, what: &str) {
    if flag == 0 { push_log(format!("TODO(RE): no flag id for {what}; unlock is tracked mod-side only")); }
    else { flags::set(flag, true); }
}

fn add_murk(amount: u32) -> Result<(), GrantError> {
    match game_data_man() {
        Some(g) => { g.murk = g.murk.saturating_add(amount); Ok(()) }
        None => Err(GrantError::NotNow),
    }
}

/// Calls the game's item-give routine (the one the CE "item spawner" uses).
/// TODO(RE): signature `ItemGib(CS::GameDataMan*, ItemGibEntry* list, count, ...)` as in ER.
fn give_goods(goods_id: u32, qty: u32) -> Result<(), GrantError> {
    if goods_id == 0 { push_log("TODO(RE): goods id unknown, skipped"); return Ok(()); }
    unsafe {
        if let Some(f) = ITEM_GIB {
            let entry = ItemGibEntry { category: 0x4000_0000 | goods_id, quantity: qty, ..Default::default() };
            let list = ItemGibList { count: 1, entries: [entry] };
            f(game_data_man().ok_or(GrantError::NotNow)? as *mut _ as *mut u8, &list as *const _ as *mut u8, std::ptr::null_mut(), 1);
            Ok(())
        } else { Err(GrantError::Unknown("ItemGib not resolved".into())) }
    }
}

#[repr(C)] #[derive(Default, Clone, Copy)]
pub struct ItemGibEntry { pub category: u32, pub quantity: u32, pub relic_seed: i32, pub ash: i32 }
#[repr(C)]
pub struct ItemGibList { pub count: u32, pub entries: [ItemGibEntry; 1] }
type ItemGibFn = unsafe extern "C" fn(*mut u8, *mut u8, *mut u8, u32);
pub static mut ITEM_GIB: Option<ItemGibFn> = None;

fn trap(idx: usize) -> Result<(), GrantError> {
    match idx {
        0 => push_log("trap: cursed relic (TODO: equip a negative-effect Depths relic)"),
        1 => { if let Some(g) = game_data_man() { g.murk = g.murk.saturating_sub(1000); } }
        2 => push_log("trap: Night's Cavalry ambush (TODO: spawn via ChrIns creation)"),
        3 => push_log("trap: circle collapse (TODO: write rain timer in expedition state)"),
        _ => {}
    }
    Ok(())
}

pub fn queue_death(s: &mut Shared) {
    // Applied by the poller: sets HP to 0 through PlayerGameData.
    if let Some(g) = game_data_man() {
        if let Some(p) = unsafe { g.player_game_data.as_mut() } { p.hp = 0; }
    }
    s.log.push_back("DeathLink: you died".into());
}
