import React, { memo, useMemo } from 'react';

export interface AdminChartDatum {
  label: string;
  value: number;
  color?: string;
  hint?: string;
}

const DEFAULT_COLORS = ['#6366F1', '#14B8A6', '#F59E0B', '#EF4444', '#06B6D4', '#8B5CF6', '#EC4899', '#22C55E'];

const normalizeValue = (value: number): number => {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Number(value));
};

const getColor = (index: number, color?: string): string => {
  if (color && String(color).trim()) return color;
  return DEFAULT_COLORS[index % DEFAULT_COLORS.length];
};

const formatPercent = (value: number, total: number): number => {
  if (total <= 0) return 0;
  return Math.round((value / total) * 1000) / 10;
};

interface AdminDonutChartProps {
  title?: string;
  data: AdminChartDatum[];
  centerLabel?: string;
  centerValue?: string | number;
  size?: number;
  thickness?: number;
  emptyText?: string;
}

const AdminDonutChartInner: React.FC<AdminDonutChartProps> = ({
  title,
  data,
  centerLabel = '总计',
  centerValue,
  size = 128,
  thickness = 24,
  emptyText = '暂无图表数据',
}) => {
  const normalizedData = useMemo(() => {
    return data
      .map((item, index) => ({
        ...item,
        value: normalizeValue(item.value),
        color: getColor(index, item.color),
      }))
      .filter((item) => item.value > 0);
  }, [data]);

  const total = useMemo(() => {
    return normalizedData.reduce((sum, item) => sum + item.value, 0);
  }, [normalizedData]);

  const gradient = useMemo(() => {
    if (total <= 0) {
      return 'conic-gradient(#E5E7EB 0deg 360deg)';
    }

    let start = 0;
    const parts = normalizedData.map((item) => {
      const percent = item.value / total;
      const end = start + percent * 360;
      const segment = `${item.color} ${start.toFixed(2)}deg ${end.toFixed(2)}deg`;
      start = end;
      return segment;
    });

    return `conic-gradient(${parts.join(', ')})`;
  }, [normalizedData, total]);

  const centerDisplay = centerValue ?? total;

  return (
    <div className="space-y-3">
      {title ? <h3 className="font-bold text-sm text-book-text-main">{title}</h3> : null}

      <div className="flex items-center gap-4">
        <div className="relative shrink-0" style={{ width: size, height: size }}>
          <div className="absolute inset-0 rounded-full" style={{ background: gradient }} />
          <div
            className="absolute rounded-full bg-book-bg-paper border border-book-border/40 flex flex-col items-center justify-center text-center px-2"
            style={{ inset: thickness }}
          >
            <div className="text-[11px] text-book-text-muted leading-none">{centerLabel}</div>
            <div className="text-sm font-bold text-book-text-main leading-none mt-1">{centerDisplay}</div>
          </div>
        </div>

        <div className="min-w-0 flex-1 space-y-2">
          {total > 0 ? (
            normalizedData.map((item, index) => {
              const percent = formatPercent(item.value, total);
              return (
                <div key={`${item.label}-${index}`} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <div className="min-w-0 flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: item.color }} />
                      <span className="text-book-text-main truncate">{item.label}</span>
                    </div>
                    <span className="text-book-text-muted">{item.value} · {percent}%</span>
                  </div>
                  {item.hint ? <div className="text-[11px] text-book-text-muted">{item.hint}</div> : null}
                </div>
              );
            })
          ) : (
            <div className="text-xs text-book-text-muted">{emptyText}</div>
          )}
        </div>
      </div>
    </div>
  );
};

interface AdminBarListChartProps {
  title?: string;
  data: AdminChartDatum[];
  totalOverride?: number;
  emptyText?: string;
}

