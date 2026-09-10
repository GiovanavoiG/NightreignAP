//! Event-flag reads/writes and the flag-id catalogue.
//!
//! Nightreign, like Elden Ring, records "Nightlord defeated", "Remembrance chapter complete",
//! "vessel purchased", "character unlocked" etc. as event flags. The ids in `catalogue` are
//! placeholders (0) until captured. Capture method: Hexinton CE table -> "Event Flag" watch, or
//! diff `NR0000.sl2` event-flag blocks before/after the action with alfizari's save editor.
use super::singletons::event_flag_man;
use crate::state::SlotData;

/// Flag id -> bit lookup mirroring `CSEventFlagMan::getEventFlag` (ER layout; TODO(RE)).
pub fn is_set(flag: u32) -> bool {
    let Some(efm) = event_flag_man() else { return false };
    if efm.flag_blocks.is_null() || efm.flag_divisor == 0 { return false; }
    let block = flag / efm.flag_divisor;
    let bit = flag % efm.flag_divisor;
    unsafe {
        // Blocks are stored in a hash-map-like tree in ER; the DS3 client walks it via the
        // game's own getter. Until that function is signatured for Nightreign, this is a stub.
        let _ = (block, bit);
        get_event_flag_native(flag)
    }
}

pub fn set(flag: u32, value: bool) {
    unsafe { set_event_flag_native(flag, value) }
}

// TODO(RE): AOB-scan `CSEventFlagMan::GetEventFlag` / `SetEventFlag` in nightreign.exe.
// ER 1.10 signatures (for reference, will differ):
//   get: 48 83 EC 28 8B 02 44 8B C8 ...
//   set: 48 89 5C 24 08 44 8B 49 1C 44 8B D2 33 D2 41 8B C2 41 F7 F1 ...
type GetFlagFn = unsafe extern "C" fn(*mut super::singletons::CSEventFlagMan, u32) -> bool;
type SetFlagFn = unsafe extern "C" fn(*mut super::singletons::CSEventFlagMan, u32, bool);
static mut GET_FLAG: Option<GetFlagFn> = None;
static mut SET_FLAG: Option<SetFlagFn> = None;

pub unsafe fn get_event_flag_native(flag: u32) -> bool {
    match (GET_FLAG, event_flag_man()) {
        (Some(f), Some(efm)) => f(efm as *mut _, flag),
        _ => false,
    }
}
pub unsafe fn set_event_flag_native(flag: u32, value: bool) {
    if let (Some(f), Some(efm)) = (SET_FLAG, event_flag_man()) { f(efm as *mut _, flag, value) }
}

pub fn goal_reached(sd: &SlotData) -> bool {
    use catalogue::*;
    match sd.goal {
        0 => is_set(NIGHTLORD_DEFEATED[7]),
        1 => NIGHTLORD_DEFEATED[..8].iter().all(|f| is_set(*f)),
        _ => NIGHTLORD_DEFEATED.iter().all(|f| is_set(*f)),
    }
}

/// Well-known flags the mod needs outside of the per-location table sent in slot data.
pub mod catalogue {
    /// NightBossMenuParam.defeat_event_flag, rows 0-9 (regulation 1.03.x). Index order matches
    /// `data.NIGHTLORDS` in the apworld: Tricephalos..Fissure, Night Aspect, Balancers, Dreglord.
    pub const NIGHTLORD_DEFEATED: [u32; 10] = [150, 151, 152, 153, 154, 155, 156, 160, 161, 162];
    /// NightBossMenuParam.unlock_event_flag (vanilla gates): 0 = open, 110 = first clear, 115 = all seven.
    pub const NIGHTLORD_UNLOCK: [u32; 10] = [0, 110, 110, 110, 110, 110, 110, 115, 135, 136];
    /// Everdark Sovereign defeat flags (online only; informational).
    pub const EVERDARK_DEFEATED: [u32; 8] = [170, 171, 172, 173, 174, 175, 176, 181];
    /// HeroParam.character_unlock_flag (Wylder..Undertaker); 0 = always unlocked.
    pub const NIGHTFARER_UNLOCKED: [u32; 10] = [0, 0, 0, 6031, 0, 6037, 0, 0, 6038, 6039];
    /// Shifting Earth "available" flags. TODO(RE): not in the params read so far (likely EMEVD/MapPattern).
    pub const SHIFTING_EARTH_AVAILABLE: [u32; 5] = [0; 5];
    /// NightBossMenuParam row 100 unlock flag (Deep of Night).
    pub const DEEP_OF_NIGHT_UNLOCKED: u32 = 130;
    /// In-expedition flags (EMEVD): boss encounter started / finished, night-boss death guards.
    pub const RUN_ENCOUNTER_STARTED: u32 = 8061;
    pub const RUN_ENCOUNTER_FINISHED: u32 = 8062;
    pub const RUN_NIGHT1_BOSS_DEAD: u32 = 7511;
    pub const RUN_NIGHT2_BOSS_DEAD: u32 = 7512;

    /// AntiqueStandParam vessel unlock flags for hero_type 1..10.
    pub fn vessel_flags(hero_type: u32) -> [u32; 6] {
        let b = 60000 + 50 * (hero_type - 1);
        let e = 60600 + 20 * (hero_type - 1);
        [b + 10, b + 20, b + 30, b + 40, e, e + 10]
    }
}
