/* SPDX-License-Identifier: GPL-3.0-only
 * Run after installing Playwright/Chromium: node tests/browser_regressions.cjs
 */
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {pathToFileURL} = require('node:url');
const {chromium} = require('playwright');

const root = path.resolve(__dirname, '..');
const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'ganttify-regressions-'));
const elementId = 'ganttify-browser-test';

async function settled(page) {
    await page.waitForFunction(id => {
        const runtime = document.getElementById(id).__ganttifyRuntime;
        return runtime && runtime.state.lastRangeKey && !runtime.state.running &&
            !runtime.state.pending && runtime.state.timer === null && runtime.state.internal === 0;
    }, elementId);
}

function fixture(caseName) {
    const target = path.join(temporary, `${caseName}.html`);
    const result = spawnSync(process.env.PYTHON || 'python',
        [...(process.env.GANTTIFY_TEST_INSTALLED ? ['-I'] : []),
            path.join(__dirname, 'browser_fixture.py'), target, caseName], {
            cwd: root,
            encoding: 'utf8',
            env: {...process.env, PYTHONPATH: path.join(root, 'src')},
        });
    assert.equal(result.status, 0, result.stderr || result.stdout);
    return target;
}

async function hover(page, when, row, expected) {
    await page.mouse.move(1, 1);
    const point = await page.evaluate(({id, when, row}) => {
        const el = document.getElementById(id);
        const box = el.getBoundingClientRect();
        const x = el._fullLayout.xaxis;
        const y = el._fullLayout.yaxis;
        return {x: box.left + x._offset + x.d2p(when), y: box.top + y._offset + y.d2p(row)};
    }, {id: elementId, when, row});
    assert.ok(Number.isFinite(point.x) && Number.isFinite(point.y), JSON.stringify(point));
    await page.mouse.move(point.x, point.y);
    await page.waitForFunction(expected => [...document.querySelectorAll('.hoverlayer .hovertext')]
        .some(node => node.textContent.includes(expected)), expected, {timeout: 5000});
    return page.locator('.hoverlayer .hovertext').allTextContents();
}

