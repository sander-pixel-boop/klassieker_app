import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto('http://localhost:3000')

        # Navigate to guest login
        await page.get_by_role('button', name='🚪 Doorgaan als gast (zonder cloud-opslag)').click()

        # Wait for the page to load
        await page.wait_for_timeout(3000)

        # Close any popups if they exist
        try:
            await page.locator("button[aria-label='Close']").click(timeout=1000)
        except:
            pass

        # Open sidebar if collapsed
        try:
            await page.locator("[data-testid='collapsedControl']").click(timeout=1000)
        except:
            pass

        # Click on Giro: Bouwer C5
        await page.get_by_text('Giro: Bouwer C5').click()

        await page.wait_for_timeout(2000)

        await page.screenshot(path='bouwer_c5_current.png', full_page=True)
        await browser.close()

asyncio.run(main())
