//! Version-gated RVA table for nightreign.exe, produced by `tools/nr_scan.py` (static scan of
//! App 1.03.2, PE ProductVersion "1.3.3.0"). See research/nightreign_exe_scan.md for the evidence
//! behind each entry. Every function RVA carries a unique byte signature that is verified at load;
//! a mismatch disables the affected feature rather than calling into the wrong code.
use std::sync::OnceLock;
use windows::Win32::System::LibraryLoader::GetModuleHandleW;

#[derive(Debug, Clone, Copy)]
pub struct Rvas {
    // --- singleton statics (.data slots holding the instance pointer) ---
    pub game_data_man: usize,        // CONFIRMED: allocated 0x458, ctor 0x1fa740, main_player_game_data at +8
    pub cs_event_flag_man: usize,    // CONFIRMED (FD4Singleton)
    pub world_chr_man: usize,        // CONFIRMED (FD4Singleton)
    pub cs_menu_man: usize,          // CONFIRMED
    pub map_item_man: usize,         // CONFIRMED
    pub solo_param_repository: usize,
    pub msg_repository: usize,
    pub cs_gaitem: usize,
    pub game_man: usize,
    // --- functions ---
    pub vmf_get_flag: usize,         // CSFD4VirtualMemoryFlag::GetFlag(this, u32) -> bool
    pub vmf_set_flag: usize,         // CSFD4VirtualMemoryFlag::SetFlag(this, u32, bool)
    pub efm_get_event_flag: usize,   // CSEventFlagMan::GetEventFlag(this, u32*) -> bool
    pub efm_set_event_flag: usize,   // CSEventFlagMan::SetEventFlag(this, u32*, bool, u64)
    pub add_inventory_equip: usize,  // CS::EquipGameData::AddInventoryEquip (LIKELY hook / grant target)
    pub map_item_give: usize,        // 0x57a0f0: per-item give with HUD notification (LIKELY)
    pub request_regist_get_item: usize, // MapItemManImpl::_RequestRegistGetItem (LIKELY, item-lot entry)
}

/// nightreign.exe 1.03.2 (ProductVersion 1.3.3.0, en)
pub const V1_3_3_0: Rvas = Rvas {
    game_data_man: 0x3c078d0,
    cs_event_flag_man: 0x3c115a8,
    world_chr_man: 0x3c0f0a8,
    cs_menu_man: 0x3c149d8,
    map_item_man: 0x3c10b68,
    solo_param_repository: 0x3c28880,
    msg_repository: 0x3c246a8,
    cs_gaitem: 0x3c131c8,
    game_man: 0x3c13258,
    vmf_get_flag: 0x60ce40,
    vmf_set_flag: 0x60d330,
    efm_get_event_flag: 0x5e7260,
    efm_set_event_flag: 0x5e79f0,
    add_inventory_equip: 0x1f0160,
    map_item_give: 0x57a0f0,
    request_regist_get_item: 0x581800,
};

/// Byte signatures that must match at the pinned RVAs (fail closed on mismatch).
pub const SIG_VMF_GET_FLAG: &[u8] = &[0x44, 0x8B, 0x41, 0x1C, 0x44, 0x8B, 0xDA, 0x33, 0xD2, 0x41, 0x8B, 0xC3, 0x41, 0xF7, 0xF0, 0x4C, 0x8B, 0xD1, 0x45, 0x33, 0xC9, 0x44, 0x0F, 0xAF, 0xC0, 0x45, 0x2B, 0xD8, 0x4C, 0x8B, 0x41, 0x38];
pub const SIG_VMF_SET_FLAG: &[u8] = &[0x48, 0x89, 0x5C, 0x24, 0x08, 0x44, 0x8B, 0x49, 0x1C, 0x44, 0x8B, 0xD2, 0x33, 0xD2, 0x41, 0x8B, 0xC2, 0x41, 0xF7, 0xF1, 0x4C, 0x8B, 0xD9, 0x41, 0x8B, 0xD8, 0x48, 0x8B, 0x49, 0x38];
pub const SIG_EFM_GET: &[u8] = &[0x48, 0x89, 0x5C, 0x24, 0x08, 0x57, 0x48, 0x83, 0xEC, 0x20, 0x83, 0x3A, 0x00, 0x48, 0x8B, 0xDA, 0x48, 0x8B, 0xF9];
pub const SIG_EFM_SET: &[u8] = &[0x48, 0x89, 0x5C, 0x24, 0x20, 0x55, 0x56, 0x57, 0x48, 0x83, 0xEC, 0x30, 0x83, 0x3A, 0x00, 0x49, 0x8B, 0xE9, 0x41, 0x0F, 0xB6, 0xF8, 0x48, 0x8B, 0xDA, 0x48, 0x8B, 0xF1, 0x0F, 0x84];
pub const SIG_ADD_INVENTORY_EQUIP: &[u8] = &[0x48, 0x89, 0x5C, 0x24, 0x10, 0x48, 0x89, 0x74, 0x24, 0x18, 0x48, 0x89, 0x7C, 0x24, 0x20, 0x55, 0x41, 0x54, 0x41, 0x55, 0x41, 0x56, 0x41, 0x57, 0x48, 0x8D, 0x6C, 0x24, 0xD9, 0x48, 0x81, 0xEC, 0x90, 0x00, 0x00, 0x00];
pub const SIG_MAP_ITEM_GIVE: &[u8] = &[0x4C, 0x89, 0x4C, 0x24, 0x20, 0x44, 0x88, 0x44, 0x24, 0x18, 0x48, 0x89, 0x4C, 0x24, 0x08, 0x55, 0x53, 0x56, 0x57, 0x41, 0x54, 0x41, 0x55, 0x41, 0x56, 0x41, 0x57, 0x48, 0x8B, 0xEC, 0x48, 0x83, 0xEC, 0x68];

/// Struct offsets confirmed by the scan (ER-compatible).
pub mod off {
    pub const VMF_DIVISOR: usize = 0x1c;
    pub const VMF_HOLDER_SIZE: usize = 0x20;
    pub const VMF_FLAG_BLOCKS: usize = 0x28;
    pub const VMF_DESCRIPTOR_TREE: usize = 0x38;
    pub const GDM_MAIN_PLAYER_GAME_DATA: usize = 0x08;
    pub const PGD_EQUIP_GAME_DATA: usize = 0x1d8;
    pub const EGD_LAST_ADD_ITEM_RESULT: usize = 0x304;
    pub const PGD_RUNES_ER: usize = 0x6c;   // ER value; Nightreign Murk/rune offsets are TODO(live)
}

static BASE: OnceLock<usize> = OnceLock::new();
pub fn module_base() -> usize {
    *BASE.get_or_init(|| unsafe { GetModuleHandleW(None).map(|h| h.0 as usize).unwrap_or(0) })
}
pub fn va(rva: usize) -> usize { module_base() + rva }

pub fn current() -> Option<&'static Rvas> {
    // Version gate: PE ProductVersion of the running exe.
    match crate::game::version::product_version().as_deref() {
        Some("1.3.3.0") => Some(&V1_3_3_0),
        _ => None,
    }
}

/// Verify a signature at an RVA (reads process memory; the section is mapped read/execute).
pub fn sig_ok(rva: usize, sig: &[u8]) -> bool {
    let p = va(rva) as *const u8;
    if p.is_null() { return false; }
    let bytes = unsafe { std::slice::from_raw_parts(p, sig.len()) };
    bytes == sig
}
