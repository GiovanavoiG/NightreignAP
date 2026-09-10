//! FD4 singleton access for Nightreign.
//!
//! `fromsoftware_shared::fd4::singleton` resolves `CS::*` singletons by the name strings the game
//! embeds next to each `FD4Singleton` registration (Tremwil / Dasaav technique). This works
//! unchanged for Nightreign because it is the same engine generation as Elden Ring.
use fromsoftware_shared::singleton::get_instance;
use std::sync::atomic::{AtomicBool, Ordering};

// --- struct layouts -------------------------------------------------------------------------
// Only the fields we need. Offsets are the Elden Ring 1.16 values; TODO(RE): verify for Nightreign.

#[repr(C)]
pub struct CSEventFlagMan {
    _pad0: [u8; 0x28],
    pub flag_blocks: *mut u8,      // TODO(RE): virtual memory flag holder
    pub flag_block_size: u32,
    _pad1: [u8; 0x0c],
    pub flag_divisor: u32,         // 1000 in ER: flag id -> (block = id / divisor, bit = id % divisor)
}

#[repr(C)]
pub struct GameDataMan {
    _pad0: [u8; 0x08],
    pub player_game_data: *mut PlayerGameData,
    _pad1: [u8; 0x70],
    pub murk: u32,                 // TODO(RE): Nightreign "Murk" replaces runes here? (speculative)
}

#[repr(C)]
pub struct PlayerGameData {
    _pad0: [u8; 0x08],
    pub hp: u32,
    pub max_hp: u32,
    _pad1: [u8; 0x0c],
    pub is_dead_flag: u8,          // TODO(RE)
}

#[repr(C)]
pub struct WorldChrMan {
    _pad0: [u8; 0x1E508],
    pub main_player: *mut u8,      // ChrIns*  TODO(RE)
}

// --- accessors ------------------------------------------------------------------------------
static READY: AtomicBool = AtomicBool::new(false);

pub fn init() -> Result<(), String> {
    // Force-resolve the singleton table now so failures are visible at startup.
    let ok = unsafe { get_instance::<CSEventFlagMan>().is_ok() };
    READY.store(true, Ordering::SeqCst);
    if ok { Ok(()) } else { Err("FD4 singleton table not found (Arxan? wrong exe?)".into()) }
}

pub fn event_flag_man() -> Option<&'static mut CSEventFlagMan> {
    unsafe { get_instance::<CSEventFlagMan>().ok().flatten() }
}
pub fn game_data_man() -> Option<&'static mut GameDataMan> {
    unsafe { get_instance::<GameDataMan>().ok().flatten() }
}
pub fn world_chr_man() -> Option<&'static mut WorldChrMan> {
    unsafe { get_instance::<WorldChrMan>().ok().flatten() }
}

/// True once the player has loaded into the Roundtable Hold or an expedition.
pub fn in_game() -> bool {
    world_chr_man().map(|w| !w.main_player.is_null()).unwrap_or(false)
}

/// Edge-triggered death detection.
pub fn player_just_died() -> bool {
    static WAS_DEAD: AtomicBool = AtomicBool::new(false);
    let dead = game_data_man()
        .and_then(|g| unsafe { g.player_game_data.as_ref() })
        .map(|p| p.hp == 0)
        .unwrap_or(false);
    let was = WAS_DEAD.swap(dead, Ordering::SeqCst);
    dead && !was
}
