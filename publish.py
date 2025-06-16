import os
import re
import json
import zipfile
import logging
import datetime
from pathlib import Path
from dotenv import load_dotenv
import boto3
import semantic_version
from urllib.parse import urljoin

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
R2_ACCESS_KEY = os.getenv('R2_ACCESS_KEY_ID')
R2_SECRET_KEY = os.getenv('R2_SECRET_ACCESS_KEY')
R2_ENDPOINT_URL = os.getenv('R2_ENDPOINT_URL')
R2_BUCKET_NAME = os.getenv('R2_BUCKET_NAME')
R2_PUBLIC_URL = os.getenv('R2_PUBLIC_URL')
PLUGIN_DOMAIN = os.getenv('PLUGIN_DOMAIN')

# Validate environment variables
required_env = {
    'R2_ACCESS_KEY_ID': R2_ACCESS_KEY,
    'R2_SECRET_ACCESS_KEY': R2_SECRET_KEY,
    'R2_ENDPOINT_URL': R2_ENDPOINT_URL,
    'R2_BUCKET_NAME': R2_BUCKET_NAME,
    'R2_PUBLIC_URL': R2_PUBLIC_URL,
    'PLUGIN_DOMAIN': PLUGIN_DOMAIN,
}
for key, value in required_env.items():
    if not value:
        logger.error(f"Missing environment variable: {key}")
        exit(1)

# Plugin constants
EXCLUDE_EXTENSIONS = {'.zip', '.tar', '.gz', '.tgz', '.bz2', '.rar', '.7z'}
EXCLUDE_DIRS = {'py', 'old'}

def get_current_version(plugin_dir, plugin_file):
    """Read the current version from the plugin's main file."""
    try:
        with plugin_file.open('r', encoding='utf-8') as f:
            content = f.read()
            match = re.search(r'Version:\s*([\d.]+)', content)
            if not match:
                logger.error("Could not find version in plugin file")
                exit(1)
            return semantic_version.Version(match.group(1))
    except FileNotFoundError:
        logger.error(f"Plugin file not found: {plugin_file}")
        exit(1)

