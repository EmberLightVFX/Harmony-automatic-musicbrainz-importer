from harmony_driver import HarmonyDriver

if __name__ == "__main__":
    driver = HarmonyDriver(
        pause_on_found_release=False,
        manual_review_before_publish=True,
        song_urls=[
            "",
        ],
    )

    driver.process()
