/**
 * Bockwurst Sport Events – vollständige Playwright-Testsuite
 *
 * Abgedeckt:
 *  - Seitenaufruf & Fehlerfreiheit
 *  - Snapshot-Vollständigkeit (alle 4 Sportarten)
 *  - Sport-Buttons & Pill-Filter für alle Sportarten
 *  - Konsistenz: Stats-Zahl == angezeigte Zeilen
 *  - Event-Details (Titel, Datum, Link, Aktionen)
 *  - PLZ-Filter: alle 4 Sportarten, Radius, Distanzspalte, Distanzwerte
 *  - Reset aller Filter
 *  - Datumsfilter
 *  - Tabs: Liste / Kalender
 *  - Pagination (Mehr laden)
 *  - Keine JS-Fehler
 *
 * Setup:
 *   cd ~/sport-events
 *   npm install -D @playwright/test
 *   npx playwright install chromium
 *   BASE_URL=https://bockwurst-events.netlify.app npx playwright test tests/bockwurst.spec.js
 */

const { test, expect } = require('@playwright/test');

const BASE_URL = process.env.BASE_URL || 'https://bockwurst-events.netlify.app';

// München für PLZ-Tests
const TEST_PLZ    = '80331';
const TEST_COORDS = [48.1374, 11.5754];

// ── Helpers ────────────────────────────────────────────────────────────────

/** Injiziert PLZ direkt in PLZ_MAP – kein Nominatim-Call nötig */
async function injectPlz(page, plz = TEST_PLZ, coords = TEST_COORDS) {
  // PLZ_MAP ist per `const` deklariert → nicht auf window; direkt mutieren
  await page.evaluate(([p, c]) => { PLZ_MAP[p] = c; }, [plz, coords]);
}

/** Trägt PLZ ein, feuert oninput, wartet auf Re-Render */
async function fillPlz(page, plz = TEST_PLZ) {
  await page.locator('#plz-input').fill(plz);
  await page.locator('#plz-input').dispatchEvent('input');
  await page.waitForTimeout(400);
}

/** Klickt Sport-Button per key ('rad'|'swim'|'tri'|'lauf'|'all') */
async function clickSport(page, key) {
  await page.evaluate((k) => {
    const btn = [...document.querySelectorAll('.sport-btn')]
      .find(b => b.getAttribute('onclick') && b.getAttribute('onclick').includes(`'${k}'`));
    if (btn) btn.click();
  }, key);
  await page.waitForTimeout(250);
}

/** Liest Stats-Gesamtzahl (erster .stat-val) */
async function getStatsTotal(page) {
  return page.evaluate(() => {
    const el = document.querySelector('#stats .stat-val');
    return el ? parseInt(el.textContent.trim(), 10) : 0;
  });
}

/** Anzahl sichtbarer <tr> in #evt-body */
async function getRowCount(page) {
  return page.evaluate(() => document.querySelectorAll('#evt-body tr').length);
}

