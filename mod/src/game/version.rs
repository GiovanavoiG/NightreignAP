//! PE VERSIONINFO reader for the running executable (ProductVersion string).
use std::sync::OnceLock;
use windows::core::PCWSTR;
use windows::Win32::Storage::FileSystem::{GetFileVersionInfoSizeW, GetFileVersionInfoW, VerQueryValueW, VS_FIXEDFILEINFO};
use windows::Win32::System::LibraryLoader::GetModuleFileNameW;

static VERSION: OnceLock<Option<String>> = OnceLock::new();

pub fn product_version() -> Option<String> {
    VERSION.get_or_init(read).clone()
}

fn read() -> Option<String> {
    unsafe {
        let mut path = [0u16; 1024];
        let n = GetModuleFileNameW(None, &mut path) as usize;
        if n == 0 { return None; }
        let mut handle = 0u32;
        let size = GetFileVersionInfoSizeW(PCWSTR(path.as_ptr()), Some(&mut handle));
        if size == 0 { return None; }
        let mut buf = vec![0u8; size as usize];
        if GetFileVersionInfoW(PCWSTR(path.as_ptr()), 0, size, buf.as_mut_ptr() as _).is_err() { return None; }
        let mut ptr: *mut core::ffi::c_void = std::ptr::null_mut();
        let mut len = 0u32;
        let root: Vec<u16> = "\\".encode_utf16().chain(std::iter::once(0)).collect();
        if !VerQueryValueW(buf.as_ptr() as _, PCWSTR(root.as_ptr()), &mut ptr, &mut len).as_bool() { return None; }
        let ffi = &*(ptr as *const VS_FIXEDFILEINFO);
        Some(format!("{}.{}.{}.{}", ffi.dwProductVersionMS >> 16, ffi.dwProductVersionMS & 0xffff,
                     ffi.dwProductVersionLS >> 16, ffi.dwProductVersionLS & 0xffff))
    }
}
