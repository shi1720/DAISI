// Decode the synthetic public-data screenshots preserved by the CI log fallback.
// Usage: node browser-tests/extract-evidence.mjs <downloaded-run.log> <output-directory>
import { readFileSync, mkdirSync, writeFileSync } from 'node:fs';
import { join, basename } from 'node:path';
import { createHash } from 'node:crypto';

const [logPath, outputDirectory] = process.argv.slice(2);
if (!logPath || !outputDirectory) throw new Error('Provide a downloaded CI log and output directory.');
mkdirSync(outputDirectory, { recursive: true });
let current = null;
let count = 0;
for (const line of readFileSync(logPath, 'utf8').split('\n')) {
  const begin = line.match(/(?:^|\s)HB_PNG_BEGIN\|([^|]+)\|([a-f0-9]{64})\|(\d+)$/);
  if (begin) { current = {name:basename(begin[1]),sha256:begin[2],bytes:Number(begin[3]),chunks:[]}; continue; }
  const data = line.match(/(?:^|\s)HB_PNG_DATA\|([A-Za-z0-9+/=]+)$/);
  if (data && current) { current.chunks.push(data[1]); continue; }
  const end = line.match(/(?:^|\s)HB_PNG_END\|(.+)$/);
  if (end && current) {
    if (basename(end[1]) !== current.name) throw new Error('Mismatched screenshot record.');
    const image = Buffer.from(current.chunks.join(''), 'base64');
    if (image.length !== current.bytes || createHash('sha256').update(image).digest('hex') !== current.sha256) throw new Error(`Incomplete or invalid screenshot: ${current.name}`);
    const target = join(outputDirectory, current.name);
    writeFileSync(target, image); console.log(target); count++; current = null;
  }
}
if (current) throw new Error(`Truncated screenshot record: ${current.name}`);
if (!count) throw new Error('No complete screenshots were present in the log.');
console.log(`Extracted and verified ${count} screenshots.`);
