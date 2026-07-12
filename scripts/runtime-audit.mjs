import { spawn } from 'node:child_process'
import { createRequire } from 'node:module'
import http from 'node:http'

const require = createRequire(import.meta.url)
const { chromium } = require('C:/Users/T1372/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright')

const root = new URL('../', import.meta.url).pathname.replace(/^\/([A-Z]:)/, '$1')
const processes = []

function start(command, args, cwd) {
  const child = spawn(command, args, { cwd, windowsHide: true })
  child.stdout.on('data', (data) => process.stdout.write(String(data)))
  child.stderr.on('data', (data) => process.stderr.write(String(data)))
  processes.push(child)
  return child
}

function waitFor(url, timeoutMs = 20000) {
  const end = Date.now() + timeoutMs
  return new Promise((resolve, reject) => {
    const tick = () => {
      http
        .get(url, (response) => {
          response.resume()
          resolve()
        })
        .on('error', () => {
          if (Date.now() > end) reject(new Error(`timeout ${url}`))
          else setTimeout(tick, 500)
        })
    }
    tick()
  })
}

async function main() {
  start('python', ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000'], `${root}/backend`)
  start(process.env.ComSpec || 'cmd.exe', ['/c', 'npm.cmd', 'run', 'dev', '--', '--host', '127.0.0.1'], `${root}/frontend`)

  await waitFor('http://127.0.0.1:8000/api/health')
  await waitFor('http://127.0.0.1:5173/')

  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 430, height: 844 }, deviceScaleFactor: 2, isMobile: true })
  const logs = []
  page.on('console', (message) => {
    if (['error', 'warning'].includes(message.type())) logs.push(`${message.type()}: ${message.text()}`)
  })
  page.on('pageerror', (error) => logs.push(`pageerror: ${error.message}`))

  await page.goto('http://127.0.0.1:5173/', { waitUntil: 'networkidle' })

  // Text mode: select scene, chat, end, and inspect replay details.
  await page.locator('text=开始挑战').first().click()
  await page.locator('text=开始体验').click()
  await page.locator('input[placeholder="输入您的回复..."]').fill('我需要先核实一下')
  await page.locator('button.send').click()
  await page.waitForTimeout(1200)
  await page.locator('text=结束挑战').click()
  await page.waitForTimeout(500)
  const title = await page.locator('.page-title').textContent()
  const hasDetail = await page.locator('text=查看复盘详情').count()
  await page.locator('text=查看复盘详情').click()
  await page.locator('text=对话记录').click()
  await page.waitForTimeout(300)
  const detailText = await page.locator('.glass-panel').textContent()

  // Phone mode: accept call, send a quick reply through the same backend session, then hang up.
  await page.goto('http://127.0.0.1:5173/', { waitUntil: 'networkidle' })
  await page.locator('text=开始挑战').first().click()
  await page.locator('label.mode').nth(1).click()
  await page.locator('text=开始体验').click()
  await page.locator('text=接听').click()
  await page.locator('.call-quick button').first().click()
  await page.waitForTimeout(1200)
  const phoneHasReply = (await page.locator('.call-quick').count()) === 1
  await page.locator('button.hangup').click()
  await page.waitForTimeout(500)
  const phoneReviewTitle = await page.locator('.page-title').textContent()

  // Video mode: reuse call session logic with quick reply and hangup.
  await page.goto('http://127.0.0.1:5173/', { waitUntil: 'networkidle' })
  await page.locator('text=开始挑战').first().click()
  await page.locator('label.mode').nth(2).click()
  await page.locator('text=开始体验').click()
  await page.locator('.video-quick button').first().click()
  await page.waitForTimeout(1200)
  const videoHasReply = (await page.locator('.video-quick').count()) === 1
  await page.locator('button.hangup').click()
  await page.waitForTimeout(500)
  const videoReviewTitle = await page.locator('.page-title').textContent()

  await page.locator('text=换个场景').click()
  await page.locator('text=历史记录').click()
  const historyHasRecord = (await page.locator('.history-list button').count()) > 0

  const size = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    scrollHeight: document.documentElement.scrollHeight,
    clientHeight: document.documentElement.clientHeight
  }))

  await browser.close()
  console.log(JSON.stringify({
    textFlow: { title, hasDetail, detailHasUser: detailText.includes('我需要先核实一下') },
    phoneFlow: { phoneHasReply, phoneReviewTitle },
    videoFlow: { videoHasReply, videoReviewTitle },
    historyFlow: { historyHasRecord },
    logs,
    size
  }, null, 2))
}

main()
  .catch((error) => {
    console.error(error)
    process.exitCode = 1
  })
  .finally(() => {
    for (const child of processes) {
      try {
        child.kill()
      } catch {}
    }
    setTimeout(() => process.exit(process.exitCode || 0), 300)
  })
