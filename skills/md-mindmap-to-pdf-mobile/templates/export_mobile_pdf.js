/**
 * Playwright run-code 脚本模板（移动端竖版）
 * 使用方式：修改 HTML_PATH 和 PDF_PATH，然后运行：
 *   playwright-cli run-code --filename export_mobile_pdf.js
 *
 * 核心要点：
 * - 用 page.goto('file://...') 加载本地 HTML（open 命令会拦截 file 协议）
 * - 设置手机宽度视口（414px），确保 PDF 窄而长，适合手机滑动
 * - 动态测量页面尺寸，避免内容被截断
 * - printBackground: true 必须开启，否则背景色丢失
 */

async (page) => {
  const HTML_PATH = 'file:///F:/.playwright-cli/词根_volv-volu-（卷·转）_mobile.html';
  const PDF_PATH  = 'F:/.playwright-cli/词根_volv-volu-（卷·转）_mobile.pdf';

  // 设置手机宽度视口，确保 PDF 窄而长，适合手机滑动查看
  await page.setViewportSize({ width: 414, height: 800 });

  await page.goto(HTML_PATH, { waitUntil: 'networkidle' });

  // 等待页面渲染完成
  await page.waitForTimeout(1500);

  // 动态测量内容尺寸，防止裁切
  const dims = await page.evaluate(() => {
    const el = document.querySelector('.container') || document.body;
    return {
      width: el.scrollWidth + 40,
      height: el.scrollHeight + 40
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

  console.log('Mobile PDF exported: ' + PDF_PATH + ' (' + dims.width + 'x' + dims.height + ')');
}
