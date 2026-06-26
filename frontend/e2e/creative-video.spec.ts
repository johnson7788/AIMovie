import { test, expect } from 'playwright/test'
import path from 'path'
import { fileURLToPath } from 'url'

/**
 * 创意视频生成：选取一张参考图片 + 一段提示词 -> 生成视频。
 *
 * 覆盖前端 /creative 页面的完整交互：
 *  1. 上传参考图片（Uploads/upload）
 *  2. 填写提示词
 *  3. 自动选中视频模型、设置时长/分辨率
 *  4. 点击「生成视频」，校验 Creative/video 接口返回 task_id
 */

const __dirname = path.dirname(fileURLToPath(import.meta.url))

const FRONTEND = 'http://127.0.0.1:36310/aimovie/'
const BACKEND = 'http://127.0.0.1:8666'
const STORAGE_KEY = 'SHORT-PLAY.USERINFO'
const REFERENCE_IMAGE = path.join(__dirname, 'fixtures', 'reference.jpg')
const PROMPT = '镜头缓慢推进，画面中的人物轻轻微笑，发丝随微风飘动，柔和的自然光，电影级质感。'

test('参考图片 + 提示词 生成创意视频任务', async ({ page, request }) => {
    // 1. 通过后端注册一个全新用户，拿到登录态（token）
    const username = `pwtest_${Date.now().toString(36)}`
    const password = 'pwtest1234'
    const reg = await request.post(`${BACKEND}/app/user/api/Login/register`, {
        data: { username, password, vpassword: password },
    })
    expect(reg.ok()).toBeTruthy()
    const regBody = await reg.json()
    expect(regBody.code).toBe(200)
    const userInfo = regBody.data
    expect(userInfo.token).toBeTruthy()

    // 2. 在 SPA 启动前把登录态写入 localStorage，绕过登录弹窗
    await page.addInitScript(
        ([key, value]) => {
            window.localStorage.setItem(key as string, value as string)
        },
        [STORAGE_KEY, JSON.stringify({ expire: 0, data: userInfo })],
    )

    // 3. 打开创意视频页面（hash 路由）
    await page.goto(`${FRONTEND}#/creative`)
    await expect(page.locator('.creative-input-panel')).toBeVisible()

    // 4. 选取一张参考图片（触发上传），等待预览出现
    const fileInput = page.locator('.creative-upload input[type=file]')
    await fileInput.setInputFiles(REFERENCE_IMAGE)
    await expect(page.locator('.creative-preview-img')).toBeVisible({ timeout: 20_000 })

    // 5. 填写提示词
    const promptBox = page.locator('.creative-input-panel textarea')
    await promptBox.fill(PROMPT)
    await expect(promptBox).toHaveValue(PROMPT)

    // 6. 设置时长 5s / 分辨率 720p（模型已自动选中第一个）
    // Element Plus 单选按钮的 input 被 label 遮挡，点击可见的 label 文本
    await page.locator('label.el-radio-button', { hasText: '720p' }).click()

    // 等待生成按钮可用（图片 + 模型都已就绪）
    const generateBtn = page.locator('.creative-generate-btn')
    await expect(generateBtn).toBeEnabled({ timeout: 20_000 })

    // 7. 点击生成，捕获 Creative/video 接口响应
    const [resp] = await Promise.all([
        page.waitForResponse(
            (r) => r.url().includes('/Creative/video') && r.request().method() === 'POST',
        ),
        generateBtn.click(),
    ])
    const body = await resp.json()
    expect(body.code).toBe(200)
    expect(body.data.task_id).toBeTruthy()
    expect(body.data.status).toBe('pending')

    // 校验提交载荷确实带上了参考图片和提示词
    const payload = resp.request().postDataJSON()
    expect(payload.image_url).toContain('/api/uploads/')
    expect(payload.prompt).toBe(PROMPT)
    expect(payload.resolution).toBe('720p')
    expect(payload.model_id).toBeTruthy()

    await page.screenshot({ path: path.join(__dirname, 'creative-video.png'), fullPage: true })
})
