const fs = require("fs").promises;
const path = require("path");

module.exports = async function fileTool(action, filePath, content = "") {
  const resolved = path.join(process.cwd(), "data", filePath);

  try {
    if (action === "read") {
      const data = await fs.readFile(resolved, "utf8");
      return { tool: "files", success: true, data };
    }
    if (action === "write") {
      await fs.writeFile(resolved, content, "utf8");
      return { tool: "files", success: true };
    }
    return { tool: "files", success: false, error: "unknown action" };
  } catch (e) {
    return { tool: "files", success: false, error: e.message };
  }
};
