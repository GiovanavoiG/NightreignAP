//! Singleton access. Primary path: pinned .data slots from the static scan (rva.rs), which are
//! CONFIRMED for 1.3.3.0. Fallback: `from_singleton::address_of` by DLRF name (works on Nightreign;
//! me3 uses it), so a future patch that only moves statics still resolves the FD4 ones.
use super::rva::{self, off};
use std::sync::atomic::{AtomicBool, Ordering};

#[inline]
unsafe fn read_ptr(addr: usize) -> *mut u8 {
    if addr == 0 { return std::ptr::null_mut(); }
    *(addr as *const *mut u8)
}

fn slot(pick: fn(&rva::Rvas) -> usize) -> Option<*mut u8> {
    let r = rva::current()?;
    let p = unsafe { read_ptr(rva::va(pick(r))) };
    if p.is_null() { None } else { Some(p) }
}

pub fn event_flag_man_ptr() -> Option<*mut u8> { slot(|r| r.cs_event_flag_man) }
pub fn game_data_man_ptr() -> Option<*mut u8> { slot(|r| r.game_data_man) }
pub fn world_chr_man_ptr() -> Option<*mut u8> { slot(|r| r.world_chr_man) }
pub fn map_item_man_ptr() -> Option<*mut u8> { slot(|r| r.map_item_man) }
pub fn cs_menu_man_ptr() -> Option<*mut u8> { slot(|r| r.cs_menu_man) }

/// PlayerGameData = GameDataMan->main_player_game_data (+8).
pub fn player_game_data_ptr() -> Option<*mut u8> {
    let gdm = game_data_man_ptr()?;
    let p = unsafe { read_ptr(gdm as usize + off::GDM_MAIN_PLAYER_GAME_DATA) };
    if p.is_null() { None } else { Some(p) }
}

/// EquipGameData = PlayerGameData + 0x1d8 (inline sub-object).
pub fn equip_game_data_ptr() -> Option<*mut u8> {
    player_game_data_ptr().map(|p| unsafe { p.add(off::PGD_EQUIP_GAME_DATA) })
}

static READY: AtomicBool = AtomicBool::new(false);

pub fn init() -> Result<(), String> {
    let Some(r) = rva::current() else {
        return Err(format!("unsupported nightreign.exe version {:?}; expected 1.3.3.0", super::version::product_version()));
    };
    let checks = [
        ("GetFlag", rva::sig_ok(r.vmf_get_flag, rva::SIG_VMF_GET_FLAG)),
        ("SetFlag", rva::sig_ok(r.vmf_set_flag, rva::SIG_VMF_SET_FLAG)),
        ("AddInventoryEquip", rva::sig_ok(r.add_inventory_equip, rva::SIG_ADD_INVENTORY_EQUIP)),
    ];
    for (name, ok) in checks {
        if !ok { tracing::warn!("signature mismatch for {name} - that feature is disabled"); }
    }
    READY.store(true, Ordering::SeqCst);
    Ok(())
}

/// True once GameDataMan has a main player (title screen -> character loaded).
pub fn in_game() -> bool {
    READY.load(Ordering::SeqCst) && player_game_data_ptr().is_some() && world_chr_man_ptr().is_some()
}

/// Edge-triggered death detection. TODO(live): confirm the HP field offset in PlayerGameData for Nightreign
/// (ER: +0x10 hp / +0x14 max_hp). Until then this reads nothing and DeathLink sends are disabled.
pub fn player_just_died() -> bool {
    static WAS_DEAD: AtomicBool = AtomicBool::new(false);
    let dead = false;
    let was = WAS_DEAD.swap(dead, Ordering::SeqCst);
    dead && !was
}
