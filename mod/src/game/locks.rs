//! Lock enforcement (mod-side state; not persisted in the save).
//!
//! Strategy (mirrors 4laric's Region Locks in ER-AP): keep the vanilla unlock flags alone and
//! instead intercept the UI/flow points where the player would *use* something they haven't
//! received:
//!  * Expedition select: hook the map-table confirm (`CSMenuMan` expedition confirm) and refuse
//!    when the expedition is locked, showing a toast.
//!  * Nightfarer select: hook the character-select confirm the same way.
//!  * Shifting Earth: when the expedition seed is chosen, re-roll until a pattern without a locked
//!    Shifting Earth is picked (thefifthmatt's randomizer proves the seed is a single u32 chosen
//!    after Nightlord selection).
//!  * Remembrance: hook the "active remembrance" selection so only chapters <= received count
//!    can be active.
//! All four hook sites are TODO(RE); the bookkeeping below is complete.
use crate::state::{push_log, shared};
use parking_lot::Mutex;

#[derive(Default)]
struct Locks {
    nightfarers: [bool; 10],
    expeditions: [bool; 10],
    shifting_earth: [bool; 5],
    remembrance: [u8; 10],
}
static LOCKS: Mutex<Locks> = Mutex::new(Locks { nightfarers: [false; 10], expeditions: [false; 10],
                                               shifting_earth: [false; 5], remembrance: [0; 10] });

pub fn mark_nightfarer(i: usize) { LOCKS.lock().nightfarers[i] = true; }
pub fn mark_expedition(i: usize) { LOCKS.lock().expeditions[i] = true; }
pub fn mark_shifting_earth(i: usize) { LOCKS.lock().shifting_earth[i] = true; }
pub fn advance_remembrance(i: usize) { LOCKS.lock().remembrance[i] += 1; }
pub fn unlock_all_remembrance(i: usize) { LOCKS.lock().remembrance[i] = u8::MAX; }

pub fn nightfarer_allowed(i: usize) -> bool {
    let sd = &shared().lock().slot_data;
    !sd.nightfarer_shuffle || LOCKS.lock().nightfarers[i]
}
pub fn expedition_allowed(i: usize) -> bool {
    let sd = &shared().lock().slot_data;
    !sd.expedition_locks || i == 0 || LOCKS.lock().expeditions[i]
}
pub fn shifting_earth_allowed(i: usize) -> bool {
    let sd = &shared().lock().slot_data;
    !sd.shifting_earth_locks || LOCKS.lock().shifting_earth[i]
}
/// `remembrance_locks` in slot data: 0 = none, 1 = key, 2 = progressive.
pub fn remembrance_chapter_allowed(nightfarer: usize, chapter: u8) -> bool {
    let mode = shared().lock().slot_data.remembrance_locks;
    mode == 0 || LOCKS.lock().remembrance[nightfarer] >= chapter
}

/// Re-applies defaults after (re)connect: starting Nightfarer + Tricephalos always allowed.
pub fn refresh() {
    let start = shared().lock().slot_data.starting_nightfarer.clone();
    const NAMES: [&str; 10] = ["Wylder", "Guardian", "Ironeye", "Duchess", "Raider", "Revenant", "Recluse", "Executor", "Scholar", "Undertaker"];
    if let Some(i) = NAMES.iter().position(|n| *n == start) { LOCKS.lock().nightfarers[i] = true; }
    LOCKS.lock().expeditions[0] = true;
}

/// Installs the ilhook detours on the four TODO(RE) sites. Currently a no-op that logs.
pub fn install_hooks() -> Result<(), String> {
    // Example of the intended shape (from the DS3 4.x client):
    //   let hook = ilhook::x64::Hooker::new(addr, ilhook::x64::HookType::JmpBack(on_expedition_confirm), CallbackOption::None, 0, HookFlags::empty());
    //   unsafe { hook.hook() }.map_err(|e| e.to_string())?;
    push_log("locks: hooks not installed (TODO(RE): expedition/nightfarer/remembrance confirm sites)");
    Ok(())
}
