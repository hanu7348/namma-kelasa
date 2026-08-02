import { copyFileSync, cpSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";

const files = [
  ["node_modules/bootstrap/dist/css/bootstrap.min.css", "static/vendor/bootstrap/bootstrap.min.css"],
  ["node_modules/bootstrap/dist/css/bootstrap.min.css.map", "static/vendor/bootstrap/bootstrap.min.css.map"],
  ["node_modules/bootstrap/dist/js/bootstrap.bundle.min.js", "static/vendor/bootstrap/bootstrap.bundle.min.js"],
  ["node_modules/bootstrap/dist/js/bootstrap.bundle.min.js.map", "static/vendor/bootstrap/bootstrap.bundle.min.js.map"],
  ["node_modules/bootstrap/LICENSE", "static/vendor/bootstrap/LICENSE"],
  ["node_modules/bootstrap-icons/font/bootstrap-icons.min.css", "static/vendor/bootstrap-icons/bootstrap-icons.min.css"],
  ["node_modules/bootstrap-icons/LICENSE", "static/vendor/bootstrap-icons/LICENSE"],
];

for (const [source, destination] of files) {
  mkdirSync(dirname(destination), { recursive: true });
  copyFileSync(source, destination);
}

cpSync("node_modules/bootstrap-icons/font/fonts", "static/vendor/bootstrap-icons/fonts", { recursive: true });
