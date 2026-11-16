const assert = require('node:assert/strict');
const fs = require('node:fs');
const crypto = require('node:crypto');
assert.equal(process.version, `v${process.env.EXPECTED_NODE_VERSION}`);
assert.equal(process.execPath, '/actions-runner/externals/node24/bin/node');
assert.equal(process.env.ACCESS_TOKEN, undefined);
assert.notEqual(process.getuid(), 0);
assert.ok(crypto.createHash('sha256').update(fs.readFileSync('runtime-policy.json')).digest('hex'));
console.log(JSON.stringify({ version: process.version, executable: process.execPath, arch: process.arch }));
