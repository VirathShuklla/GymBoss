#!/usr/bin/env bash
# Builds the store (Capacitor) bundle and syncs it into the android/ and ios/ projects.
# Usage: REACT_APP_BACKEND_URL=https://api.gymboss.in ./scripts/build-mobile.sh
set -euo pipefail
cd "$(dirname "$0")/.."
: "${REACT_APP_BACKEND_URL:?Set REACT_APP_BACKEND_URL to your production API origin (e.g. https://gymboss.in)}"
export REACT_APP_STORE_BUILD=true
export GENERATE_SOURCEMAP=false
yarn build
[ -d android ] || npx cap add android
[ -d ios ] || npx cap add ios
npx cap sync
echo "Done. Android: cd android && ./gradlew bundleRelease (AAB) or assembleDebug (APK). iOS: npx cap open ios (Xcode, macOS only)."
