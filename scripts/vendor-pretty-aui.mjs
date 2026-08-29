import { cp, mkdir, readdir, readFile, rm } from "node:fs/promises";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const source = join(root, "node_modules", "pretty-aui", "dist", "standalone");
const target = join(
  root,
  "src",
  "psycheval",
  "assets",
  "web",
  "vendor",
  "pretty-aui",
);
const checking = process.argv.includes("--check");

async function fileSet(directory) {
  const found = [];
  async function visit(current) {
    for (const entry of await readdir(current, { withFileTypes: true })) {
      const path = join(current, entry.name);
      if (entry.isDirectory()) await visit(path);
      else if (entry.isFile()) found.push(relative(directory, path));
      else throw new Error(`unsupported vendored entry: ${path}`);
    }
  }
  await visit(directory);
  return found.sort();
}

if (checking) {
  const [sourceFiles, targetFiles] = await Promise.all([
    fileSet(source),
    fileSet(target),
  ]);
  if (JSON.stringify(sourceFiles) !== JSON.stringify(targetFiles)) {
    throw new Error("vendored pretty-aui file set differs from the installed package");
  }
  for (const name of sourceFiles) {
    const [expected, actual] = await Promise.all([
      readFile(join(source, name)),
      readFile(join(target, name)),
    ]);
    if (!expected.equals(actual)) {
      throw new Error(`vendored pretty-aui asset differs: ${name}`);
    }
  }
  console.log("vendored pretty-aui assets match the installed package");
} else {
  await rm(target, { recursive: true, force: true });
  await mkdir(dirname(target), { recursive: true });
  await cp(source, target, { recursive: true, errorOnExist: true });
  console.log(`vendored pretty-aui standalone assets into ${relative(root, target)}`);
}
