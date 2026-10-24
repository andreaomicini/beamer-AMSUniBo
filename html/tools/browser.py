"""browser.py -- the two engines the checks run in, from Homebrew only, behind one interface.

firefox: the Firefox cask, headless, through geckodriver (WebDriver over plain HTTP)
webkit:  Playwright's WebKit, through the Node library in the playwright-cli formula

    with Browser('webkit', 1024, 768) as b:
        b.goto(url); b.eval(js); b.shot(png)

As a command: browser.py shoot <engine> <deck.html> <outdir> <pages> [scale] -- s-01.png ...
"""
import base64, json, os, socket, subprocess, sys, time, urllib.request
from pathlib import Path

PWCLI = os.environ.get('PLAYWRIGHT_CLI', '/opt/homebrew/opt/playwright-cli/libexec/lib/node_modules/@playwright/cli')
NODE = os.environ.get('NODE', '/opt/homebrew/bin/node')
GECKO = os.environ.get('GECKODRIVER', '/opt/homebrew/bin/geckodriver')

# a function is called, anything else is returned, as Playwright's evaluate does
WRAP = 'const __v = ({js}); return typeof __v === "function" ? __v() : __v;'

BRIDGE = r'''
import { createRequire } from 'module';
import * as readline from 'readline';
const require = createRequire(process.argv[1] + '/package.json');
const { webkit } = require('playwright-core');
const [w, h, s] = process.argv.slice(2).map(Number);
const b = await webkit.launch();
const pg = await b.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: s });
const out = v => process.stdout.write(JSON.stringify(v === undefined ? null : v) + '\n');
for await (const line of readline.createInterface({ input: process.stdin })) {
  const c = JSON.parse(line);
  try {
    if (c.op === 'goto') { await pg.goto(c.url); out(null); }
    else if (c.op === 'eval') out(await pg.evaluate(new Function(c.body)));
    else if (c.op === 'shot') { await pg.screenshot({ path: c.path }); out(null); }
    else if (c.op === 'quit') { await b.close(); out(null); process.exit(0); }
  } catch (e) { out({ __error: String(e) }); }
}
'''


class Browser:
    def __init__(self, engine, width=1024, height=768, scale=1):
        self.engine, self.w, self.h, self.s = engine, width, height, scale
        if engine not in ('firefox', 'webkit'):
            raise SystemExit('browser.py: engine is firefox or webkit')

    def __enter__(self):
        if self.engine == 'webkit':
            self.p = subprocess.Popen([NODE, '--input-type=module', '-e', BRIDGE, PWCLI, str(self.w), str(self.h), str(self.s)],
                                      stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        else:
            with socket.socket() as k:
                k.bind(('127.0.0.1', 0)); self.port = k.getsockname()[1]
            self.p = subprocess.Popen([GECKO, '--port', str(self.port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for _ in range(100):
                try:
                    self._wd('GET', '/status'); break
                except OSError:
                    time.sleep(0.05)
            opts = {'args': ['-headless', f'--width={self.w}', f'--height={self.h}'],
                    'prefs': {'layout.css.devPixelsPerPx': str(self.s)}}
            self.sid = self._wd('POST', '/session', {'capabilities': {'alwaysMatch': {'moz:firefoxOptions': opts}}})['sessionId']
            # the window counts the browser's chrome, headless too: grow it until the viewport fits
            self._wd('POST', f'/session/{self.sid}/window/rect', {'width': self.w, 'height': self.h})
            iw, ih = self.eval('[innerWidth, innerHeight]')
            self._wd('POST', f'/session/{self.sid}/window/rect', {'width': 2 * self.w - iw, 'height': 2 * self.h - ih})
        return self

    def __exit__(self, *a):
        if self.engine == 'webkit':
            self._pw({'op': 'quit'}); self.p.wait()
        else:
            self._wd('DELETE', f'/session/{self.sid}'); self.p.terminate(); self.p.wait()

    def _wd(self, method, path, body=None):
        r = urllib.request.Request(f'http://127.0.0.1:{self.port}{path}', method=method,
                                   data=None if body is None else json.dumps(body).encode(),
                                   headers={'Content-Type': 'application/json'})
        return json.load(urllib.request.urlopen(r, timeout=120))['value']

    def _pw(self, cmd):
        self.p.stdin.write(json.dumps(cmd) + '\n'); self.p.stdin.flush()
        v = json.loads(self.p.stdout.readline())
        if isinstance(v, dict) and '__error' in v:
            raise RuntimeError(v['__error'])
        return v

    def goto(self, url):
        if self.engine == 'webkit':
            self._pw({'op': 'goto', 'url': url})
        else:
            self._wd('POST', f'/session/{self.sid}/url', {'url': url})

    def eval(self, js):
        body = WRAP.format(js=js)
        if self.engine == 'webkit':
            return self._pw({'op': 'eval', 'body': body})
        return self._wd('POST', f'/session/{self.sid}/execute/sync', {'script': body, 'args': []})

    def wait(self, ms):
        time.sleep(ms / 1000)

    def shot(self, path):
        if self.engine == 'webkit':
            self._pw({'op': 'shot', 'path': str(path)})
        else:
            Path(path).write_bytes(base64.b64decode(self._wd('GET', f'/session/{self.sid}/screenshot')))


if __name__ == '__main__' and len(sys.argv) >= 6 and sys.argv[1] == 'shoot':
    eng, page, out, n = sys.argv[2], Path(sys.argv[3]).resolve(), Path(sys.argv[4]).resolve(), int(sys.argv[5])
    scale = float(sys.argv[6]) if len(sys.argv) > 6 else 1
    out.mkdir(parents=True, exist_ok=True)
    with Browser(eng, 1024, 768, scale) as b:
        b.goto(page.as_uri() + '#1'); b.wait(500)
        for i in range(1, n + 1):
            b.eval(f'location.hash = "#{i}"'); b.wait(400)
            b.shot(out / f's-{i:02d}.png')
elif __name__ == '__main__':
    print(__doc__.strip().splitlines()[-1], file=sys.stderr); sys.exit(2)
