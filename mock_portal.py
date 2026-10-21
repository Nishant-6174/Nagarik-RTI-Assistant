import sys
import asyncio
from pathlib import Path
from playwright.sync_api import sync_playwright

# Fix for Windows asyncio subprocess loop policy with Playwright
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

def file_rti_on_mock_portal(authority: str, draft_text: str):
    try:
        html_file = Path(__file__).parent / "mock_portal.html"
        
        if not html_file.exists():
            return {"error": f"mock_portal.html not found at {html_file.resolve()}"}
            
        file_url = html_file.resolve().as_uri()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, slow_mo=400)
            page = browser.new_page()
            
            # Navigate to local mock portal
            page.goto(file_url)
            
            # Form field entry
            page.fill("#department", authority)
            page.fill("#rti_text", draft_text)
            
            # Dynamically read and solve CAPTCHA
            captcha_code = page.locator("#captcha_text").inner_text()
            page.fill("#captcha_input", captcha_code)
            
            # Click payment & submission button
            page.click("#pay_submit")
            
            # Wait for success container
            page.wait_for_selector("#success_area", state="visible")
            
            # Scrape output registration ID
            reg_number = page.locator("#success_reg_number").inner_text()
            
            page.wait_for_timeout(1500)
            browser.close()
            
            return {
                "registration_number": reg_number,
                "deadline": "30 Days (Standard under RTI Act 2005)",
                "target_url": file_url
            }

    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    print("Testing mock portal automation with CAPTCHA...")
    res = file_rti_on_mock_portal("Public Works Department, Karnataka", "Test draft text for RTI application.")
    print(res)