const path = require('node:path');
const {createRequire} = require('node:module');
const {mkdirSync} = require('node:fs');
const {chromium} = createRequire(path.resolve(__dirname, '../pack-preview/package.json'))('playwright');
const assert = require('node:assert/strict');
const output = path.resolve(__dirname, '../reports');
mkdirSync(output,{recursive:true});
async function pixels(page) {
  return page.locator('canvas').evaluate(canvas => {
    const copy=document.createElement('canvas');copy.width=canvas.width;copy.height=canvas.height;
    const ctx=copy.getContext('2d');ctx.drawImage(canvas,0,0);const p=ctx.getImageData(0,0,copy.width,copy.height).data;
    let dark=0,hash=0;for(let i=0;i<p.length;i+=16){if(p[i]<145&&p[i+1]<145&&p[i+2]<145)dark++;hash=(hash+p[i]*(i%97+1))%1000000007;}
    return {dark,hash,width:copy.width,height:copy.height};
  });
}
(async()=>{
  const browser=await chromium.launch({headless:true,
    ...(process.env.PLAYWRIGHT_CHANNEL ? {channel:process.env.PLAYWRIGHT_CHANNEL} : {})});
  try {
    const page=await browser.newPage({viewport:{width:1440,height:960},deviceScaleFactor:1});
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.goto(process.env.PREVIEW_URL || 'http://127.0.0.1:5173/');
    await page.waitForFunction(()=>window.previewState?.textureLoaded);
    await page.screenshot({path:path.join(output,'pack-preview-desktop.png')});
    let before=await pixels(page);assert(before.dark>2000,'Desktop canvas must contain rendered model pixels');
    const box=await page.locator('canvas').boundingBox();
    await page.mouse.move(box.x+box.width*.5,box.y+box.height*.5);
    await page.mouse.down();await page.mouse.move(box.x+box.width*.7,box.y+box.height*.55,{steps:12});await page.mouse.up();
    await page.waitForTimeout(350);
    assert.notEqual((await pixels(page)).hash,before.hash,'Orbit drag must change rendered pixels');
    await page.getByRole('button',{name:'Reset camera'}).click();
    await page.locator('#turntable').check();before=await pixels(page);await page.waitForTimeout(700);
    assert.notEqual((await pixels(page)).hash,before.hash,'Turntable must move the rendered model');
    await page.locator('#turntable').uncheck();
    for(const id of ['wfp_satchel','wfp_backpack','wfp_expedition']) {
      await page.locator(`[data-id="${id}"]`).click();
      await page.waitForFunction(id=>window.previewState.id===id,id);
      await page.waitForTimeout(150);assert((await pixels(page)).dark>1000,id+' must render');
      await page.locator('#zoom-in').click();await page.locator('#zoom-in').click();
      await page.waitForTimeout(150);
      await page.screenshot({path:path.join(output,`pack-preview-${id}-closeup.png`)});
      await page.locator('[data-view="side"]').click();
      await page.locator('#zoom-in').click();await page.locator('#zoom-in').click();
      await page.waitForTimeout(150);
      await page.screenshot({path:path.join(output,`pack-preview-${id}-side-closeup.png`)});
    }
    await page.locator('[data-surface="wire"]').click();
    await page.locator('[data-surface="clay"]').click();
    await page.locator('[data-surface="textured"]').click();
    await page.locator('#lighting').selectOption('warm');
    await page.locator('[data-view="back"]').click();
    await page.screenshot({path:path.join(output,'pack-preview-back.png')});
    await page.locator('[data-view="side"]').click();
    await page.screenshot({path:path.join(output,'pack-preview-side.png')});
    if (!(await page.locator('#reference').isDisabled())) {
      await page.locator('#reference').check();
      await page.screenshot({path:path.join(output,'pack-preview-harness.png')});
      await page.locator('#reference').uncheck();
    }
    await page.locator('[data-id="wfp_backpack"]').click();
    await page.locator('#lighting').selectOption('studio');
    await page.setViewportSize({width:390,height:844});
    await page.getByRole('button',{name:'Reset camera'}).click();
    await page.waitForTimeout(300);assert((await pixels(page)).dark>500,'Mobile model must render');
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'No mobile horizontal overflow');
    await page.screenshot({path:path.join(output,'pack-preview-mobile.png'),fullPage:true});
    assert.deepEqual(errors,[]);
    console.log('PASS: desktop/mobile rendering, real texture, three variants, orbit drag, turntable, surfaces, lighting, and no page errors.');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
