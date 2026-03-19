import React, { useId, useMemo } from 'react';

type BookSliderChangeHandler = (nextValue: number) => void;

function clampNumber(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) return min;
  if (!Number.isFinite(min) || !Number.isFinite(max) || min === max) return value;
  return Math.max(min, Math.min(max, value));
}

function countDecimals(step: number): number {
  if (!Number.isFinite(step)) return 0;
  const raw = step.toString().toLowerCase();
  if (raw.includes('e-')) {
    const [, exp] = raw.split('e-');
    const n = Number(exp);
    return Number.isFinite(n) ? Math.max(0, Math.floor(n)) : 0;
  }
  const dot = raw.indexOf('.');
  return dot === -1 ? 0 : Math.max(0, raw.length - dot - 1);
}

function normalizeToStep(value: number, min: number, max: number, step: number): number {
  const clamped = clampNumber(value, min, max);
  if (!Number.isFinite(step) || step <= 0 || !Number.isFinite(min) || !Number.isFinite(max) || max <= min) {
    return clamped;
  }
  const snapped = Math.round((clamped - min) / step) * step + min;
  const decimals = countDecimals(step);
  return Number(snapped.toFixed(decimals));
}

function toFiniteNumber(value: unknown): number | null {
  const n = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

interface BookSliderProps {
  label: string;
  value: number;
  onChange: BookSliderChangeHandler;
  min: number;
  max: number;
  step?: number;
  disabled?: boolean;
  hint?: string;
  formatValue?: (value: number) => string;
  showNumberInput?: boolean;
  numberInputWidthClassName?: string;
}

export const BookSlider: React.FC<BookSliderProps> = ({
  label,
  value,
  onChange,
  min,
  max,
  step = 1,
  disabled = false,
  hint,
  formatValue,
  showNumberInput = true,
  numberInputWidthClassName = 'w-24',
}) => {
  const sliderId = useId();
  const safeMin = Number.isFinite(min) ? min : 0;
  const safeMax = Number.isFinite(max) ? max : safeMin;
  const clampedValue = normalizeToStep(value, safeMin, safeMax, step);

  const percent = useMemo(() => {
    if (!Number.isFinite(safeMin) || !Number.isFinite(safeMax) || safeMax <= safeMin) return 0;
    const p = ((clampedValue - safeMin) / (safeMax - safeMin)) * 100;
    return Math.max(0, Math.min(100, p));
  }, [clampedValue, safeMin, safeMax]);

  const displayValue = formatValue ? formatValue(clampedValue) : String(clampedValue);

  return (
    <div className="w-full">
      <div className="mb-2 ml-1 flex items-center justify-between gap-3">
        <label
          htmlFor={sliderId}
          className="block text-[0.72rem] font-bold uppercase tracking-[0.18em] text-book-text-sub"
        >
          {label}
        </label>
        <div className="text-xs font-mono text-book-text-sub">{displayValue}</div>
      </div>

      <div className="flex items-center gap-3">
        <input
          id={sliderId}
          type="range"
          min={safeMin}
          max={safeMax}
          step={step}
          value={clampedValue}
          disabled={disabled}
          onChange={(e) => {
            const next = toFiniteNumber(e.target.value);
            if (next === null) return;
            onChange(normalizeToStep(next, safeMin, safeMax, step));
          }}
          className="book-range flex-1"
          style={{ ['--range-percent' as any]: `${percent}%` }}
        />

        {showNumberInput ? (
          <input
            type="number"
            min={safeMin}
            max={safeMax}
            step={step}
            value={clampedValue}
            disabled={disabled}
            onChange={(e) => {
              const next = toFiniteNumber(e.target.value);
              if (next === null) return;
              onChange(normalizeToStep(next, safeMin, safeMax, step));
            }}
            className={`book-control ${numberInputWidthClassName} rounded-2xl border px-3 py-2 text-sm text-book-text-main outline-none focus:border-book-primary/50`}
          />
        ) : null}
      </div>

      {hint ? (
        <div className="mt-2 ml-1 text-xs leading-relaxed text-book-text-sub">
          {hint}
        </div>
      ) : null}
    </div>
  );
};
