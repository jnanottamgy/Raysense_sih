// Renders presentation/judge_drill.html to a print-ready A4 PDF.
//   npm i playwright && node make_qa_pdf.mjs
// The page carries its own @media print rules — this only drives the printer.
import { chromium } from 'playwright';

// Only needed where the bundled browser revision is missing; drop it otherwise.
const EXE = process.env.CHROME_PATH || undefined;

const browser = await chromium.launch(EXE ? { executablePath: EXE } : {});
const page = await browser.newPage();
await page.emulateMedia({ colorScheme: 'light' });   // paper is always the light set
await page.goto('file://' + process.cwd() + '/judge_drill.html', { waitUntil: 'networkidle' });
await page.evaluate(() => document.fonts.ready);
await page.waitForTimeout(1500);                     // let the webfonts settle
await page.pdf({
  path: 'Raysense_Judge_QA.pdf',
  format: 'A4',
  printBackground: true,
  displayHeaderFooter: true,
  headerTemplate: '<span></span>',
  footerTemplate: `<div style="width:100%;font-family:Helvetica,Arial,sans-serif;font-size:7.5pt;
    color:#5F6D69;padding:0 14mm;display:flex;justify-content:space-between;">
    <span>Team Raysense &middot; SIH26053 &middot; DRDO &middot; judge Q&amp;A</span>
    <span class="pageNumber"></span></div>`,
  margin: { top: '12mm', bottom: '15mm', left: '14mm', right: '14mm' },
});
await browser.close();
console.log('wrote Raysense_Judge_QA.pdf');
