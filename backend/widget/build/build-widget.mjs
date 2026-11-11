// Genera backend/widget/dist/widget.js: la versión minificada y ofuscada que sirve
// el backend en /widget.js. El código legible vive en static_src/widget.js.
//
// Por qué un archivo versionado y no un paso de compilación: en Render el backend
// corre con Python nativo, sin Node. La CI ejecuta `npm run check` y falla si
// dist/widget.js no corresponde al fuente actual.
//
// Uso:  npm ci --ignore-scripts && npm run build     (regenera dist/widget.js)
//       npm run check                                (solo comprueba)
import { readFileSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import JavaScriptObfuscator from "javascript-obfuscator";

const here = dirname(fileURLToPath(import.meta.url));
const SOURCE = join(here, "..", "static_src", "widget.js");
const OUTPUT = join(here, "..", "dist", "widget.js");

// Opciones moderadas: ocultan la lógica sin romper el widget ni hacerlo lento.
// - Los nombres públicos se conservan: window.BDChatbot, sus métodos, los eventos
//   bdchatbot:* y los atributos data-* que usan las páginas que lo instalan.
// - Sin autodefensa ni bloqueo del depurador: rompen sitios de terceros y no
//   protegen nada que el servidor no proteja ya.
// - La semilla fija hace que el resultado sea reproducible (la CI lo compara).
const OPTIONS = {
  compact: true,
  seed: 20261111,
  target: "browser",
  identifierNamesGenerator: "hexadecimal",
  renameGlobals: false,
  renameProperties: false,
  stringArray: true,
  stringArrayEncoding: ["base64"],
  stringArrayThreshold: 1,
  stringArrayRotate: true,
  stringArrayShuffle: true,
  splitStrings: false,
  controlFlowFlattening: false,
  deadCodeInjection: false,
  selfDefending: false,
  debugProtection: false,
  disableConsoleOutput: false,
  sourceMap: false,
};

function build() {
  const source = readFileSync(SOURCE, "utf8");
  const digest = createHash("sha256").update(source).digest("hex");
  const code = JavaScriptObfuscator.obfuscate(source, OPTIONS).getObfuscatedCode();
  // La primera línea identifica el fuente: así la CI y una persona saben de qué versión sale.
  return `/* Black Dog Store chatbot widget · generado desde static_src/widget.js sha256:${digest} */\n${code}\n`;
}

const output = build();
if (process.argv.includes("--check")) {
  let current = "";
  try {
    current = readFileSync(OUTPUT, "utf8");
  } catch {
    // sin archivo: se informa abajo
  }
  if (current !== output) {
    console.error("dist/widget.js no corresponde a static_src/widget.js. Ejecuta: cd backend/widget/build && npm run build");
    process.exit(1);
  }
  console.log("dist/widget.js está al día.");
} else {
  writeFileSync(OUTPUT, output);
  console.log(`escrito ${OUTPUT} (${output.length} bytes; fuente ${readFileSync(SOURCE).length} bytes)`);
}
