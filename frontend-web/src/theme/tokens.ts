// src/theme/tokens.ts

export const THEME_TOKENS = {
  light: {
    // Organic Theme (from all_configs.json)
    colors: {
      primary: '#8B4513',
      primaryLight: '#A0522D',
      primaryDark: '#6B3410',
      accent: '#A0522D',
      text: {
        primary: '#2C1810',
        secondary: '#5D4037',
        tertiary: '#6D6560',
        placeholder: '#8D8580',
      },
      background: {
        primary: '#F9F5F0', // 米白
        secondary: '#FFFBF0',
        tertiary: '#F0EBE5',
        card: '#FFFBF0',
        glass: 'rgba(249, 245, 240, 0.85)',
      },
      border: {
        default: '#D7CCC8',
        light: '#E8E4DF',
      },
      semantic: {
        success: '#4a9f6e',
        error: '#A85448',
        warning: '#d4923a',
        info: '#4a8db3',
      }
    },
    shadows: {
      card: '0 4px 20px -2px rgba(139,69,19,0.08), 0 2px 8px -2px rgba(139,69,19,0.04)',
      glass: '0 8px 32px 0 rgba(139, 69, 19, 0.05)',
    }
  },
  dark: {
    // Academia Theme (from all_configs.json)
    colors: {
      primary: '#E89B6C', // 黄铜色
      primaryLight: '#F0B088',
      primaryDark: '#D4845A',
      accent: '#D4845A',
      text: {
        primary: '#E8DFD4', // 羊皮纸色
        secondary: '#9C8B7A',
        tertiary: '#7A6B5A',
        placeholder: '#5A4D40',
      },
      background: {
        primary: '#1C1714', // 深木色
        secondary: '#251E19',
        tertiary: '#3D332B',
        card: '#251E19',
        glass: 'rgba(37, 30, 25, 0.85)',
      },
      border: {
        default: '#4A3F35',
        light: '#3D332B',
      },
      semantic: {
        success: '#4a9f6e',
        error: '#A85448',
        warning: '#D4923A',
        info: '#4A8DB3',
      }
    },
    shadows: {
      card: '0 4px 20px -2px rgba(0,0,0,0.4), 0 2px 8px -2px rgba(0,0,0,0.2)',
      glass: '0 8px 32px 0 rgba(0, 0, 0, 0.4)',
    }
  }
};

export const TYPOGRAPHY = {
  fontFamily: {
    heading: '"Noto Serif SC", "Source Han Serif SC", serif',
    body: '"Noto Sans SC", "Source Han Sans SC", sans-serif',
  }
};