async function main() {
    const browser = await chromium.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-dev-shm-usage'],
        ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ?
            {executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE} : {}),
    });
    const errors = [];
    const requests = [];
    let checks = 0;
    async function open(caseName) {
        const page = await browser.newPage({viewport: {width: 1200, height: 900}});
        page.on('pageerror', error => errors.push(`${caseName}: ${error.message}`));
        page.on('console', message => {
            if (message.type() === 'error' || message.type() === 'warning') {
                errors.push(`${caseName}: ${message.text()}`);
            }
        });
        page.on('request', request => {
            if (/^https?:/.test(request.url())) requests.push(request.url());
        });
        await page.goto(pathToFileURL(fixture(caseName)).href);
        await settled(page);
        return page;
    }
    try {
        let page = await open('margin');
        const labels = await page.evaluate(id => {
            const el = document.getElementById(id);
            const boundary = el.getBoundingClientRect().left + el._fullLayout.margin.l;
            return [...el.querySelectorAll('.ytick text')].map(node => ({
                right: node.getBoundingClientRect().right,
                boundary,
                title: node.querySelector('title')?.textContent,
            }));
        }, elementId);
        assert.ok(labels.length > 0);
        assert.ok(labels.some(label => label.title), 'narrow-gutter truncation keeps full titles');
        for (const label of labels) assert.ok(label.right <= label.boundary + 1, JSON.stringify(label));
        checks += 1;
        await page.close();

        page = await open('labels');
        async function customLabels() {
            return page.evaluate(() => [...document.querySelectorAll('.ytick text')].map(node => ({
                visible: node.textContent,
                full: node.querySelector('title')?.textContent,
                count: node.querySelectorAll('title').length,
            })));
        }
        let custom = await customLabels();
        assert.ok(custom.length > 0);
        for (const label of custom) {
            assert.ok(label.full?.startsWith('Custom row '), JSON.stringify(label));
            assert.equal(label.count, 1);
        }
        await page.evaluate(async id => Plotly.relayout(document.getElementById(id),
            {'xaxis.range': ['2024-09-01', '2024-10-01']}), elementId);
        await settled(page);
        custom = await customLabels();
        for (const label of custom) {
            assert.ok(label.full?.startsWith('Custom row '), JSON.stringify(label));
            assert.equal(label.count, 1);
        }
        checks += 1;
        await page.close();

        page = await open('static');
        const before = await page.evaluate(id => document.getElementById(id).layout.yaxis.range.slice(), elementId);
        await page.mouse.move(500, 250);
        await page.mouse.wheel(0, 200);
        await page.waitForTimeout(150);
        assert.deepEqual(await page.evaluate(id => document.getElementById(id).layout.yaxis.range, elementId), before,
            'staticPlot disables Ganttify wheel interaction');
        checks += 1;
        await page.close();

        page = await open('line');
        for (const row of [1, 1.25, 1.75, 2]) await hover(page, '2025-01-20', row, 'Deadline');
        await page.evaluate(async id => Plotly.relayout(document.getElementById(id), {height: 700}), elementId);
        await settled(page);
        for (const row of [1, 1.25, 1.75, 2]) await hover(page, '2025-01-20', row, 'Deadline');
        checks += 1;
        await page.close();

        page = await open('line-scroll');
        const initialScroll = await page.evaluate(id => document.getElementById(id).layout.yaxis.range[0], elementId);
        await page.mouse.move(500, 200);
        await page.mouse.wheel(0, 120);
        await page.waitForFunction(({id, previous}) =>
            document.getElementById(id).layout.yaxis.range[0] < previous,
        {id: elementId, previous: initialScroll});
        await settled(page);
        const range = await page.evaluate(id => document.getElementById(id).layout.yaxis.range.slice(), elementId);
        await hover(page, '2025-01-20', (range[0] + range[1]) / 2, 'Deadline');
        checks += 1;
        await page.close();

        page = await open('area');
        await page.evaluate(async id => Plotly.relayout(document.getElementById(id),
            {'xaxis.range': ['2025-01-11', '2025-01-12']}), elementId);
        await settled(page);
        const top = await page.evaluate(id => document.getElementById(id).layout.yaxis.range[1], elementId);
        const areaText = await hover(page, '2025-01-11 12:00:00', top - 0.03, 'Long review area');
        assert.ok(areaText.some(text => text.includes('1900-01-01') && text.includes('2100-01-01')),
            'zoomed area hover retains original interval');
        checks += 1;
        await page.close();

        page = await open('normalized');
        const activity = await page.evaluate(id => {
            const el = document.getElementById(id);
            const trace = el.data.find(item => item.meta?.ganttify?.role === 'actual');
            return {y: trace.y[0], color: trace.marker.color};
        }, elementId);
        assert.equal(activity.color, 'red', 'JSON numeric category mapping is resolved');
        const actualText = await hover(page, '2025-01-20', activity.y, 'Computed actual end');
        assert.ok(actualText.some(text => text.includes('Computed actual end: 2025-02-01')));
        const midpoint = await page.evaluate(id => {
            const range = document.getElementById(id).layout.yaxis.range;
            return (range[0] + range[1]) / 2;
        }, elementId);
        const sameDay = await hover(page, '2025-02-05', midpoint, 'One day range');
        assert.ok(sameDay.some(text => text.includes('Start: 2025-02-05') && text.includes('End: 2025-02-05') &&
            text.includes('Duration: 1 days')), 'equal-endpoint interval keeps interval tooltip');
        checks += 1;
        await page.close();

        for (const position of ['bottom', 'top', 'both']) {
            for (const activityLabels of [0, 1]) {
                for (const wbsLabels of [0, 1]) {
                    page = await open(`matrix-${position}-${activityLabels}-${wbsLabels}`);
                    const state = await page.evaluate(id => {
                        const el = document.getElementById(id);
                        return {side: el.layout.xaxis.side, top: !!el.layout.xaxis2,
                            labels: [...el.querySelectorAll('.ytick text')].map(node => node.textContent)};
                    }, elementId);
                    assert.equal(state.side, position === 'top' ? 'top' : 'bottom');
                    assert.equal(state.top, position === 'both');
                    assert.equal(state.labels.some(label => label.includes('•')), !!activityLabels);
                    assert.equal(state.labels.some(label => label.includes('Project Summary')), !!wbsLabels);
                    checks += 1;
                    await page.close();
                }
            }
        }
        assert.deepEqual(errors, []);
        assert.deepEqual(requests, []);
        console.log(`Chromium parity regressions passed: ${checks} cases, no browser errors or external requests.`);
    } finally {
        await browser.close();
    }
}

main().catch(error => {
    console.error(error);
    process.exitCode = 1;
}).finally(() => fs.rmSync(temporary, {recursive: true, force: true}));
