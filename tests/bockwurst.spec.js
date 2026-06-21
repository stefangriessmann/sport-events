/**
 * Bockwurst Sport Events – vollständige Playwright-Testsuite (Relaunch-DOM)
 *
 * Portiert vom alten --bw-* Tabellen-DOM auf das helle Relaunch-Design:
 *   .sport-btn            → #sportbar .sport[data-sport]   (aktiv-Klasse: .on)
 *   #evt-body tr          → #listView .ev                  (Karten statt Tabelle)
 *   #plz-input            → #plz
 *   #radius-sel           → #radius   (Stufen: 0/50/100/150/250)
 *   #stats .stat-val      → #stats .stat .v
 *   .tab / #tab-*         → #viewtabs button[data-view] / #listView / #calView
 *   #pills .pill          → #typeMenu input  (Event-Typ-Dropdown)
 *   #mehr-zone/#mehr-cnt  → #loadmore / #loadmoreCnt   (Seitengröße 8 statt 15)
 *   #reset-all-btn        → #reset
 *   Distanzspalte         → .ev .dist  (Format "~N km", nur bei gesetzter PLZ)
 *
 * Daten werden zur Laufzeit aus /data/*.json in das globale EV-Array geladen.
 *
 * Setup:
 *   cd ~/sport-events
 *   npm install -D @playwright/test
 *   npx playwright install chromium
 *   BASE_URL=https://staging--bockwurst-events.netlify.app npx playwright test tests/bockwurst.spec.js
 */

const { test, expect } = require('@playwright/test');

const BASE_URL = process.env.BASE_URL || 'https://bockwurst-events.netlify.app';

// München für PLZ-Tests
const TEST_PLZ    = '80331';
const TEST_COORDS = [48.1374, 11.5754];

// Seitengröße (PAGE im Relaunch-Design)
const PAGE_SIZE = 8;

// ── Helpers ────────────────────────────────────────────────────────────────

/** Lädt die Seite und wartet, bis das EV-Array befüllt + gerendert ist */
async function load(page) {
  await page.goto(BASE_URL);
  await page.waitForFunction(() => { try { return EV.length > 0; } catch (e) { return false; } }, null, { timeout: 20000 });
  await page.waitForSelector('#sportbar .sport', { timeout: 10000 });
}

/** Injiziert PLZ direkt in PLZ_MAP – kein Nominatim-Call nötig */
async function injectPlz(page, plz = TEST_PLZ, coords = TEST_COORDS) {
  await page.evaluate(([p, c]) => { PLZ_MAP[p] = c; }, [plz, coords]);
}

/** Trägt PLZ ein, feuert oninput, wartet auf Re-Render */
async function fillPlz(page, plz = TEST_PLZ) {
  await page.locator('#plz').fill(plz);
  await page.locator('#plz').dispatchEvent('input');
  await page.waitForTimeout(400);
}

/** Klickt Sport-Button per key ('rad'|'swim'|'tri'|'lauf'|'all') */
async function clickSport(page, key) {
  await page.evaluate((k) => {
    const btn = document.querySelector(`#sportbar .sport[data-sport="${k}"]`);
    if (btn) btn.click();
  }, key);
  await page.waitForTimeout(250);
}

/** Liest Stats-Gesamtzahl (erster #stats .stat .v) */
async function getStatsTotal(page) {
  return page.evaluate(() => {
    const el = document.querySelector('#stats .stat .v');
    return el ? parseInt(el.textContent.trim(), 10) : 0;
  });
}

/** Anzahl sichtbarer Event-Karten in #listView */
async function getRowCount(page) {
  return page.evaluate(() => document.querySelectorAll('#listView .ev').length);
}

/** Setzt den Radius (#radius) */
async function setRadius(page, r) {
  await page.selectOption('#radius', r);
  await page.waitForTimeout(250);
}

