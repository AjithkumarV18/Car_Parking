import { useMemo } from 'react';
import { Box } from '@mui/material';

import { createReceiptQrMatrix } from '@/features/parking/receiptQr';

const CODE_39: Record<string, string> = {
  '0': 'nnnwwnwnn', '1': 'wnnwnnnnw', '2': 'nnwwnnnnw', '3': 'wnwwnnnnn', '4': 'nnnwwnnnw',
  '5': 'wnnwwnnnn', '6': 'nnwwwnnnn', '7': 'nnnwnnwnw', '8': 'wnnwnnwnn', '9': 'nnwwnnwnn',
  A: 'wnnnnwnnw', B: 'nnwnnwnnw', C: 'wnwnnwnnn', D: 'nnnnwwnnw', E: 'wnnnwwnnn', F: 'nnwnwwnnn',
  G: 'nnnnnwwnw', H: 'wnnnnwwnn', I: 'nnwnnwwnn', J: 'nnnnwwwnn', K: 'wnnnnnnww', L: 'nnwnnnnww',
  M: 'wnwnnnnwn', N: 'nnnnwnnww', O: 'wnnnwnnwn', P: 'nnwnwnnwn', Q: 'nnnnnnwww', R: 'wnnnnnwwn',
  S: 'nnwnnnwwn', T: 'nnnnwnwwn', U: 'wwnnnnnnw', V: 'nwwnnnnnw', W: 'wwwnnnnnn', X: 'nwnnwnnnw',
  Y: 'wwnnwnnnn', Z: 'nwwnwnnnn', '-': 'nwnnnnwnw', '.': 'wwnnnnwnn', ' ': 'nwwnnnwnn',
  $: 'nwnwnwnnn', '/': 'nwnwnnnwn', '+': 'nwnnnwnwn', '%': 'nnnwnwnwn', '*': 'nwnnwnwnn',
};

export function ReceiptQrCode({ value }: { value: string }) {
  const matrix = useMemo(() => createReceiptQrMatrix(value), [value]);
  return <Box component="svg" viewBox="0 0 21 21" role="img" aria-label={`QR code for ${value}`} sx={{ width: 82, height: 82, bgcolor: 'common.white', p: 0.5, shapeRendering: 'crispEdges' }}>{matrix.flatMap((line, row) => line.map((module, column) => module ? <rect key={`${row}-${column}`} x={column} y={row} width="1" height="1" fill="black" /> : null))}</Box>;
}

export function ReceiptBarcode({ value }: { value: string }) {
  const encoded = `*${value.toUpperCase().split('').filter((character) => CODE_39[character]).join('').slice(0, 32)}*`;
  const bars = useMemo(() => {
    let cursor = 10;
    const result: Array<{ x: number; width: number }> = [];
    encoded.split('').forEach((character) => {
      CODE_39[character].split('').forEach((widthCode, index) => {
        const width = widthCode === 'w' ? 3 : 1;
        if (index % 2 === 0) result.push({ x: cursor, width });
        cursor += width;
      });
      cursor += 1;
    });
    return { bars: result, width: cursor + 10 };
  }, [encoded]);
  return <Box component="svg" viewBox={`0 0 ${bars.width} 42`} role="img" aria-label={`Barcode for ${value}`} sx={{ width: '100%', height: 48, display: 'block' }}>{bars.bars.map((bar, index) => <rect key={`${bar.x}-${index}`} x={bar.x} y="1" width={bar.width} height="30" fill="black" />)}<text x={bars.width / 2} y="40" textAnchor="middle" fontSize="7" fontFamily="monospace">{value}</text></Box>;
}
