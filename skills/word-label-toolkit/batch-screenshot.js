// 批量截图 HTML 文件，并自动裁剪空白边缘
// 依赖: npm install sharp
// 用法: node batch-screenshot.js

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const sharp = require('sharp');

// ==================== 配置区域 ====================
const HTML_DIR = path.resolve("G:\\draw_long\\GPT-image-2.0\\batches\\参考\\label_only_html");
const OUTPUT_DIR = path.resolve("G:\\draw_long\\GPT-image-2.0\\batches\\参考\\label_only_png");
// =================================================

const TEMP_HTML = path.join(HTML_DIR, 'temp_screenshot.html');

const EDGE_PATHS = [
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
];

function findEdge() {
  for (const p of EDGE_PATHS) {
    if (fs.existsSync(p)) return p;
  }
  try {
    const where = execSync('where msedge', { encoding: 'utf-8' }).trim().split('\n')[0];
    if (where && fs.existsSync(where)) return where;
  } catch {}
  return null;
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function screenshotFile(edgePath, htmlPath, pngPath) {
  // 坑点：文件名含 emoji/特殊字符时，Edge 通过 file:// URL 打不开
  // 解决：先复制到临时文件，截图完删除
  fs.copyFileSync(htmlPath, TEMP_HTML);
  const fileUrl = 'file:///' + TEMP_HTML.replace(/\\/g, '/');

  // 坑点：Edge 不支持 --screenshot-fullpage，要用超大窗口 + sharp trim 裁剪
  const cmd = `"${edgePath}" --headless --disable-gpu --hide-scrollbars --run-all-compositor-stages-before-draw --virtual-time-budget=1500 --window-size=1500,3000 --screenshot="${pngPath}" "${fileUrl}"`;
  try {
    execSync(cmd, { stdio: 'pipe', timeout: 30000 });
    return true;
  } catch (e) {
    return false;
  }
}

async function trimImage(inputPath, outputPath) {
  try {
    await sharp(inputPath)
      .trim() // 自动裁剪边缘空白
      .toFile(outputPath);
    return true;
  } catch (e) {
    return false;
  }
}

async function main() {
  const edgePath = findEdge();
  if (!edgePath) {
    console.error('❌ 找不到 Microsoft Edge 浏览器');
    console.error('💡 请确认系统已安装 Edge，或手动修改 EDGE_PATHS');
    process.exit(1);
  }
  console.log(`🌐 使用 Edge: ${edgePath}\n`);

  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }

  const files = fs.readdirSync(HTML_DIR)
    .filter(f => f.endsWith('.html') && f !== 'temp_screenshot.html')
    .sort();

  console.log(`📸 共 ${files.length} 个文件，开始截图+裁剪...\n`);

  let success = 0;
  let fail = 0;
  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    const htmlPath = path.join(HTML_DIR, file);
    const rawPng = path.join(OUTPUT_DIR, file.replace('.html', '_raw.png'));
    const finalPng = path.join(OUTPUT_DIR, file.replace('.html', '.png'));

    process.stdout.write(`[${String(i+1).padStart(3)}/${files.length}] ${file.slice(0,35)}... `);

    const ok1 = screenshotFile(edgePath, htmlPath, rawPng);
    if (!ok1) {
      console.log('截图失败');
      fail++;
      continue;
    }

    const ok2 = await trimImage(rawPng, finalPng);
    fs.unlinkSync(rawPng);

    if (!ok2) {
      console.log('裁剪失败');
      fail++;
      continue;
    }

    const stats = fs.statSync(finalPng);
    console.log(`✅ ${(stats.size/1024).toFixed(1)}KB`);
    success++;

    await delay(200);
  }

  // 清理临时文件
  if (fs.existsSync(TEMP_HTML)) {
    fs.unlinkSync(TEMP_HTML);
  }

  console.log(`\n🎉 完成！成功 ${success}/${files.length}，失败 ${fail}。`);
  console.log(`📁 保存在: ${OUTPUT_DIR}`);
}

main().catch(console.error);
