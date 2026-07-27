const QR_ALPHANUMERIC = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:';

function bitLength(value: number): number {
  return value === 0 ? 0 : Math.floor(Math.log2(value)) + 1;
}

function gfTables(): { exp: number[]; log: number[] } {
  const exp = Array<number>(512).fill(0);
  const log = Array<number>(256).fill(0);
  let value = 1;
  for (let index = 0; index < 255; index += 1) {
    exp[index] = value;
    log[value] = index;
    value <<= 1;
    if (value & 0x100) value ^= 0x11d;
  }
  for (let index = 255; index < 512; index += 1) exp[index] = exp[index - 255];
  return { exp, log };
}

function multiply(left: number, right: number, tables: { exp: number[]; log: number[] }): number {
  return left === 0 || right === 0 ? 0 : tables.exp[tables.log[left] + tables.log[right]];
}

function errorCorrection(data: number[]): number[] {
  const tables = gfTables();
  let generator = [1];
  for (let degree = 0; degree < 7; degree += 1) {
    const next = Array<number>(generator.length + 1).fill(0);
    generator.forEach((coefficient, index) => {
      next[index] ^= coefficient;
      next[index + 1] ^= multiply(coefficient, tables.exp[degree], tables);
    });
    generator = next;
  }
  const remainder = Array<number>(7).fill(0);
  data.forEach((byte) => {
    const factor = byte ^ remainder.shift()!;
    remainder.push(0);
    if (factor !== 0) generator.slice(1).forEach((coefficient, index) => { remainder[index] ^= multiply(coefficient, factor, tables); });
  });
  return remainder;
}

function qrCodewords(value: string): number[] {
  const normalized = value.toUpperCase().split('').filter((character) => QR_ALPHANUMERIC.includes(character)).join('').slice(0, 25) || 'RECEIPT';
  let bits = '0010';
  bits += normalized.length.toString(2).padStart(9, '0');
  for (let index = 0; index < normalized.length; index += 2) {
    if (index + 1 < normalized.length) bits += (QR_ALPHANUMERIC.indexOf(normalized[index]) * 45 + QR_ALPHANUMERIC.indexOf(normalized[index + 1])).toString(2).padStart(11, '0');
    else bits += QR_ALPHANUMERIC.indexOf(normalized[index]).toString(2).padStart(6, '0');
  }
  bits += '0000'.slice(0, Math.min(4, 152 - bits.length));
  while (bits.length % 8) bits += '0';
  const codewords = Array.from({ length: bits.length / 8 }, (_, index) => Number.parseInt(bits.slice(index * 8, index * 8 + 8), 2));
  let padIndex = 0;
  while (codewords.length < 19) { codewords.push(padIndex % 2 === 0 ? 0xec : 0x11); padIndex += 1; }
  return [...codewords, ...errorCorrection(codewords)];
}

function setFinder(matrix: Array<Array<boolean | null>>, row: number, column: number) {
  for (let y = -1; y <= 7; y += 1) for (let x = -1; x <= 7; x += 1) {
    if (row + y < 0 || row + y >= 21 || column + x < 0 || column + x >= 21) continue;
    matrix[row + y][column + x] = y >= 0 && y <= 6 && x >= 0 && x <= 6 && (y === 0 || y === 6 || x === 0 || x === 6 || (y >= 2 && y <= 4 && x >= 2 && x <= 4));
  }
}

function formatBits(): number {
  const data = 0b01000; // Error correction L, mask pattern 0.
  let remainder = data << 10;
  while (bitLength(remainder) >= bitLength(0x537)) remainder ^= 0x537 << (bitLength(remainder) - bitLength(0x537));
  return ((data << 10) | remainder) ^ 0x5412;
}

function setFormat(matrix: Array<Array<boolean | null>>) {
  const bits = formatBits();
  for (let index = 0; index < 15; index += 1) {
    const module = ((bits >> index) & 1) === 1;
    if (index < 6) matrix[index][8] = module;
    else if (index < 8) matrix[index + 1][8] = module;
    else matrix[21 - 15 + index][8] = module;
    if (index < 8) matrix[8][21 - index - 1] = module;
    else if (index < 9) matrix[8][15 - index - 1 + 1] = module;
    else matrix[8][15 - index - 1] = module;
  }
  matrix[13][8] = true;
}

export function createReceiptQrMatrix(value: string): boolean[][] {
  const matrix: Array<Array<boolean | null>> = Array.from({ length: 21 }, () => Array<boolean | null>(21).fill(null));
  setFinder(matrix, 0, 0); setFinder(matrix, 14, 0); setFinder(matrix, 0, 14);
  for (let index = 8; index < 13; index += 1) {
    if (matrix[index][6] === null) matrix[index][6] = index % 2 === 0;
    if (matrix[6][index] === null) matrix[6][index] = index % 2 === 0;
  }
  setFormat(matrix);
  const codewords = qrCodewords(value);
  let byteIndex = 0; let bitIndex = 7; let row = 20; let direction = -1;
  for (let column = 20; column > 0; column -= 2) {
    if (column === 6) column -= 1;
    while (true) {
      for (let offset = 0; offset < 2; offset += 1) {
        if (matrix[row][column - offset] !== null) continue;
        const bit = byteIndex < codewords.length && ((codewords[byteIndex] >>> bitIndex) & 1) === 1;
        matrix[row][column - offset] = (row + column - offset) % 2 === 0 ? !bit : bit;
        bitIndex -= 1;
        if (bitIndex < 0) { byteIndex += 1; bitIndex = 7; }
      }
      row += direction;
      if (row < 0 || row >= 21) { row -= direction; direction = -direction; break; }
    }
  }
  return matrix.map((line) => line.map(Boolean));
}
