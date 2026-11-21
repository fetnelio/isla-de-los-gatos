const { chromium } = require("playwright"); const fs=require("fs");
(async()=>{
 const [json, out, ...ts]=process.argv.slice(2);
 const b=await chromium.launch(); const p=await b.newPage({viewport:{width:1080,height:1920}});
 await p.goto("file://" + require("path").resolve(__dirname, "index.html")); await p.evaluate(()=>document.fonts.ready);
 await p.evaluate(d=>window.load(d), JSON.parse(fs.readFileSync(json)));
 for (const t of ts){ await p.evaluate(t=>window.render(t), Number(t)); await p.screenshot({path:`${out}_${t}.png`}); }
 await b.close();})();
