import { downloadBlob } from './downloadFile';

type CsvCell = string | number | boolean | null | undefined;
type CsvRow = CsvCell[];

const csvEscape = (value: CsvCell): string => {
  const text = String(value ?? '');
  return `"${text.replace(/"/g, '""')}"`;
};

export const toCsv = (header: CsvRow, rows: CsvRow[]): string => {
  return [header, ...rows].map((line) => line.map(csvEscape).join(',')).join('\n');
};

export const downloadCsv = (header: CsvRow, rows: CsvRow[], filename: string) => {
  const csv = toCsv(header, rows);
  const blob = new Blob([`\ufeff${csv}`], { type: 'text/csv;charset=utf-8;' });
  downloadBlob(blob, filename);
};

