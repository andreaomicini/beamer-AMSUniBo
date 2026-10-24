#!/bin/sh
# shoot.sh <firefox|webkit> <deck.html> <outdir> <pages> [scale] -- one 1024x768 PNG per page, s-01.png ...
# firefox: the Firefox cask through geckodriver; webkit: Playwright's WebKit from playwright-cli
exec python3 "$(dirname "$0")/browser.py" shoot "$@"
