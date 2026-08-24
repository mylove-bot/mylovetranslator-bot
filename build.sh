#!/usr/bin/env bash
set -e

echo "========================================"
echo "Installing Python dependencies"
echo "========================================"

pip install --upgrade pip
pip install -r requirements.txt

echo "========================================"
echo "Installing Argos translation packages"
echo "========================================"

python - <<'PY'
import argostranslate.package

print("Updating Argos package index...")

argostranslate.package.update_package_index()

available = argostranslate.package.get_available_packages()

wanted = {
    ("en", "ru"),
    ("en", "tr"),
    ("ru", "en"),
    ("tr", "en"),
}

installed = set()

for package in available:
    pair = (package.from_code, package.to_code)

    if pair in wanted and pair not in installed:
        print(
            f"Installing Argos model: "
            f"{package.from_code} -> {package.to_code}"
        )

        path = package.download()
        argostranslate.package.install_from_path(path)

        installed.add(pair)

print("========================================")
print("Installed translation models:")
print(installed)
print("========================================")

required = {
    ("en", "ru"),
    ("en", "tr"),
    ("ru", "en"),
    ("tr", "en"),
}

missing = required - installed

if missing:
    print("WARNING: Missing models:", missing)
else:
    print("All required translation models installed.")
PY

echo "========================================"
echo "Build completed successfully"
echo "========================================"
