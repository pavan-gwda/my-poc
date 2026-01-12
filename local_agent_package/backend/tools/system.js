const { exec } = require("child_process");

module.exports = async function systemTool(command) {
  return new Promise(resolve => {
    exec(command, (err, stdout, stderr) => {
      if (err) return resolve({ tool: "system", success: false, error: stderr });
      resolve({ tool: "system", success: true, output: stdout });
    });
  });
};
