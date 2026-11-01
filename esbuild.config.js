import esbuild from "esbuild";
import fs from "fs";
import path from "path";

const watch = process.argv.includes("--watch");
const dev = process.argv.includes("--dev");

const srcDir = "src";
// The bundle ships inside the integration (served as a static path by
// frontend.py), so it must land in custom_components/singbox/www/.
const outDir =
    process.env.BUILD_DEV_PATH || "custom_components/singbox/www";
const file = "singbox-panel-card";

function ensureOutDir() {
    if (!fs.existsSync(outDir)) {
        fs.mkdirSync(outDir, { recursive: true });
    }
}

async function build() {
    ensureOutDir();

    console.log("Building:", path.join(srcDir, `${file}.js`), "->", outDir);

    const context = await esbuild.context({
        entryPoints: [path.join(srcDir, `${file}.js`)],
        bundle: true,
        format: "esm",
        platform: "browser",
        external: ["https://*"],
        minify: !dev,
        sourcemap: dev,
        outfile: path.join(outDir, `${file}.js`),
    });

    await context.rebuild();

    if (watch) {
        await context.watch();
    } else {
        await context.dispose();
    }

    console.log(watch ? "Watch Mode Active" : "Build Completed");
}

build().catch((e) => {
    console.error(e);
    process.exit(1);
});