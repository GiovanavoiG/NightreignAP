//! Event flags: calls the game's own CSFD4VirtualMemoryFlag::GetFlag / SetFlag at the pinned,
//! signature-verified RVAs (research/nightreign_exe_scan.md §7). Layout is ER-compatible:
//! CSEventFlagMan+0 is the CSFD4VirtualMemoryFlag; divisor +0x1c, holder size +0x20, blocks +0x28,
//! descriptor tree +0x38; bit = 7 - (id % divisor) % 8. SetFlag silently no-ops for groups without a
//! descriptor, exactly like Elden Ring.
use super::rva::{self, SIG_VMF_GET_FLAG, SIG_VMF_SET_FLAG};
use super::singletons::event_flag_man_ptr;
use crate::state::SlotData;
use std::sync::OnceLock;

type GetFlagFn = unsafe extern "C" fn(*mut u8, u32) -> bool;
type SetFlagFn = unsafe extern "C" fn(*mut u8, u32, bool);

struct FlagFns { get: GetFlagFn, set: SetFlagFn }
static FNS: OnceLock<Option<FlagFns>> = OnceLock::new();

fn fns() -> Option<&'static FlagFns> {
    FNS.get_or_init(|| {
        let r = rva::current()?;
        if !rva::sig_ok(r.vmf_get_flag, SIG_VMF_GET_FLAG) || !rva::sig_ok(r.vmf_set_flag, SIG_VMF_SET_FLAG) {
            tracing::error!("event flag function signatures do not match; flags disabled");
            return None;
        }
        unsafe {
            Some(FlagFns {
                get: std::mem::transmute::<usize, GetFlagFn>(rva::va(r.vmf_get_flag)),
                set: std::mem::transmute::<usize, SetFlagFn>(rva::va(r.vmf_set_flag)),
            })
        }
    }).as_ref()
}

pub fn is_set(flag: u32) -> bool {
    if flag == 0 { return false; }
    match (fns(), event_flag_man_ptr()) {
        (Some(f), Some(efm)) => unsafe { (f.get)(efm, flag) },
        _ => false,
    }
}

pub fn set(flag: u32, value: bool) {
    if flag == 0 { return; }
    if let (Some(f), Some(efm)) = (fns(), event_flag_man_ptr()) {
        unsafe { (f.set)(efm, flag, value) }
    }
}

pub fn goal_reached(sd: &SlotData) -> bool {
    use catalogue::*;
    match sd.goal {
        0 => is_set(NIGHTLORD_DEFEATED[7]),
        1 => NIGHTLORD_DEFEATED[..8].iter().all(|f| is_set(*f)),
        _ => NIGHTLORD_DEFEATED.iter().all(|f| is_set(*f)),
    }
}

/// Well-known flags (all read from regulation 1.03.5 params; see apworld data.py).
pub mod catalogue {
    /// NightBossMenuParam.defeat_event_flag rows 0-9: Tricephalos..Fissure, Night Aspect, Balancers, Dreglord.
    pub const NIGHTLORD_DEFEATED: [u32; 10] = [150, 151, 152, 153, 154, 155, 156, 160, 161, 162];
    /// NightBossMenuParam.unlock_event_flag: 0 = open, 110 = first clear, 115 = all seven, 135/136 DLC.
    pub const NIGHTLORD_UNLOCK: [u32; 10] = [0, 110, 110, 110, 110, 110, 110, 115, 135, 136];
    pub const EVERDARK_DEFEATED: [u32; 8] = [170, 171, 172, 173, 174, 175, 176, 181];
    /// HeroParam.character_unlock_flag (Wylder..Undertaker); 0 = always unlocked.
    pub const NIGHTFARER_UNLOCKED: [u32; 10] = [0, 0, 0, 6031, 0, 6037, 0, 0, 6038, 6039];
    /// Shifting Earth availability: TODO(live) - not in params; likely EMEVD/MapPattern flags.
    pub const SHIFTING_EARTH_AVAILABLE: [u32; 5] = [0; 5];
    /// NightBossMenuParam row 100 (Deep of Night) unlock flag.
    pub const DEEP_OF_NIGHT_UNLOCKED: u32 = 130;
    /// In-expedition EMEVD flags.
    pub const RUN_ENCOUNTER_STARTED: u32 = 8061;
    pub const RUN_ENCOUNTER_FINISHED: u32 = 8062;
    pub const RUN_NIGHT1_BOSS_DEAD: u32 = 7511;
    pub const RUN_NIGHT2_BOSS_DEAD: u32 = 7512;

    /// AntiqueStandParam vessel unlock flags per hero_type 1..10: [Goblet, Chalice, Soot-Covered Urn, Sealed Urn, Decrepit Goblet, Forgotten Goblet].
    pub fn vessel_flags(hero_type: u32) -> [u32; 6] {
        match hero_type {
            9 => [60510, 60520, 60530, 60540, 60760, 60770],
            10 => [60560, 60570, 60580, 60590, 60780, 60790],
            h => { let b = 60000 + 50 * (h - 1); let e = 60600 + 20 * (h - 1); [b + 10, b + 20, b + 30, b + 40, e, e + 10] }
        }
    }
    /// Shared Grails: Spirit Shelter, Giant's Cradle, Sacred Erdtree, Scadutree (DLC).
    pub const GRAIL_FLAGS: [u32; 4] = [60410, 60420, 60400, 60430];
}
