# Laravel Bulk Project Installer

A Python-based GUI tool to automate the setup of multiple Laravel projects on Ubuntu/Debian systems. This application handles cloning, environment setup, PHP extension installation, Apache VirtualHosts, symlinking, and Composer dependencies automatically.

---

## 🌟 Features

- Add multiple Laravel projects with project name and Git repository URL.
- Automatically clone or pull the latest version of each project.
- Copy `.env.example` to `.env` if `.env` does not exist.
- Detect required PHP version from `composer.json` and switch PHP accordingly.
- Automatically install common PHP extensions (curl, dom, gd, mbstring, zip, xml, pdo, etc.).
- Create symlinks from project `public` folder to `/var/www/html/<project>`.
- Add projects to `/etc/hosts`.
- Configure Apache VirtualHosts for each project.
- Set proper file permissions and ownership.
- Bulk setup all added projects with a single click.

---

## 💻 How It Works

### Non-Technical

1. Enter the project name and Git repository URL.
2. Add multiple projects to the list.
3. Click **Setup All Projects**.
4. The tool will automatically:
    - Clone the repositories.
    - Configure environment files.
    - Install necessary PHP extensions and dependencies.
    - Set up Apache VirtualHosts.
    - Symlink project `public` directories.
    - Add host entries.
    - Set permissions.

### Technical

- Uses Python with Tkinter for GUI.
- Executes Git, Composer, and system commands.
- Detects required PHP version from `composer.json`.
- Installs missing PHP extensions using `apt` with `sudo`.
- Creates Apache `.conf` files for each project.
- Uses `sudo` only when necessary (e.g., `/etc/hosts`, symlinks, permissions, Apache reload).

---

## 🛠 Requirements

- Ubuntu/Debian-based system
- Python 3.x
- Tkinter (`sudo apt install python3-tk`)
- Git (`sudo apt install git`)
- Composer (`sudo apt install composer` or `/usr/local/bin/composer`)
- Apache2 (`sudo apt install apache2`)
- PHP (multiple versions supported)
- PHP-FPM (matching installed PHP versions)
- Sudo privileges

---

## ⚙️ Installation Steps

1. Clone this repository:
    ```bash
    git clone <your-repo-url> ~/laravel-bulk-installer
    cd ~/laravel-bulk-installer
    ```

2. Run the application:
    ```bash
    python3 app.py
    ```

3. Add your Laravel projects:
    - Application Name
    - Git Repository URL
    - Click **Add Project**

4. Once all projects are added, click **Setup All Projects**.

---

## 📂 What Happens During Setup

1. **Git clone or pull**: Ensures you have the latest project files.
2. **Copy `.env`**: If `.env` is missing, copy `.env.example`.
3. **PHP version detection**: Reads `composer.json` and sets the correct PHP version.
4. **Install PHP extensions**: Installs common Laravel-required extensions.
5. **Composer install**: Installs all dependencies.
6. **Symlink public folder**: Links `/var/www/<project>/public` to `/var/www/html/<project>`.
7. **Hosts update**: Adds `127.0.0.1 <project>.test` to `/etc/hosts`.
8. **Permissions**: Sets `775` permissions and ownership to `www-data:<user>`.
9. **Apache VirtualHost**: Creates `.conf`, enables site, and reloads Apache.

---

## ⚡ Tips

- Ensure SSH keys are properly configured for private repositories.
- Run the app as a normal user; `sudo` privileges are only required for system modifications.
- Install PHP versions and FPM modules beforehand if needed.
- Composer installation might be slow on the first run if PHP extensions are missing; the app installs them automatically.

---

## 🚀 Next Steps

- Open your browser and navigate to `http://<project>.test`.
- Update `.env` with database credentials or other environment variables.
- Run migrations if needed:
    ```bash
    php artisan migrate
    php artisan db:seed
    ```
- Install Laravel Passport or other package-specific setup commands as required.

---

## 📌 Notes

- Designed for Ubuntu/Debian only.
- The bulk setup ensures consistent environment configuration for multiple projects.

---

