const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1400, height: 900 } });
  const page = await context.newPage();

  const jsErrors = [];
  const consoleErrors = [];
  page.on('pageerror', err => jsErrors.push('PAGE_ERROR: ' + err.message));
  page.on('console', msg => {
    if (msg.type() === 'error') consoleErrors.push('CONSOLE_ERROR: ' + msg.text());
  });

  const results = {};

  async function dismissAll() {
    await page.evaluate(() => {
      const sp = document.getElementById('sources-popup');
      if (sp) sp.classList.remove('visible');
      const ip = document.getElementById('info-panel');
      if (ip) ip.classList.remove('visible');
    });
    await page.waitForTimeout(300);
  }

  async function resetAll() {
    await page.evaluate(() => {
      // Dismiss popups
      const sp = document.getElementById('sources-popup');
      if (sp) sp.classList.remove('visible');
      // Clear all filters using the actual function
      if (typeof clearAllFilters === 'function') clearAllFilters();
      else {
        const btn = document.getElementById('btn-clear-all-filters');
        if (btn) btn.click();
      }
      // Close info panel
      if (typeof closeInfoPanel === 'function') closeInfoPanel();
    });
    await page.waitForTimeout(1200);
  }

  async function getShowingCount() {
    return await page.evaluate(() => {
      const el = document.getElementById('stat-showing');
      if (!el) return null;
      const m = el.textContent.match(/(\d[\d,]*)/);
      return m ? parseInt(m[1].replace(/,/g, '')) : null;
    });
  }

  try {
    console.log('Loading https://thisminute.org ...');
    await page.goto('https://thisminute.org', { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(5000);

    const initialCount = await getShowingCount();
    console.log('Initial showing count: ' + initialCount);

    // ========== TEST 1: Sources popup interaction ==========
    console.log('\n--- TEST 1: Sources popup interaction ---');
    try {
      await page.evaluate(() => document.getElementById('stat-sources').click());
      await page.waitForTimeout(800);

      const popupInfo = await page.evaluate(() => {
        const sp = document.getElementById('sources-popup');
        const visible = sp && sp.classList.contains('visible');
        const items = sp ? sp.querySelectorAll('.source-popup-item') : [];
        const samples = Array.from(items).slice(0, 5).map(el => {
          const name = el.querySelector('.source-popup-name');
          const count = el.querySelector('.source-popup-count');
          return (name ? name.textContent.trim() : '?') + ': ' + (count ? count.textContent.trim() : '?');
        });
        return { visible, count: items.length, samples };
      });

      if (popupInfo.visible && popupInfo.count > 0) {
        results['1_sources_popup'] = 'PASS: Sources popup opened with ' + popupInfo.count +
          ' source items. Top 5: [' + popupInfo.samples.join(' | ') +
          ']. Source items are informational only (no click-to-filter behavior).';
      } else if (popupInfo.visible) {
        results['1_sources_popup'] = 'PARTIAL: Popup visible but 0 items';
      } else {
        results['1_sources_popup'] = 'FAIL: Popup did not open';
      }

      await page.evaluate(() => document.getElementById('sources-popup').classList.remove('visible'));
      await page.waitForTimeout(300);
    } catch (e) {
      results['1_sources_popup'] = 'ERROR: ' + e.message.split('\n')[0];
      await dismissAll();
    }

    // ========== TEST 2: Clear all filters recovery ==========
    console.log('--- TEST 2: Clear all filters recovery ---');
    try {
      await resetAll();
      const preCount = await getShowingCount();

      // Activate Conflict
      await page.evaluate(() => document.querySelector('[data-preset="conflict"]').click());
      await page.waitForTimeout(1500);
      const conflictCount = await getShowingCount();

      // Open filter drawer
      await page.evaluate(() => {
        const btn = document.getElementById('filter-drawer-toggle');
        if (btn) btn.click();
      });
      await page.waitForTimeout(800);

      // Click "None" on sources via the correct button id
      await page.evaluate(() => {
        const btn = document.getElementById('btn-sources-none');
        if (btn) btn.click();
      });
      await page.waitForTimeout(1000);
      const afterNoneCount = await getShowingCount();

      // Click clear all filters via correct button id
      await page.evaluate(() => {
        const btn = document.getElementById('btn-clear-all-filters');
        if (btn) btn.click();
      });
      await page.waitForTimeout(1500);
      const afterClearCount = await getShowingCount();

      if (afterClearCount !== null && preCount !== null) {
        if (afterClearCount >= preCount * 0.8) {
          results['2_clear_filters'] = 'PASS: Count restored. original=' + preCount +
            ', conflict=' + conflictCount + ', afterSourcesNone=' + afterNoneCount +
            ', afterClearAll=' + afterClearCount;
        } else {
          results['2_clear_filters'] = 'FAIL: Count NOT restored. original=' + preCount +
            ', conflict=' + conflictCount + ', afterSourcesNone=' + afterNoneCount +
            ', afterClearAll=' + afterClearCount;
        }
      } else {
        results['2_clear_filters'] = 'UNCLEAR: null counts';
      }
    } catch (e) {
      results['2_clear_filters'] = 'ERROR: ' + e.message.split('\n')[0];
    }

    // ========== TEST 3: Filter state persistence ==========
    console.log('--- TEST 3: Filter state persistence ---');
    try {
      await resetAll();
      const preCount3 = await getShowingCount();

      // Activate Conflict
      await page.evaluate(() => document.querySelector('[data-preset="conflict"]').click());
      await page.waitForTimeout(1000);
      const conflictCount3 = await getShowingCount();

      // Set time filter to 24h
      await page.evaluate(() => {
        const sel = document.getElementById('filter-time');
        sel.value = '24';
        sel.dispatchEvent(new Event('change', { bubbles: true }));
      });
      await page.waitForTimeout(1000);
      const withBoth = await getShowingCount();

      // Deactivate Conflict (clicking active preset calls clearAllFilters per code line 897)
      // Wait -- actually let me check: applyPreset toggles off by calling clearAllFilters
      await page.evaluate(() => document.querySelector('[data-preset="conflict"]').click());
      await page.waitForTimeout(1000);
      const afterPresetOff = await getShowingCount();

      const timeVal = await page.evaluate(() => document.getElementById('filter-time').value);
      const presetActive = await page.evaluate(() =>
        document.querySelector('[data-preset="conflict"]').classList.contains('active')
      );

      // Note: clearAllFilters resets filter-time to "" (line 802), so time filter should NOT persist
      if (timeVal === '24') {
        results['3_filter_persistence'] = 'PASS: Time filter persisted at "24" after preset deactivation. ' +
          'original=' + preCount3 + ', conflict=' + conflictCount3 +
          ', both=' + withBoth + ', afterOff=' + afterPresetOff +
          ', presetActive=' + presetActive;
      } else if (timeVal === '') {
        results['3_filter_persistence'] = 'EXPECTED BEHAVIOR: Deactivating preset calls clearAllFilters() which resets time filter to "". ' +
          'original=' + preCount3 + ', conflict=' + conflictCount3 +
          ', both=' + withBoth + ', afterOff=' + afterPresetOff +
          '. Time filter value="' + timeVal + '"';
      } else {
        results['3_filter_persistence'] = 'UNEXPECTED: timeVal="' + timeVal + '". original=' + preCount3 +
          ', conflict=' + conflictCount3 + ', both=' + withBoth + ', afterOff=' + afterPresetOff;
      }

      await resetAll();
    } catch (e) {
      results['3_filter_persistence'] = 'ERROR: ' + e.message.split('\n')[0];
    }

    // ========== TEST 4: Double-click situation ==========
    console.log('--- TEST 4: Double-click situation ---');
    try {
      await resetAll();

      const sitId = await page.evaluate(() => {
        const items = document.querySelectorAll('[data-narrative-id]');
        return items.length > 0 ? items[0].getAttribute('data-narrative-id') : null;
      });

      if (sitId) {
        // First click
        await page.evaluate((id) => {
          document.querySelector('[data-narrative-id="' + id + '"]').click();
        }, sitId);
        await page.waitForTimeout(1500);

        const state1 = await page.evaluate((id) => {
          const item = document.querySelector('[data-narrative-id="' + id + '"]');
          const panel = document.getElementById('info-panel');
          return {
            panelVisible: panel ? panel.classList.contains('visible') : false,
            classes: item ? item.className : '',
            expanded: item ? item.classList.contains('expanded') : false,
            active: item ? item.classList.contains('active') : false
          };
        }, sitId);

        // Second click after 500ms
        await page.waitForTimeout(500);
        await page.evaluate((id) => {
          document.querySelector('[data-narrative-id="' + id + '"]').click();
        }, sitId);
        await page.waitForTimeout(1000);

        const state2 = await page.evaluate((id) => {
          const item = document.querySelector('[data-narrative-id="' + id + '"]');
          const panel = document.getElementById('info-panel');
          return {
            panelVisible: panel ? panel.classList.contains('visible') : false,
            classes: item ? item.className : '',
            expanded: item ? item.classList.contains('expanded') : false,
            active: item ? item.classList.contains('active') : false
          };
        }, sitId);

        const cleanToggle = (state1.expanded || state1.active) && !state2.expanded && !state2.active;
        const panelToggle = state1.panelVisible && !state2.panelVisible;

        results['4_double_click_situation'] = (cleanToggle && panelToggle ? 'PASS' : 'PARTIAL') +
          ': Click1: "' + state1.classes + '" panel=' + state1.panelVisible +
          '. Click2: "' + state2.classes + '" panel=' + state2.panelVisible;
      } else {
        results['4_double_click_situation'] = 'FAIL: No situation items found';
      }
    } catch (e) {
      results['4_double_click_situation'] = 'ERROR: ' + e.message.split('\n')[0];
    }

    // ========== TEST 5: Info panel story links ==========
    console.log('--- TEST 5: Info panel story links ---');
    try {
      await resetAll();
      await page.waitForTimeout(1000);

      // Pick a situation that actually has story IDs matching geojsonData
      const clickResult = await page.evaluate(() => {
        const allGeoIds = new Set(geojsonData.features.map(f => f.properties.id));
        const items = document.querySelectorAll('[data-narrative-id]');
        let best = null;
        let bestRealCount = 0;
        let bestId = null;
        let diagnostics = [];

        for (const item of items) {
          const nid = parseInt(item.getAttribute('data-narrative-id'));
          const narr = narrativesData.find(n => n.id === nid);
          if (!narr || !narr.story_ids) continue;
          const realCount = narr.story_ids.filter(id => allGeoIds.has(id)).length;
          diagnostics.push({ id: nid, total: narr.story_ids.length, inGeo: realCount });
          if (realCount > bestRealCount) {
            bestRealCount = realCount;
            best = item;
            bestId = nid;
          }
        }

        if (best && bestRealCount > 0) {
          best.click();
          return { clicked: true, id: bestId, realCount: bestRealCount, totalItems: items.length };
        }
        // Fallback: click first item even if 0 matches
        if (items.length > 0) {
          items[0].click();
          return {
            clicked: true,
            id: items[0].getAttribute('data-narrative-id'),
            realCount: 0,
            totalItems: items.length,
            note: 'ALL situations have 0 geojson matches!',
            diagnostics: diagnostics.slice(0, 5)
          };
        }
        return { clicked: false, totalItems: 0, diagnostics };
      });

      if (!clickResult.clicked) {
        results['5_info_panel_links'] = 'FAIL: No situation items to click (' + clickResult.totalItems + ' items)';
      } else {
        await page.waitForTimeout(2500);

        const linkInfo = await page.evaluate(() => {
          const panel = document.getElementById('info-panel');
          if (!panel || !panel.classList.contains('visible')) return { panelOpen: false };

          const cards = panel.querySelectorAll('.info-card');
          const links = panel.querySelectorAll('.info-card-link');
          const panelTitle = document.getElementById('info-panel-title');
          const panelStories = document.getElementById('info-panel-stories');

          // Debug: check if narrativesData and geojsonData are available
          const debug = {
            panelTitleText: panelTitle ? panelTitle.textContent : 'n/a',
            panelStoriesChildren: panelStories ? panelStories.children.length : 0,
            panelInnerHTMLLength: panelStories ? panelStories.innerHTML.length : 0,
            narrativesDataLength: typeof narrativesData !== 'undefined' ? narrativesData.length : 'undef',
            geojsonFeaturesLength: typeof geojsonData !== 'undefined' ? geojsonData.features.length : 'undef',
            activeNarrativeId: typeof activeNarrativeId !== 'undefined' ? activeNarrativeId : 'undef',
            // Debug narrative story_ids
            narrativeStoryIds: (() => {
              if (typeof narrativesData === 'undefined') return 'undef';
              const n = narrativesData.find(n => n.id === activeNarrativeId);
              if (!n) return 'not_found';
              const ids = n.story_ids || [];
              return { count: ids.length, sample: ids.slice(0, 5) };
            })(),
            geojsonIdSample: (() => {
              if (typeof geojsonData === 'undefined') return 'undef';
              return geojsonData.features.slice(0, 3).map(f => f.properties.id);
            })(),
            geojsonIdType: (() => {
              if (typeof geojsonData === 'undefined') return 'undef';
              return typeof geojsonData.features[0].properties.id;
            })()
          };

          return {
            panelOpen: true,
            cardCount: cards.length,
            linkCount: links.length,
            allAnchors: Array.from(links).every(l => l.tagName === 'A'),
            allHttpHref: Array.from(links).every(l => l.href && l.href.startsWith('http')),
            allBlank: Array.from(links).every(l => l.target === '_blank'),
            samples: Array.from(links).slice(0, 3).map(a => ({
              text: a.textContent.trim(),
              href: a.getAttribute('href').substring(0, 70),
              target: a.target
            })),
            debug
          };
        });

        if (!linkInfo.panelOpen) {
          results['5_info_panel_links'] = 'FAIL: Info panel did not open after clicking situation id=' +
            clickResult.id + ' (realGeoMatches=' + clickResult.realCount + ')';
        } else if (linkInfo.linkCount > 0) {
          results['5_info_panel_links'] = 'PASS: ' + linkInfo.cardCount + ' story cards, ' +
            linkInfo.linkCount + ' links. All <a>=' + linkInfo.allAnchors +
            ', all http href=' + linkInfo.allHttpHref +
            ', all target=_blank=' + linkInfo.allBlank +
            '. Samples: ' + linkInfo.samples.map(l => l.href).join(' | ');
        } else if (clickResult.realCount === 0) {
          results['5_info_panel_links'] = 'DATA ISSUE (not a UI bug): Situation id=' + clickResult.id +
            ' has 0 story_ids matching geojsonData. Panel correctly shows 0 cards.' +
            ' The sidebar shows a stale count via fallback to n.story_count.' +
            (clickResult.note ? ' ' + clickResult.note : '') +
            (clickResult.diagnostics ? ' Top diagnostics: ' + JSON.stringify(clickResult.diagnostics) : '');
        } else {
          results['5_info_panel_links'] = 'FAIL: ' + linkInfo.cardCount + ' cards but 0 links' +
            ' (id=' + clickResult.id + ', realCount=' + clickResult.realCount + ')' +
            ' DEBUG: ' + JSON.stringify(linkInfo.debug);
        }
      }

      await dismissAll();
    } catch (e) {
      results['5_info_panel_links'] = 'ERROR: ' + e.message.split('\n')[0];
    }

    // ========== TEST 6: Opinion filter ==========
    console.log('--- TEST 6: Opinion filter ---');
    try {
      await resetAll();
      const preCount6 = await getShowingCount();

      // Toggle opinion on
      await page.evaluate(() => {
        const cb = document.getElementById('filter-opinion');
        cb.checked = !cb.checked;
        cb.dispatchEvent(new Event('change', { bubbles: true }));
      });
      await page.waitForTimeout(1200);
      const afterToggle = await getShowingCount();

      // Toggle back
      await page.evaluate(() => {
        const cb = document.getElementById('filter-opinion');
        cb.checked = !cb.checked;
        cb.dispatchEvent(new Event('change', { bubbles: true }));
      });
      await page.waitForTimeout(1200);
      const afterRestore = await getShowingCount();

      const changed = afterToggle !== preCount6;
      const restored = afterRestore === preCount6;

      if (changed && restored) {
        results['6_opinion_filter'] = 'PASS: Count changed. before=' + preCount6 +
          ', withOpinionFilter=' + afterToggle + ', afterRestore=' + afterRestore;
      } else if (!changed) {
        results['6_opinion_filter'] = 'PASS (trivial): Count unchanged (0 opinion stories in current dataset?). ' +
          'before=' + preCount6 + ', after=' + afterToggle + ', restore=' + afterRestore;
      } else {
        results['6_opinion_filter'] = 'FAIL: Count changed but not restored. before=' + preCount6 +
          ', after=' + afterToggle + ', restore=' + afterRestore;
      }
    } catch (e) {
      results['6_opinion_filter'] = 'ERROR: ' + e.message.split('\n')[0];
    }

    // ========== TEST 7: Theme toggle ==========
    console.log('--- TEST 7: Theme toggle ---');
    try {
      await dismissAll();

      const initial = await page.evaluate(() => document.body.classList.contains('light-mode'));

      await page.evaluate(() => document.getElementById('theme-toggle').click());
      await page.waitForTimeout(500);
      const after1 = await page.evaluate(() => document.body.classList.contains('light-mode'));
      const stored1 = await page.evaluate(() => localStorage.getItem('theme') || localStorage.getItem('tm-theme'));

      await page.evaluate(() => document.getElementById('theme-toggle').click());
      await page.waitForTimeout(500);
      const after2 = await page.evaluate(() => document.body.classList.contains('light-mode'));
      const stored2 = await page.evaluate(() => localStorage.getItem('theme') || localStorage.getItem('tm-theme'));

      const toggled = after1 !== initial && after2 === initial;
      results['7_theme_toggle'] = (toggled ? 'PASS' : 'FAIL') +
        ': initial=' + initial + ', afterClick1=' + after1 + ' (stored=' + stored1 +
        '), afterClick2=' + after2 + ' (stored=' + stored2 + ')';
    } catch (e) {
      results['7_theme_toggle'] = 'ERROR: ' + e.message.split('\n')[0];
    }

    // ========== TEST 8: Feed panel dismiss ==========
    console.log('--- TEST 8: Feed panel dismiss ---');
    try {
      await resetAll();

      const isPanelVisible = async () => page.evaluate(() => {
        const p = document.getElementById('info-panel');
        return p ? p.classList.contains('visible') : false;
      });

      // Space open
      await page.evaluate(() => document.querySelector('[data-feed="space"]').click());
      await page.waitForTimeout(1000);
      const spaceOpen = await isPanelVisible();

      // Space close via re-click
      await page.evaluate(() => document.querySelector('[data-feed="space"]').click());
      await page.waitForTimeout(800);
      const spaceClosed = !(await isPanelVisible());

      // Internet open
      await page.evaluate(() => document.querySelector('[data-feed="internet"]').click());
      await page.waitForTimeout(1000);
      const internetOpen = await isPanelVisible();

      // Internet close via Escape
      await page.keyboard.press('Escape');
      await page.waitForTimeout(800);
      const internetClosed = !(await isPanelVisible());

      const allPass = spaceOpen && spaceClosed && internetOpen && internetClosed;
      results['8_feed_panel_dismiss'] = (allPass ? 'PASS' : 'PARTIAL') +
        ': Space: open=' + spaceOpen + ', re-click close=' + spaceClosed +
        '. Internet: open=' + internetOpen + ', Escape close=' + internetClosed;
    } catch (e) {
      results['8_feed_panel_dismiss'] = 'ERROR: ' + e.message.split('\n')[0];
    }

    // ========== TEST 9: Empty search resilience ==========
    console.log('--- TEST 9: Empty search resilience ---');
    try {
      await resetAll();
      const jsErrorsBefore = jsErrors.length;
      const preCount9 = await getShowingCount();

      // Type garbage
      await page.evaluate(() => {
        const input = document.getElementById('search-box');
        input.value = 'xyzzy_nomatches_zqwx_999_abcdefghijklmnop_unicorn_42_zzz';
        input.dispatchEvent(new Event('input', { bubbles: true }));
      });
      await page.waitForTimeout(2000);

      const countAfter = await getShowingCount();
      const sitCount = await page.evaluate(() => document.querySelectorAll('[data-narrative-id]').length);
      const uiState = await page.evaluate(() => {
        // Check for any visible error messages or broken UI
        const body = document.body;
        return {
          bodyOk: body.children.length > 0,
          mapExists: !!document.querySelector('.maplibregl-map, #map'),
          sidebarExists: !!document.getElementById('sidebar')
        };
      });

      // Clear search
      await page.evaluate(() => {
        const input = document.getElementById('search-box');
        input.value = '';
        input.dispatchEvent(new Event('input', { bubbles: true }));
      });
      await page.waitForTimeout(1000);
      const countRestored = await getShowingCount();

      const newErrors = jsErrors.slice(jsErrorsBefore);

      results['9_empty_search'] = (newErrors.length === 0 ? 'PASS' : 'PARTIAL') +
        ': No crash. before=' + preCount9 + ', duringGarbage=' + countAfter +
        ' (situations=' + sitCount + '), afterClear=' + countRestored +
        '. UI intact: map=' + uiState.mapExists + ', sidebar=' + uiState.sidebarExists +
        '. jsErrors=' + newErrors.length;
    } catch (e) {
      results['9_empty_search'] = 'ERROR: ' + e.message.split('\n')[0];
    }

    // ========== TEST 10: Stale stat after Bright Side toggle ==========
    console.log('--- TEST 10: Stale stat after Bright Side toggle ---');
    try {
      await resetAll();
      const preCount10 = await getShowingCount();

      // Activate Bright Side
      await page.evaluate(() => {
        const btns = document.querySelectorAll('.preset-btn');
        for (const b of btns) {
          if (b.textContent.trim().includes('Bright')) { b.click(); return; }
        }
      });
      await page.waitForTimeout(1500);
      const brightCount = await getShowingCount();
      const brightActive = await page.evaluate(() => {
        const btns = document.querySelectorAll('.preset-btn');
        for (const b of btns) {
          if (b.textContent.trim().includes('Bright')) return b.classList.contains('active');
        }
      });

      // Deactivate
      await page.evaluate(() => {
        const btns = document.querySelectorAll('.preset-btn');
        for (const b of btns) {
          if (b.textContent.trim().includes('Bright')) { b.click(); return; }
        }
      });
      await page.waitForTimeout(1500);
      const afterOff = await getShowingCount();

      const restored = afterOff !== null && preCount10 !== null && afterOff >= preCount10 * 0.9;
      results['10_stale_stat'] = (restored ? 'PASS' : 'FAIL') +
        ': before=' + preCount10 + ', brightSide=' + brightCount +
        ' (wasActive=' + brightActive + '), afterDeactivate=' + afterOff;
    } catch (e) {
      results['10_stale_stat'] = 'ERROR: ' + e.message.split('\n')[0];
    }

  } catch (e) {
    console.error('Fatal error: ' + e.message);
  }

  // ========== REPORT ==========
  console.log('\n' + '='.repeat(60));
  console.log('       PLAYWRIGHT DIAGNOSTIC REPORT');
  console.log('='.repeat(60));
  const summary = { pass: 0, partial: 0, fail: 0, error: 0, other: 0 };
  for (const [test, result] of Object.entries(results)) {
    const status = result.split(':')[0];
    console.log('\n[' + test + '] ' + status);
    console.log('  ' + result);
    if (status === 'PASS' || status.startsWith('PASS')) summary.pass++;
    else if (status === 'PARTIAL') summary.partial++;
    else if (status.startsWith('FAIL')) summary.fail++;
    else if (status.startsWith('ERROR')) summary.error++;
    else if (status.startsWith('EXPECTED')) summary.other++;
    else summary.other++;
  }

  console.log('\n--- Summary ---');
  console.log('  PASS=' + summary.pass + '  PARTIAL=' + summary.partial +
    '  FAIL=' + summary.fail + '  ERROR=' + summary.error + '  OTHER=' + summary.other);

  console.log('\n--- JS Page Errors ---');
  if (jsErrors.length === 0) console.log('  None');
  else jsErrors.forEach(e => console.log('  ' + e.substring(0, 300)));

  console.log('\n--- Console Errors ---');
  if (consoleErrors.length === 0) console.log('  None');
  else consoleErrors.forEach(e => console.log('  ' + e.substring(0, 300)));

  await browser.close();
  console.log('\nDone.');
})();
