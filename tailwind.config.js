// tailwind.config.js
const colors = require('tailwindcss/colors');

module.exports = {
  darkMode: 'media',   // ⬅️ important: enables .dark class control
  content: [
    "./templates/**/*.html",
    "./static/js/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        primary: colors.amber,
        secondary: colors.slate,
        base: colors.zinc,
        muted: colors.zinc[400],
        textbase: colors.zinc[900],
        success: colors.green,
        warning: colors.amber,
        danger: colors.red,
        info: colors.blue,
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
};
