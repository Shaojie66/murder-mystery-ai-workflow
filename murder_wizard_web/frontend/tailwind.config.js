/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'mw-red': '#9B1C1C',
        'mw-gold': '#B45309',
        'mw-dark': '#12110F',
        'mw-surface': '#1C1917',
        'mw-border': '#3D3532',
        // Editorial palette
        'editorial': {
          'bg': '#12110F',
          'raised': '#1C1917',
          'elevated': '#292524',
          'cream': '#F5F0E8',
          'muted': '#A89F94',
          'faint': '#6B6460',
          'crimson': '#9B1C1C',
          'gold': '#B45309',
        },
      },
      fontFamily: {
        'serif': ['Playfair Display', 'Georgia', 'serif'],
        'body': ['Crimson Pro', 'Georgia', 'serif'],
        'mono': ['JetBrains Mono', 'Consolas', 'monospace'],
      },
      fontSize: {
        'display': ['clamp(2rem, 4vw, 3rem)', { lineHeight: '1.1', letterSpacing: '-0.02em' }],
        'headline': ['clamp(1.5rem, 3vw, 2rem)', { lineHeight: '1.2' }],
        'title': ['1.25rem', { lineHeight: '1.3' }],
        'body': ['1.0625rem', { lineHeight: '1.65' }],
        'small': ['0.875rem', { lineHeight: '1.5' }],
        'label': ['0.6875rem', { lineHeight: '1', letterSpacing: '0.1em' }],
      },
      spacing: {
        '18': '4.5rem',
        '22': '5.5rem',
      },
      borderRadius: {
        'none': '0',
        'sm': '2px',
        DEFAULT: '3px',
        'md': '4px',
        'lg': '6px',
      },
      boxShadow: {
        'editorial': '0 1px 3px rgba(0,0,0,0.4), 0 1px 2px rgba(0,0,0,0.3)',
        'elevated': '0 4px 12px rgba(0,0,0,0.5)',
      },
      transitionDuration: {
        '150': '150ms',
        '250': '250ms',
      },
    },
  },
  plugins: [],
}
