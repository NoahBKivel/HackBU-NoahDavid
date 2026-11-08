import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

export const root = fileURLToPath(new URL('.', import.meta.url));
export const output = path.join(root, 'dist');
export const assets = ['index.html', 'styles.css', 'model.js', 'charts.js', 'preview-data.js', 'live-data.js', 'app.js', 'fonts/IBMPlexSans.ttf', 'fonts/OFL-IBMPlexSans.txt', 'fonts/IBMPlexMono-Medium.ttf', 'fonts/OFL-IBMPlexMono.txt'];

export async function build() {
  await mkdir(output, { recursive: true });
  for (const asset of assets) {
    await mkdir(path.dirname(path.join(output, asset)), { recursive: true });
    await writeFile(path.join(output, asset), await readFile(path.join(root, asset)));
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await build();
  console.log('Built VISION static preview in ' + output);
}