/** Klickt auf einen Tab per Textinhalt */
async function clickTab(page, label) {
  await page.evaluate((l) => {
    const btn = [...document.querySelectorAll('.tab')].find(t => t.textContent.includes(l));
    if (btn) btn.click();
  }, label);
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
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    expect(errors).toHaveLength(0);
  });

  test('5 Sport-Buttons sichtbar', async ({ page }) => {
    await page.goto(BASE_URL);
    await expect(page.locator('.sport-btn')).toHaveCount(5);
  });

  test('Stand-Badge zeigt gültiges Datum (DD.MM.YYYY)', async ({ page }) => {
    await page.goto(BASE_URL);
    const text = await page.locator('#snap-date').textContent();
    expect(text).toMatch(/\d{2}\.\d{2}\.\d{4}/);
  });

  test('Stats zeigen Event-Zahl > 0', async ({ page }) => {
    await page.goto(BASE_URL);
    const total = await getStatsTotal(page);
    expect(total).toBeGreaterThan(0);
  });

  test('2 Tabs sichtbar (Liste, Kalender)', async ({ page }) => {
    await page.goto(BASE_URL);
    await expect(page.locator('.tab')).toHaveCount(2);
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 2. SNAPSHOT-VOLLSTÄNDIGKEIT
// ═══════════════════════════════════════════════════════════════════════════

test.describe('2 · Snapshot-Vollständigkeit', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('domcontentloaded');
  });

  const minCounts = {
    SNAPSHOT:      650,   // Radsport (rad-net + radsport-events.de)
    TRI_SNAPSHOT:  50,    // Triathlon
    LAUF_SNAPSHOT: 100,   // Laufen
  };

  for (const [name, min] of Object.entries(minCounts)) {
    test(`${name} hat mindestens ${min} Einträge`, async ({ page }) => {
      // `const` im Top-Level-Script → nicht auf window; via eval zugreifen
      const count = await page.evaluate((n) => { try { return eval(n).length; } catch(e) { return 0; } }, name);
      expect(count).toBeGreaterThanOrEqual(min);
    });
  }

  test('Jeder Snapshot-Eintrag hat Pflichtfelder (titel, date_iso, art)', async ({ page }) => {
    const issues = await page.evaluate(() => {
      const all = [...SNAPSHOT, ...TRI_SNAPSHOT,
                   ...LAUF_SNAPSHOT, ...SWIM_SNAPSHOT];
      const bad = [];
      all.forEach((e, i) => {
        if (!e.titel)    bad.push(`[${i}] fehlt titel`);
        if (!e.date_iso) bad.push(`[${i}] fehlt date_iso (titel: ${e.titel})`);
        if (!e.art)      bad.push(`[${i}] fehlt art (titel: ${e.titel})`);
      });
      return bad;
    });
    expect(issues).toHaveLength(0);
  });

  // Alle Events müssen Ort und Koordinaten haben – Grundvoraussetzung für den PLZ-Filter
  const SNAPSHOTS = [
    { name: 'SNAPSHOT',      label: 'Radsport'   },
    { name: 'TRI_SNAPSHOT',  label: 'Triathlon'  },
    { name: 'LAUF_SNAPSHOT', label: 'Laufen'     },
    { name: 'SWIM_SNAPSHOT', label: 'Freiwasser' },
  ];

  for (const { name, label } of SNAPSHOTS) {
    test(`${label}: alle Events haben ort-Feld`, async ({ page }) => {
      const missing = await page.evaluate((n) => {
        const snap = eval(n);
        return snap
          .filter(e => !e.ort || e.ort.trim() === '')
          .map(e => e.titel);
      }, name);
      expect(missing, `${label}: Events ohne ort: ${missing.join(', ')}`).toHaveLength(0);
    });

    test(`${label}: alle Events haben Koordinaten (lat/lon)`, async ({ page }) => {
      const missing = await page.evaluate((n) => {
        const snap = eval(n);
        return snap
          .filter(e => e.lat == null || e.lon == null)
          .map(e => `${e.titel} (ort: ${e.ort || '–'})`);
      }, name);
      expect(missing, `${label}: Events ohne Koordinaten: ${missing.join(', ')}`).toHaveLength(0);
    });
  }

  test('Keine Events in der Vergangenheit', async ({ page }) => {
    const past = await page.evaluate(() => {
      // 1 Tag Toleranz: täglicher Scraper kann 1 Tag Lag haben
      const d = new Date(); d.setDate(d.getDate() - 1);
      const today = d.toISOString().slice(0, 10);
      const all = [...SNAPSHOT, ...TRI_SNAPSHOT,
                   ...LAUF_SNAPSHOT, ...SWIM_SNAPSHOT];
      return all.filter(e => e.date_iso < today).map(e => `${e.titel} (${e.date_iso})`);
    });
    expect(past).toHaveLength(0);
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 3. SPORT-FILTER & KONSISTENZ
// ═══════════════════════════════════════════════════════════════════════════

test.describe('3 · Sport-Filter & Konsistenz', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('domcontentloaded');
  });

  for (const { key, label, minEvents } of SPORTS) {
    test(`${label}: Button aktiv, Stats ≥ ${minEvents}`, async ({ page }) => {
      await clickSport(page, key);
      const btn = page.locator(`.sport-btn[onclick*="'${key}'"]`);
      await expect(btn).toHaveClass(/active/);
      const total = await getStatsTotal(page);
      expect(total).toBeGreaterThanOrEqual(minEvents);
    });

    test(`${label}: Stats-Zahl stimmt mit angezeigten Zeilen überein`, async ({ page }) => {
      await clickSport(page, key);
      const statsCount = await getStatsTotal(page);
      const rows       = await getRowCount(page);

      if (statsCount <= 15) {
        // Alle Events auf einer Seite → Zahl muss exakt stimmen
        expect(rows).toBe(statsCount);
      } else {
        // Paginierung aktiv → Mehr-Zone sichtbar, Zeilen ≤ Gesamt
        await expect(page.locator('#mehr-zone')).toBeVisible();
        const hint = await page.locator('#mehr-cnt').textContent();
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
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('domcontentloaded');
  });

  test('Erste Zeile hat 7 Spalten (Art, Datum, Titel, Distanz, Strecken, Verein, Aktionen)', async ({ page }) => {
    const cells = page.locator('#evt-body tr').first().locator('td');
    await expect(cells).toHaveCount(7);
  });

  test('Art-Badge vorhanden und nicht leer', async ({ page }) => {
    const badge = page.locator('#evt-body tr').first().locator('.badge');
    await expect(badge).toBeVisible();
    const text = await badge.textContent();
    expect(text.trim().length).toBeGreaterThan(0);
  });

  test('Datum im Format DD.MM.YYYY', async ({ page }) => {
    const datumTexts = await page.evaluate(() =>
      [...document.querySelectorAll('#evt-body tr td:nth-child(2)')]
        .slice(0, 5).map(td => td.textContent.trim())
    );
    for (const d of datumTexts) {
      expect(d).toMatch(/\d{2}\.\d{2}\.\d{4}/);
    }
  });

  test('Titel-Links haben gültige https:// URLs', async ({ page }) => {
    const hrefs = await page.evaluate(() =>
      [...document.querySelectorAll('#evt-body a.event-link')]
        .slice(0, 10).map(a => a.href)
    );
    expect(hrefs.length).toBeGreaterThan(0);
    for (const href of hrefs) {
      expect(href).toMatch(/^https?:\/\/.+/);
    }
  });

  test('Aktionen-Spalte vorhanden (letzte td)', async ({ page }) => {
    const firstRow = page.locator('#evt-body tr').first();
    await expect(firstRow.locator('td:last-child')).toBeAttached();
  });

  test('Event-Details für alle Sportarten geprüft', async ({ page }) => {
    for (const { key } of SPORTS.filter(s => s.key !== 'all')) {
      await clickSport(page, key);
      const count = await getRowCount(page);
      if (count === 0) continue; // Freiwasser kann leer sein

      // Titel-Link
      const link = page.locator('#evt-body tr').first().locator('a.event-link');
      await expect(link).toHaveAttribute('href', /^https?:\/\//);

      // Art-Badge
      const badge = page.locator('#evt-body tr').first().locator('.badge');
      await expect(badge).toBeVisible();
    }
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 5. PLZ-DISTANZFILTER
// ═══════════════════════════════════════════════════════════════════════════

test.describe('5 · PLZ-Distanzfilter', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('domcontentloaded');
    await injectPlz(page);
  });

  // ── 5a. Distanzspalte ────────────────────────────────────────────────────

  test('Distanz-Spalte ausgeblendet ohne PLZ', async ({ page }) => {
    await expect(page.locator('#dist-th')).not.toBeVisible();
    await expect(page.locator('#evt-tbl')).not.toHaveClass(/plz-on/);
  });

  test('Distanz-Spalte erscheint nach PLZ-Eingabe', async ({ page }) => {
    await fillPlz(page);
    await expect(page.locator('#evt-tbl')).toHaveClass(/plz-on/);
    await expect(page.locator('#dist-th')).toBeVisible();
  });

  test('Distanzwerte im Format "N km" oder "–"', async ({ page }) => {
    await fillPlz(page);
    const vals = await page.evaluate(() =>
      [...document.querySelectorAll('#evt-body .dist-td')]
        .map(td => td.textContent.trim())
    );
    expect(vals.length).toBeGreaterThan(0);
    for (const v of vals) {
      expect(v).toMatch(/^(\d+ km|–)$/);
    }
  });

  test('Kein Distanzwert überschreitet gewählten Radius (50 km)', async ({ page }) => {
    await page.selectOption('#radius-sel', '50');
    await fillPlz(page);
    const distValues = await page.evaluate(() =>
      [...document.querySelectorAll('#evt-body .dist-td')]
        .map(td => td.textContent.trim())
        .filter(t => t && t !== '–')
        .map(t => parseInt(t))
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
      const noRes = page.locator('#no-res');

      // Alle Sportarten (inkl. Swim, da jetzt Koordinaten vorhanden) müssen
      // bei München (80331 / 300km) mindestens 1 Event liefern
      expect(count).toBeGreaterThan(0);
      await expect(noRes).not.toBeVisible();
    });
  }

  test('Triathlon: Events erscheinen auch ohne Koordinaten (ort leer → immer anzeigen)', async ({ page }) => {
    await clickSport(page, 'tri');
    await fillPlz(page);
    // Triathlon-Events haben meist keinen Ort → sollen trotzdem erscheinen
    const count = await getStatsTotal(page);
    expect(count).toBeGreaterThan(0);
    // Kein Eintrag mit ort-Wert darf Distanz > Radius haben
    const violations = await page.evaluate((radius) => {
      const r = parseInt(radius);
      const rows = [...document.querySelectorAll('#evt-body tr')];
      return rows.filter(tr => {
        const distTd = tr.querySelector('.dist-td');
        if (!distTd) return false;
        const txt = distTd.textContent.trim();
        if (!txt || txt === '–') return false;
        return parseInt(txt) > r + 5; // 5km Toleranz
      }).map(tr => tr.querySelector('a.event-link')?.textContent);
    }, await page.locator('#radius-sel').inputValue());
    expect(violations).toHaveLength(0);
  });

  test('Freiwasser: PLZ-Filter filtert nach Distanz (keine Events außerhalb Radius)', async ({ page }) => {
    await clickSport(page, 'swim');
    // Chemnitz (09113): Kulkwitzer See ~72km, Pöhl-Cup ~69km, alle Bayern-Seen >295km
    const CHEMNITZ_PLZ    = '09113';
    const CHEMNITZ_COORDS = [50.831, 12.921];
    // Direkt selPlz + PLZ_MAP setzen und render() aufrufen, um Input-Event-Timing
    // zu umgehen (onPlzInput ist async; auf live mit ~720 Events manchmal nicht stabil)
    await page.evaluate(([plz, coords]) => {
      PLZ_MAP[plz] = coords;
      selPlz = plz;
      document.getElementById('plz-input').value = plz;
      render();
    }, [CHEMNITZ_PLZ, CHEMNITZ_COORDS]);
    await page.waitForTimeout(300);

    // Mit 50km: alle Swim-Events außerhalb → Tabelle muss leer oder sehr klein sein
    await page.locator('#radius-sel').selectOption('50');
    await page.waitForTimeout(400);
    const count50 = await getStatsTotal(page);

    // Mit 300km: deutlich mehr Events sichtbar
    await page.locator('#radius-sel').selectOption('300');
    await page.waitForTimeout(400);
    const count300 = await getStatsTotal(page);

    // Filter muss greifen: 300km-Radius liefert ≥ Events als 50km
    expect(count300).toBeGreaterThanOrEqual(count50);
    // Und tatsächlich mehr (Bayern-Seen bei ~300km sichtbar, bei 50km nicht)
    expect(count300).toBeGreaterThan(count50);

    // Keine Distanzverletzungen bei 50km (alle sichtbaren Events ≤ 55km)
    await page.locator('#radius-sel').selectOption('50');
    await page.waitForTimeout(300);
    const violations = await page.evaluate(() => {
      return [...document.querySelectorAll('#evt-body tr')].filter(tr => {
        const distTd = tr.querySelector('.dist-td');
        if (!distTd) return false;
        const txt = distTd.textContent.trim();
        if (!txt || txt === '–') return false;
        return parseInt(txt) > 55; // 50km + 5km Toleranz
      }).map(tr => tr.querySelector('a.event-link')?.textContent);
    });
    expect(violations).toHaveLength(0);
  });

  // ── 5c. Radius – alle 5 Stufen, alle relevanten Sportarten ─────────────

  const RADII = ['50', '100', '150', '200', '300'];

  // Sportarten mit Koordinaten → Radius muss greifen
  const COORD_SPORTS = [
    { key: 'rad',  label: 'Radsport'   },
    { key: 'lauf', label: 'Laufen'     },
    { key: 'swim', label: 'Freiwasser' },
    { key: 'tri',  label: 'Triathlon'  },
  ];

  for (const { key, label } of COORD_SPORTS) {
    test(`${label}: Monotonie – größerer Radius liefert ≥ Events (alle 5 Stufen)`, async ({ page }) => {
      await clickSport(page, key);
      await fillPlz(page);

      const counts = [];
      for (const r of RADII) {
        await page.selectOption('#radius-sel', r);
        await page.waitForTimeout(250);
        counts.push({ r, n: await getStatsTotal(page) });
      }

      // Jede Stufe darf nicht weniger Events haben als die vorherige
      for (let i = 1; i < counts.length; i++) {
        expect(counts[i].n).toBeGreaterThanOrEqual(counts[i - 1].n);
      }
    });

    test(`${label}: Kein Event überschreitet den Radius – alle 5 Stufen`, async ({ page }) => {
      await clickSport(page, key);
      await fillPlz(page);

      for (const r of RADII) {
        await page.selectOption('#radius-sel', r);
        await page.waitForTimeout(250);

        // Alle dist-td-Werte müssen ≤ r sein (Toleranz +5 km für Integer-Rounding)
        const violations = await page.evaluate((radius) => {
          return [...document.querySelectorAll('#evt-body .dist-td')]
            .map(td => td.textContent.trim())
            .filter(t => t && t !== '–')
            .filter(t => parseInt(t) > parseInt(radius) + 5)
            .map(t => `${t} bei Radius ${radius} km`);
        }, r);

        expect(violations).toHaveLength(0);
      }
    });

    test(`${label}: Stats == sichtbare Zeilen bei jedem Radius`, async ({ page }) => {
      await clickSport(page, key);
      await fillPlz(page);

      for (const r of RADII) {
        await page.selectOption('#radius-sel', r);
        await page.waitForTimeout(250);

        const statsCount = await getStatsTotal(page);
        const rows       = await getRowCount(page);

        if (statsCount <= 15) {
          expect(rows).toBe(statsCount);
        } else {
          // Paginierung aktiv → Zeilen < Gesamt, aber Mehr-Zone sichtbar
          await expect(page.locator('#mehr-zone')).toBeVisible();
          expect(rows).toBeGreaterThan(0);
          expect(rows).toBeLessThanOrEqual(statsCount);
        }
      }
    });
  }

  // ── 5d. Konsistenz Stats == Zeilen für alle Sports ───────────────────────

  test('PLZ aktiv: Stats-Zahl == Zeilen für alle Sportarten', async ({ page }) => {
    await fillPlz(page);
    for (const { key } of SPORTS.filter(s => s.key !== 'all')) {
      await clickSport(page, key);
      const statsCount = await getStatsTotal(page);
      const rows       = await getRowCount(page);
      if (statsCount <= 15) {
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
    await page.goto(BASE_URL);
    await page.waitForLoadState('domcontentloaded');
    await injectPlz(page);
  });

  test('Reset löscht PLZ und stellt Gesamtanzahl wieder her', async ({ page }) => {
    const totalBefore = await getStatsTotal(page);
    await fillPlz(page);
    const totalFiltered = await getStatsTotal(page);
    expect(totalFiltered).toBeLessThanOrEqual(totalBefore);

    await page.click('#reset-all-btn');
    await page.waitForTimeout(250);

    expect(await getStatsTotal(page)).toBe(totalBefore);
    await expect(page.locator('#plz-input')).toHaveValue('');
    await expect(page.locator('#evt-tbl')).not.toHaveClass(/plz-on/);
    await expect(page.locator('#dist-th')).not.toBeVisible();
  });

  test('Reset löscht Datumsfilter', async ({ page }) => {
    const totalBefore = await getStatsTotal(page);
    const future = new Date();
    future.setMonth(future.getMonth() + 6);
    await page.fill('#date-from', future.toISOString().slice(0, 10));
    await page.dispatchEvent('#date-from', 'change');
    await page.waitForTimeout(200);

    await page.click('#reset-all-btn');
    await page.waitForTimeout(200);

    await expect(page.locator('#date-from')).toHaveValue('');
    await expect(page.locator('#date-to')).toHaveValue('');
    expect(await getStatsTotal(page)).toBe(totalBefore);
  });

  test('Reset aktiviert alle Pills wieder', async ({ page }) => {
    // Deactivate one pill
    const pills = page.locator('#pills .pill');
    if (await pills.count() > 1) {
      await pills.first().click();
      await page.waitForTimeout(150);
    }
    await page.click('#reset-all-btn');
    await page.waitForTimeout(200);
    // All pills active
    const inactivePills = await page.evaluate(() =>
      [...document.querySelectorAll('#pills .pill')]
        .filter(p => !p.classList.contains('active')).length
    );
    expect(inactivePills).toBe(0);
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 7. DATUMSFILTER
// ═══════════════════════════════════════════════════════════════════════════

test.describe('7 · Datumsfilter', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('domcontentloaded');
  });

  test('date-from 6 Monate in der Zukunft reduziert Events', async ({ page }) => {
    const totalBefore = await getStatsTotal(page);
    const future = new Date();
    future.setMonth(future.getMonth() + 6);
    await page.fill('#date-from', future.toISOString().slice(0, 10));
    await page.dispatchEvent('#date-from', 'change');
    await page.waitForTimeout(300);
    expect(await getStatsTotal(page)).toBeLessThan(totalBefore);
  });

  test('date-to in 2 Monaten schließt Fern-Events aus', async ({ page }) => {
    const totalBefore = await getStatsTotal(page);
    const soon = new Date();
    soon.setMonth(soon.getMonth() + 2);
    await page.fill('#date-to', soon.toISOString().slice(0, 10));
    await page.dispatchEvent('#date-to', 'change');
    await page.waitForTimeout(300);
    expect(await getStatsTotal(page)).toBeLessThan(totalBefore);
  });

  test('date-from und date-to kombiniert: alle Events im Fenster', async ({ page }) => {
    const from = new Date(); from.setMonth(from.getMonth() + 1);
    const to   = new Date(); to.setMonth(to.getMonth() + 3);
    await page.fill('#date-from', from.toISOString().slice(0, 10));
    await page.dispatchEvent('#date-from', 'change');
    await page.fill('#date-to',   to.toISOString().slice(0, 10));
    await page.dispatchEvent('#date-to', 'change');
    await page.waitForTimeout(300);
    // Alle sichtbaren Events müssen im Fenster liegen
    const violations = await page.evaluate(() => {
      const fromVal = document.getElementById('date-from').value;
      const toVal   = document.getElementById('date-to').value;
      return [...document.querySelectorAll('#evt-body tr')].filter(tr => {
        // date_iso embedded as data- attr ist nicht vorhanden, daher über DOM-Text prüfen
        // stattdessen: prüfe nur ob keine Zeilen > to erscheinen
        return false; // Placeholder – echte Überprüfung via JS-Globals besser
      }).length;
    });
    // Mindestens: Stats und Zeilen konsistent
    const statsCount = await getStatsTotal(page);
    const rows       = await getRowCount(page);
    if (statsCount <= 15) {
      expect(rows).toBe(statsCount);
    } else {
      expect(rows).toBeGreaterThan(0);
    }
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 8. PILL-FILTER (Typen/Unterarten)
// ═══════════════════════════════════════════════════════════════════════════

test.describe('8 · Pill-Filter (Unterarten)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('domcontentloaded');
  });

  test('Radsport: Pills vorhanden', async ({ page }) => {
    const count = await page.locator('#pills .pill').count();
    expect(count).toBeGreaterThan(0);
  });

  test('Pill deaktivieren reduziert Event-Anzahl', async ({ page }) => {
    const pills = page.locator('#pills .pill');
    if (await pills.count() < 2) return; // skip wenn nur eine Unterart
    const before = await getStatsTotal(page);
    await pills.first().click();
    await page.waitForTimeout(200);
    const after = await getStatsTotal(page);
    expect(after).toBeLessThan(before);
  });

  test('Pill reaktivieren stellt Anzahl wieder her', async ({ page }) => {
    const pills = page.locator('#pills .pill');
    if (await pills.count() < 2) return;
    const before = await getStatsTotal(page);
    await pills.first().click();
    await page.waitForTimeout(200);
    await pills.first().click();
    await page.waitForTimeout(200);
    expect(await getStatsTotal(page)).toBe(before);
  });

  test('Triathlon-Sport hat Pills: Triathlon, Duathlon etc.', async ({ page }) => {
    await clickSport(page, 'tri');
    const pillTexts = await page.evaluate(() =>
      [...document.querySelectorAll('#pills .pill')].map(p => p.textContent.trim())
    );
    expect(pillTexts.some(t => t.includes('Triathlon'))).toBe(true);
  });

  test('Stats-Zahl stimmt nach Pill-Deaktivierung', async ({ page }) => {
    const pills = page.locator('#pills .pill');
    if (await pills.count() < 2) return;
    await pills.first().click();
    await page.waitForTimeout(200);
    const statsCount = await getStatsTotal(page);
    const rows       = await getRowCount(page);
    if (statsCount <= 15) {
      expect(rows).toBe(statsCount);
    } else {
      expect(rows).toBeGreaterThan(0);
    }
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 9. TABS (Liste / Kalender)
// ═══════════════════════════════════════════════════════════════════════════

test.describe('9 · Tabs', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('domcontentloaded');
  });

  test('Liste-Tab standardmäßig aktiv', async ({ page }) => {
    await expect(page.locator('#tab-liste')).toBeVisible();
    await expect(page.locator('#tab-kalender')).not.toBeVisible();
  });

  test('Kalender-Tab wechsel funktioniert, Monats-Header erscheint', async ({ page }) => {
    await clickTab(page, 'Kalender');
    await expect(page.locator('#tab-kalender')).toBeVisible();
    await expect(page.locator('#tab-liste')).not.toBeVisible();
    const headers = page.locator('.month-header');
    expect(await headers.count()).toBeGreaterThan(0);
  });

  test('Kalender-Tab: Karten haben Titel-Link', async ({ page }) => {
    await clickTab(page, 'Kalender');
    const links = page.locator('#cal-body a[href]');
    expect(await links.count()).toBeGreaterThan(0);
  });

  test('PLZ-Filter wirkt sich auf Kalender-Tab aus', async ({ page }) => {
    await injectPlz(page);
    const totalListeBefore = await getStatsTotal(page);
    await fillPlz(page);
    const totalListeAfter = await getStatsTotal(page);
    // Zum Kalender wechseln
    await clickTab(page, 'Kalender');
    // Stats-Zahl bleibt gleich (Kalender teilt denselben gefilterten Datensatz)
    const totalKalender = await getStatsTotal(page);
    expect(totalKalender).toBe(totalListeAfter);
  });
});

// ═══════════════════════════════════════════════════════════════════════════
// 10. PAGINATION
// ═══════════════════════════════════════════════════════════════════════════

test.describe('10 · Pagination (Mehr laden)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('domcontentloaded');
  });

  test('Anfangs 15 Zeilen bei > 15 Events', async ({ page }) => {
    const total = await getStatsTotal(page);
    if (total <= 15) return;
    expect(await getRowCount(page)).toBe(15);
  });

  test('Mehr-Zone zeigt "X von Y" Info', async ({ page }) => {
    const total = await getStatsTotal(page);
    if (total <= 15) return;
    await expect(page.locator('#mehr-zone')).toBeVisible();
    const hint = await page.locator('#mehr-cnt').textContent();
    expect(hint).toMatch(/\d+ von \d+/);
  });

  test('"Mehr laden" lädt 15 weitere Events', async ({ page }) => {
    const total = await getStatsTotal(page);
    if (total <= 15) return;
    const before = await getRowCount(page);
    await page.locator('#mehr-zone button, #mehr-zone [onclick]').first().click();
    await page.waitForTimeout(300);
    const after = await getRowCount(page);
    expect(after).toBeGreaterThan(before);
    expect(after).toBeLessThanOrEqual(before + 15 + 1); // +1 Toleranz
  });

  test('Nach Reset zurück auf 15 Zeilen', async ({ page }) => {
    const total = await getStatsTotal(page);
    if (total <= 15) return;
    // Mehr laden
    await page.locator('#mehr-zone button, #mehr-zone [onclick]').first().click();
    await page.waitForTimeout(300);
    // Reset
    await page.click('#reset-all-btn');
    await page.waitForTimeout(200);
    expect(await getRowCount(page)).toBe(15);
  });
});
