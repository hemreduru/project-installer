#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$ROOT_DIR/build"
PKG_NAME="laravel-installer"
VERSION="$(python3 - <<'PY'
import tomllib
from pathlib import Path
data = tomllib.loads(Path("pyproject.toml").read_text())
print(data["project"]["version"])
PY
)"
PKG_ROOT="$BUILD_DIR/${PKG_NAME}_${VERSION}_amd64"
APP_ROOT="$PKG_ROOT/opt/laravel-installer"
LIB_DIR="$APP_ROOT/lib"

ensure_pip() {
  if python3 -m pip --version >/dev/null 2>&1; then
    return
  fi

  mkdir -p "$BUILD_DIR"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL https://bootstrap.pypa.io/get-pip.py -o "$BUILD_DIR/get-pip.py"
  elif command -v wget >/dev/null 2>&1; then
    wget -qO "$BUILD_DIR/get-pip.py" https://bootstrap.pypa.io/get-pip.py
  else
    echo "curl or wget is required to bootstrap pip." >&2
    exit 1
  fi

  python3 "$BUILD_DIR/get-pip.py" --user --break-system-packages
}

rm -rf "$PKG_ROOT"
mkdir -p "$APP_ROOT" "$PKG_ROOT/usr/bin" "$PKG_ROOT/usr/share/applications" "$PKG_ROOT/usr/share/icons/hicolor/scalable/apps" "$PKG_ROOT/usr/share/polkit-1/actions" "$PKG_ROOT/DEBIAN"

mkdir -p "$LIB_DIR"
ensure_pip
python3 -m pip install --user --upgrade pip --break-system-packages
python3 -m pip install --target "$LIB_DIR" "$ROOT_DIR" --break-system-packages

cp "$ROOT_DIR/laravel_installer/assets/laravel-installer.desktop" "$PKG_ROOT/usr/share/applications/"
cp "$ROOT_DIR/laravel_installer/assets/laravel-installer.svg" "$PKG_ROOT/usr/share/icons/hicolor/scalable/apps/"
cp "$ROOT_DIR/laravel_installer/polkit/com.emre.laravel-installer.policy" "$PKG_ROOT/usr/share/polkit-1/actions/"

cat > "$PKG_ROOT/usr/bin/laravel-installer" <<'SH'
#!/usr/bin/env bash
export PYTHONPATH=/opt/laravel-installer/lib${PYTHONPATH:+:$PYTHONPATH}
exec /usr/bin/python3 -m laravel_installer.main "$@"
SH
chmod 755 "$PKG_ROOT/usr/bin/laravel-installer"

mkdir -p "$PKG_ROOT/usr/lib/laravel-installer"
cat > "$PKG_ROOT/usr/lib/laravel-installer/laravel-installer-helper" <<'SH'
#!/usr/bin/env bash
export PYTHONPATH=/opt/laravel-installer/lib${PYTHONPATH:+:$PYTHONPATH}
exec /usr/bin/python3 -m laravel_installer.privileged_helper "$@"
SH
chmod 755 "$PKG_ROOT/usr/lib/laravel-installer/laravel-installer-helper"

cat > "$PKG_ROOT/DEBIAN/control" <<EOF
Package: $PKG_NAME
Version: $VERSION
Section: devel
Priority: optional
Architecture: amd64
Maintainer: Emre <noreply@example.com>
Depends: python3, python3-tk, policykit-1
Description: Desktop Laravel project installer for Ubuntu
 Automates Laravel project checkout, dependency setup and Apache publishing.
EOF

dpkg-deb --build "$PKG_ROOT"
echo "Built package: ${PKG_ROOT}.deb"
