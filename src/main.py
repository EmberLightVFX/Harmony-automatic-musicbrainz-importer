import argparse
from harmony_driver import HarmonyDriver

if __name__ == "__main__":

    class DefVal:
        pause_on_found: bool
        manual_review: bool
        close_tabs: bool
        copy_id: bool
        manual_labels: bool
        urls: list[str] | None
        urls_file: str | None

    parser = argparse.ArgumentParser(
        description="Harmony Assistant: Automated MusicBrainz importer using Harmony and Selenium",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--urls",
        nargs="+",
        help="Album URLs",
    )
    parser.add_argument(
        "--urls-file",
        help="File containing album URLs, one per line",
    )
    parser.add_argument(
        "--pause-on-found",
        default=False,
        action="store_true",
        help="Pause when an album is already linked to MusicBrainz",
    )
    parser.add_argument(
        "--manual-review",
        default=True,
        action="store_true",
        help="Require manual review before publishing releases",
    )
    parser.add_argument(
        "--close-tabs",
        default=False,
        action="store_true",
        help="Close processing tabs after each album",
    )
    parser.add_argument(
        "--copy-id",
        default=True,
        action="store_true",
        help="Copy MusicBrainz release IDs to clipboard",
    )
    parser.add_argument(
        "--manual-labels",
        default=True,
        action="store_true",
        help="Enable manual label selection for error fixing",
    )

    args = parser.parse_args(namespace=DefVal)

    song_urls = []
    if args.urls:
        song_urls.extend(args.urls)
    if args.urls_file:
        with open(args.urls_file, "r") as f:
            song_urls.extend(line.strip() for line in f if line.strip())

    if not song_urls:
        parser.error(
            "No URLs provided. Use --urls or --urls-file to specify album URLs."
        )

    driver = HarmonyDriver(
        pause_on_found_release=args.pause_on_found,
        manual_review_before_publish=args.manual_review,
        close_process_tab_after_processing=args.close_tabs,
        copy_MB_ID_to_clipboard=args.copy_id,
        manual_label_selection=args.manual_labels,
        song_urls=song_urls,
    )

    driver.process()
