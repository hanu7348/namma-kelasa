/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./templates/**/*.html", "./jobs/**/*.py", "./accounts/**/*.py"],
  prefix: "tw-",
  corePlugins: { preflight: false },
  darkMode: ["class", '[data-bs-theme="dark"]'],
  theme: {
    extend: {
      colors: { brand: "#5b5cf0", aqua: "#39d9c3" },
    },
  },
  plugins: [],
};