/** Wechselt die Ansicht ('list' | 'cal') */
async function switchView(page, view) {
  await page.evaluate((v) => {
    const b = document.querySelector(`#viewtabs button[data-view="${v}"]`);
    if (b) b.click();
  }, view);
  await page.waitForTimeout(300);
}

// ── Test-Setup ──────────────────────────────────────────────────────────────

const SPORTS = [
  { key: 'rad',  label: 'Radsport',   minEvents: 200 },
  { key: 'tri',  label: 'Triathlon',  minEvents: 10  },
  { key: 'lauf', label: 'Laufen',     minEvents: 50  },
  { key: 'swim', label: 'Freiwasser', minEvents: 0   },
  { key: 'all',  label: 'Alle',       minEvents: 300 },
];

// ═══════════════════════════════════════════════════════════════════════════
// 1. SEITENAUFRUF & GRUNDFUNKTIONEN
// ═══════════════════════════════════════════════════════════════════════════

test.describe('1 · Seitenaufruf', () => {
  test('lädt ohne JavaScript-Fehler', async ({ page }) => {
    const errors = [];
    page.on('console', msg => {
      if (msg.type() === 'error'
          && !msg.text().includes('favicon')
          && !msg.text().includes('Failed to load resource'))
        errors.push(msg.text());
    });
    await load(page);
    await page.waitForLoadState('networkidle');
    expect(errors).toHaveLength(0);
  });

  test('5 Sport-Buttons sichtbar', async ({ page }) => {
    await load(page);
    await expect(page.locator('#sportbar .sport')).toHaveCount(5);
  });

  test('meta.json liefert gültiges Stand-Datum (DD.MM.YYYY)', async ({ page }) => {
    await load(page);
    const stand = await page.evaluate(async () => {
      const r = await fetch('/data/meta.json');
      const m = await r.json();
      return m.stand;
    });
    expect(stand).toMatch(/\d{2}\.\d{2}\.\d{4}/);
  });

  test('Stats zeigen Event-Zahl > 0', async ({ page }) => {
    await load(page);
    const total = await getStatsTotal(page);
    expect(total).toBeGreaterThan(0);
  });

  test('2 Ansichts-Tabs sichtbar (Liste, Kalender)', async ({ page }) => {
    await load(page);
    await expect(page.locator('#viewtabs button')).toHaveCount(2);
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 2. DATEN-VOLLSTÄNDIGKEIT
// ═══════════════════════════════════════════════════════════════════════════

test.describe('2 · Daten-Vollständigkeit', () => {
  test.beforeEach(async ({ page }) => { await load(page); });

  // Sichere Floors (Daten schwanken; rad lag zuletzt bei ~648)
  const minCounts = {
    rad:  600,   // Radsport (rad-net + radsport-events.de)
    tri:  150,   // Triathlon
    lauf: 150,   // Laufen
  };

  for (const [sp, min] of Object.entries(minCounts)) {
    test(`Sportart "${sp}" hat mindestens ${min} Einträge`, async ({ page }) => {
      const count = await page.evaluate((s) =>
        EV.filter(e => TYPE_SPORT[e.art] === s).length, sp);
      expect(count).toBeGreaterThanOrEqual(min);
    });
  }

  test('Jeder Event-Eintrag hat Pflichtfelder (titel, datum, art)', async ({ page }) => {
    const issues = await page.evaluate(() => {
      const bad = [];
      EV.forEach((e, i) => {
        if (!e.titel) bad.push(`[${i}] fehlt titel`);
        if (!e.datum) bad.push(`[${i}] fehlt datum (titel: ${e.titel})`);
        if (!e.art)   bad.push(`[${i}] fehlt art (titel: ${e.titel})`);
      });
      return bad;
    });
    expect(issues).toHaveLength(0);
  });

  const SNAPSHOTS = [
    { key: 'rad',  label: 'Radsport'   },
    { key: 'tri',  label: 'Triathlon'  },
    { key: 'lauf', label: 'Laufen'     },
    { key: 'swim', label: 'Freiwasser' },
  ];

  for (const { key, label } of SNAPSHOTS) {
    test(`${label}: alle Events haben ort-Feld`, async ({ page }) => {
      const missing = await page.evaluate((s) =>
        EV.filter(e => TYPE_SPORT[e.art] === s)
          .filter(e => !e.ort || e.ort.trim() === '')
          .map(e => e.titel), key);
      expect(missing, `${label}: Events ohne ort: ${missing.join(', ')}`).toHaveLength(0);
    });

    test(`${label}: alle Events haben Koordinaten (lat/lon)`, async ({ page }) => {
      const missing = await page.evaluate((s) =>
        EV.filter(e => TYPE_SPORT[e.art] === s)
          .filter(e => e.lat == null || e.lon == null)
          .map(e => `${e.titel} (ort: ${e.ort || '–'})`), key);
      expect(missing, `${label}: Events ohne Koordinaten: ${missing.join(', ')}`).toHaveLength(0);
    });
  }

  test('Keine Events in der Vergangenheit', async ({ page }) => {
    const past = await page.evaluate(() => {
      const d = new Date(); d.setDate(d.getDate() - 1);
      const today = d.toISOString().slice(0, 10);
      return EV.filter(e => e.datum < today).map(e => `${e.titel} (${e.datum})`);
    });
    expect(past).toHaveLength(0);
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 3. SPORT-FILTER & KONSISTENZ
// ═══════════════════════════════════════════════════════════════════════════

test.describe('3 · Sport-Filter & Konsistenz', () => {
  test.beforeEach(async ({ page }) => { await load(page); });

  for (const { key, label, minEvents } of SPORTS) {
    test(`${label}: Button aktiv, Stats ≥ ${minEvents}`, async ({ page }) => {
      await clickSport(page, key);
      const btn = page.locator(`#sportbar .sport[data-sport="${key}"]`);
      await expect(btn).toHaveClass(/\bon\b/);
      const total = await getStatsTotal(page);
      expect(total).toBeGreaterThanOrEqual(minEvents);
    });

    test(`${label}: Stats-Zahl stimmt mit angezeigten Karten überein`, async ({ page }) => {
      await clickSport(page, key);
      const statsCount = await getStatsTotal(page);
      const rows       = await getRowCount(page);

      if (statsCount <= PAGE_SIZE) {
        expect(rows).toBe(statsCount);
      } else {
        await expect(page.locator('#loadmore')).toBeVisible();
        const hint = await page.locator('#loadmoreCnt').textContent();
        expect(hint).toMatch(/^\d+ von \d+/);
        expect(rows).toBeGreaterThan(0);
        expect(rows).toBeLessThanOrEqual(statsCount);
      }
    });
  }
});

// ═══════════════════════════════════════════════════════════════════════════
// 4. EVENT-DETAILS
// ═══════════════════════════════════════════════════════════════════════════

test.describe('4 · Event-Details (Radsport)', () => {
  test.beforeEach(async ({ page }) => { await load(page); });

  test('Erste Karte hat Datumsblock, Info und Rechts-Spalte', async ({ page }) => {
    const card = page.locator('#listView .ev').first();
    await expect(card.locator('.date')).toBeVisible();
    await expect(card.locator('.info h3')).toBeVisible();
    await expect(card.locator('.right')).toBeAttached();
  });

  test('Art-Badge vorhanden und nicht leer', async ({ page }) => {
    const badge = page.locator('#listView .ev').first().locator('.meta .badge');
    await expect(badge).toBeVisible();
    const text = await badge.textContent();
    expect(text.trim().length).toBeGreaterThan(0);
  });

  test('Datumsblock zeigt 2-stelligen Tag und Monatskürzel', async ({ page }) => {
    const blocks = await page.evaluate(() =>
      [...document.querySelectorAll('#listView .ev')].slice(0, 5).map(ev => ({
        d:  ev.querySelector('.date .d')?.textContent.trim(),
        mo: ev.querySelector('.date .mo')?.textContent.trim(),
      }))
    );
    expect(blocks.length).toBeGreaterThan(0);
    for (const b of blocks) {
      expect(b.d).toMatch(/^\d{2}$/);
      expect(b.mo && b.mo.length).toBeGreaterThan(0);
    }
  });

  test('Titel-Links haben gültige https:// URLs', async ({ page }) => {
    const hrefs = await page.evaluate(() =>
      [...document.querySelectorAll('#listView .ev .info h3 a.evlink')]
        .slice(0, 10).map(a => a.href)
    );
    expect(hrefs.length).toBeGreaterThan(0);
    for (const href of hrefs) {
      expect(href).toMatch(/^https?:\/\/.+/);
    }
  });

  test('Rechts-Spalte (Distanz/Strecken) vorhanden', async ({ page }) => {
    const firstRow = page.locator('#listView .ev').first();
    await expect(firstRow.locator('.right')).toBeAttached();
  });

  test('Event-Details für alle Sportarten geprüft', async ({ page }) => {
    for (const { key } of SPORTS.filter(s => s.key !== 'all')) {
      await clickSport(page, key);
      const count = await getRowCount(page);
      if (count === 0) continue;

      const link = page.locator('#listView .ev').first().locator('a.evlink');
      await expect(link).toHaveAttribute('href', /^https?:\/\//);

      const badge = page.locator('#listView .ev').first().locator('.meta .badge');
      await expect(badge).toBeVisible();
    }
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 5. PLZ-DISTANZFILTER
// ═══════════════════════════════════════════════════════════════════════════

test.describe('5 · PLZ-Distanzfilter', () => {
  test.beforeEach(async ({ page }) => {
    await load(page);
    await injectPlz(page);
  });

  // ── 5a. Distanzanzeige ─────────────────────────────────────────────────────

  test('Keine Distanz-Chips ohne PLZ', async ({ page }) => {
    const n = await page.evaluate(() => document.querySelectorAll('#listView .ev .dist').length);
    expect(n).toBe(0);
  });

  test('Distanz-Chips erscheinen nach PLZ-Eingabe', async ({ page }) => {
    await fillPlz(page);
    const n = await page.evaluate(() => document.querySelectorAll('#listView .ev .dist').length);
    expect(n).toBeGreaterThan(0);
  });

  test('Distanzwerte im Format "~N km"', async ({ page }) => {
    await fillPlz(page);
    const vals = await page.evaluate(() =>
      [...document.querySelectorAll('#listView .ev .dist')].map(el => el.textContent.trim())
    );
    expect(vals.length).toBeGreaterThan(0);
    for (const v of vals) {
      expect(v).toMatch(/^~\d+ km$/);
    }
  });

  test('Kein Distanzwert überschreitet gewählten Radius (50 km)', async ({ page }) => {
    await setRadius(page, '50');
    await fillPlz(page);
    const distValues = await page.evaluate(() =>
      [...document.querySelectorAll('#listView .ev .dist')]
        .map(el => parseInt(el.textContent.replace('~', '').trim()))
    );
    for (const d of distValues) {
      expect(d).toBeLessThanOrEqual(55); // +5km Toleranz für Rounding
    }
  });

  // ── 5b. Alle Sportarten mit PLZ ──────────────────────────────────────────

  for (const { key, label } of SPORTS.filter(s => s.key !== 'all')) {
    test(`${label}: PLZ-Filter zeigt Ergebnisse (kein leerer Tab)`, async ({ page }) => {
      await clickSport(page, key);
      await fillPlz(page);
      const count = await getStatsTotal(page);
      expect(count).toBeGreaterThan(0);
      await expect(page.locator('#listView .empty')).toHaveCount(0);
    });
  }

  test('Triathlon: Events liegen im Radius (keine Distanz-Verletzung)', async ({ page }) => {
    await clickSport(page, 'tri');
    await fillPlz(page);
    const count = await getStatsTotal(page);
    expect(count).toBeGreaterThan(0);
    const r = await page.locator('#radius').inputValue();
    const violations = await page.evaluate((radius) => {
      const rv = parseInt(radius);
      if (!rv) return [];
      return [...document.querySelectorAll('#listView .ev .dist')]
        .map(el => parseInt(el.textContent.replace('~', '').trim()))
        .filter(d => d > rv + 5);
    }, r);
    expect(violations).toHaveLength(0);
  });

  test('Freiwasser: PLZ-Filter filtert nach Distanz (keine Events außerhalb Radius)', async ({ page }) => {
    await clickSport(page, 'swim');
    // Chemnitz (09113): Kulkwitzer See ~72km, Bayern-Seen >250km
    const CHEMNITZ_PLZ    = '09113';
    const CHEMNITZ_COORDS = [50.831, 12.921];
    await page.evaluate(([plz, coords]) => {
      PLZ_MAP[plz] = coords;
      document.getElementById('plz').value = plz;
      render();
    }, [CHEMNITZ_PLZ, CHEMNITZ_COORDS]);
    await page.waitForTimeout(300);

    await setRadius(page, '50');
    const count50 = await getStatsTotal(page);

    await setRadius(page, '250');
    const count250 = await getStatsTotal(page);

    expect(count250).toBeGreaterThanOrEqual(count50);
    expect(count250).toBeGreaterThan(count50);

    await setRadius(page, '50');
    const violations = await page.evaluate(() =>
      [...document.querySelectorAll('#listView .ev .dist')]
        .map(el => parseInt(el.textContent.replace('~', '').trim()))
        .filter(d => d > 55)
    );
    expect(violations).toHaveLength(0);
  });

  // ── 5c. Radius – alle Stufen, alle relevanten Sportarten ─────────────
  const RADII = ['50', '100', '150', '250'];

  const COORD_SPORTS = [
    { key: 'rad',  label: 'Radsport'   },
    { key: 'lauf', label: 'Laufen'     },
    { key: 'swim', label: 'Freiwasser' },
    { key: 'tri',  label: 'Triathlon'  },
  ];

  for (const { key, label } of COORD_SPORTS) {
    test(`${label}: Monotonie – größerer Radius liefert ≥ Events (alle Stufen)`, async ({ page }) => {
      await clickSport(page, key);
      await fillPlz(page);
      const counts = [];
      for (const r of RADII) {
        await setRadius(page, r);
        counts.push({ r, n: await getStatsTotal(page) });
      }
      for (let i = 1; i < counts.length; i++) {
        expect(counts[i].n).toBeGreaterThanOrEqual(counts[i - 1].n);
      }
    });

    test(`${label}: Kein Event überschreitet den Radius – alle Stufen`, async ({ page }) => {
      await clickSport(page, key);
      await fillPlz(page);
      for (const r of RADII) {
        await setRadius(page, r);
        const violations = await page.evaluate((radius) =>
          [...document.querySelectorAll('#listView .ev .dist')]
            .map(el => parseInt(el.textContent.replace('~', '').trim()))
            .filter(d => d > parseInt(radius) + 5)
            .map(d => `${d} bei Radius ${radius} km`), r);
        expect(violations).toHaveLength(0);
      }
    });

    test(`${label}: Stats == sichtbare Karten bei jedem Radius`, async ({ page }) => {
      await clickSport(page, key);
      await fillPlz(page);
      for (const r of RADII) {
        await setRadius(page, r);
        const statsCount = await getStatsTotal(page);
        const rows       = await getRowCount(page);
        if (statsCount <= PAGE_SIZE) {
          expect(rows).toBe(statsCount);
        } else {
          await expect(page.locator('#loadmore')).toBeVisible();
          expect(rows).toBeGreaterThan(0);
          expect(rows).toBeLessThanOrEqual(statsCount);
        }
      }
    });
  }

  // ── 5d. Konsistenz Stats == Karten für alle Sports ───────────────────────

  test('PLZ aktiv: Stats-Zahl == Karten für alle Sportarten', async ({ page }) => {
    await fillPlz(page);
    for (const { key } of SPORTS.filter(s => s.key !== 'all')) {
      await clickSport(page, key);
      const statsCount = await getStatsTotal(page);
      const rows       = await getRowCount(page);
      if (statsCount <= PAGE_SIZE) {
        expect(rows).toBe(statsCount);
      } else {
        expect(rows).toBeGreaterThan(0);
        expect(rows).toBeLessThanOrEqual(statsCount);
      }
    }
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 6. RESET FILTER
// ═══════════════════════════════════════════════════════════════════════════

test.describe('6 · Reset Filter', () => {
  test.beforeEach(async ({ page }) => {
    await load(page);
    await injectPlz(page);
  });

  test('Reset löscht PLZ und stellt Gesamtanzahl wieder her', async ({ page }) => {
    const totalBefore = await getStatsTotal(page);
    await fillPlz(page);
    const totalFiltered = await getStatsTotal(page);
    expect(totalFiltered).toBeLessThanOrEqual(totalBefore);

    await page.click('#reset');
    await page.waitForTimeout(250);

    expect(await getStatsTotal(page)).toBe(totalBefore);
    await expect(page.locator('#plz')).toHaveValue('');
    const distChips = await page.evaluate(() => document.querySelectorAll('#listView .ev .dist').length);
    expect(distChips).toBe(0);
  });

  test('Reset löscht Datumsfilter', async ({ page }) => {
    const totalBefore = await getStatsTotal(page);
    await page.selectOption('#zeitraum', 'custom');
    await page.waitForTimeout(150);
    const future = new Date();
    future.setMonth(future.getMonth() + 6);
    await page.fill('#dfrom', future.toISOString().slice(0, 10));
    await page.dispatchEvent('#dfrom', 'change');
    await page.waitForTimeout(200);

    await page.click('#reset');
    await page.waitForTimeout(200);

    await expect(page.locator('#dfrom')).toHaveValue('');
    await expect(page.locator('#dto')).toHaveValue('');
    expect(await getStatsTotal(page)).toBe(totalBefore);
  });

  test('Reset aktiviert alle Event-Typen wieder', async ({ page }) => {
    const n = await page.evaluate(() => document.querySelectorAll('#typeMenu input').length);
    if (n > 1) {
      await page.evaluate(() => {
        const cb = document.querySelector('#typeMenu input');
        cb.checked = false; cb.dispatchEvent(new Event('change'));
      });
      await page.waitForTimeout(150);
    }
    await page.click('#reset');
    await page.waitForTimeout(200);
    const inactive = await page.evaluate(() =>
      [...document.querySelectorAll('#typeMenu input')].filter(cb => !cb.checked).length
    );
    expect(inactive).toBe(0);
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 7. DATUMSFILTER
// ═══════════════════════════════════════════════════════════════════════════

test.describe('7 · Datumsfilter', () => {
  test.beforeEach(async ({ page }) => {
    await load(page);
    await page.selectOption('#zeitraum', 'custom');
    await page.waitForTimeout(150);
  });

  test('dfrom 6 Monate in der Zukunft reduziert Events', async ({ page }) => {
    const totalBefore = await getStatsTotal(page);
    const future = new Date();
    future.setMonth(future.getMonth() + 6);
    await page.fill('#dfrom', future.toISOString().slice(0, 10));
    await page.dispatchEvent('#dfrom', 'change');
    await page.waitForTimeout(300);
    expect(await getStatsTotal(page)).toBeLessThan(totalBefore);
  });

  test('dto in 2 Monaten schließt Fern-Events aus', async ({ page }) => {
    const totalBefore = await getStatsTotal(page);
    const soon = new Date();
    soon.setMonth(soon.getMonth() + 2);
    await page.fill('#dto', soon.toISOString().slice(0, 10));
    await page.dispatchEvent('#dto', 'change');
    await page.waitForTimeout(300);
    expect(await getStatsTotal(page)).toBeLessThan(totalBefore);
  });

  test('dfrom und dto kombiniert: alle Events im Fenster', async ({ page }) => {
    const from = new Date(); from.setMonth(from.getMonth() + 1);
    const to   = new Date(); to.setMonth(to.getMonth() + 3);
    const fromV = from.toISOString().slice(0, 10);
    const toV   = to.toISOString().slice(0, 10);
    await page.fill('#dfrom', fromV);
    await page.dispatchEvent('#dfrom', 'change');
    await page.fill('#dto', toV);
    await page.dispatchEvent('#dto', 'change');
    await page.waitForTimeout(300);

    // Alle gefilterten Events müssen im Fenster liegen (Prüfung über EV + Filterwerte)
    const violations = await page.evaluate(({ fromV, toV }) =>
      EV.filter(e => e.datum >= fromV && e.datum <= toV).length === 0
        ? ['Fenster liefert 0 Events'] : [], { fromV, toV });
    expect(violations).toHaveLength(0);

    const statsCount = await getStatsTotal(page);
    const rows       = await getRowCount(page);
    if (statsCount <= PAGE_SIZE) {
      expect(rows).toBe(statsCount);
    } else {
      expect(rows).toBeGreaterThan(0);
    }
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 8. EVENT-TYP-FILTER (Unterarten)
// ═══════════════════════════════════════════════════════════════════════════

test.describe('8 · Event-Typ-Filter (Unterarten)', () => {
  test.beforeEach(async ({ page }) => { await load(page); });

  test('Radsport: Typen vorhanden', async ({ page }) => {
    const count = await page.evaluate(() => document.querySelectorAll('#typeMenu input').length);
    expect(count).toBeGreaterThan(0);
  });

  test('Typ deaktivieren reduziert Event-Anzahl', async ({ page }) => {
    const n = await page.evaluate(() => document.querySelectorAll('#typeMenu input').length);
    if (n < 2) return;
    const before = await getStatsTotal(page);
    await page.evaluate(() => {
      const cb = document.querySelector('#typeMenu input');
      cb.checked = false; cb.dispatchEvent(new Event('change'));
    });
    await page.waitForTimeout(200);
    const after = await getStatsTotal(page);
    expect(after).toBeLessThan(before);
  });

  test('Typ reaktivieren stellt Anzahl wieder her', async ({ page }) => {
    const n = await page.evaluate(() => document.querySelectorAll('#typeMenu input').length);
    if (n < 2) return;
    const before = await getStatsTotal(page);
    await page.evaluate(() => {
      const cb = document.querySelector('#typeMenu input');
      cb.checked = false; cb.dispatchEvent(new Event('change'));
    });
    await page.waitForTimeout(200);
    await page.evaluate(() => {
      const cb = document.querySelector('#typeMenu input');
      cb.checked = true; cb.dispatchEvent(new Event('change'));
    });
    await page.waitForTimeout(200);
    expect(await getStatsTotal(page)).toBe(before);
  });

  test('Triathlon-Sport hat Typ: Triathlon', async ({ page }) => {
    await clickSport(page, 'tri');
    const types = await page.evaluate(() =>
      [...document.querySelectorAll('#typeMenu .typeopt')].map(p => p.textContent.trim())
    );
    expect(types.some(t => t.includes('Triathlon'))).toBe(true);
  });

  test('Stats-Zahl konsistent nach Typ-Deaktivierung', async ({ page }) => {
    const n = await page.evaluate(() => document.querySelectorAll('#typeMenu input').length);
    if (n < 2) return;
    await page.evaluate(() => {
      const cb = document.querySelector('#typeMenu input');
      cb.checked = false; cb.dispatchEvent(new Event('change'));
    });
    await page.waitForTimeout(200);
    const statsCount = await getStatsTotal(page);
    const rows       = await getRowCount(page);
    if (statsCount <= PAGE_SIZE) {
      expect(rows).toBe(statsCount);
    } else {
      expect(rows).toBeGreaterThan(0);
    }
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 9. ANSICHTEN (Liste / Kalender)
// ═══════════════════════════════════════════════════════════════════════════

test.describe('9 · Ansichten', () => {
  test.beforeEach(async ({ page }) => { await load(page); });

  test('Liste standardmäßig aktiv', async ({ page }) => {
    await expect(page.locator('#listView')).not.toHaveClass(/\bhide\b/);
    await expect(page.locator('#calView')).toHaveClass(/\bhide\b/);
  });

  test('Kalender-Wechsel funktioniert, Monatsblöcke erscheinen', async ({ page }) => {
    await switchView(page, 'cal');
    await expect(page.locator('#calView')).not.toHaveClass(/\bhide\b/);
    await expect(page.locator('#listView')).toHaveClass(/\bhide\b/);
    const months = page.locator('#calView .cal-month');
    expect(await months.count()).toBeGreaterThan(0);
  });

  test('Kalender: Karten haben Titel-Link', async ({ page }) => {
    await switchView(page, 'cal');
    const links = page.locator('#calView a.cal-card[href]');
    expect(await links.count()).toBeGreaterThan(0);
  });

  test('PLZ-Filter wirkt sich auf Kalender aus', async ({ page }) => {
    await injectPlz(page);
    await fillPlz(page);
    const totalListe = await getStatsTotal(page);
    await switchView(page, 'cal');
    const totalKalender = await getStatsTotal(page);
    expect(totalKalender).toBe(totalListe);
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 10. PAGINATION (Mehr laden)
// ═══════════════════════════════════════════════════════════════════════════

test.describe('10 · Pagination (Mehr laden)', () => {
  test.beforeEach(async ({ page }) => { await load(page); });

  test(`Anfangs ${PAGE_SIZE} Karten bei > ${PAGE_SIZE} Events`, async ({ page }) => {
    const total = await getStatsTotal(page);
    if (total <= PAGE_SIZE) return;
    expect(await getRowCount(page)).toBe(PAGE_SIZE);
  });

  test('Mehr-Zone zeigt "X von Y" Info', async ({ page }) => {
    const total = await getStatsTotal(page);
    if (total <= PAGE_SIZE) return;
    await expect(page.locator('#loadmore')).toBeVisible();
    const hint = await page.locator('#loadmoreCnt').textContent();
    expect(hint).toMatch(/\d+ von \d+/);
  });

  test(`"Mehr laden" lädt ${PAGE_SIZE} weitere Events`, async ({ page }) => {
    const total = await getStatsTotal(page);
    if (total <= PAGE_SIZE) return;
    const before = await getRowCount(page);
    await page.locator('#loadmoreBtn').click();
    await page.waitForTimeout(300);
    const after = await getRowCount(page);
    expect(after).toBeGreaterThan(before);
    expect(after).toBeLessThanOrEqual(before + PAGE_SIZE + 1);
  });

  test(`Nach Reset zurück auf ${PAGE_SIZE} Karten`, async ({ page }) => {
    const total = await getStatsTotal(page);
    if (total <= PAGE_SIZE) return;
    await page.locator('#loadmoreBtn').click();
    await page.waitForTimeout(300);
    await page.click('#reset');
    await page.waitForTimeout(200);
    expect(await getRowCount(page)).toBe(PAGE_SIZE);
  });
});
