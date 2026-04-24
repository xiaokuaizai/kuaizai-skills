/**
 * Playwright run-code 脚本模板
 * 使用方式：修改 HTML_PATH 和 PDF_PATH，然后运行：
 *   playwright-cli run-code --filename export_pdf.js
 *
 * 核心要点：
 * - 用 page.goto('file://...') 加载本地 HTML（open 命令会拦截 file 协议）
 * - 动态测量页面尺寸，避免内容被截断
 * - printBackground: true 必须开启，否则背景色丢失
 */

async (page) => {
  const HTML_PATH = 'file:///G:/draw_long/单词划分/逻辑式组成/output/前缀_re-思维导图-v2.html';
  const PDF_PATH  = 'G:/draw_long/单词划分/逻辑式组成/output/前缀_re-思维导图-v2.pdf';

  await page.goto(HTML_PATH, { waitUntil: 'networkidle' });

  // 等待 JS 画线完成
  await page.waitForTimeout(1500);

  // 动态测量内容尺寸，防止裁切
  const dims = await page.evaluate(() => {
    const el = document.getElementById('page') || document.body;
    return {
      width: el.scrollWidth + 80,
      height: el.scrollHeight + 80
    };
  });

  await page.pdf({
    path: PDF_PATH,
    width: dims.width + 'px',
    height: dims.height + 'px',
    printBackground: true,
    preferCSSPageSize: false,
    margin: { top: '0', right: '0', bottom: '0', left: '0' }
  });

  console.log('PDF exported: ' + PDF_PATH + ' (' + dims.width + 'x' + dims.height + ')');
}
