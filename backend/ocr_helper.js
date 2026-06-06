/**
 * OCR 辅助脚本 — 使用 tesseract.js 提取图片文字
 * 调用方式: node ocr_helper.js <图片路径>
 * 输出: JSON { text: "识别结果" }
 */
const { createWorker } = require('tesseract.js');

const imgPath = process.argv[2];
if (!imgPath) {
  console.log(JSON.stringify({ error: 'No image path provided' }));
  process.exit(1);
}

(async () => {
  try {
    const worker = await createWorker('chi_sim+eng', 1, {
      langPath: 'C:/Users/12804/AppData/Local/Temp',
    });
    const { data: { text } } = await worker.recognize(imgPath);
    await worker.terminate();
    console.log(JSON.stringify({ text: text.trim() }));
  } catch (e) {
    console.log(JSON.stringify({ error: e.message }));
  }
})();
