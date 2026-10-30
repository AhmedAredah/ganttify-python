/* SPDX-License-Identifier: GPL-3.0-only
 * Optional real-browser integration test. Install playwright and its Chromium first:
 * npm install --no-save playwright
 * npx playwright install chromium
 * node tests/browser_smoke.cjs
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
const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'ganttify-browser-test-'));
const html = path.join(temporary, 'chart.html');

async function settled(page) {
    await page.waitForFunction(() => {
        const runtime = document.getElementById('ganttify-browser-test').__ganttifyRuntime;
        return runtime && runtime.state.lastRangeKey && !runtime.state.running &&
            !runtime.state.pending && runtime.state.timer === null && runtime.state.internal === 0;
    });
}

async function snapshot(page) {
    return page.evaluate(() => {
        const el = document.getElementById('ganttify-browser-test');
        const trace = el.data.find(item => item.meta?.ganttify?.id === 'SAME-DAY');
        return {
            range: el.layout.xaxis.range,
            xType: el.layout.xaxis.type,
            topType: el.layout.xaxis2.type,
            width: trace.x[0],
            base: trace.base[0],
            original: trace.meta.ganttify,
            hover: trace.hovertext[0],
            shapes: el.layout.shapes.map(shape => shape.name),
            ticks: el.layout.xaxis.ticktext,
            topTicks: el.layout.xaxis2.ticktext,
            y: el.layout.yaxis.range,
            rows: el.layout.meta.ganttify.total_rows,
            actuals: el.data.filter(item => item.meta?.ganttify?.role === 'actual').length,
            patterns: document.querySelectorAll('pattern').length,
            lastError: el.__ganttifyRuntime.state.lastError?.message || null,
        };
    });
}

async function hoverBar(page, id, role, atDate, expected) {
    const point = await page.evaluate(({id, role, atDate}) => {
        const el = document.getElementById('ganttify-browser-test');
        const trace = el.data.find(item => item.meta?.ganttify?.id === id &&
            item.meta.ganttify.role === role);
        const bounds = el.getBoundingClientRect();
        const xaxis = el._fullLayout.xaxis;
        const yaxis = el._fullLayout.yaxis;
        return {
            x: bounds.left + xaxis._offset + xaxis.d2p(atDate),
            y: bounds.top + yaxis._offset + yaxis.d2p(trace.y[0]),
            xRange: xaxis.range,
            xType: xaxis.type,
            xLayout: el.layout.xaxis,
            yRange: yaxis.range,
            row: trace.y[0],
        };
    }, {id, role, atDate});
    assert.ok(Number.isFinite(point.x) && Number.isFinite(point.y),
        `Hover coordinates must be finite: ${JSON.stringify(point)}`);
    await page.mouse.move(point.x, point.y);
    await page.waitForSelector('.hoverlayer .hovertext');
    try {
        await page.waitForFunction(expected => [...document.querySelectorAll('.hoverlayer .hovertext')]
            .some(node => node.textContent.includes(expected)), expected, {timeout: 5000});
    } catch (error) {
        const actual = await page.locator('.hoverlayer .hovertext').allTextContents();
        if (process.env.GANTTIFY_SCREENSHOT) await page.screenshot({path: process.env.GANTTIFY_SCREENSHOT});
        throw new Error(`Expected hover containing ${JSON.stringify(expected)}; saw ${JSON.stringify(actual)} at ${JSON.stringify(point)}`, {cause: error});
    }
    return page.locator('.hoverlayer .hovertext').allTextContents();
}

async function main() {
    const generated = spawnSync(process.env.PYTHON || 'python',
        [...(process.env.GANTTIFY_TEST_INSTALLED ? ['-I'] : []),
            path.join(__dirname, 'browser_fixture.py'), html], {
            cwd: root,
            encoding: 'utf8',
            env: {...process.env, PYTHONPATH: path.join(root, 'src')},
        });
    assert.equal(generated.status, 0, generated.stderr || generated.stdout);
    const browser = await chromium.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-dev-shm-usage'],
        ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ?
            {executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE} : {}),
    });
    try {
        const page = await browser.newPage({viewport: {width: 1200, height: 800}});
        const errors = [];
        const networkRequests = [];
        page.on('request', request => {
            if (/^https?:/.test(request.url())) networkRequests.push(request.url());
        });
        page.on('pageerror', error => errors.push(error.message));
        page.on('console', message => {
            if (message.type() === 'error' || message.type() === 'warning') errors.push(message.text());
        });
        await page.goto(pathToFileURL(html).href);
        await settled(page);
        const initial = await snapshot(page);
        assert.equal(initial.xType, 'date');
        assert.equal(initial.rows, 24);
        assert.equal(initial.actuals, 13);
        assert.ok(initial.patterns > 0, 'actual bars render SVG stripe patterns');
        assert.equal(initial.original.start, '2024-09-10');
        assert.equal(initial.original.end, '2024-09-10');
        assert.match(initial.hover, /2024-09-10/);
        assert.equal(initial.lastError, null);
        assert.equal(initial.shapes.filter(value => value === 'ganttify-milestone').length, 2);
        assert.ok(initial.shapes.includes('ganttify-background'));
        assert.deepEqual(initial.ticks, initial.topTicks);

        const labels = await page.evaluate(() => {
            const el = document.getElementById('ganttify-browser-test');
            const rightLimit = el.getBoundingClientRect().left + el._fullLayout.margin.l;
            return [...el.querySelectorAll('.ytick text')].map(node => ({
                right: node.getBoundingClientRect().right,
                limit: rightLimit,
                title: node.querySelector('title')?.textContent,
                titleCount: node.querySelectorAll('title').length,
                full: node.getAttribute('aria-label'),
            }));
        });
        assert.ok(labels.length > 0);
        for (const label of labels) assert.ok(label.right <= label.limit + 1, JSON.stringify(label));
        assert.ok(labels.some(label => label.title?.includes('deliberately long accessible label')));
        for (const label of labels.filter(label => label.title)) {
            assert.equal(label.title, label.full);
            assert.equal(label.titleCount, 1);
        }

        await page.evaluate(async () => {
            const el = document.getElementById('ganttify-browser-test');
            await Plotly.relayout(el, {'xaxis.range': ['2022-01-01', '2027-01-01']});
        });
        await settled(page);
        const zoomedOut = await snapshot(page);
        assert.equal(zoomedOut.xType, 'date', 'zoom out retains the date axis');
        const expectedOut = (Date.parse('2027-01-01') - Date.parse('2022-01-01')) * 0.003;
        assert.ok(Math.abs(zoomedOut.width - expectedOut) < 1);
        assert.equal(zoomedOut.hover, initial.hover);
        assert.equal(zoomedOut.shapes.filter(value => value === 'ganttify-milestone').length, 2);
        assert.deepEqual(zoomedOut.ticks, zoomedOut.topTicks);

        await page.evaluate(async () => {
            const el = document.getElementById('ganttify-browser-test');
            await Plotly.relayout(el, {'xaxis.range': ['2024-09-09', '2024-09-11']});
        });
        await settled(page);
        const zoomedIn = await snapshot(page);
        assert.equal(zoomedIn.xType, 'date', 'zoom in retains the date axis');
        assert.ok(Math.abs(zoomedIn.width - 2 * 86400000 * 0.003) < 1);
        const centered = Date.parse(zoomedIn.base) + zoomedIn.width / 2;
        assert.ok(Math.abs(centered - Date.parse('2024-09-10')) < 1);
        assert.equal(zoomedIn.original.start, initial.original.start);
        assert.equal(zoomedIn.hover, initial.hover);

        const box = await page.locator('#ganttify-browser-test').boundingBox();
        await page.mouse.move(box.x + 500, box.y + 200);
        await page.mouse.wheel(0, 200);
        await page.waitForFunction(previous => {
            const el = document.getElementById('ganttify-browser-test');
            return el.layout.yaxis.range[0] < previous;
        }, zoomedIn.y[0]);
        await settled(page);
        const scrolled = await snapshot(page);
        assert.equal(scrolled.xType, 'date', 'wheel scrolling retains the date axis');
        assert.equal(scrolled.y[1] - scrolled.y[0], 8);
        assert.ok(scrolled.y[0] >= 0.5 && scrolled.y[1] <= 24.5);

        await page.evaluate(async () => {
            const el = document.getElementById('ganttify-browser-test');
            await Plotly.relayout(el, {'yaxis.range': [-100, 100]});
        });
        await settled(page);
        const clamped = await snapshot(page);
        assert.equal(clamped.xType, 'date', 'vertical zoom correction retains the date axis');
        assert.equal(clamped.y[1] - clamped.y[0], 8);
        assert.ok(clamped.y[0] >= 0.5 && clamped.y[1] <= 24.5);
        await page.evaluate(() => {
            const el = document.getElementById('ganttify-browser-test');
            el.__smokeEvents = 0;
            el.on('plotly_relayout', () => { el.__smokeEvents += 1; });
        });
        await page.waitForTimeout(200);
        assert.equal(await page.evaluate(() => document.getElementById('ganttify-browser-test').__smokeEvents), 0);
        await page.evaluate(async ({x, y}) => {
            const el = document.getElementById('ganttify-browser-test');
            await Plotly.relayout(el, {'xaxis.range': x, 'yaxis.range': y});
        }, {x: initial.range, y: initial.y});
        await settled(page);
        const restoredLabels = await page.evaluate(() => [...document.querySelectorAll('.ytick text')]
            .filter(node => node.hasAttribute('aria-label')).map(node => ({
                count: node.querySelectorAll('title').length,
                title: node.querySelector('title')?.textContent,
                full: node.getAttribute('aria-label'),
            })));
        assert.ok(restoredLabels.length > 0);
        for (const label of restoredLabels) {
            assert.equal(label.count, 1);
            assert.equal(label.title, label.full);
        }
        // A shaded milestone overlaps these bars; it must not swallow their hovers.
        const sameDayHover = await hoverBar(page, 'SAME-DAY', 'planned', '2024-09-10', 'Same day dispatch');
        assert.ok(sameDayHover.some(text => text.includes('Same day dispatch')), sameDayHover.join(' '));
        const actualHover = await hoverBar(page, 'A1', 'actual', '2024-09-20', 'Design UI');
        assert.ok(actualHover.some(text => text.includes('Design UI') && text.includes('Actual')),
            actualHover.join(' '));

        assert.deepEqual(errors, []);
        assert.deepEqual(networkRequests, [], 'standalone HTML must not request network resources');
        if (process.env.GANTTIFY_SCREENSHOT) await page.screenshot({path: process.env.GANTTIFY_SCREENSHOT});
        console.log('Chromium standalone HTML integration passed: rendering, hovers, labels, zoom, bands, scrolling, axes, and event guards.');
    } finally {
        await browser.close();
    }
}

main().catch(error => {
    console.error(error);
    process.exitCode = 1;
}).finally(() => fs.rmSync(temporary, {recursive: true, force: true}));