def update_plugin_version(plugin_file, new_version):
    """Update the version in the plugin's main file and constant."""
    try:
        with plugin_file.open('r', encoding='utf-8') as f:
            content = f.read()
        # Update Version in plugin header
        content = re.sub(r'(Version:\s*)[\d.]+', f'\\g<1>{new_version}', content)
        # Update HSPORTAL_PLUGIN_VERSION constant
        content = re.sub(
            r"(define\s*\(\s*'HSPORTAL_PLUGIN_VERSION'\s*,\s*')[\d.]+(')",
            f"\\g<1>{new_version}\\g<2>",
            content
        )
        with plugin_file.open('w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Updated plugin version to {new_version} in header and constant")
    except Exception as e:
        logger.error(f"Failed to update plugin version: {e}")
        exit(1)

def create_zip(plugin_dir, plugin_slug, new_version):
    """Create a zip file of the plugin with correct folder name, excluding compressed files and specified directories."""
    zip_name = f"{plugin_slug}-{new_version}.zip"
    zip_path = plugin_dir / zip_name
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(plugin_dir):
                root_path = Path(root)
                # Skip excluded directories
                if any(part in EXCLUDE_DIRS for part in root_path.parts):
                    continue
                # Handle logs directory specially
                if 'logs' in root_path.parts:
                    # Include the logs directory itself (empty)
                    if root_path.name == 'logs':
                        arcname = Path(plugin_slug) / root_path.relative_to(plugin_dir)
                        zf.write(root_path, arcname)
                    continue
                for file in files:
                    file_path = root_path / file
                    # Skip files in logs directory and excluded extensions
                    if 'logs' in file_path.parts or file_path.suffix.lower() in EXCLUDE_EXTENSIONS or file == '.env':
                        continue
                    # Use plugin_slug as the top-level directory in the ZIP
                    arcname = Path(plugin_slug) / file_path.relative_to(plugin_dir)
                    zf.write(file_path, arcname)
        logger.info(f"Created zip file: {zip_name} with top-level folder {plugin_slug}")
        return zip_name
    except Exception as e:
        logger.error(f"Failed to create zip file: {e}")
        exit(1)

def update_metadata(plugin_dir, plugin_slug, new_version, zip_name, changelog, is_stable):
    """Update update.json to include new version metadata."""
    update_json_path = plugin_dir / 'update.json'
    today = datetime.date.today().isoformat()
    new_version_data = {
        'version': str(new_version),
        'download_url': f"{R2_PUBLIC_URL.rstrip('/')}/{R2_BUCKET_NAME.strip('/')}/{zip_name.lstrip('/')}",
        'plugin_url': f"{PLUGIN_DOMAIN}/{plugin_slug}",
        'last_updated': today,
        'changelog': f"<h4>{new_version}</h4><ul>{changelog}</ul>",
        'requires': '5.8',
        'tested': '6.6',
        'requires_php': '7.4',
        'banners': {
            'low': f"{PLUGIN_DOMAIN}/updates/banners/low.jpg",
            'high': f"{PLUGIN_DOMAIN}/updates/banners/high.jpg"
        },
        'icons': {
            '1x': f"{PLUGIN_DOMAIN}/updates/icons/icon-128x128.png",
            '2x': f"{PLUGIN_DOMAIN}/updates/icons/icon-256x256.png"
        }
    }

    # Load existing update.json or create new
    metadata = {'plugin': plugin_slug, 'versions': []}
    try:
        if os.path.exists(update_json_path):
            with open(update_json_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
    except json.JSONDecodeError:
        logger.warning("Existing update.json is invalid, creating new.")

    # Remove existing entry for this version (if any)
    metadata['versions'] = [v for v in metadata['versions'] if v['version'] != str(new_version)]
    metadata['versions'].append(new_version_data)

    # Sort versions by semantic version (descending)
    metadata['versions'].sort(key=lambda x: semantic_version.Version(x['version']), reverse=True)

    try:
        with open(update_json_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        logger.info("Updated update.json")
    except Exception as e:
        logger.error(f"Failed to update update.json: {e}")
        exit(1)

    # Update stable version if marked
    if is_stable:
        metadata['stable_version'] = str(new_version)
        with open(update_json_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"Marked version {new_version} as stable")

def upload_to_r2(files):
    """Upload files to Cloudflare R2."""
    try:
        session = boto3.session.Session()
        s3_client = session.client(
            's3',
            endpoint_url=R2_ENDPOINT_URL,
            aws_access_key_id=R2_ACCESS_KEY,
            aws_secret_access_key=R2_SECRET_KEY
        )
        for file_path in files:
            file_name = Path(file_path).name
            with open(file_path, 'rb') as f:
                s3_client.upload_fileobj(
                    f,
                    R2_BUCKET_NAME,
                    file_name,
                    ExtraArgs={'ContentType': 'application/json' if file_name.endswith('.json') else 'application/zip'}
                )
            logger.info(f"Uploaded {file_name} to R2 bucket {R2_BUCKET_NAME}")
    except Exception as e:
        logger.error(f"Failed to upload to R2: {e}")
        exit(1)

def main():
    """Main function to automate the publish process."""
    # Prompt for plugin directory
    plugin_path = input("Enter the plugin directory path: ").strip()
    plugin_dir = Path(plugin_path).resolve()
    
    if not plugin_dir.exists():
        logger.error(f"Plugin directory does not exist: {plugin_dir}")
        exit(1)

    plugin_file = plugin_dir / 'hsportal-youtube-upload.php'
    plugin_slug = 'hsportal-youtube-upload'

    # Get current version
    current_version = get_current_version(plugin_dir, plugin_file)
    logger.info(f"Current version: {current_version}")

    # Prompt for version increment
    increment = input("Enter version increment (patch/minor/major): ").strip().lower()
    if increment not in ['patch', 'minor', 'major']:
        logger.error("Invalid increment type. Use patch, minor, or major.")
        exit(1)

    # Calculate new version
    if increment == 'patch':
        new_version = current_version.next_patch()
    elif increment == 'minor':
        new_version = current_version.next_minor()
    else:  # major
        new_version = current_version.next_major()

    logger.info(f"New version: {new_version}")

    # Prompt for changelog
    print("Enter changelog (one item per line, enter blank line to finish):")
    changelog_items = []
    while True:
        line = input().strip()
        if not line:
            break
        changelog_items.append(f"<li>{line}</li>")
    if not changelog_items:
        logger.error("Changelog cannot be empty.")
        exit(1)
    changelog = ''.join(changelog_items)

    # Prompt for stable version
    is_stable = input("Mark this version as stable? (y/n): ").strip().lower() == 'y'

    # Update plugin version
    update_plugin_version(plugin_file, new_version)

    # Create zip file
    zip_name = create_zip(plugin_dir, plugin_slug, new_version)

    # Update metadata
    update_metadata(plugin_dir, plugin_slug, new_version, zip_name, changelog, is_stable)

    # Upload to R2
    upload_to_r2([plugin_dir / 'update.json', plugin_dir / zip_name])

    logger.info(f"Publish complete! Version {new_version} uploaded to R2.")

if __name__ == '__main__':
    main()