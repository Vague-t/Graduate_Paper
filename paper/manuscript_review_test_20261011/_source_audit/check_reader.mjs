import {chromium} from '/Users/channtang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';
import fs from 'node:fs';
const root='/Users/channtang/Downloads/paper/manuscript_review_test_20261011';
const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
try {
const page=await browser.newPage({viewport:{width:1440,height:1100},deviceScaleFactor:1});
const errors=[];const requests=[]; page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.url().startsWith('http'))requests.push(r.url())});
await page.goto('file://'+root+'/00_论文阅读与评审.html');
await page.screenshot({path:root+'/_source_audit/reader_overview.png'});
await page.locator('#tab3').click();
await page.locator('#toc a').filter({hasText:'3.7 JS 对齐在做什么'}).click();
await page.waitForFunction(()=>{const h=[...document.querySelectorAll('#doc3 h3')].find(x=>x.textContent.includes('3.7 JS'));return h.getBoundingClientRect().top>=100&&h.getBoundingClientRect().top<300});
const tocTargetTop=await page.locator('#doc3 h3').filter({hasText:'3.7 JS 对齐在做什么'}).evaluate(e=>e.getBoundingClientRect().top);
await page.screenshot({path:root+'/_source_audit/reader_math.png'});
await page.locator('#search').fill('严格接受门');
const results=await page.locator('.result').count();
await page.locator('.result').first().click();
const searchDoc=await page.locator('.doc:visible').getAttribute('data-doc');
await page.locator('#tab1').click();
await page.screenshot({path:root+'/_source_audit/reader_review.png'});
const desktop=await page.evaluate(()=>({math:document.querySelectorAll('math').length,unreplaced:document.body.innerText.includes('MATHPLACEHOLDER'),horizontalOverflow:document.documentElement.scrollWidth>innerWidth,visibleArticles:[...document.querySelectorAll('.doc')].filter(x=>!x.hidden).length,toc:document.querySelectorAll('#toc a').length}));
await page.setViewportSize({width:390,height:844});
await page.locator('#tab2').click();
await page.screenshot({path:root+'/_source_audit/reader_mobile.png'});
const mobile=await page.evaluate(()=>({horizontalOverflow:document.documentElement.scrollWidth>innerWidth}));
const report={errors,requests,tocTargetTop,searchResults:results,searchDoc,desktop,mobile};
fs.writeFileSync(root+'/_source_audit/reader_qa.json',JSON.stringify(report,null,2));
console.log(JSON.stringify(report));
} finally {await browser.close();}
