# Status: real

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import Error, sync_playwright


REPO_ROOT = Path(__file__).resolve().parents[2]
SCREENSHOT_DIR = REPO_ROOT / "Workout" / "assets"
COURSE_ID = "5f63a7c3-1c76-513c-88a5-f335d6190816"
FRONTEND_ORIGIN = "http://localhost:5173"
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def wait_for_network_idle(page) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=15_000)
    except Error:
        # The course shell may keep lightweight polling alive; its visible
        # readiness assertions below remain authoritative.
        page.wait_for_load_state("domcontentloaded")


def target_url(node_id: str = "route-foundation-clearance:http-basics") -> str:
    return (
        f"{FRONTEND_ORIGIN}/course?courseId={COURSE_ID}"
        "&view=structured&tab=path&pathMode=course"
        "&routeId=route-foundation-clearance"
        f"&nodeId={quote(node_id, safe='')}"
    )


def main() -> None:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    console_errors: list[str] = []
    page_errors: list[str] = []
    failed_requests: list[str] = []
    media_responses: list[dict[str, object]] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=EDGE_PATH,
            headless=True,
            args=["--proxy-server=direct://", "--proxy-bypass-list=*"],
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000},
            device_scale_factor=1,
        )
        page = context.new_page()
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "requestfailed",
            lambda request: failed_requests.append(
                f"{request.method} {request.url} :: {request.failure}"
            ),
        )
        page.on(
            "response",
            lambda response: media_responses.append(
                {"status": response.status, "url": response.url}
            )
            if "/api/v1/media/" in response.url
            else None,
        )

        redirect = quote(target_url().replace(FRONTEND_ORIGIN, ""), safe="")
        page.goto(
            f"{FRONTEND_ORIGIN}/login?demo=student&redirect={redirect}",
            wait_until="domcontentloaded",
        )
        wait_for_network_idle(page)
        page.get_by_role("heading", name="登录 SecureHub").wait_for(timeout=15_000)
        page.screenshot(
            path=str(SCREENSHOT_DIR / "19-login-recon.png"),
            full_page=True,
        )

        page.get_by_role("button", name="登录", exact=True).click()
        page.wait_for_url(re.compile(r".*/course\?.*"), timeout=20_000)
        wait_for_network_idle(page)
        page.goto(target_url(), wait_until="domcontentloaded")
        wait_for_network_idle(page)

        gallery = page.get_by_role("region", name="视觉讲解")
        gallery.wait_for(state="visible", timeout=20_000)
        gallery.scroll_into_view_if_needed()
        page.wait_for_timeout(500)

        heading = gallery.get_by_role("heading", name=re.compile(r"视觉讲解"))
        assert "HTTP / HTTPS 协议基础" in heading.inner_text()
        image = gallery.get_by_alt_text("HTTP 请求与响应时序图")
        image.wait_for(state="visible")
        image_metrics = image.evaluate(
            "(element) => ({ width: element.naturalWidth, height: element.naturalHeight })"
        )
        assert image_metrics == {"width": 1672, "height": 941}
        assert gallery.get_by_text("精选图解", exact=True).is_visible()
        gallery.screenshot(path=str(SCREENSHOT_DIR / "19-multimodal-desktop.png"))

        gallery.get_by_role(
            "button",
            name="查看HTTP 请求与响应详情",
        ).click()
        sheet = page.get_by_role("dialog")
        sheet.wait_for(state="visible")
        assert sheet.get_by_text("openai-imagegen", exact=True).is_visible()
        assert sheet.get_by_text("Codex built-in image generation", exact=True).is_visible()
        sheet.screenshot(path=str(SCREENSHOT_DIR / "19-multimodal-details.png"))
        page.keyboard.press("Escape")

        gallery.get_by_role("tab", name=re.compile(r"^动画")).click()
        video = gallery.locator("video").first
        video.wait_for(state="visible")
        video.evaluate(
            """async (element) => {
              if (element.readyState >= 1) return;
              await new Promise((resolve, reject) => {
                element.addEventListener('loadedmetadata', resolve, { once: true });
                element.addEventListener('error', reject, { once: true });
              });
            }"""
        )
        video_metrics = video.evaluate(
            "(element) => ({ width: element.videoWidth, height: element.videoHeight, duration: element.duration })"
        )
        assert video_metrics["width"] == 1280
        assert video_metrics["height"] == 720
        assert 5.5 <= video_metrics["duration"] <= 7.5, video_metrics
        video.evaluate("(element) => element.play()")
        page.wait_for_timeout(1_200)
        current_time = video.evaluate("(element) => element.currentTime")
        assert current_time > 0.4
        video.evaluate("(element) => element.pause()")
        gallery.screenshot(path=str(SCREENSHOT_DIR / "19-multimodal-video.png"))

        gallery.get_by_role("button", name="实时生成图解").click()
        alert = gallery.get_by_role("alert")
        alert.wait_for(state="visible", timeout=20_000)
        assert "图像生成" in alert.inner_text()
        assert any(
            response["status"] == 503
            and str(response["url"]).endswith("/api/v1/media/generate-image")
            for response in media_responses
        )

        page.goto(
            target_url("route-foundation-clearance:sql-injection"),
            wait_until="domcontentloaded",
        )
        wait_for_network_idle(page)
        sql_gallery = page.get_by_role("region", name="视觉讲解")
        sql_gallery.wait_for(state="visible", timeout=20_000)
        sql_gallery.scroll_into_view_if_needed()
        assert sql_gallery.get_by_alt_text(
            "SQL 字符串拼接与参数化查询防御对照图"
        ).is_visible()

        page.set_viewport_size({"width": 390, "height": 844})
        mobile_gallery = page.get_by_role("region", name="视觉讲解")
        mobile_gallery.wait_for(state="visible", timeout=20_000)
        mobile_gallery.scroll_into_view_if_needed()
        page.wait_for_timeout(400)
        overflow = page.evaluate(
            "() => document.documentElement.scrollWidth - window.innerWidth"
        )
        assert overflow <= 1
        mobile_gallery.screenshot(
            path=str(SCREENSHOT_DIR / "19-multimodal-mobile.png")
        )

        result = {
            "desktop_image": image_metrics,
            "video": video_metrics,
            "video_current_time_after_play": current_time,
            "live_generation_status": next(
                (
                    response["status"]
                    for response in media_responses
                    if str(response["url"]).endswith(
                        "/api/v1/media/generate-image"
                    )
                ),
                None,
            ),
            "mobile_overflow_px": overflow,
            "console_errors": console_errors,
            "page_errors": page_errors,
            "failed_requests": failed_requests,
        }
        print(json.dumps(result, ensure_ascii=False))
        browser.close()


if __name__ == "__main__":
    main()
