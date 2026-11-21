// Graba video.json -> MP4 vertical 1080x1920 con Playwright + ffmpeg.
// Uso: node render/grabar.js video.json salida.mp4 [audio.wav] [fps]
const { chromium } = require("playwright");
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

(async () => {
  const [jsonPath, outPath, audio, fpsArg] = process.argv.slice(2);
  const fps = Number(fpsArg || 30);
  const data = JSON.parse(fs.readFileSync(jsonPath, "utf8"));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  await page.goto("file://" + path.resolve(__dirname, "index.html"));
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(d => window.load(d), data);

  const args = ["-y", "-f", "image2pipe", "-c:v", "mjpeg", "-r", String(fps), "-i", "-"];
  if (audio) args.push("-i", audio, "-c:a", "aac", "-b:a", "160k", "-shortest");
  args.push("-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "veryfast", outPath);
  const ff = spawn("ffmpeg", args, { stdio: ["pipe", "ignore", "inherit"] });

  const frames = Math.ceil(data.duration * fps);
  for (let f = 0; f < frames; f++) {
    await page.evaluate(t => window.render(t), f / fps);
    const buf = await page.screenshot({ type: "jpeg", quality: 92 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once("drain", r));
    if (f % (fps * 5) === 0) process.stderr.write(`  ${(f / fps).toFixed(0)}s / ${data.duration.toFixed(0)}s\n`);
  }
  ff.stdin.end();
  await new Promise(r => ff.on("close", r));
  await browser.close();
  console.log("Listo:", outPath);
})();
