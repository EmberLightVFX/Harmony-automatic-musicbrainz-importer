import logging
import os
import re
import shutil
import sys
import time
from io import BytesIO
from urllib.parse import unquote, urlparse
from urllib.request import urlopen

import chime
import pyperclip
from dotenv import load_dotenv
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("debug.log"), logging.StreamHandler(sys.stdout)],
)

load_dotenv()

current_folder = os.path.dirname(os.path.realpath(__file__))
cookie_file_path = os.path.join(current_folder, "cookies.json")
screenshot_folder = os.path.join(current_folder, "screenshots")
os.makedirs(screenshot_folder, exist_ok=True)
cover_folder = os.path.join(current_folder, "covers")
os.makedirs(cover_folder, exist_ok=True)
ff_profile_folder = os.path.join(current_folder, "ff_profile")
os.makedirs(ff_profile_folder, exist_ok=True)


class HarmonyDriver:
    def __init__(
        self,
        pause_on_found_release: bool,
        manual_review_before_publish: bool,
        close_process_tab_after_processing: bool,
        copy_MB_ID_to_clipboard: bool,
        manual_label_selection: bool,
        use_test_mb: bool,
        song_urls: list[str],
    ):
        self.pause_on_found_release = pause_on_found_release
        self.manual_review_before_publish = manual_review_before_publish
        self.close_process_tab_after_processing = close_process_tab_after_processing
        self.copy_MB_ID_to_clipboard = copy_MB_ID_to_clipboard
        self.manual_label_selection = manual_label_selection
        self.use_test_mb = use_test_mb
        self.song_urls = song_urls

        self.harmony_tab: str | None = None
        self.processing_tab: str

        options = Options()
        options.profile = ff_profile_folder

        self.driver = webdriver.Firefox(options=options)
        self.driver.implicitly_wait(10)

    def process(self):
        logging.info(f"Starting Harmony processing of {len(self.song_urls)} albums.")
        chime.success()
        for i, song_url in enumerate(self.song_urls, start=1):
            logging.info(f"Processing album {i}/{len(self.song_urls)}")
            logging.info(f"Album URL: {song_url}")
            self.process_harmony(song_url)
        logging.info(f"Done processing {len(self.song_urls)} albums.")
        chime.success()

    def process_harmony(self, song_url: str):
        if self.harmony_tab is not None:
            self.driver.switch_to.window(self.harmony_tab)

        logging.info("Open Harmony")
        self.driver.get("https://harmony.pulsewidth.org.uk/")
        self.harmony_tab = self.driver.current_window_handle

        logging.info("Enable MusicBrainz provider")
        self.driver.find_element(By.ID, "musicbrainz-input").click()

        logging.info(f"Submitting album URL: {song_url}")
        provider_url = self.wait_find_element(By.ID, "url-input")
        provider_url.clear()
        provider_url.send_keys(song_url)
        logging.info("Submitting form")
        provider_url.submit()
        time.sleep(1.5)

        logging.info("Waiting for page to update")
        logging.info("Find import button")
        import_button = self.wait_find_element(
            By.XPATH, "//input[@type='submit' and @value='Import into MusicBrainz']", 10
        )
        logging.info("Check if album already exists")
        page_text = self.driver.find_element(By.TAG_NAME, "body").text
        if "is already linked to this" in page_text:
            logging.info("Album already linked to MusicBrainz release")
            link = self.driver.find_element(
                By.CSS_SELECTOR, "div p a[href*='musicbrainz.org/release']"
            )
            link_text = link.text
            logging.info("Release already linked:")
            logging.info(link_text)
            if self.copy_MB_ID_to_clipboard:
                logging.info("Copied to your clipboard")
                pyperclip.copy(link_text)
            if self.pause_on_found_release:
                chime.info()
                input("!!! Press Enter to continue to the next album...")
            return
        else:
            logging.info("Album not yet linked, proceeding with import")
        if self.use_test_mb:
            logging.info("Modifying MusicBrainz links to use test server")
            self.modify_musicbrainz_links()

        logging.info("Open processing page in new tab")
        _, self.processing_tab = self.open_in_new_tab(
            import_button,
        )
        self.process_musicbrainz_submission()
        self.process_ISRC()
        if self.use_test_mb:
            logging.info("Modifying MusicBrainz links to use test server")
            self.modify_musicbrainz_links()
            logging.info("Skipping ISRC submission in test MB mode")
        else:
            self.process_ISRC()
        self.process_external_links_to_tracks()
        self.process_cover_art()
        logging.info(f"Finished processing album {song_url}")
        if self.copy_MB_ID_to_clipboard:
            elem = self.wait_find_element(
                By.XPATH,
                '//li[@data-provider="MusicBrainz"]//a[contains(@class,"provider-id")]',
            )
            logging.info(f"Copying MusicBrainz release ID to clipboard: {elem.text}")
            pyperclip.copy(elem.text)
        if self.close_process_tab_after_processing:
            logging.info("Closing processing tab")
            self.driver.close()
        self.driver.switch_to.window(self.harmony_tab)

    def process_musicbrainz_submission(self):
        logging.info("Processing MusicBrainz submission")
        continue_button = self.wait_find_element(
            By.XPATH,
            "//button[@type='submit' and normalize-space() = 'Continue']",
        )
        logging.info("Click continue button")
        continue_button.click()

        new_login = False
        if self.driver.title.startswith("Log in"):
            logging.info("Login to MusicBrainz required.")
            if self.use_test_mb:
                logging.info("Modifying MusicBrainz login to use test server")
                os.environ["mb_pass"] = "mb"
            if os.getenv("mb_user") and os.getenv("mb_pass"):
                mb_user = os.getenv("mb_user")
                mb_pass = os.getenv("mb_pass")
                if mb_user is None or mb_pass is None:
                    raise SystemExit(
                        "MusicBrainz username or password environment variables are not set."
                    )
                self.wait_find_element(By.ID, "id-username").send_keys(mb_user)
                self.wait_find_element(By.ID, "id-password").send_keys(mb_pass)
                remember_me = self.wait_find_element(By.ID, "id-remember_me")
                remember_me.click()
                remember_me.submit()
            else:
                chime.info()
                input(
                    "!!! Press Enter after you are done logging into MusicBrainz. Remember the check 'Keep me logged in'"
                )
            new_login = True
        else:
            logging.info("Already logged in to MusicBrainz")

        logging.info("Wait for page to load and go to edit tab")
        edit_note_button = self.wait_find_element(
            By.XPATH, "//a[normalize-space() = 'Edit note']"
        )
        if new_login:
            logging.info("Saving Firefox profile after login to MusicBrainz")
            self.save_profile()
        edit_note_button.click()

        logging.info("Check for release duplicates")
        time.sleep(0.5)
        li_locator = "//li[a[normalize-space(text())='Release duplicates']]"
        li = self.wait_find_element(By.XPATH, li_locator)
        logging.info("Checking if duplicates found")
        time.sleep(0.5)
        if li.get_attribute("aria-disabled") is None:
            chime.info()
            input(
                "!!! Possible duplicate releases found. Please review them manually and then press Enter to continue."
            )
            edit_note_button.click()

        logging.info("Look for errors")
        error_tabs = []
        try:
            error_tabs = self.driver.find_elements(By.CLASS_NAME, "error-tab")
            logging.info(f"Errors found: {len(error_tabs)}")
        except Exception:
            pass

        if len(error_tabs) >= 2:
            logging.info("Multiple errors found, manual intervention required")
            chime.info()
            input(
                "!!! Multiple errors detected, please take care of them manually and then press enter."
            )
        elif len(error_tabs) == 1:
            logging.info("Single error found, attempting to fix")
            error_tabs[0].click()
            time.sleep(0.5)  # wait for tab content to load
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            if "You haven’t selected a label for" in page_text:
                logging.info("Fetch release event fieldset")
                release_event_fieldset = self.wait_find_element(
                    By.XPATH, "//fieldset[legend[normalize-space(.)='Release event']]"
                )
                logging.info("Fixing missing label error")
                label_search_list = release_event_fieldset.find_elements(
                    By.CSS_SELECTOR, "span.autocomplete"
                )
                remove_label_list = release_event_fieldset.find_elements(
                    By.CLASS_NAME, "remove-release-label"
                )
                for i, label_search in enumerate(label_search_list):
                    logging.info(
                        f"Trying to fix label {i + 1}/{len(label_search_list)}"
                    )
                    search_input = label_search.find_element(By.CSS_SELECTOR, "input")
                    logging.info("Find search button")
                    search_button = label_search.find_element(By.CSS_SELECTOR, "img")
                    logging.info("Click label search")
                    search_button.click()

                    logging.info("Find correct search list")
                    search_list = self.wait_find_element(
                        By.CSS_SELECTOR,
                        f'ul[data-input-id="{search_input.get_attribute("id")}"]',
                    )
                    logging.info("Waiting for search list to appear")
                    WebDriverWait(self.driver, timeout=10).until(
                        lambda d: "display: none"
                        not in (search_list.get_attribute("style") or "").lower()
                    )

                    logging.info("Grab first search result")
                    first_result = search_list.find_element(By.XPATH, ".//li[1]//a")
                    logging.info(
                        "Filtering, normalizing, trim and lowercasing result text"
                    )
                    text: str = self.driver.execute_script(
                        "return Array.from(arguments[0].childNodes)"
                        ".filter(n => n.nodeType === Node.TEXT_NODE)"
                        ".map(n => n.textContent)"
                        ".join('').trim().toLowerCase();",
                        first_result,
                    )

                    logging.info("Checking if matching label")
                    pre_entered_text = search_input.get_attribute("value")
                    if pre_entered_text is not None:
                        pre_entered_text = pre_entered_text.strip().lower()
                        if text and text == pre_entered_text:
                            logging.info("Found matching label, selecting it")
                            first_result.click()
                        else:
                            logging.info("No matching label found")
                            if self.manual_label_selection:
                                logging.info("Manual label fixing needed")
                                chime.info()
                                input(
                                    "!!! Please check the label manually and then press enter."
                                )
                            else:
                                logging.info("Automatically removing label entry")
                                remove_label_list[i].click()
                        logging.info("Label errors fixed")
                    else:
                        logging.info("Pre-entered label text is empty, cannot match")
            else:
                logging.info("Unknown error type, manual intervention required")
                chime.info()
                input(
                    "!!! An error was detected that cannot be automatically fixed. Please take care of it manually and then press enter."
                )

            edit_note_button.click()
            error_tabs[0].click()

        if self.manual_review_before_publish:
            chime.info()
            input("!!! Waiting for manual review. Press Enter to continue publishing")

        logging.info("Publish release")
        edit_note_button.click()
        enter_edit = self.wait_find_element(By.ID, "enter-edit")
        enter_edit.click()

        logging.info("Waiting for publish to complete")
        self.wait_find_element(
            By.XPATH,
            "//h2[contains(normalize-space(.), 'Release Actions')]",
            120,
        )
        logging.info("Release published successfully")

    def process_ISRC(self):
        try:
            logging.info("Processing ISRC submission")
            magicISRC_button = self.wait_find_element(
                By.XPATH,
                "//a[contains(normalize-space(.), 'Open with MagicISRC')]",
            )
            _, _ = self.open_in_new_tab(magicISRC_button)

            logging.info("Check if need to login")
            # Wait for a button to load so we know the page is ready
            self.wait_find_element(By.ID, "check-isrcs-submit")
            page_text = self.wait_find_element(By.TAG_NAME, "body").text
            new_login = False
            if "Login to MusicBrainz" in page_text:
                logging.info("Logging in to MusicBrainz")
                self.wait_find_element(
                    By.XPATH,
                    "//button[@type='button' and normalize-space() = 'Login to MusicBrainz']",
                ).click()

                logging.info("Accepting access")
                self.wait_find_element(
                    By.XPATH,
                    "//button[@type='submit' and normalize-space() = 'Allow access']",
                ).click()
                # Enter edit
                logging.info("Waiting for login to complete")
                time.sleep(0.5)
                self.driver.refresh()
                new_login = True
            else:
                logging.info("Already logged in to MusicBrainz for MagicISRC")

            logging.info("Submitting ISRCs")
            submit_button = self.wait_find_element(
                By.ID,
                "edit-submit",
            )
            if new_login:
                logging.info("Saving Firefox profile after login to MagicISRC")
                self.save_profile()

            submit_button.click()
            logging.info("Waiting for ISRC submission to complete")
            self.wait_find_element(
                By.XPATH,
                "//p[contains(normalize-space(.), 'The ISRCs have been successfully submitted.')]",
            )
        except Exception:
            pass

        logging.info("ISRC submission complete, closing tab")
        self.driver.close()
        self.driver.switch_to.window(self.processing_tab)

    def process_external_links_to_tracks(self):
        logging.info("Finding track external ID links")
        track_id_links = self.wait_find_elements(
            By.XPATH,
            "//a[contains(normalize-space(.), 'Link external IDs')]",
        )
        logging.info(f"Found {len(track_id_links)} track external ID links to process.")
        for link in track_id_links:
            logging.info("Opening track external ID link in new tab")
            _, _ = self.open_in_new_tab(link)
            logging.info("Submitting track external ID")
            self.wait_find_element(
                By.XPATH,
                "//button[@type='submit' and normalize-space() = 'Enter edit']",
                30,
            ).click()
            logging.info("Waiting for submission to complete")
            self.wait_find_element(
                By.CLASS_NAME,
                "banner",
                120,
            )
            logging.info("Submission complete, closing tab")
            self.driver.close()
            self.driver.switch_to.window(self.processing_tab)

    def process_cover_art(self):
        # Get and set cover art
        logging.info("Finding cover art candidates")
        cover_arts = self.wait_find_elements(By.CSS_SELECTOR, "figure.cover-image")
        logging.info(f"Found {len(cover_arts)} cover art candidates.")
        best_overall = None  # tuple (area, width, height, data, src_url)
        for cover in cover_arts:
            urls = self.candidate_urls_from_cover(cover)
            for url in urls:
                try:
                    w, h, data = self.get_image_size_from_url(url)
                except Exception:
                    continue
                area = w * h
                if (best_overall is None) or (area > best_overall[0]):
                    best_overall = (area, w, h, data, url)

        if best_overall is None:
            raise SystemExit("No valid images found")

        logging.info("Found best cover art")
        area, w, h, data, src_url = best_overall

        logging.info("Extract filename from url")
        cover_out_path = os.path.join(cover_folder, self.filename_from_url(src_url))
        _, file_extension = os.path.splitext(cover_out_path)
        if file_extension == "":
            logging.info("No file extension found, defaulting to .jpg")
            cover_out_path += ".jpg"
        logging.info(f"Saving cover art to {cover_out_path}")
        with open(cover_out_path, "wb") as f:
            f.write(data)
        logging.info(
            f"Selected cover art from {src_url} with size {w}x{h}, saved to {cover_out_path}"
        )

        logging.info("Open cover art submission page")
        add_cover_button = self.wait_find_element(
            By.XPATH, "//a[normalize-space() = 'Add cover art']"
        )
        _, _ = self.open_in_new_tab(add_cover_button)

        logging.info("Waiting for file input")
        file_input = self.wait_find_element(
            By.CSS_SELECTOR,
            "input[type='file']",
            10,
        )

        logging.info("Checking if cover art already exists on MusicBrainz")
        cover_art_link = self.wait_find_element(
            By.XPATH,
            "//a[contains(@href, '/cover-art')]/bdi",
            10,
        )
        text = cover_art_link.text
        match = re.search(r"Cover art \((\d+)\)", text)
        if match:
            count = int(match.group(1))
            if count > 0:
                logging.info(
                    f"Cover art already exists ({count} images), skipping upload"
                )
                return

        logging.info("Sending cover file path to input")
        file_input.send_keys(cover_out_path)

        logging.info("Set cover art type to 'Front'")
        self.wait_find_element(
            By.XPATH, "//li[label/span[normalize-space() = 'Front']]"
        ).click()

        logging.info("Uploading cover art")
        self.wait_find_element(
            By.XPATH,
            "//button[@type='submit' and normalize-space() = 'Enter edit']",
        ).click()
        logging.info("Waiting for submission to complete")
        self.wait_find_element(
            By.XPATH,
            "//p[contains(normalize-space(.), 'Thank you, your')]",
            120,
        )
        logging.info("Cover art submission complete, closing tab")
        self.driver.close()
        self.driver.switch_to.window(self.processing_tab)

    ## Helper functions ##

    def wait_find_element(
        self, by: str, identifier: str, timeout: int = 10
    ) -> WebElement:
        while True:
            try:
                return WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((by, identifier))
                )
            except TimeoutException:
                user_input = (
                    input(
                        f"Timeout waiting for element ({by}: {identifier}). Press 'r' to retry or 'c' to continue (may raise exception): "
                    )
                    .strip()
                    .lower()
                )
                if user_input != "r":
                    raise

    def wait_find_elements(
        self, by: str, identifier: str, timeout: int = 10
    ) -> list[WebElement]:
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_all_elements_located((by, identifier))
        )

    def wait_find_clickable(
        self, identifier: WebElement, timeout: int = 10
    ) -> WebElement:
        return WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable(identifier)
        )

    def open_in_new_tab(
        self,
        click_locator: WebElement,
        timeout: float = 10,
    ) -> tuple[str, str]:
        original_handle = self.driver.current_window_handle
        before = set(self.driver.window_handles)

        logging.info("Opening link in new tab...")
        elem = self.wait_find_clickable(click_locator)
        elem.send_keys(Keys.CONTROL + Keys.ENTER)

        # Wait for a new window handle to appear
        logging.info("Waiting for new tab to open...")
        WebDriverWait(self.driver, timeout).until(
            lambda d: len(set(d.window_handles) - before) > 0
        )
        after = set(self.driver.window_handles)
        new_handles = after - before
        new_handle = new_handles.pop()

        logging.info("Switching to new tab...")
        self.driver.switch_to.window(new_handle)

        logging.info("Returning handles...")
        return original_handle, new_handle

    def candidate_urls_from_cover(self, cover: WebElement):
        # prefer the anchor href (likely high-res) plus the img src as fallback
        urls: list[str] = []
        try:
            a = cover.find_element(By.CSS_SELECTOR, "a")
            href = a.get_attribute("href")
            if href:
                urls.append(href)
        except Exception:
            pass
        try:
            img = cover.find_element(By.CSS_SELECTOR, "img")
            src = img.get_attribute("src")
            if src and src not in urls:
                urls.append(src)
        except Exception:
            pass
        return urls

    def get_image_size_from_url(self, url: str, timeout: float = 20):
        with urlopen(url, timeout=timeout) as response:
            data = response.read()
        img = Image.open(BytesIO(data))
        img.verify()
        img = Image.open(BytesIO(data))
        return img.width, img.height, data

    def filename_from_url(self, url: str) -> str:
        path = urlparse(url).path
        name = os.path.basename(unquote(path)) or "image"
        return name

    def save_profile(self):
        profile = self.driver.capabilities["moz:profile"]
        logging.info(f"Saving Firefox profile {profile} to {ff_profile_folder}")
        shutil.rmtree(ff_profile_folder)
        shutil.copytree(
            profile,
            ff_profile_folder,
            ignore=shutil.ignore_patterns("parent.lock", "lock", ".parentlock"),
        )
