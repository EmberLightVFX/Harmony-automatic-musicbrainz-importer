# Harmony Assistant

Importing albums into [MusicBrainz](https://musicbrainz.org/) by leveraging [Harmony](https://harmony.pulsewidth.org.uk/)'s web interface and Selenium for browser automation.

## Features

- **Automated Import**: Automatically submits album URLs to Harmony and imports them into MusicBrainz.
- **ISRC Submission**: Handles ISRC (International Standard Recording Code) submission for tracks using MagicISRC.
- **Cover Art Upload**: Downloads and uploads the best available cover art for releases.
- **External ID Linking**: Links external IDs (e.g., streaming service URIs) to tracks.
- **Error Handling**: Detects and attempts to fix common errors, such as missing labels, with options for manual intervention.
- **Duplicate Detection**: Checks for existing releases and handles duplicates.
- **Clipboard Integration**: Optionally copies MusicBrainz release IDs to the clipboard.
- **Firefox Profile Persistence**: Saves and reuses Firefox profiles to maintain login sessions across runs.
- **Configurable Options**: Various flags to control behavior, such as pausing on found releases or manual reviews.

## Requirements

- Python 3.10 or higher
- Firefox browser (for Selenium WebDriver)
- A MusicBrainz account

## Installation

1. Clone the repository:

```bash
git clone https://github.com/EmberLightVFX/Harmony-automatic-musicbrainz-importer.git
cd Harmony-automatic-musicbrainz-importer
```

1. Install dependencies using pip:

```bash
pip install -e .
```

Or using uv (if available):

```bash
uv pip install -e .
```

1. Ensure Firefox is installed on your system, as the script uses Selenium with Firefox WebDriver.

## Configuration

Create a `.env` file in the project root directory with your MusicBrainz credentials:

```env
mb_user = "your_musicbrainz_username"
mb_pass = "your_musicbrainz_password"
```

If these are not set, the script will prompt for manual login during execution.

## Usage

1. Prepare a list of album URLs from supported streaming services. You can create a text file (e.g., `albums.txt`) with one URL per line.

2. Run the script with your desired options. For example, to process albums from a file with manual review enabled:

```bash
python src/main.py --urls-file albums.txt --manual-review
```

Or directly with URLs:

```bash
python src/main.py --urls "https://example.com/album/..." "https://example.com/album/..."
```

### Command-Line Options

- `--urls` or `--urls-file`: Specify album URLs from supported streaming services directly or from a file.
- `--pause-on-found`: Pause when an album is already linked to MusicBrainz.
- `--manual-review`: Require manual review before publishing releases.
- `--close-tabs`: Close processing tabs after each album.
- `--copy-id`: Copy MusicBrainz release IDs to clipboard.
- `--manual-labels`: Enable manual label selection for error fixing.

Run `python src/main.py --help` for a full list of options.

### Example Workflow

1. Collect album URLs from supported streaming services.
2. Run the script: `python src/main.py --urls-file my_albums.txt --manual-review --copy-id`
3. The script will open Firefox, log into MusicBrainz (if needed), process each album, handle ISRCs, cover art, and external links.
4. Review and publish releases as prompted.
5. MusicBrainz IDs are copied to clipboard for easy access.

## Project Structure

- `src/main.py`: Entry point for the application.
- `src/harmony_driver.py`: Core logic for Selenium automation and MusicBrainz interactions.
- `pyproject.toml`: Project configuration and dependencies.
- `ff_profile/`: Directory for storing Firefox profile data.
- `covers/`: Directory for downloaded cover art images.
- `screenshots/`: Directory for debug screenshots (if enabled).

## Troubleshooting

- **Login Issues**: Ensure your MusicBrainz credentials are correct in `.env`. The script saves the Firefox profile after login to avoid re-authentication.
- **Timeouts**: If Selenium actions timeout, the script may prompt for retry. Check your internet connection and MusicBrainz/Harmony site status.
- **Errors**: The script attempts to fix common errors (e.g., missing labels). For unhandled errors, manual intervention may be required.
- **Dependencies**: Ensure all Python packages are installed. Use `pip list` to verify.
- **Firefox**: Make sure Firefox is up-to-date and not running in headless mode (the script uses a visible browser).

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request. For major changes, open an issue first to discuss.

1. Fork the repo
2. Create a feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push: `git push origin feature-name`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is for personal use and automates interactions with third-party websites. Use responsibly and in accordance with the terms of service of MusicBrainz and Harmony. The authors are not responsible for any misuse or violations.
