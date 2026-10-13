const fs = require('fs');
const path = require('path');
const sharp = require('/Users/channtang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const manifest = JSON.parse(fs.readFileSync(path.join(__dirname,'figure_manifest.json'),'utf8'));
(async()=>{
  for (const figure of manifest) {
    const svg = fs.readFileSync(figure.svg,'utf8');
    const widthPt = Number(svg.match(/<svg[^>]*\bwidth="([\d.]+)pt"/)[1]);
    const widthPx = Math.round(widthPt * 300 / 72);
    await sharp(figure.svg,{density:300}).resize({width:widthPx}).withMetadata({density:300}).png().toFile(figure.png);
    const meta = await sharp(figure.png).metadata();
    figure.png_dimensions = [meta.width,meta.height];
    figure.png_dpi = meta.density;
    const preview = path.join(__dirname,`preview_image${figure.source_media_index}.png`);
    await sharp(figure.png).resize({width:1500}).png().toFile(preview);
    figure.preview = preview;
    console.log(JSON.stringify({figure:figure.stem,size:figure.png_dimensions,dpi:figure.png_dpi}));
  }
  fs.writeFileSync(path.join(__dirname,'figure_manifest.json'),JSON.stringify(manifest,null,2));
})();
