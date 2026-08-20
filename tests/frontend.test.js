const assert = require('node:assert/strict');
const fs = require('node:fs');

const html = fs.readFileSync('index.html', 'utf8');
const inlineScripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];
assert.equal(inlineScripts.length, 1, 'expected one inline application script');

const scriptWithoutInit = inlineScripts[0][1].replace(/\s*init\(\);\s*$/, '');
const loadHelpers = new Function(
    `${scriptWithoutInit}\nreturn { parseDataTime, calculateCutoff, getFreshnessState };`
);
const { parseDataTime, calculateCutoff, getFreshnessState } = loadHelpers();

assert.equal(
    parseDataTime('2026/06/29 16:52').toISOString(),
    '2026-06-29T08:52:00.000Z',
    'legacy timestamp should be interpreted as Asia/Taipei'
);
assert.equal(
    parseDataTime('2026-08-20T13:19+08:00').toISOString(),
    '2026-08-20T05:19:00.000Z',
    'ISO timestamp should preserve its UTC offset'
);
assert.equal(parseDataTime('not-a-date'), null);

const now = new Date('2026-08-20T13:30:00+08:00');
assert.equal(calculateCutoff('近1週', now).toISOString(), '2026-08-13T05:30:00.000Z');
assert.equal(calculateCutoff('近1月', now).toISOString(), '2026-07-20T05:30:00.000Z');
assert.equal(calculateCutoff('近1年', now).toISOString(), '2025-08-20T05:30:00.000Z');
assert.equal(calculateCutoff('今年', now).toISOString(), '2025-12-31T16:00:00.000Z');

const fresh = getFreshnessState(new Date('2026-08-20T13:19:00+08:00'), now);
assert.equal(fresh.className, 'freshness-status fresh');
const stale = getFreshnessState(new Date(now.getTime() - 73 * 60 * 60 * 1000), now);
assert.equal(stale.className, 'freshness-status stale');
assert.match(stale.text, /73 小時未更新/);

console.log('Frontend date, range, and freshness tests passed');
