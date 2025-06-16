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