const AdminBarListChartInner: React.FC<AdminBarListChartProps> = ({
  title,
  data,
  totalOverride,
  emptyText = '暂无图表数据',
}) => {
  const normalizedData = useMemo(() => {
    return data.map((item, index) => ({
      ...item,
      value: normalizeValue(item.value),
      color: getColor(index, item.color),
    }));
  }, [data]);

  const total = useMemo(() => {
    if (typeof totalOverride === 'number' && Number.isFinite(totalOverride) && totalOverride > 0) {
      return totalOverride;
    }
    return normalizedData.reduce((sum, item) => sum + item.value, 0);
  }, [normalizedData, totalOverride]);

  const visibleRows = normalizedData.filter((item) => item.value > 0);

  return (
    <div className="space-y-3">
      {title ? <h3 className="font-bold text-sm text-book-text-main">{title}</h3> : null}

      {visibleRows.length > 0 ? (
        <div className="space-y-2">
          {visibleRows.map((item, index) => {
            const percent = formatPercent(item.value, total);
            return (
              <div key={`${item.label}-${index}`} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-book-text-main truncate">{item.label}</span>
                  <span className="text-book-text-muted">{item.value} · {percent}%</span>
                </div>
                <div className="h-2 rounded bg-book-bg overflow-hidden">
                  <div
                    className="h-2 rounded"
                    style={{ width: `${Math.min(percent, 100)}%`, backgroundColor: item.color }}
                  />
                </div>
                {item.hint ? <div className="text-[11px] text-book-text-muted">{item.hint}</div> : null}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="text-xs text-book-text-muted">{emptyText}</div>
      )}
    </div>
  );
};

interface AdminStackedProgressProps {
  title?: string;
  segments: AdminChartDatum[];
  emptyText?: string;
}

const AdminStackedProgressInner: React.FC<AdminStackedProgressProps> = ({
  title,
  segments,
  emptyText = '暂无图表数据',
}) => {
  const normalized = useMemo(() => {
    return segments.map((item, index) => ({
      ...item,
      value: normalizeValue(item.value),
      color: getColor(index, item.color),
    }));
  }, [segments]);

  const total = useMemo(() => {
    return normalized.reduce((sum, item) => sum + item.value, 0);
  }, [normalized]);

  const visibleRows = normalized.filter((item) => item.value > 0);

  return (
    <div className="space-y-3">
      {title ? <h3 className="font-bold text-sm text-book-text-main">{title}</h3> : null}

      {visibleRows.length > 0 ? (
        <>
          <div className="h-3 rounded bg-book-bg overflow-hidden flex">
            {visibleRows.map((item, index) => {
              const percent = formatPercent(item.value, total);
              return (
                <div
                  key={`${item.label}-${index}`}
                  style={{ width: `${Math.min(percent, 100)}%`, backgroundColor: item.color }}
                  className="h-3"
                />
              );
            })}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {visibleRows.map((item, index) => {
              const percent = formatPercent(item.value, total);
              return (
                <div key={`${item.label}-${index}`} className="flex items-center justify-between text-xs border border-book-border/40 rounded-lg px-3 py-2">
                  <div className="min-w-0 flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: item.color }} />
                    <span className="truncate text-book-text-main">{item.label}</span>
                  </div>
                  <span className="text-book-text-muted">{item.value} · {percent}%</span>
                </div>
              );
            })}
          </div>
        </>
      ) : (
        <div className="text-xs text-book-text-muted">{emptyText}</div>
      )}
    </div>
  );
};

export interface AdminTrendPoint {
  label: string;
  value: number;
}

export interface AdminTrendSeries {
  label: string;
  color?: string;
  points: AdminTrendPoint[];
}

interface AdminTrendChartProps {
  title?: string;
  series: AdminTrendSeries[];
  mode?: 'line' | 'bar';
  height?: number;
  emptyText?: string;
}

const AdminTrendChartInner: React.FC<AdminTrendChartProps> = ({
  title,
  series,
  mode = 'line',
  height = 220,
  emptyText = '暂无趋势数据',
}) => {
  const normalizedSeries = useMemo(() => {
    return series
      .map((item, index) => ({
        ...item,
        color: getColor(index, item.color),
        points: item.points.map((point) => ({
          label: String(point.label || ''),
          value: normalizeValue(point.value),
        })),
      }))
      .filter((item) => item.points.length > 0);
  }, [series]);

  const labels = useMemo(() => {
    if (normalizedSeries.length <= 0) return [];
    return normalizedSeries[0].points.map((point) => point.label);
  }, [normalizedSeries]);

  const maxValue = useMemo(() => {
    let max = 0;
    normalizedSeries.forEach((item) => {
      item.points.forEach((point) => {
        if (point.value > max) max = point.value;
      });
    });
    return max;
  }, [normalizedSeries]);

  const chartWidth = 1000;
  const paddingLeft = 40;
  const paddingRight = 20;
  const paddingTop = 16;
  const paddingBottom = 42;
  const innerWidth = chartWidth - paddingLeft - paddingRight;
  const innerHeight = Math.max(height - paddingTop - paddingBottom, 40);
  const xStep = labels.length > 1 ? innerWidth / (labels.length - 1) : innerWidth;

  const gridValues = useMemo(() => {
    if (maxValue <= 0) return [0];
    return [0, 0.25, 0.5, 0.75, 1].map((ratio) => Math.round(maxValue * ratio));
  }, [maxValue]);

  const shouldRender = normalizedSeries.length > 0 && labels.length > 0;

  const xLabelInterval = useMemo(() => {
    if (labels.length <= 8) return 1;
    return Math.ceil(labels.length / 8);
  }, [labels.length]);

  return (
    <div className="space-y-3">
      {title ? <h3 className="font-bold text-sm text-book-text-main">{title}</h3> : null}

      {shouldRender ? (
        <>
          <div className="overflow-x-auto">
            <svg viewBox={`0 0 ${chartWidth} ${height}`} className="min-w-[680px] w-full">
              {gridValues.map((value) => {
                const ratio = maxValue <= 0 ? 0 : value / maxValue;
                const y = paddingTop + innerHeight - ratio * innerHeight;
                return (
                  <g key={`grid-${value}`}>
                    <line
                      x1={paddingLeft}
                      y1={y}
                      x2={chartWidth - paddingRight}
                      y2={y}
                      stroke="rgba(148, 163, 184, 0.25)"
                      strokeDasharray="4 4"
                    />
                    <text
                      x={paddingLeft - 8}
                      y={y + 4}
                      textAnchor="end"
                      className="text-book-text-muted"
                      fill="currentColor"
                      fontSize="11"
                    >
                      {value}
                    </text>
                  </g>
                );
              })}

              {mode === 'line'
                ? normalizedSeries.map((item, seriesIndex) => {
                    const points = item.points
                      .map((point, pointIndex) => {
                        const x = paddingLeft + pointIndex * xStep;
                        const y = paddingTop + innerHeight - (maxValue <= 0 ? 0 : (point.value / maxValue) * innerHeight);
                        return `${x.toFixed(2)},${y.toFixed(2)}`;
                      })
                      .join(' ');

                    return (
                      <g key={`line-${seriesIndex}`}>
                        <polyline
                          points={points}
                          fill="none"
                          stroke={item.color}
                          strokeWidth={2.5}
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                        {item.points.map((point, pointIndex) => {
                          const x = paddingLeft + pointIndex * xStep;
                          const y = paddingTop + innerHeight - (maxValue <= 0 ? 0 : (point.value / maxValue) * innerHeight);
                          return <circle key={`dot-${seriesIndex}-${pointIndex}`} cx={x} cy={y} r={2.5} fill={item.color} />;
                        })}
                      </g>
                    );
                  })
                : normalizedSeries.map((item, seriesIndex) => {
                    const groupWidth = labels.length > 0 ? innerWidth / labels.length : innerWidth;
                    const barGap = 2;
                    const maxBarWidth = Math.max((groupWidth - barGap * (normalizedSeries.length + 1)) / Math.max(normalizedSeries.length, 1), 2);

                    return (
                      <g key={`bar-series-${seriesIndex}`}>
                        {item.points.map((point, pointIndex) => {
                          const groupX = paddingLeft + pointIndex * groupWidth;
                          const barHeight = maxValue <= 0 ? 0 : (point.value / maxValue) * innerHeight;
                          const x = groupX + barGap + seriesIndex * (maxBarWidth + barGap);
                          const y = paddingTop + innerHeight - barHeight;
                          return (
                            <rect
                              key={`bar-${seriesIndex}-${pointIndex}`}
                              x={x}
                              y={y}
                              width={maxBarWidth}
                              height={Math.max(barHeight, 1)}
                              rx={1.5}
                              fill={item.color}
                            />
                          );
                        })}
                      </g>
                    );
                  })}

              {labels.map((label, index) => {
                if (index % xLabelInterval !== 0 && index !== labels.length - 1) return null;
                const x = paddingLeft + index * xStep;
                return (
                  <text
                    key={`label-${label}-${index}`}
                    x={x}
                    y={height - 14}
                    textAnchor="middle"
                    className="text-book-text-muted"
                    fill="currentColor"
                    fontSize="11"
                  >
                    {label.slice(5)}
                  </text>
                );
              })}
            </svg>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {normalizedSeries.map((item, index) => {
              const latestPoint = item.points[item.points.length - 1];
              return (
                <div key={`legend-${item.label}-${index}`} className="flex items-center justify-between text-xs border border-book-border/40 rounded-lg px-3 py-2">
                  <div className="min-w-0 flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: item.color }} />
                    <span className="truncate text-book-text-main">{item.label}</span>
                  </div>
                  <span className="text-book-text-muted">最新 {latestPoint?.value ?? 0}</span>
                </div>
              );
            })}
          </div>
        </>
      ) : (
        <div className="text-xs text-book-text-muted">{emptyText}</div>
      )}
    </div>
  );
};

export const AdminDonutChart = memo(AdminDonutChartInner);
export const AdminBarListChart = memo(AdminBarListChartInner);
export const AdminStackedProgress = memo(AdminStackedProgressInner);
export const AdminTrendChart = memo(AdminTrendChartInner);
