import sys
import asyncio
import time
import ctypes
from pathlib import Path
from playwright.sync_api import sync_playwright

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

def force_bring_to_front():
    """Windows API ka use karke browser window ko forcefully sabse upar laane ke liye"""
    if sys.platform != 'win32':
        return
    time.sleep(0.8) # Browser khulne ka thoda wait
    user32 = ctypes.windll.user32
    EnumWindows = user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    
    def callback(hwnd, extra):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                # Check agar window title mein Mock RTI ya Chromium hai
                if "Mock RTI" in buff.value or "Chromium" in buff.value:
                    user32.ShowWindow(hwnd, 9) # SW_RESTORE
                    user32.SetForegroundWindow(hwnd)
                    user32.BringWindowToTop(hwnd)
                    return False
        return True
    EnumWindows(EnumWindowsProc(callback), 0)

def file_rti_on_mock_portal(authority: str, draft_text: str):
    print("--- [PLAYWRIGHT DEBUG] Starting portal with forced foreground window ---")
    try:
        html_file = Path(__file__).parent / "mock_portal.html"
        
        if not html_file.exists():
            return {"error": f"mock_portal.html not found at {html_file.resolve()}"}
            
        file_url = html_file.resolve().as_uri()

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False, 
                args=["--start-maximized", "--window-position=0,0"]
            )
            context = browser.new_context(no_viewport=True)
            page = context.new_page()
            
            page.goto(file_url)
            
            # Form field auto-fill
            page.fill("#department", authority)
            page.fill("#rti_text", draft_text)
            
            # Forcefully bring browser window to the very top over Streamlit/all windows
            force_bring_to_front()
            
            print("--- [PLAYWRIGHT DEBUG] Waiting for user to solve CAPTCHA 1... ---")
            # Wait for Step 2 container
            page.wait_for_selector("#step2", state="visible", timeout=120000)
            
            print("--- [PLAYWRIGHT DEBUG] Step 1 cleared! Waiting for Step 2 CAPTCHA... ---")
            # Wait for Success screen
            page.wait_for_selector("#success_area", state="visible", timeout=120000)
            
            reg_number = page.locator("#success_reg_number").inner_text()
            print(f"--- [PLAYWRIGHT DEBUG] Extracted Registration ID: {reg_number} ---")
            
            page.wait_for_timeout(2000)
            browser.close()
            
            return {
                "registration_number": reg_number,
                "deadline": "30 Days (Standard under RTI Act 2005)",
                "target_url": file_url
            }

    except Exception as e:
        print(f"--- [PLAYWRIGHT EXCEPTION] {str(e)} ---")
        return {"error": str(e)}