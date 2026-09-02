#!/usr/bin/env node
/**
 * The picture a link to the site shows in a messenger.
 *
 * Ссылку на курс пересылают в WhatsApp и Telegram — там карточка без изображения выглядит
 * как ссылка на что-то сомнительное. Картинка рисуется здесь, а не берётся из макета,
 * которого для неё нет: цвета и шрифт те же, что и на сайте, потому что берутся из
 * `tokens.json` и из того же файла шрифта.
 *
 * Рисует браузер, которым и так проверяются сценарии: SVG соцсети не принимают, а тащить
 * растеризатор ради одной картинки дороже, чем открыть страницу и снять её.
 *
 *   node tools/covers/og-image.mjs
 */
import { readFileSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { chromium } from '@playwright/test'

const ROOT = resolve(import.meta.dirname, '../..')
const TOKENS = JSON.parse(readFileSync(resolve(ROOT, 'tokens.json'), 'utf8'))
const FONT = resolve(ROOT, 'frontend/src/assets/fonts/manrope-cyrillic.woff2')
const OUT = resolve(ROOT, 'frontend/public/og-cover.jpg')

// Размер, который читают все: 1200×630 — то, что просят и Open Graph, и Telegram.
const WIDTH = 1200
const HEIGHT = 630

const color = (group, step) => TOKENS.color[group][step].$value

const page = `<!doctype html>
<meta charset="utf-8" />
<style>
  @font-face {
    font-family: 'Manrope';
    src: url('data:font/woff2;base64,${readFileSync(FONT).toString('base64')}') format('woff2');
    font-weight: 200 800;
  }
  html, body { margin: 0; padding: 0; }
  body {
    width: ${WIDTH}px; height: ${HEIGHT}px;
    display: flex; flex-direction: column; justify-content: space-between;
    box-sizing: border-box; padding: 80px;
    font-family: 'Manrope', sans-serif; letter-spacing: -0.03em;
    color: #ffffff;
    background:
      radial-gradient(120% 120% at 100% 0%, ${color('primary', 500)} 0%, transparent 55%),
      linear-gradient(140deg, ${color('primary', 950)} 0%, ${color('primary', 800)} 100%);
  }
  .mark { font-size: 34px; font-weight: 800; letter-spacing: 0.08em; }
  h1 { margin: 0; font-size: 66px; font-weight: 800; line-height: 1.08; max-width: 900px; }
  p { margin: 0; font-size: 30px; font-weight: 500; color: ${color('primary', 200)}; }
</style>
<div class="mark">ЦАИДМО</div>
<h1>Центрально-Азиатский Институт Дополнительного Медицинского Образования</h1>
<p>Повышение квалификации для врачей и медсестёр</p>
`

const browser = await chromium.launch()
const tab = await browser.newPage({ viewport: { width: WIDTH, height: HEIGHT } })
await tab.setContent(page)
await tab.evaluate(() => document.fonts.ready)
// JPEG, а не PNG: на градиенте разница в четыре раза, а картинку эту грузят
// мессенджеры на телефонах.
writeFileSync(OUT, await tab.screenshot({ type: 'jpeg', quality: 90 }))
await browser.close()
console.log(`written: ${OUT}`)
