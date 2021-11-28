const CopyWebpackPlugin = require("copy-webpack-plugin");
const path = require("path");

module.exports = {
  mode: "development",
  entry: "./bootstrap.js",
  plugins: [
    new CopyWebpackPlugin({
      patterns: ["target/html/index.html"],
    }),
  ],
};
