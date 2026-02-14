import React, { useEffect, useRef } from 'react';

type RGB = [number, number, number];

type Palette = {
  ink: RGB;
  inkAlt: RGB;
  paper: RGB;
  border: RGB;
  sparkle: RGB;
  line: RGB;
};

type NavigatorConnectionInfo = Navigator & {
  connection?: {
    saveData?: boolean;
    effectiveType?: string;
  };
};

const clamp255 = (n: number) => Math.max(0, Math.min(255, Math.round(n)));
const clamp01 = (n: number) => Math.max(0, Math.min(1, n));

const parseRgbTriplet = (raw: string): RGB | null => {
  const parts = String(raw || '')
    .trim()
    .split(/[\s,]+/)
    .filter(Boolean)
    .slice(0, 3);
  if (parts.length < 3) return null;
  const nums = parts.map((p) => Number(p));
  if (nums.some((n) => !Number.isFinite(n))) return null;
  return [clamp255(nums[0]), clamp255(nums[1]), clamp255(nums[2])];
};

const rgba = (rgb: RGB, alpha: number) =>
  `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, ${clamp01(alpha)})`;

export const ParticleBackground: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const context = ctx;

    const prefersReducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true;
    if (prefersReducedMotion) return;

    const connection = (navigator as NavigatorConnectionInfo).connection;
    const effectiveType = String(connection?.effectiveType || '').toLowerCase();
    const cpuCores = Number((navigator as Navigator & { hardwareConcurrency?: number }).hardwareConcurrency || 0);
    const lowPowerMode = Boolean(
      connection?.saveData ||
      effectiveType.includes('2g') ||
      effectiveType.includes('3g') ||
      (Number.isFinite(cpuCores) && cpuCores > 0 && cpuCores <= 4)
    );

    const maxFps = lowPowerMode ? 24 : 40;
    const frameIntervalMs = 1000 / maxFps;

    let animationFrameId: number | null = null;
    let width = 0;
    let height = 0;
    let dpr = 1;
    let lastDrawTime = 0;

    const rand = (min: number, max: number) => Math.random() * (max - min) + min;

    const readVar = (name: string, fallback: RGB): RGB => {
      try {
        const raw = getComputedStyle(document.documentElement).getPropertyValue(name);
        const parsed = parseRgbTriplet(raw);
        return parsed ?? fallback;
      } catch {
        return fallback;
      }
    };

    const paletteRef = { current: null as Palette | null };

    const refreshPalette = () => {
      const isDark = document.documentElement.classList.contains('dark');

      // 颜色策略对齐桌面端：首页粒子在浅色主题下不应造成“整体偏暗”的暗色调
      // - 浅色：尽量使用更“灰”的墨色与更浅的连线色，降低玻璃态面板下的发灰感
      // - 深色：允许更饱和的主色与更明显的连线
      const ink = readVar(isDark ? '--color-primary' : '--color-text-tertiary', [109, 101, 96]);
      const inkAlt = readVar(isDark ? '--color-primary-light' : '--color-primary-light', [160, 82, 45]);
      const paper = readVar('--color-bg-secondary', [255, 251, 240]);
      const border = readVar('--color-border', [215, 204, 200]);
      const sparkle = readVar('--color-primary-light', [160, 82, 45]);
      const line = readVar(isDark ? '--color-primary' : '--color-border', [215, 204, 200]);

      paletteRef.current = { ink, inkAlt, paper, border, sparkle, line };
    };

    const resize = () => {
      dpr = Math.max(1, Number(window.devicePixelRatio) || 1);
      width = Math.max(1, Math.floor(window.innerWidth));
      height = Math.max(1, Math.floor(window.innerHeight));

      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);

      // 以 CSS 像素为单位绘制（对齐 UI 布局），避免高 DPI 下模糊
      context.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    type ParticleType = 'ink' | 'paper' | 'sparkle';

    class Particle {
      type: ParticleType;
      x = 0;
      y = 0;
      vx = 0;
      vy = 0;
      size = 0;
      opacity = 0;
      phase = 0;
      pulseSpeed = 0;
      rotation = 0;
      rotationSpeed = 0;

      // ink
      spread = 0;
      maxSpread = 0;
      useAltColor = false;

      // paper
      widthRatio = 1;
      flutter = 0;

      // sparkle
      twinkleSpeed = 0;

      constructor(type: ParticleType) {
        this.type = type;
        this.reset();
      }

      reset() {
        this.x = rand(0, width);
        this.y = rand(0, height);
        this.opacity = rand(0.3, 0.7);
        this.phase = rand(0, Math.PI * 2);
        this.pulseSpeed = rand(0.02, 0.05);
        this.rotation = rand(0, 360);
        this.rotationSpeed = rand(-1, 1);

        if (this.type === 'ink') {
          this.vx = rand(-0.15, 0.15);
          this.vy = rand(-0.1, 0.2);
          this.size = rand(3, 8);
          this.spread = 0;
          this.maxSpread = rand(0, 3);
          this.useAltColor = Math.random() < 0.3;
          return;
        }

        if (this.type === 'paper') {
          this.vx = rand(-0.3, 0.3);
          this.vy = rand(-0.2, 0.1);
          this.size = rand(8, 15);
          this.widthRatio = rand(0.4, 0.8);
          this.flutter = rand(0.5, 1.5);
          return;
        }

        // sparkle
        this.vx = rand(-0.05, 0.05);
        this.vy = rand(-0.05, 0.05);
        this.size = rand(1, 3);
        this.twinkleSpeed = rand(0.05, 0.15);
      }

      getOpacity() {
        // 呼吸效果：对齐桌面端的“诗意感”，同时控制浅色主题下不显脏
        const breath = 0.3 + 0.2 * Math.sin(this.phase);
        return this.opacity * breath;
      }

      update() {
        this.phase += this.pulseSpeed;
        this.rotation += this.rotationSpeed;

        if (this.type === 'paper') {
          this.x += Math.sin(this.phase * 2) * this.flutter * 0.1;
        }

        this.x += this.vx;
        this.y += this.vy;

        // 边界反弹（桌面端同款）
        if (this.x <= 0 || this.x >= width) this.vx = -this.vx;
        if (this.y <= 0 || this.y >= height) this.vy = -this.vy;

        if (this.type === 'ink' && this.spread < this.maxSpread) {
          this.spread += 0.01;
        }
      }

      draw() {
        const pal = paletteRef.current;
        if (!pal) return;

        const base = this.getOpacity();

        if (this.type === 'ink') {
          const color = this.useAltColor ? pal.inkAlt : pal.ink;
          const alpha = base * (100 / 255);

          context.fillStyle = rgba(color, alpha);
          context.beginPath();
          context.arc(this.x, this.y, this.size + this.spread, 0, Math.PI * 2);
          context.fill();

          if (this.spread > 0.001) {
            context.fillStyle = rgba(color, base * (25 / 255));
            context.beginPath();
            context.arc(this.x, this.y, (this.size + this.spread) * 1.8, 0, Math.PI * 2);
            context.fill();
          }
          return;
        }

        if (this.type === 'paper') {
          const w = this.size;
          const h = this.size * this.widthRatio;
          const alpha = base * (70 / 255);

          context.save();
          context.translate(this.x, this.y);
          context.rotate((this.rotation * Math.PI) / 180);

          context.fillStyle = rgba(pal.paper, alpha);
          context.fillRect(-w / 2, -h / 2, w, h);

          context.strokeStyle = rgba(pal.border, base * (20 / 255));
          context.lineWidth = 0.5;
          context.strokeRect(-w / 2, -h / 2, w, h);

          context.restore();
          return;
        }

        // sparkle
        const twinkle = 0.2 + 0.8 * (0.5 + 0.5 * Math.sin(this.phase * 3));
        const alpha = base * twinkle * (180 / 255);

        context.fillStyle = rgba(pal.sparkle, alpha);
        context.beginPath();
        context.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        context.fill();

        context.fillStyle = rgba(pal.sparkle, base * twinkle * (30 / 255));
        context.beginPath();
        context.arc(this.x, this.y, this.size * 3, 0, Math.PI * 2);
        context.fill();

        if (alpha > 0.08) {
          context.strokeStyle = rgba(pal.sparkle, base * twinkle * (100 / 255));
          context.lineWidth = 0.5;
          const length = this.size * 4;
          context.beginPath();
          context.moveTo(this.x - length, this.y);
          context.lineTo(this.x + length, this.y);
          context.moveTo(this.x, this.y - length);
          context.lineTo(this.x, this.y + length);
          context.stroke();
        }
      }
    }

    const particles: Particle[] = [];
    const sparkleParticles: Particle[] = [];

    const init = () => {
      particles.length = 0;
      sparkleParticles.length = 0;

      const inkCount = lowPowerMode ? 8 : 15;
      const paperCount = lowPowerMode ? 4 : 8;
      const sparkleCount = lowPowerMode ? 10 : 20;

      for (let i = 0; i < inkCount; i++) {
        const p = new Particle('ink');
        particles.push(p);
      }
      for (let i = 0; i < paperCount; i++) {
        particles.push(new Particle('paper'));
      }
      for (let i = 0; i < sparkleCount; i++) {
        const p = new Particle('sparkle');
        particles.push(p);
        sparkleParticles.push(p);
      }
    };

    const drawConstellations = () => {
      const pal = paletteRef.current;
      if (!pal) return;

      // 星座连线：只连接 sparkle 粒子，降低计算量与“脏感”
      const maxDistance = lowPowerMode ? 120 : 150;
      const maxDistanceSq = maxDistance * maxDistance;
      const isDark = document.documentElement.classList.contains('dark');
      const alphaBase = (isDark ? 20 : 10) / 255;
      for (let i = 0; i < sparkleParticles.length; i++) {
        for (let j = i + 1; j < sparkleParticles.length; j++) {
          const a = sparkleParticles[i];
          const b = sparkleParticles[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const distSq = dx * dx + dy * dy;
          if (distSq > maxDistanceSq) continue;

          const dist = Math.sqrt(distSq);
          const alpha = alphaBase * (1 - dist / maxDistance);
          context.strokeStyle = rgba(pal.line, alpha);
          context.lineWidth = 0.5;
          context.beginPath();
          context.moveTo(a.x, a.y);
          context.lineTo(b.x, b.y);
          context.stroke();
        }
      }
    };

    const animate = (timestamp: number) => {
      // 如果标签页不在前台，降低无谓绘制（浏览器仍会降帧，但我们主动减少负载）
      if (!document.hidden && timestamp - lastDrawTime >= frameIntervalMs) {
        lastDrawTime = timestamp;
        context.clearRect(0, 0, width, height);
        for (const p of particles) {
          p.update();
        }
        if (!lowPowerMode) {
          drawConstellations();
        }
        for (const p of particles) {
          p.draw();
        }
      }
      animationFrameId = requestAnimationFrame(animate);
    };

    const observer = new MutationObserver(() => refreshPalette());
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class', 'style'] });

    window.addEventListener('resize', resize, { passive: true });
    resize();
    refreshPalette();
    init();
    animationFrameId = requestAnimationFrame(animate);

    return () => {
      window.removeEventListener('resize', resize);
      observer.disconnect();
      if (animationFrameId !== null) cancelAnimationFrame(animationFrameId);
    };
  }, []);

  // 视觉口径：浅色主题下粒子应更“淡”，避免玻璃态面板下整体偏暗；深色主题允许更明显
  return <canvas ref={canvasRef} className="fixed inset-0 pointer-events-none z-0 opacity-20 dark:opacity-50" />;
};
