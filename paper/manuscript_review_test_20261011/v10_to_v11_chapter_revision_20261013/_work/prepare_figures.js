const fs=require('fs');
const path=require('path');
const sharp=require('/Users/channtang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const O=path.resolve(__dirname,'..');
const cfg=JSON.parse(fs.readFileSync(path.join(O,'_work/figure_decision.json'),'utf8'));
if(!cfg.user_confirmed || cfg.main_model!=='Qwen3.5-9B')throw new Error('model confirmation missing');
(async()=>{
for(const i of [3,5,6]){
const source=fs.readFileSync(path.join(O,`_source/image${i}.svg`),'utf8');
const svg=source.replaceAll('Qwen3.8','Qwen3.5').replaceAll('27B','9B').replaceAll('16全注意力块','8全注意力块').replaceAll('仅16个全注意力块','仅8个全注意力块');
fs.writeFileSync(path.join(O,`_work/image${i}_v11.svg`),svg);
await sharp(Buffer.from(svg),{density:300}).png().toFile(path.join(O,`_work/image${i}_v11.png`));
console.log(`image${i}: vector retained and PNG fallback rendered`);
}
})();
