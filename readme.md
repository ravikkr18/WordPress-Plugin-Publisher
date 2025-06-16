# WordPress Plugin Publisher

A Python tool to automate the publishing process for WordPress plugins. This script updates the plugin's version in both the header and a defined constant, creates a ZIP file with the correct folder structure, generates update metadata, and uploads files to Cloudflare R2 for distribution.

## Features

- **Version Management**: Automatically increments the plugin version (patch, minor, or major) in the plugin header (e.g., `Version: 1.0.0`) and a defined constant (e.g., `define('PLUGIN_VERSION', '1.0.0');`).
- **ZIP Creation**: Generates a ZIP file with the plugin files, ensuring the top-level folder matches the plugin slug (e.g., `my-plugin`).
- **Metadata Generation**: Updates `update.json` with version details, changelog, and download URLs for WordPress update checks.
- **Cloudflare R2 Integration**: Uploads the ZIP file and `update.json` to a Cloudflare R2 bucket for distribution.
- **Logging**: Provides detailed logs for debugging and tracking the publishing process.
- **Exclusion Rules**: Excludes compressed files (e.g., `.zip`, `.tar`), specified directories (e.g., `py`, `old`), and sensitive files (e.g., `.env`) from the ZIP.

## Prerequisites

- Python 3.8 or higher
- A Cloudflare R2 account with access keys and bucket configured
- A `.env` file with required environment variables (see [Configuration](#configuration))
- A WordPress plugin directory with a main PHP file containing a version header and constant

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/ravikkr18/wordpress-plugin-publisher.git
   cd wordpress-plugin-publisher
   ```

2. **Install Dependencies**:
   Install the required Python packages using pip:
   ```bash
   pip install semantic_version boto3 python-dotenv
   ```

3. **Set Up Environment Variables**:
   Create a `.env` file in the project root with the following variables:
   ```env
   R2_ACCESS_KEY_ID=your_r2_access_key
   R2_SECRET_ACCESS_KEY=your_r2_secret_key
   R2_ENDPOINT_URL=https://your_r2_endpoint_url
   R2_BUCKET_NAME=your_r2_bucket_name
   R2_PUBLIC_URL=https://your_r2_public_url
   PLUGIN_DOMAIN=https://your_plugin_domain
   ```
   Replace the values with your Cloudflare R2 and plugin domain details.

## Usage

1. **Prepare the Plugin Directory**:
   Ensure the plugin directory is ready with all necessary files (e.g., `my-plugin.php`, `includes/`, etc.). The directory name should match the plugin slug (e.g., `my-plugin`). The main PHP file must include:
   - A WordPress plugin header with a `Version` field (e.g., `Version: 1.0.0`).
   - A PHP constant for the version (e.g., `define('PLUGIN_VERSION', '1.0.0');`).
   See the [Sample Plugin File](#sample-plugin-file) for an example.

2. **Run the Script**:
   Execute the script from the root directory and follow the prompts:
   ```bash
   python publish.py
   ```

   **Prompts**:
   - **Plugin directory path**: Enter the absolute or relative path to the plugin directory (e.g., `/path/to/my-plugin` or `plugins/` for the sample plugin).
   - **Plugin slug**: Enter the plugin slug (e.g., `my-plugin`), which should match the directory name and main PHP file (e.g., `my-plugin.php`).
   - **Version increment**: Choose `patch`, `minor`, or `major` to increment the plugin version.
   - **Changelog**: Enter changelog items (one per line, press Enter twice to finish).
   - **Stable version**: Enter `y` or `n` to mark the version as stable.

3. **Script Actions**:
   - Updates the version in the main PHP file (header and constant).
   - Creates a ZIP file (e.g., `my-plugin-1.0.1.zip`) with the top-level folder matching the plugin slug.
   - Generates or updates `update.json` with version metadata.
   - Uploads the ZIP and `update.json` to the specified Cloudflare R2 bucket.

4. **Verify Output**:
   - Check the generated ZIP file to ensure it extracts to the plugin slug folder (e.g., `my-plugin/`).
   - Verify `update.json` contains the correct version details.
   - Review the console logs for success or error messages.

## Configuration

The script relies on environment variables defined in a `.env` file:

| Variable                | Description                                      | Example                              |
|-------------------------|--------------------------------------------------|--------------------------------------|
| `R2_ACCESS_KEY_ID`      | Cloudflare R2 access key ID                      | `abc123`                             |
| `R2_SECRET_ACCESS_KEY`  | Cloudflare R2 secret access key                  | `xyz789`                             |
| `R2_ENDPOINT_URL`       | R2 endpoint URL                                  | `https://<account>.r2.cloudflarestorage.com` |
| `R2_BUCKET_NAME`        | R2 bucket name                                   | `plugins`                            |
| `R2_PUBLIC_URL`         | Public URL for R2 bucket                         | `https://pub-<hash>.r2.dev`          |
| `PLUGIN_DOMAIN`         | Domain for plugin URLs (banners, icons, etc.)    | `https://yourdomain.com`             |

## Example

```bash
$ python publish.py
Enter the plugin directory path: plugins/
Enter the plugin slug: my-plugin
2025-06-16 17:21:34,123 - INFO - Current version: 1.0.0
Enter version increment (patch/minor/major): patch
2025-06-16 17:21:40,456 - INFO - New version: 1.0.1
Enter changelog (one item per line, enter blank line to finish):
Fixed minor bug
Improved performance

Mark this version as stable? (y/n): y
2025-06-16 17:21:50,789 - INFO - Updated plugin version to 1.0.1 in header and constant
2025-06-16 17:21:51,012 - INFO - Created zip file: my-plugin-1.0.1.zip with top-level folder my-plugin
2025-06-16 17:21:51,234 - INFO - Updated update.json
2025-06-16 17:21:51,456 - INFO - Marked version 1.0.1 as stable
2025-06-16 17:21:52,678 - INFO - Uploaded update.json to R2 bucket plugins
2025-06-16 17:21:53,890 - INFO - Uploaded my-plugin-1.0.1.zip to R2 bucket plugins
2025-06-16 17:21:54,123 - INFO - Publish complete! Version 1.0.1 uploaded to R2.
```

## Sample Plugin File

Below is an example of a WordPress plugin main PHP file (`my-plugin.php`) that the script can process:

```php
<?php
/**
 * Plugin Name: My Plugin
 * Plugin URI: https://yourdomain.com/my-plugin
 * Description: A sample WordPress plugin for demonstration purposes.
 * Version: 1.0.0
 * Author: Your Name
 * Author URI: https://yourdomain.com
 * Text Domain: my-plugin
 * Requires at least: 5.8
 * Requires PHP: 7.4
 */

if (!defined('ABSPATH')) {
    exit; // Prevent direct access
}

// Define plugin constants
define('PLUGIN_VERSION', '1.0.0');
define('PLUGIN_DIR', plugin_dir_path(__FILE__));
define('PLUGIN_URL', plugin_dir_url(__FILE__));

// Add your plugin functionality here
add_action('init', function () {
    // Example functionality: Register a custom post type
    register_post_type('my_custom_post', [
        'labels' => [
            'name' => __('My Custom Posts', 'my-plugin'),
            'singular_name' => __('My Custom Post', 'my-plugin'),
        ],
        'public' => true,
        'has_archive' => true,
        'supports' => ['title', 'editor', 'thumbnail'],
    ]);
});
```

The script will:
- Update `Version: 1.0.0` to the new version (e.g., `1.0.1`) in the header.
- Update `define('PLUGIN_VERSION', '1.0.0');` to match the new version.
- Create a ZIP file with the top-level folder `my-plugin`.

## Directory Structure

```
wordpress-plugin-publisher/
├── plugins/                # Sample plugin directory
│   └── my-plugin.php       # Sample plugin file
├── publish.py       # Main script
├── .env.example            # Example .env file
├── .gitignore              # Git ignore file
├── README.md               # This file
└── requirements.txt        # Python dependencies
```

## Contributing

Contributions are welcome! Please follow these steps:
1. Fork the repository.
2. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature
   ```
3. Commit your changes:
   ```bash
   git commit -m 'Add your feature'
   ```
4. Push to the branch:
   ```bash
   git push origin feature/your-feature
   ```
5. Open a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Support

For issues or questions, please open an issue on the [GitHub repository](https://github.com/ravikkr18/wordpress-plugin-publisher/issues) or contact the maintainer at cool18.ravi@gmail.com.

## Acknowledgments

- Built with [Python](https://www.python.org/), [boto3](https://boto3.amazonaws.com/), [semantic_version](https://python-semanticversion.readthedocs.io/), and [python-dotenv](https://saurabh-kumar.com/python-dotenv/).
- Thanks to the WordPress and Cloudflare communities for their documentation and tools.